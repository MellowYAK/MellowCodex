"""Shared schemas for development actions; same candidate service for all callers."""
from ..i18n import t

def register_mcp(mcp,local,read,write):
    @mcp.tool(annotations=write)
    async def selfdevelop_prepare_update(task_id:str,candidate_id:str,revision:int):
        """Prepare an independent Hub/MCP update from a tested SelfDevelop candidate. Copies changed files, previous-file backups and supervisor outside live code. Does not stop services or activate. Inspect result and ensure all work is idle before explicitly activating."""
        return await local('/api/development/control-plane/prepare',dict(task_id=task_id,candidate_id=candidate_id,revision=revision),timeout=120)
    @mcp.tool(annotations=read)
    async def selfdevelop_update_status(update_id:str):
        """Read persistent control-plane update journal and supervisor liveness after reconnecting. ACTIVE_VERIFIED means new Hub/MCP health; ROLLED_BACK means old files restored. RECOVERY_REQUIRED is not success."""
        return await local('/api/development/control-plane/status/'+update_id)
    @mcp.tool(annotations=write)
    async def selfdevelop_activate_update(update_id:str,request_id:str,recover:bool=False):
        """Explicitly activate a previously prepared update for the user's authorized self-upgrade, or recover an interrupted update. Requires idle tasks. Independent supervisor restarts owned Hub/MCP only and restores changed files if health fails. Connection may disconnect: retain update_id and poll after reconnecting. Stable request_id prevents duplicate launch. Does not change dependencies, restore task DB, or update desktop process."""
        return await local('/api/development/control-plane/activate',dict(update_id=update_id,request_id=request_id,recover=recover))

    @mcp.tool(annotations=write)
    async def selfdevelop_start(objective:str,conversation_key:str,transport:str='mcp'):
        """Start MellowCodex SelfDevelop on explicit user request to repair/improve the agent itself. Retain one conversation_key and returned chat_id. External GPT is director; local executor waits for bounded instructions and returns evidence for review. No autonomous next step. Session creation does not deploy anything. Explicit selfdevelop_prepare_update/activate_update/status tools use Mellow Guard for owned Hub/MCP updates. transport is mcp or play, not proof of a connected director."""
        return await local('/api/selfdevelop/start',dict(objective=objective,conversation_key=conversation_key,transport=transport))
    @mcp.tool(annotations=read)
    async def selfdevelop_status(chat_id:str):
        """Read persistent SelfDevelop objective, current step and deployment limitations after reconnecting."""
        return await local('/api/selfdevelop/'+chat_id)
    @mcp.tool(annotations=write)
    async def selfdevelop_review(chat_id:str,expected_revision:int,decision:str,reason:str):
        """External director reviews the current SelfDevelop step after inspecting its recorded actions and diff/tests. decision: approve, request_changes, reject. Approval is checked against actual verification evidence; it does not deploy code. request_changes resumes the SAME bounded task, retaining tool constraints. A further step requires approval. Not a request for repetitive human approval."""
        if decision not in ('approve','request_changes','reject'):raise ValueError('Invalid decision')
        state=await local('/api/selfdevelop/'+chat_id)
        if not state.get('task_id'):raise ValueError('No step to review')
        return await local('/api/tasks/'+state['task_id']+'/review',dict(expected_revision=expected_revision,decision=decision,reason=reason))
    @mcp.tool(annotations=write)
    async def selfdevelop_step(chat_id:str,request_id:str,instruction:str,allowed_tools:list[str],required_tools:list[str]|None=None,required_sources:list[dict]|None=None,evidence_only:bool=False,exact_patch:dict|None=None,context_read:dict|None=None):
        """Dispatch ONE director-authored SelfDevelop step with explicit tool scope installed before execution. Prefer isolated candidate tools; exact_patch is applied verbatim. Poll get_task, inspect actual diff/output, review the same task before another step. Reuse request_id on retry. No deployment implied."""
        return await local('/api/selfdevelop/'+chat_id+'/step',dict(request_id=request_id,instruction=instruction,allowed_tools=allowed_tools,required_tools=required_tools or [],required_sources=required_sources or [],evidence_only=evidence_only,exact_patch=exact_patch,context_read=context_read))
    @mcp.tool(annotations=write)
    async def selfdevelop_run_objective(chat_id:str,task_id:str,request_id:str,
                                        paths:list[str],tests:list[str],model:str|None=None,
                                        max_attempts:int=1,director_mode:str='gpt',
                                        deploy_after_review:bool=False):
        """Authorize ONE persisted objective-level run for an existing reviewed source-mapping task. Mechanical candidate repair, bounded test feedback, and approved Guard continuation run without separate per-phase instructions. GPT semantic review remains mandatory; local policy cannot auto-deploy."""
        return await local('/api/development/selfdevelop/objective/run',
            dict(chat_id=chat_id,task_id=task_id,request_id=request_id,paths=paths,
                 tests=tests,model=model,max_attempts=max_attempts,
                 director_mode=director_mode,deploy_after_review=deploy_after_review))

    @mcp.tool(annotations=write)
    async def selfdevelop_recover_objective(chat_id:str,request_id:str,mode:str,
                                            reason:str,expected_candidate_revision:int,
                                            paths:list[str]|None=None,tests:list[str]|None=None):
        """GPT-directed recovery in the SAME SelfDevelop objective/chat.
        Narrow requires unchanged candidate and proven preflight-only
        context-budget failure. Exact verifies current revision and original
        tests before explicit semantic GPT review.
        Uncertain effects are never replayed. No local approval or Guard.
        """
        return await local('/api/development/selfdevelop/objective/recover',
            dict(chat_id=chat_id,request_id=request_id,mode=mode,reason=reason,
                 expected_candidate_revision=expected_candidate_revision,
                 paths=paths,tests=tests),timeout=170)

    @mcp.tool(annotations=read)
    async def selfdevelop_objective_status(chat_id:str):
        """Return persisted original objective, repair phase, candidate revision, test evidence, director-review gate and Guard update ID after reconnect. Read-only and never auto-approves tests."""
        return await local('/api/development/selfdevelop/objective/'+chat_id)

    @mcp.tool(annotations=write)
    async def selfdevelop_close_failed(chat_id:str,task_id:str,expected_revision:int,request_id:str,reason:str):
        """Director closes an inspected final failed SelfDevelop step; no action replay or automatic skip."""
        return await local('/api/development/selfdevelop/close-failed',dict(chat_id=chat_id,task_id=task_id,expected_revision=expected_revision,request_id=request_id,reason=reason))
    @mcp.tool(annotations=write)
    async def selfdevelop_command(chat_id:str,request_id:str,instruction:str,command:str,shell:str='powershell',timeout:int=60):
        """Run ONE exact director-authored shell command through the local task runner, without model rewriting. Only for the user's authorized SelfDevelop objective. Use stable request_id. Poll task, inspect actual output and requested effects, then selfdevelop_review. Execution never implies semantic approval. Pending or failed commands are not replayed automatically; diagnose and create a new explicit step after review. No automatic elevation or restart."""
        return await local('/api/selfdevelop/'+chat_id+'/command',dict(request_id=request_id,instruction=instruction,command=command,shell=shell,timeout=timeout))

    @mcp.tool(annotations=write)
    async def selfdevelop_command_correct(chat_id:str,task_id:str,expected_revision:int,request_id:str,reason:str,command:str,shell:str='powershell',timeout:int=60):
        """Correct ONE failed/reviewed exact command on the SAME task. Inspect output first. Supply current task revision, a new stable request ID, reason and corrected command. Rejects pending uncertain actions, stale revisions and wrong chats. Retains original objective and audit trail; prior commands are not replayed. Poll then review observed effects."""
        return await local('/api/selfdevelop/'+chat_id+'/command/correct',dict(task_id=task_id,expected_revision=expected_revision,request_id=request_id,reason=reason,command=command,shell=shell,timeout=timeout))

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
    async def candidate_repair(task_id:str,candidate_id:str,revision:int,paths:list[str],tests:list[str],model:str|None=None,max_attempts:int=1):
        return await local('/api/development/repair',dict(task_id=task_id,candidate_id=candidate_id,revision=revision,paths=paths,tests=tests,model=model,max_attempts=max_attempts),timeout=740)
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
        schema('candidate_repair',t('development.repair_tool'),{'candidate_id':string,'revision':{'type':'integer','minimum':0},'paths':{'type':'array','items':string,'minItems':1,'maxItems':10},'tests':{'type':'array','items':string,'minItems':1,'maxItems':30},'model':string,'max_attempts':{'type':'integer','minimum':1,'maximum':3,'description':'1 performs one proposal; 2 or 3 enables local correction using observed test failures. Never activates source.'}},('candidate_id','revision','paths','tests')),
        schema('candidate_create',t('development.create_tool'),{}),
        schema('project_git_status',t('development.git_status_tool'),{}),
        schema('candidate_diff',t('development.diff_tool'),{'candidate_id':string},('candidate_id',)),
        schema('candidate_test',t('development.test_tool'),{'candidate_id':string,'revision':{'type':'integer','minimum':0},'tests':{'type':'array','items':string,'minItems':1,'maxItems':30},'timeout':{'type':'integer','minimum':1,'maximum':300}},('candidate_id','revision','tests')),
        schema('candidate_inspect',t('development.inspect_tool'),{'candidate_id':string},('candidate_id',)),
        schema('candidate_patch',t('development.patch_tool'),{'candidate_id':string,'expected_revision':{'type':'integer','minimum':0},'changes':{'type':'array','items':change,'minItems':1,'maxItems':50}},('candidate_id','expected_revision','changes'))]
