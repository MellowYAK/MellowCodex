"""Seed coding tasks with measured project context, recorded like other actions."""
import json
from ..i18n import t

async def prepare(engine,task,messages):
    if task['mode']!='code':return
    if engine.store.latest_event(task['id'],'director_exact_command'):
        engine.store.event(task['id'],'source_navigation_delegated',{'basis':'Exact director command; no autonomous discovery'})
        return
    from ..development.guidance import Guidance
    if Guidance(engine.store).context_read(task['id']):
        # Deterministic read executes exactly the director-selected index tool.
        engine.store.event(task['id'],'source_navigation_delegated',{'basis':'Deterministic director context read; no autonomous bootstrap'})
        return
    scope=Guidance(engine.store).allowed_tools(task['id'])
    if scope is not None and 'project_context' not in scope:
        # A director-limited task must not start with a forbidden broad
        # project_context lookup before the bounded task can execute.
        engine.store.event(task['id'],'source_navigation_delegated',
                           {'basis':'Explicit director tool scope excludes project_context'})
        return
    if Guidance(engine.store).exact_patch(task['id']):
        # The director already selected the candidate and versioned contents.
        # A fresh autonomous discovery pass is outside this bounded write step.
        engine.store.event(task['id'],'source_navigation_delegated',{'basis':'Exact director patch with candidate revision and file hashes'})
        return
    messages[0]['content']+='\n'+t('context.coding_instruction')
    async def read(name,args=None):
        args=args or {}
        action_id=engine.store.begin_action(task['id'],name,args)
        engine.store.event(task['id'],'tool_start',{'action_id':action_id,'name':name,'args':args,'origin':'context_bootstrap'})
        try:result=await engine.runner.execute(task,name,args)
        except Exception as exc:result={'error':str(exc)}
        if name=='project_context' and result.get('required_constraints'):
            # Required obligations belong to the fixed packet, not evictable history.
            messages[0]['content']+='\n'+t('context.required_packet')+'\n'+json.dumps(result['required_constraints'],ensure_ascii=False)
        engine.store.end_action(action_id,result)
        engine.store.event(task['id'],'tool_result',{'action_id':action_id,'name':name,'result':result,'origin':'context_bootstrap'})
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':name,'arguments':args}}]},
                         {'role':'tool','tool_name':name,'content':json.dumps(result,ensure_ascii=False)}])
        return result
    current=await read('project_context')
    if not current.get('error') and not current.get('index'):
        await read('context_refresh')
        current=await read('project_context')
    if current.get('mode')=='fast':
        from .exploration import SOURCE_SYSTEM, DIRECTED_SOURCE_SYSTEM
        # Keep the actual input preference and source obligations, but do not
        # spend the code model's context on unrelated screenshot/login recipes.
        preference=messages[0]['content'].partition('\nInput preference: ')[2].split('\n')[0]
        from ..development.guidance import Guidance
        directed=engine.store.latest_event(task['id'],'chatgpt_action')
        evidence_only=Guidance(engine.store).evidence_only(task['id']) or bool(Guidance(engine.store).exact_patch(task['id']))
        if evidence_only and not directed:directed={'data':{}}
        source_instruction=DIRECTED_SOURCE_SYSTEM if directed else SOURCE_SYSTEM+'\n'+t('context.fast_instruction')
        messages[0]['content']=source_instruction+'\nInput preference: '+preference
        if current.get('required_constraints'):
            messages[0]['content']+='\n'+t('context.required_packet')+'\n'+json.dumps(current['required_constraints'],ensure_ascii=False)
        if directed:
            messages[0]['content']+='\nThis is one director-assigned execution step. Perform the CURRENT STEP only. The overall objective constrains scope but is not a request to complete all future stages now. Return observed evidence for the director to review; do not restart broad project exploration when specific source ranges were requested.'
        # Observe instructions from current source, not a guessed project summary.
        observed=[]
        entries=current.get('entrypoints',[])[:3]
        if directed:
            # Project obligations remain applicable. Architecture/discovery is
            # delegated to the director's specific step, not repeated on every
            # feedback round. The full map stays available through the tools.
            entries=[entry for entry in entries if entry['path']=='AGENTS.md']
        for entry in entries:
            source=await read('context_expand',{'ref':entry['ref'],'lines':80})
            if source.get('text'):observed.append(source)
        if directed:
            engine.store.event(task['id'],'source_navigation_delegated',{'basis':'Recorded director step; project constraints retained','action_id':directed['data'].get('action_id')})
            return
        from .exploration import seed_navigation
        await seed_navigation(engine,task,read,{'navigation_candidates':current.get('navigation_candidates',[]),'navigation_tree':current.get('navigation_tree',{}),'observed_source_excerpts':observed})
