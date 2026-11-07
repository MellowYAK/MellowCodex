"""One context service for authenticated HTTP, MCP, UI and task tools."""
import asyncio
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict
from ..i18n import catalog
from ..conversations import Conversations
from .service import ProjectContext

OPERATIONS=('overview','search','expand','related','refresh','annotate','recovery','import_apc')

class ContextRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    project_id:str=Field(min_length=1,max_length=64)
    query:str=Field(default='',max_length=500)
    ref:str=Field(default='',max_length=150)
    start:int=Field(default=1,ge=1)
    lines:int=Field(default=80,ge=1,le=200)
    limit:int=Field(default=10,ge=1,le=40)
    offset:int=Field(default=0,ge=0,le=10000)
    path:str=Field(default='',max_length=700)
    aliases:list[str]=Field(default_factory=list,max_length=40)
    tags:list[str]=Field(default_factory=list,max_length=40)
    notes:str=Field(default='',max_length=8000)
    must_not_break:list[str]=Field(default_factory=list,max_length=40)

def dispatch(service,operation,body):
    p=body.project_id
    if operation=='overview':return service.overview(p)
    if operation=='search':return service.search(p,body.query,body.limit,body.offset)
    if operation=='expand':return service.expand(p,body.ref,body.start,body.lines)
    if operation=='related':return service.related(p,body.ref)
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
    @routes.post('/api/project-index/register')
    async def register_index(body:Registration):
        return await asyncio.to_thread(Indexing(provider()).register,body.path,body.name)
    @routes.post('/api/project-index/settings')
    async def index_settings(body:IndexSettings):
        return Indexing(provider()).settings(body.project_id,body.enabled)
    @routes.get('/api/project-index/{project_id}')
    async def index_status(project_id:str):return Indexing(provider()).status(project_id)
    @routes.post('/api/context/{operation}')
    async def context_operation(operation:Literal['overview','search','expand','related','refresh','annotate','recovery','import_apc'],body:ContextRequest):
        return await asyncio.to_thread(dispatch,provider(),operation,body)
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
