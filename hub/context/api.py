"""One context service for authenticated HTTP, MCP, UI and task tools."""
import asyncio
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict
from ..i18n import catalog
from ..conversations import Conversations
from .service import ProjectContext

OPERATIONS=('brief','overview','search','expand','related','refresh','annotate','recovery','import_apc')

class ContextRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    project_id:str=Field(min_length=1,max_length=64)
    query:str=Field(default='',max_length=500)
    ref:str=Field(default='',max_length=700)
    start:int=Field(default=1,ge=1)
    lines:int=Field(default=80,ge=1,le=200)
    limit:int=Field(default=10,ge=1,le=40)
    offset:int=Field(default=0,ge=0,le=10000)
    path:str=Field(default='',max_length=700)
    aliases:list[str]=Field(default_factory=list,max_length=40)
    tags:list[str]=Field(default_factory=list,max_length=40)
    notes:str=Field(default='',max_length=8000)
    must_not_break:list[str]=Field(default_factory=list,max_length=40)

def dispatch(service,operation,body,origin='runner'):
    from .indexing import Indexing
    import json,time,uuid
    started=time.monotonic()
    with Indexing(service).exclusive(body.project_id):
        result=_dispatch(service,operation,body)
    # Keep retrieval receipts, not duplicated source text or model conclusions.
    receipt={'id':uuid.uuid4().hex,'at':time.time(),'project_id':body.project_id,
             'operation':operation,'origin':origin,'path':body.path,'ref':body.ref,
             'query':body.query,'start':body.start,'lines':body.lines,
             'elapsed_ms':round((time.monotonic()-started)*1000),
             'source_ref':result.get('ref') if isinstance(result,dict) else None}
    with service.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS context_access(id TEXT PRIMARY KEY,project TEXT,at REAL,receipt TEXT)')
        db.execute('INSERT INTO context_access VALUES(?,?,?,?)',(receipt['id'],body.project_id,receipt['at'],json.dumps(receipt)))
    return result

def _dispatch(service,operation,body):
    p=body.project_id
    from .indexing import Indexing
    service=Indexing(service).selected(p)
    if operation=='brief':
        from .brief import project_brief
        return project_brief(service,p,body.query)
    if operation=='overview':
        from .fast import FastContext
        return service.overview(p,body.offset,body.limit) if isinstance(service,FastContext) else service.overview(p)
    if operation=='search':return service.search(p,body.query,body.limit,body.offset)
    if operation in ('expand','related'):
        if not body.ref and not body.path:raise ValueError('Provide a source ref or indexed relative path')
        if body.ref and body.path and service.row(p,body.ref)['path']!=body.path:
            raise ValueError('Source ref and path identify different files; use the matching indexed source')
        source=body.ref or body.path
        if operation=='expand':return service.expand(p,source,body.start,body.lines)
        return service.related(p,source)
    if operation=='refresh':return service.refresh(p)
    if operation=='recovery':return service.recovery(p)
    if operation=='import_apc':return service.import_apc(p,body.path)
    return service.annotate(p,body.path,body.aliases,body.tags,body.notes,body.must_not_break)

def router(provider):
    routes=APIRouter()
    from .indexing import Indexing
    class Registration(BaseModel):
        path:str=Field(min_length=1,max_length=700)
        name:str|None=Field(default=None,max_length=160)
    class IndexSettings(BaseModel):
        project_id:str
        enabled:bool=True
        mode:Literal['fast','apc_baseline']|None=None
    @routes.post('/api/project-index/register')
    async def register_index(body:Registration):
        return await asyncio.to_thread(Indexing(provider()).register,body.path,body.name)
    @routes.post('/api/project-index/settings')
    async def index_settings(body:IndexSettings):
        return await asyncio.to_thread(Indexing(provider()).settings,body.project_id,body.enabled,body.mode)
    @routes.get('/api/project-index/{project_id}')
    async def index_status(project_id:str):return Indexing(provider()).status(project_id)
    @routes.post('/api/context/{operation}')
    async def context_operation(operation:Literal['brief','overview','search','expand','related','refresh','annotate','recovery','import_apc'],body:ContextRequest):
        return await asyncio.to_thread(dispatch,provider(),operation,body,'http')
    @routes.get('/api/context/catalog/{language}')
    async def context_catalog(language:Literal['en','he','ru']):
        return catalog(language)
    return routes

def service_for_task(task,store=None):
    from ..config import STATE
    from ..store import Store
    store=store or Store(STATE/'hub.sqlite3')
    conversations=Conversations(store)
    project=conversations.project(task['workspace'])
    return ProjectContext(store.path.parent,conversations),project['id']
