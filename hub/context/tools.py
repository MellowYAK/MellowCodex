from ..i18n import t

def definitions(schema):
    string={'type':'string'}
    return [
        schema('project_brief',t('context.brief_tool'),{'query':string}),
        schema('project_index',t('context.local_index_tool'),{}),
        schema('project_index_status',t('context.local_status_tool'),{}),
        schema('project_index_settings',t('context.local_settings_tool'),{'enabled':{'type':'boolean'},'mode':{'type':'string','enum':['fast','apc_baseline']}},('enabled',)),
        schema('project_context',t('context.overview_tool'),{'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':40}}),
        schema('context_refresh',t('context.refresh_tool'),{}),
        schema('context_search',t('context.search_tool'),{'query':string,'limit':{'type':'integer','minimum':1,'maximum':40}},('query',)),
        schema('context_expand',t('context.expand_tool'),{'ref':string,'path':string,'start':{'type':'integer','minimum':1},'lines':{'type':'integer','minimum':1,'maximum':200}}),
        schema('context_related',t('context.related_tool'),{'ref':string,'path':string}),
        schema('context_annotate',t('context.annotate_tool'),{'path':string,'aliases':{'type':'array','items':string,'maxItems':40},'tags':{'type':'array','items':string,'maxItems':40},'notes':string,'must_not_break':{'type':'array','items':string,'maxItems':40}},('path',)),
        schema('recovery_context',t('context.recovery_tool'),{})]

def register_mcp(mcp,local,read,write):
    async def observed(chat_id, project_id, operation, path, data=None, timeout=15):
        import uuid
        request_id=uuid.uuid4().hex
        endpoint='/api/chats/'+chat_id+'/mcp-observation'
        await local(endpoint,dict(project_id=project_id,request_id=request_id,operation=operation,phase='started',payload=data or {}))
        try:
            result=await local(path,data,timeout=timeout)
        except Exception as exc:
            await local(endpoint,dict(project_id=project_id,request_id=request_id,operation=operation,phase='failed',payload={'error':str(exc)}))
            raise
        await local(endpoint,dict(project_id=project_id,request_id=request_id,operation=operation,phase='completed',payload=result))
        return result

    @mcp.tool(description=t('context.brief_tool'),annotations=read)
    async def project_brief(project_id:str,chat_id:str,query:str=''):
        return await observed(chat_id,project_id,'project_brief','/api/context/brief',dict(project_id=project_id,query=query))
    @mcp.tool(description=t('context.register_tool'),annotations=write)
    async def project_index(path:str,name:str|None=None):
        return await local('/api/project-index/register',dict(path=path,name=name))
    @mcp.tool(description=t('context.index_status_tool'),annotations=read)
    async def project_index_status(project_id:str,chat_id:str):return await observed(chat_id,project_id,'project_index_status','/api/project-index/'+project_id)
    @mcp.tool(description=t('context.index_settings_tool'),annotations=write)
    async def project_index_settings(project_id:str,chat_id:str,enabled:bool=True,mode:str|None=None):
        return await observed(chat_id,project_id,'project_index_settings','/api/project-index/settings',dict(project_id=project_id,enabled=enabled,mode=mode))
    @mcp.tool(description=t('context.overview_tool'),annotations=read)
    async def project_context(project_id:str,chat_id:str,offset:int=0,limit:int=10):return await observed(chat_id,project_id,'project_context','/api/context/overview',dict(project_id=project_id,offset=offset,limit=limit))
    @mcp.tool(description=t('context.search_tool'),annotations=read)
    async def context_search(project_id:str,chat_id:str,query:str,limit:int=10,offset:int=0):
        return await observed(chat_id,project_id,'context_search','/api/context/search',dict(project_id=project_id,query=query,limit=limit,offset=offset))
    @mcp.tool(description=t('context.expand_tool'),annotations=read)
    async def context_expand(project_id:str,chat_id:str,ref:str='',start:int=1,lines:int=80,path:str=''):
        return await observed(chat_id,project_id,'context_expand','/api/context/expand',dict(project_id=project_id,ref=ref,path=path,start=start,lines=lines))
    @mcp.tool(description=t('context.related_tool'),annotations=read)
    async def context_related(project_id:str,chat_id:str,ref:str='',path:str=''):return await observed(chat_id,project_id,'context_related','/api/context/related',dict(project_id=project_id,ref=ref,path=path))
    @mcp.tool(description=t('context.refresh_tool'),annotations=write)
    async def context_refresh(project_id:str,chat_id:str):return await observed(chat_id,project_id,'context_refresh','/api/context/refresh',dict(project_id=project_id),timeout=120)
    @mcp.tool(description=t('context.annotate_tool'),annotations=write)
    async def context_annotate(project_id:str,chat_id:str,path:str,aliases:list[str]|None=None,tags:list[str]|None=None,notes:str='',must_not_break:list[str]|None=None):
        return await observed(chat_id,project_id,'context_annotate','/api/context/annotate',dict(project_id=project_id,path=path,aliases=aliases or [],tags=tags or [],notes=notes,must_not_break=must_not_break or []))
    @mcp.tool(description=t('context.recovery_tool'),annotations=read)
    async def recovery_context(project_id:str,chat_id:str):return await observed(chat_id,project_id,'recovery_context','/api/context/recovery',dict(project_id=project_id))
    @mcp.tool(description=t('context.import_tool'),annotations=write)
    async def context_import_apc(project_id:str,chat_id:str,path:str):return await observed(chat_id,project_id,'context_import_apc','/api/context/import_apc',dict(project_id=project_id,path=path),timeout=120)
