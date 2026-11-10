"""UI and MCP share these schemas and persistent service."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .delegation import Delegation, Profile

class Start(BaseModel):
    chat_id:str
    request_id:str=Field(min_length=8,max_length=200)
    objective:str=Field(min_length=1,max_length=8000)
    director_id:str

class Update(BaseModel):
    revision:int=Field(ge=0)
    action:str
    payload:dict=Field(default_factory=dict)

class Dispatch(BaseModel):
    revision:int=Field(ge=0)
    instruction:str=Field(min_length=1,max_length=8000)
    allowed_tools:list[str]=Field(min_length=1,max_length=20)
    exact_patch:dict|None=None
    context_read:dict|None=None

def router(store,engine):
    r=APIRouter(prefix='/api/delegation')
    svc=Delegation(store)
    @r.get('/labels')
    async def labels(language:str='he'):
        from .i18n import catalog
        return {k.split('.',1)[1]:v for k,v in catalog(language).items() if k.startswith('delegation.')}
    @r.get('/catalog')
    async def catalog():return svc.catalog()
    @r.get('/profiles')
    async def profiles():return {'items':svc.profiles()}
    @r.post('/profiles')
    async def save(body:Profile):return svc.save_profile(body.model_dump())
    @r.get('/runs')
    async def runs(chat_id:str):return {'items':svc.list(chat_id)}
    @r.post('/runs')
    async def start(body:Start):return svc.start(**body.model_dump())
    @r.get('/runs/{run_id}')
    async def status(run_id:str):return svc.status(run_id)
    @r.post('/runs/{run_id}')
    async def update(run_id:str,body:Update):return svc.update(run_id,**body.model_dump())
    @r.post('/runs/{run_id}/dispatch')
    async def dispatch(run_id:str,body:Dispatch):
        task=svc.dispatch(run_id,**body.model_dump())
        if task['state']=='queued':engine.enqueue(task['id'])
        return svc.status(run_id)
    @r.post('/runs/{run_id}/workers')
    async def workers(run_id:str):return await svc.run_workers(run_id)
    return r

def register_mcp(mcp,local,read,write):
    @mcp.tool(annotations=read)
    async def delegation_catalog():
        """List provider identities and transport limitations. A catalog entry is NOT a working connection. External MCP/PLAY clients are directors or workers; API workers use explicitly configured OpenAI-compatible endpoints, not automatic provider-specific adapters."""
        return await local('/api/delegation/catalog')
    @mcp.tool(annotations=read)
    async def delegation_profiles():
        """Read saved director/worker profiles shared with the UI."""
        return await local('/api/delegation/profiles')
    @mcp.tool(annotations=write)
    async def delegation_profile_save(id:str,provider:str,name:str,model:str='',transport:str='mcp',endpoint:str='',key_env:str=''):
        """Save a named model profile for future delegation runs. transport mcp, play or api. API requires model and endpoint; key_env is an environment-variable NAME, never a secret. Does not authenticate or launch a provider. Existing runs retain their selected profiles."""
        return await local('/api/delegation/profiles',dict(id=id,provider=provider,name=name,model=model,transport=transport,endpoint=endpoint,key_env=key_env))
    @mcp.tool(annotations=write)
    async def delegation_run_workers(run_id:str):
        """Run up to three eligible OpenAI-compatible API workers concurrently, returning proposals for director review. No tools, file writes or automatic approval. Only explicitly configured endpoints/models; key_env names a server environment variable, never send a secret here. MCP/PLAY workers require their external client and are not invoked by this API batch. Failed workers require explicit retry; no silent fallback."""
        return await local('/api/delegation/runs/'+run_id+'/workers',{},timeout=140)
    @mcp.tool(annotations=write)
    async def delegation_start(chat_id:str,request_id:str,objective:str,director_id:str):
        """Start director-controlled work in an EXISTING chat. Stable request_id prevents duplicates. Assign bounded workers, obtain their outputs and review them before dispatching exact implementation. Does not start autonomous provider sessions."""
        return await local('/api/delegation/runs',dict(chat_id=chat_id,request_id=request_id,objective=objective,director_id=director_id))
    @mcp.tool(annotations=read)
    async def delegation_status(run_id:str):
        """Read current revision, worker outputs, dependencies, director decisions and local execution evidence before the next step."""
        return await local('/api/delegation/runs/'+run_id)
    @mcp.tool(annotations=write)
    async def delegation_update(run_id:str,revision:int,action:str,payload:dict):
        """Advance external director workflow. assign payload: worker {id,provider,name,model,transport}, instruction, dependencies [worker IDs]. result: worker_id,result (actual worker output only). review: worker_id,decision approved/changes_requested/rejected,feedback. retry: worker_id,feedback for failed workers. cancel before execution. complete only after standard task review approved local execution. Read revision first; stale updates are rejected. Workers receive proposals-only assignments, never direct file writes."""
        return await local('/api/delegation/runs/'+run_id,dict(revision=revision,action=action,payload=payload))
    @mcp.tool(annotations=write)
    async def delegation_dispatch(run_id:str,revision:int,instruction:str,allowed_tools:list[str],exact_patch:dict|None=None,context_read:dict|None=None):
        """Director dispatches reviewed instructions through the LOCAL RUNNER. Requires all workers approved. Supply exactly one existing Guidance exact_patch or context_read contract; no local-model rewriting. Poll execution task, inspect evidence then use standard task review before completing delegation. Candidate patches do not deploy production."""
        return await local('/api/delegation/runs/'+run_id+'/dispatch',dict(revision=revision,instruction=instruction,allowed_tools=allowed_tools,exact_patch=exact_patch,context_read=context_read))
