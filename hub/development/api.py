"""Authenticated Hub routes shared by MCP and the development interface."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .contracts import PatchProposal
from .guidance import SourceRequirement, ContextRead

class TaskRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    task_id:str=Field(pattern='^[a-f0-9]{32}$')

class CandidateRequest(TaskRequest):
    candidate_id:str=Field(pattern='^[a-f0-9]{32}$')

class PatchRequest(PatchProposal):
    task_id:str=Field(pattern='^[a-f0-9]{32}$')

class TestRequest(CandidateRequest):
    revision:int=Field(ge=0)
    tests:list[str]=Field(min_length=1,max_length=30)
    timeout:int=Field(default=120,ge=1,le=300)

class GuidanceRequest(TaskRequest):
    expected_task_revision:int=Field(ge=0)
    expected_revision:int=Field(ge=0)
    consumer_epoch:str=Field(max_length=32)
    request_id:str=Field(min_length=1,max_length=100)
    text:str=Field(min_length=1,max_length=8000)
    required_tools:list[str]=Field(default_factory=list,max_length=20)
    required_sources:list[SourceRequirement]=Field(default_factory=list,max_length=20)
    allowed_tools:list[str]|None=Field(default=None,max_length=200)
    evidence_only:bool=Field(default=False,strict=True)
    exact_patch:PatchProposal|None=None
    context_read:ContextRead|None=None

class RepairRequest(TestRequest):
    max_attempts:int=Field(default=1,ge=1,le=3,strict=True)
    paths:list[str]=Field(min_length=1,max_length=10)
    model:str|None=Field(default=None,max_length=160)

def router(provider):
    routes=APIRouter(prefix='/api/development')
    def bound(body):
        dev=provider()
        try:task=dev.store.get(body.task_id)
        except KeyError:raise HTTPException(404,'Task not found')
        if task['mode'] not in ('code','desktop'):raise HTTPException(409,'Development requires a code or desktop task')
        return dev,task
    @routes.post('/guidance/status')
    async def guidance_status(body:TaskRequest):
        from .guidance import Guidance
        dev,task=bound(body)
        return await asyncio.to_thread(Guidance(dev.store).status,task['id'])
    @routes.post('/guidance')
    async def guidance(body:GuidanceRequest):
        from .guidance import Guidance
        dev,task=bound(body)
        return await asyncio.to_thread(Guidance(dev.store).submit,**body.model_dump())
    @routes.post('/create')
    async def create(body:TaskRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.create,task)
    @routes.post('/git/status')
    async def git_status(body:TaskRequest):
        from .git import status
        dev,task=bound(body)
        return await asyncio.to_thread(status,task['workspace'])
    @routes.post('/list')
    async def candidates(body:TaskRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.list,task)
    @routes.post('/inspect')
    async def inspect(body:CandidateRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.inspect,task,body.candidate_id)
    class ReadRequest(CandidateRequest):
        paths:list[str]=Field(min_length=1,max_length=10)
        start:int=Field(default=1,ge=1)
        max_lines:int=Field(default=80,ge=1,le=200)
    @routes.post('/read')
    async def read(body:ReadRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.read,task,body.candidate_id,body.paths,body.start,body.max_lines)
    @routes.post('/patch')
    async def patch(body:PatchRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.patch,task,body.model_dump(exclude={'task_id'}))
    @routes.post('/diff')
    async def diff(body:CandidateRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.diff,task,body.candidate_id)
    class ReleaseRequest(CandidateRequest):
        revision:int=Field(ge=0)
    @routes.post('/release')
    async def release(body:ReleaseRequest):
        dev,task=bound(body)
        return await asyncio.to_thread(dev.stage_release,task,body.candidate_id,body.revision)
    @routes.post('/test')
    async def test(body:TestRequest):
        dev,task=bound(body)
        return await dev.test(task,body.candidate_id,body.revision,body.tests,body.timeout)
    @routes.post('/repair')
    async def repair(body:RepairRequest):
        dev,task=bound(body)
        return await dev.repair(task,body.candidate_id,body.revision,body.paths,body.tests,body.model,body.max_attempts)
    @routes.post('/selfdevelop/close-failed')
    async def close_failed_selfdevelop(body:dict):
        from .selfdevelop import SelfDevelop
        required=('chat_id','task_id','expected_revision','request_id','reason')
        if set(body)!=set(required):
            raise ValueError('Exact closure fields are required')
        dev=provider()
        return await asyncio.to_thread(SelfDevelop(dev.store).close_failed,
                 body['chat_id'],body['task_id'],body['expected_revision'],
                 body['request_id'],body['reason'])
    class ObjectiveRun(BaseModel):
        model_config=ConfigDict(extra='forbid')
        chat_id:str=Field(pattern='^[a-f0-9]{32}$')
        task_id:str=Field(pattern='^[a-f0-9]{32}$')
        request_id:str=Field(min_length=8,max_length=100)
        paths:list[str]=Field(min_length=1,max_length=10)
        tests:list[str]=Field(min_length=1,max_length=30)
        model:str|None=Field(default=None,max_length=160)
        max_attempts:int=Field(default=1,ge=1,le=3,strict=True)
        director_mode:str='gpt'
        deploy_after_review:bool=False

    @routes.post('/selfdevelop/objective/run')
    async def objective_run(body:ObjectiveRun):
        from .selfdevelop import SelfDevelop
        dev=provider()
        return await asyncio.to_thread(SelfDevelop(dev.store).authorize_objective,
            body.chat_id,body.task_id,body.request_id,body.paths,body.tests,
            body.model,body.max_attempts,body.director_mode,body.deploy_after_review)

    class ObjectiveRecovery(BaseModel):
        model_config=ConfigDict(extra='forbid')
        chat_id:str=Field(pattern='^[a-f0-9]{32}$')
        request_id:str=Field(min_length=8,max_length=100)
        mode:str=Field(pattern='^(narrow|exact)$')
        reason:str=Field(min_length=1,max_length=1000)
        expected_candidate_revision:int=Field(ge=0,strict=True)
        paths:list[str]|None=Field(default=None,min_length=1,max_length=10)
        tests:list[str]|None=Field(default=None,min_length=1,max_length=30)

    @routes.post('/selfdevelop/objective/recover')
    async def objective_recover(body:ObjectiveRecovery):
        """GPT-requested same-chat recovery. Never infer semantic approval."""
        from .selfdevelop import SelfDevelop
        dev=provider()
        return await SelfDevelop(dev.store).recover_objective(
            body.chat_id,body.request_id,body.mode,body.reason,dev,
            body.expected_candidate_revision,body.paths,body.tests)

    @routes.get('/selfdevelop/objective/{chat_id}')
    async def objective_status(chat_id:str):
        from .selfdevelop import SelfDevelop
        dev=provider()
        return await asyncio.to_thread(SelfDevelop(dev.store).objective_status,chat_id)

    @routes.post('/control-plane/prepare')
    async def prepare_control_plane(body:ReleaseRequest):
        from ..guardian.control_plane_jobs import ControlPlaneJobs
        from ..config import ROOT
        dev,task=bound(body)
        return await asyncio.to_thread(ControlPlaneJobs(ROOT).prepare,dev,task,body.candidate_id,body.revision)
    class ControlPlaneActivation(BaseModel):
        model_config=ConfigDict(extra='forbid')
        update_id:str=Field(pattern='^[a-f0-9]{32}$')
        request_id:str=Field(min_length=8,max_length=100)
        recover:bool=False
    @routes.post('/control-plane/activate')
    async def activate_control_plane(body:ControlPlaneActivation):
        from ..guardian.control_plane_jobs import ControlPlaneJobs
        from ..config import ROOT
        return await asyncio.to_thread(ControlPlaneJobs(ROOT).submit,body.update_id,body.request_id,body.recover)
    @routes.get('/control-plane/status/{update_id}')
    async def control_plane_status(update_id:str):
        from ..guardian.control_plane_jobs import ControlPlaneJobs
        from ..config import ROOT
        return await asyncio.to_thread(ControlPlaneJobs(ROOT).status,update_id)
    return routes
