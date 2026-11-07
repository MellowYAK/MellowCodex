"""Shared schemas for development actions; same candidate service for all callers."""
from ..i18n import t

def register_mcp(mcp,local,read,write):
    @mcp.tool(annotations=write)
    async def task_request_changes(task_id:str,expected_revision:int,reason:str):
        """Return an evidence-based correction to the SAME waiting_review task and resume its runner. Read get_task first and pass its exact revision. Preserve the original objective and existing guidance/tool restrictions. This requests changes, never approves completion or deployment. If the response is lost, read the same task before retrying; a stale revision must not create a duplicate task. For structured source/tool constraints submit task_guide before this call."""
        import re
        if not re.fullmatch('[a-f0-9]{32}',task_id):raise ValueError('Invalid task ID')
        if expected_revision<0 or not reason.strip() or len(reason)>10000:raise ValueError('Invalid correction')
        return await local('/api/tasks/'+task_id+'/review',dict(decision='request_changes',expected_revision=expected_revision,reason=reason))
    @mcp.tool(description=t('development.read_tool'),annotations=read)
    async def candidate_read(task_id:str,candidate_id:str,paths:list[str],start:int=1,max_lines:int=80):
        return await local('/api/development/read',dict(task_id=task_id,candidate_id=candidate_id,paths=paths,start=start,max_lines=max_lines))
    @mcp.tool(description=t('development.release_tool'),annotations=write)
    async def candidate_stage_release(task_id:str,candidate_id:str,revision:int):
        return await local('/api/development/release',dict(task_id=task_id,candidate_id=candidate_id,revision=revision),timeout=120)
    @mcp.tool(description=t('upgrade.status_tool'),annotations=read)
    async def upgrade_status():return await local('/api/upgrades/status')
    @mcp.tool(description=t('upgrade.activate_tool'),annotations=write)
    async def upgrade_activate(release_id:str,request_id:str):return await local('/api/upgrades/activate',dict(release_id=release_id,request_id=request_id))
    @mcp.tool(description=t('upgrade.recover_tool'),annotations=write)
    async def upgrade_recover(request_id:str):return await local('/api/upgrades/recover',dict(request_id=request_id))
    @mcp.tool(description=t('development.repair_tool'),annotations=write)
    async def candidate_repair(task_id:str,candidate_id:str,revision:int,paths:list[str],tests:list[str],model:str|None=None):
        return await local('/api/development/repair',dict(task_id=task_id,candidate_id=candidate_id,revision=revision,paths=paths,tests=tests,model=model),timeout=740)
    @mcp.tool(description=t('development.git_status_tool'),annotations=read)
    async def project_git_status(task_id:str):
        return await local('/api/development/git/status',{'task_id':task_id})
    @mcp.tool(description=t('development.list_tool'),annotations=read)
    async def candidate_list(task_id:str):
        return await local('/api/development/list',{'task_id':task_id})
    @mcp.tool(description=t('development.guidance_status_tool'),annotations=read)
    async def task_guidance_status(task_id:str):
        return await local('/api/development/guidance/status',{'task_id':task_id})
    @mcp.tool(description=t('development.guide_tool'),annotations=write)
    async def task_guide(task_id:str,expected_task_revision:int,expected_revision:int,consumer_epoch:str,request_id:str,text:str,required_tools:list[str]|None=None,required_sources:list[dict]|None=None,allowed_tools:list[str]|None=None,evidence_only:bool=False,exact_patch:dict|None=None,context_read:dict|None=None):
        return await local('/api/development/guidance',dict(task_id=task_id,expected_task_revision=expected_task_revision,expected_revision=expected_revision,consumer_epoch=consumer_epoch,request_id=request_id,text=text,required_tools=required_tools or [],required_sources=required_sources or [],allowed_tools=allowed_tools,evidence_only=evidence_only,exact_patch=exact_patch,context_read=context_read))
    @mcp.tool(description=t('development.diff_tool'),annotations=read)
    async def candidate_diff(task_id:str,candidate_id:str):
        return await local('/api/development/diff',dict(task_id=task_id,candidate_id=candidate_id))
    @mcp.tool(description=t('development.create_tool'),annotations=write)
    async def candidate_create(task_id:str):
        return await local('/api/development/create',{'task_id':task_id},timeout=120)
    @mcp.tool(description=t('development.inspect_tool'),annotations=read)
    async def candidate_inspect(task_id:str,candidate_id:str):
        return await local('/api/development/inspect',dict(task_id=task_id,candidate_id=candidate_id))
    @mcp.tool(description=t('development.patch_tool'),annotations=write)
    async def candidate_patch(task_id:str,candidate_id:str,expected_revision:int,changes:list[dict]):
        return await local('/api/development/patch',dict(task_id=task_id,candidate_id=candidate_id,expected_revision=expected_revision,changes=changes),timeout=120)
    @mcp.tool(description=t('development.test_tool'),annotations=write)
    async def candidate_test(task_id:str,candidate_id:str,revision:int,tests:list[str],timeout:int=120):
        if not 1<=timeout<=300:raise ValueError('Timeout must be 1–300 seconds')
        return await local('/api/development/test',dict(task_id=task_id,candidate_id=candidate_id,revision=revision,tests=tests,timeout=timeout),timeout=timeout+15)

def definitions(schema):
    string={'type':'string'}
    change={'type':'object','additionalProperties':False,'properties':{'path':string,'base_hash':{'type':['string','null']},'content':string},'required':['path','base_hash','content']}
    return [
        schema('candidate_read',t('development.read_tool'),{'candidate_id':string,'paths':{'type':'array','items':string,'minItems':1,'maxItems':10},'start':{'type':'integer','minimum':1},'max_lines':{'type':'integer','minimum':1,'maximum':200}},('candidate_id','paths')),
        schema('candidate_stage_release',t('development.release_tool'),{'candidate_id':string,'revision':{'type':'integer','minimum':0}},('candidate_id','revision')),
        schema('upgrade_status',t('upgrade.status_tool'),{}),
        schema('upgrade_activate',t('upgrade.activate_tool'),{'release_id':string,'request_id':string},('release_id','request_id')),
        schema('upgrade_recover',t('upgrade.recover_tool'),{'request_id':string},('request_id',)),
        schema('candidate_repair',t('development.repair_tool'),{'candidate_id':string,'revision':{'type':'integer','minimum':0},'paths':{'type':'array','items':string,'minItems':1,'maxItems':10},'tests':{'type':'array','items':string,'minItems':1,'maxItems':30},'model':string},('candidate_id','revision','paths','tests')),
        schema('candidate_create',t('development.create_tool'),{}),
        schema('project_git_status',t('development.git_status_tool'),{}),
        schema('candidate_diff',t('development.diff_tool'),{'candidate_id':string},('candidate_id',)),
        schema('candidate_test',t('development.test_tool'),{'candidate_id':string,'revision':{'type':'integer','minimum':0},'tests':{'type':'array','items':string,'minItems':1,'maxItems':30},'timeout':{'type':'integer','minimum':1,'maximum':300}},('candidate_id','revision','tests')),
        schema('candidate_inspect',t('development.inspect_tool'),{'candidate_id':string},('candidate_id',)),
        schema('candidate_patch',t('development.patch_tool'),{'candidate_id':string,'expected_revision':{'type':'integer','minimum':0},'changes':{'type':'array','items':change,'minItems':1,'maxItems':50}},('candidate_id','expected_revision','changes'))]
