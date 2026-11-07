"""Authenticated Hub routes shared by MCP and the development interface."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .contracts import PatchProposal

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

class RepairRequest(TestRequest):
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
        return await dev.repair(task,body.candidate_id,body.revision,body.paths,body.tests,body.model)
    return routes
