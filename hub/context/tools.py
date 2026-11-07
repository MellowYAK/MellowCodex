from ..i18n import t

def definitions(schema):
    string={'type':'string'}
    return [
        schema('project_index',t('context.local_index_tool'),{}),
        schema('project_index_status',t('context.local_status_tool'),{}),
        schema('project_index_settings',t('context.local_settings_tool'),{'enabled':{'type':'boolean'}},('enabled',)),
        schema('project_context',t('context.overview_tool'),{}),
        schema('context_refresh',t('context.refresh_tool'),{}),
        schema('context_search',t('context.search_tool'),{'query':string,'limit':{'type':'integer','minimum':1,'maximum':40}},('query',)),
        schema('context_expand',t('context.expand_tool'),{'ref':string,'start':{'type':'integer','minimum':1},'lines':{'type':'integer','minimum':1,'maximum':200}},('ref',)),
        schema('context_related',t('context.related_tool'),{'ref':string},('ref',)),
        schema('context_annotate',t('context.annotate_tool'),{'path':string,'aliases':{'type':'array','items':string,'maxItems':40},'tags':{'type':'array','items':string,'maxItems':40},'notes':string,'must_not_break':{'type':'array','items':string,'maxItems':40}},('path',)),
        schema('recovery_context',t('context.recovery_tool'),{})]

def register_mcp(mcp,local,read,write):
    @mcp.tool(description=t('context.register_tool'),annotations=write)
    async def project_index(path:str,name:str|None=None):
        return await local('/api/project-index/register',dict(path=path,name=name))
    @mcp.tool(description=t('context.index_status_tool'),annotations=read)
    async def project_index_status(project_id:str):return await local('/api/project-index/'+project_id)
    @mcp.tool(description=t('context.index_settings_tool'),annotations=write)
    async def project_index_settings(project_id:str,enabled:bool=True):
        return await local('/api/project-index/settings',dict(project_id=project_id,enabled=enabled))
    @mcp.tool(description=t('context.overview_tool'),annotations=read)
    async def project_context(project_id:str):return await local('/api/context/overview',{'project_id':project_id})
    @mcp.tool(description=t('context.search_tool'),annotations=read)
    async def context_search(project_id:str,query:str,limit:int=10,offset:int=0):
        return await local('/api/context/search',dict(project_id=project_id,query=query,limit=limit,offset=offset))
    @mcp.tool(description=t('context.expand_tool'),annotations=read)
    async def context_expand(project_id:str,ref:str,start:int=1,lines:int=80):
        return await local('/api/context/expand',dict(project_id=project_id,ref=ref,start=start,lines=lines))
    @mcp.tool(description=t('context.related_tool'),annotations=read)
    async def context_related(project_id:str,ref:str):return await local('/api/context/related',dict(project_id=project_id,ref=ref))
    @mcp.tool(description=t('context.refresh_tool'),annotations=write)
    async def context_refresh(project_id:str):return await local('/api/context/refresh',dict(project_id=project_id),timeout=120)
    @mcp.tool(description=t('context.annotate_tool'),annotations=write)
    async def context_annotate(project_id:str,path:str,aliases:list[str]|None=None,tags:list[str]|None=None,notes:str='',must_not_break:list[str]|None=None):
        return await local('/api/context/annotate',dict(project_id=project_id,path=path,aliases=aliases or [],tags=tags or [],notes=notes,must_not_break=must_not_break or []))
    @mcp.tool(description=t('context.recovery_tool'),annotations=read)
    async def recovery_context(project_id:str):return await local('/api/context/recovery',dict(project_id=project_id))
    @mcp.tool(description=t('context.import_tool'),annotations=write)
    async def context_import_apc(project_id:str,path:str):return await local('/api/context/import_apc',dict(project_id=project_id,path=path),timeout=120)
