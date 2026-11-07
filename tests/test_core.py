import asyncio
from pathlib import Path
import pytest
from hub.store import Store, Conflict
from hub.tools import ToolRunner
from hub.engine import Engine

@pytest.fixture(autouse=True)
def isolated_visual_settings(monkeypatch):
    from hub.model_settings import ModelSettings
    monkeypatch.setattr('hub.model_settings.load_settings', lambda: ModelSettings())
    monkeypatch.setattr('hub.screen_ocr.hint', lambda path: '')

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/'db.sqlite3')

def make(store,tmp_path,**kwargs):
    return store.create('Create tested output',str(tmp_path),'code',kwargs.get('idem','test-key-1'),kwargs.get('criteria',[]))

def test_inference_profile_is_per_call_and_records_actual_options(store,monkeypatch):
    from contextlib import asynccontextmanager
    import httpx
    seen=[]
    @asynccontextmanager
    async def lease(*args,**kwargs):yield
    monkeypatch.setattr('hub.resources.Resources.inference',lease)
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,json):
            seen.append(json)
            return httpx.Response(200,request=httpx.Request('POST',url),json={
                'message':{'role':'assistant','content':'Observed answer'},'done':True,'done_reason':'stop'})
    monkeypatch.setattr('hub.engine.httpx.AsyncClient',Client)
    engine=Engine(store)
    messages=[{'role':'system','content':'Read evidence'},{'role':'user','content':'Question'}]
    _,metrics=asyncio.run(engine.chat(messages,[],think=True,response_tokens=4096))
    assert seen[-1]['think'] is True and seen[-1]['options']['num_predict']==4096
    assert metrics['packet']['think'] is True and metrics['done_reason']=='stop'
    asyncio.run(engine.chat(messages,[]))
    assert seen[-1]['think'] is False and seen[-1]['options']['num_predict']==1024
    assert 'format' not in seen[-1]
    schema={'type':'object','properties':{'answer':{'type':'string'}}}
    _,metrics=asyncio.run(engine.chat(messages,[],output_schema=schema))
    assert seen[-1]['format']==schema and metrics['packet']['output_schema_sha256']
    with pytest.raises(ValueError,match='no tool catalog'):
        asyncio.run(engine.chat(messages,[{'type':'function'}],output_schema=schema))

def test_environment_tool_remains_callable_after_development_dispatch(store,tmp_path):
    result=asyncio.run(ToolRunner().execute(make(store,tmp_path),'agent_environment',{}))
    assert isinstance(result['executor_pid'],int)
    assert result['runtime_directory']

@pytest.mark.parametrize('mode',['code','desktop'])
def test_code_tool_groups_are_discoverable_durable_and_scoped(store,tmp_path,mode):
    import json
    from hub.model_context import token_estimate
    task=make(store,tmp_path);runner=ToolRunner();runner.context_store=store
    initial=runner.catalog(mode,task['id'])
    assert token_estimate(json.dumps(initial))<7000
    assert 'model_install' not in {s['function']['name'] for s in initial}
    result=asyncio.run(runner.execute(task,'tools_enable',{'groups':['models']}))
    assert 'model_install' in result['tools'] and result['scope_changed'] is False
    restored=ToolRunner();restored.context_store=store
    assert 'model_install' in {s['function']['name'] for s in restored.catalog(mode,task['id'])}
    assert 'model_install' not in {s['function']['name'] for s in restored.catalog(mode,'different-task')}

def test_idempotency_and_conflicting_payload(store,tmp_path):
    a=make(store,tmp_path)
    assert make(store,tmp_path)['id']==a['id']
    with pytest.raises(Conflict):
        store.create('different',str(tmp_path),'code','test-key-1')

def test_revision_compare_and_swap(store,tmp_path):
    task=make(store,tmp_path)
    store.update(task['id'],expected=1,state='running')
    with pytest.raises(Conflict):
        store.update(task['id'],expected=1,state='done')

def test_crash_keeps_unknown_actions_for_reconciliation(store,tmp_path):
    task=make(store,tmp_path)
    store.update(task['id'],state='running')
    store.begin_action(task['id'],'write_file',{'path':'a'})
    Store(store.path).recover()
    assert store.get(task['id'])['state']=='waiting_user'
    assert store.actions(task['id'])[0]['state']=='pending'

def test_directory_traversal(tmp_path):
    runner=ToolRunner()
    with pytest.raises(ValueError):
        runner.path({'workspace':str(tmp_path)},'../outside.txt')

def test_readonly_cannot_write(store,tmp_path):
    task=make(store,tmp_path)
    task['mode']='inspect'
    with pytest.raises(ValueError):
        asyncio.run(ToolRunner().execute(task,'write_file',{'path':'a','content':'no'}))
    assert not (tmp_path/'a').exists()

def test_write_backup_and_read(store,tmp_path):
    task=make(store,tmp_path)
    runner=ToolRunner()
    asyncio.run(runner.execute(task,'write_file',{'path':'example.txt','content':'שלום'}))
    read=asyncio.run(runner.execute(task,'read_file',{'path':'example.txt'}))
    assert read['content']=='שלום'
    asyncio.run(runner.execute(task,'write_file',{'path':'example.txt','content':'updated'}))
    from hub.config import ARTIFACTS
    backup=next((ARTIFACTS/task['id']).glob('backup-*'))
    assert backup.read_text(encoding='utf-8')=='שלום'

def test_no_claim_of_completion_without_checks(store,tmp_path):
    task=make(store,tmp_path)
    engine=Engine(store)
    async def fake_chat(*args):
        return {'role':'assistant','content':'Done'},{}
    engine.chat=fake_chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'

def test_verified_completion_and_checkpoint(store,tmp_path):
    (tmp_path/'proof.txt').write_text('expected')
    task=make(store,tmp_path,criteria=[{'path':'proof.txt','contains':'expected'}])
    engine=Engine(store)
    async def fake_chat(*args):
        return {'role':'assistant','content':'Created output'},{}
    engine.chat=fake_chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='done'
    assert any(e['kind']=='checkpoint' for e in store.events(task['id']))

def test_failed_check_cannot_auto_complete(store,tmp_path):
    task=make(store,tmp_path,criteria=[{'path':'missing.txt'}])
    engine=Engine(store)
    async def fake_chat(*args):
        return {'role':'assistant','content':'I finished'},{}
    engine.chat=fake_chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'


def test_unsubstantiated_source_rejection_preserves_draft_without_retry(store,tmp_path,monkeypatch):
    task=make(store,tmp_path);engine=Engine(store);calls=[]
    async def chat(*args):
        calls.append(1)
        return {'role':'assistant','content':'Candidate source answer'},{}
    async def review(*args):
        return {'verdict':'needs_correction','actionable':False,'reason':'Unsubstantiated objection'}
    engine.chat=chat
    monkeypatch.setattr('hub.context.exploration.review',review)
    asyncio.run(engine.run(task['id']))
    assert len(calls)==1
    final=store.get(task['id'])
    assert final['state']=='waiting_review' and 'Candidate source answer' in final['result']
    assert store.latest_event(task['id'],'source_review_unsubstantiated')['data']['verified'] is False


def test_rejected_source_draft_is_audited_but_not_reused_as_evidence(store,tmp_path,monkeypatch):
    import json
    task=make(store,tmp_path);engine=Engine(store);attempts=[]
    async def chat(messages,catalog):
        attempts.append(json.dumps(messages))
        return {'role':'assistant','content':'Unsupported capability assertion' if len(attempts)==1 else 'Corrected source plan'},{}
    async def review(engine,task,draft):
        return {'verdict':'needs_correction','reason':'Check the required input.'} if 'Unsupported' in draft else {'verdict':'supported'}
    monkeypatch.setattr('hub.context.exploration.review',review)
    engine.chat=chat
    asyncio.run(engine.run(task['id']))
    assert len(attempts)==2
    assert 'Unsupported capability assertion' not in attempts[1]
    assert store.get(task['id'])['result']=='Corrected source plan'
    assert any(e['kind']=='model' and e['data'].get('text')=='Unsupported capability assertion' for e in store.events(task['id']))


@pytest.mark.parametrize('state',['paused','cancelled'])
def test_external_task_control_during_inference_prevents_dispatch(store,tmp_path,state):
    task=make(store,tmp_path);engine=Engine(store)
    async def chat(*args):
        Store(store.path).update(task['id'],state=state)
        return {'role':'assistant','tool_calls':[{'function':{'name':'write_file','arguments':{'path':'should-not-exist.txt','content':'wrong'}}}]},{}
    engine.chat=chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']==state
    assert not (tmp_path/'should-not-exist.txt').exists()
    assert not any(a['tool']=='write_file' for a in store.actions(task['id']))

def test_truncated_model_response_cannot_dispatch_or_claim_completion(store,tmp_path):
    task=make(store,tmp_path);engine=Engine(store)
    async def chat(*args):
        return {'role':'assistant','content':'Complete','tool_calls':[{'function':{'name':'write_file','arguments':{
            'path':'partial.txt','content':'truncated'}}}]},{'done_reason':'length','packet':{'response_tokens':256}}
    engine.chat=chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'
    assert not (tmp_path/'partial.txt').exists()
    assert not any(a['tool']=='write_file' for a in store.actions(task['id']))
    event=store.latest_event(task['id'],'model_output_incomplete')
    assert event['data']['tool_calls_dispatched'] is False


@pytest.mark.parametrize('state',['paused','cancelled'])
def test_external_control_during_final_source_review_is_preserved(store,tmp_path,monkeypatch,state):
    task=make(store,tmp_path);engine=Engine(store);reviews=[]
    async def chat(*args):return {'role':'assistant','content':'Unverified draft'},{}
    async def review(*args):
        reviews.append(1)
        if len(reviews)==3:Store(store.path).update(task['id'],state=state)
        return {'verdict':'needs_correction','reason':'Incomplete evidence'}
    engine.chat=chat
    monkeypatch.setattr('hub.context.exploration.review',review)
    asyncio.run(engine.run(task['id']))
    assert len(reviews)==3
    assert store.get(task['id'])['state']==state


def test_read_only_draft_can_request_missing_source_after_review(store,tmp_path,monkeypatch):
    task=store.create('Read-only: investigate component reuse',str(tmp_path),'code','draft-tools')
    engine=Engine(store);turns=[]
    async def prepare(engine,task,messages):
        aid=store.begin_action(task['id'],'project_context',{})
        store.end_action(aid,{'mode':'fast'})
        for i in range(6):
            aid=store.begin_action(task['id'],'context_expand',{'path':f'{i}.py'})
            store.end_action(aid,{'path':f'{i}.py','ref':f'fast/{i}:h','start':1,'end':1,'text':'def existing(): return 1'})
    async def chat(messages,catalog):
        turns.append(messages)
        if len(turns)<=2:
            assert {x['function']['name'] for x in catalog}=={'project_context','context_search','context_expand','context_related'}
        if len(turns)==1:return {'role':'assistant','content':'Unverified absence claim'},{}
        if len(turns)==2:
            assert 'Search for existing component' in str(messages)
            return {'role':'assistant','tool_calls':[{'function':{'name':'context_search','arguments':{'query':'existing component'}}}]},{}
        return {'role':'assistant','content':'Existing component found; implementation remains untested'},{}
    async def review(engine,task,draft):
        return {'verdict':'needs_correction','reason':'Search for existing component'} if 'Unverified' in draft else {'verdict':'supported'}
    async def execute(task,name,args):
        assert name=='context_search'
        return {'results':[{'path':'existing.py','ref':'fast/actual:h'}]}
    monkeypatch.setattr('hub.context.runtime.prepare',prepare)
    monkeypatch.setattr('hub.context.exploration.review',review)
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert len(turns)==3
    assert any(a['tool']=='context_search' for a in store.actions(task['id']))
    assert store.get(task['id'])['result']=='Existing component found; implementation remains untested'

def test_directed_source_draft_returns_for_external_review_without_local_critic(store,tmp_path,monkeypatch):
    task=store.create('CURRENT STEP: read input schema; OVERALL: plan a feature',str(tmp_path),'code','director-source')
    store.event(task['id'],'chatgpt_action',{'request':'Read the schema only','action_id':'step1'})
    engine=Engine(store);calls=[]
    async def prepare(engine,task,messages):
        for name,result in [('project_context',{'mode':'fast'})]:
            aid=store.begin_action(task['id'],name,{})
            store.end_action(aid,result)
    async def chat(*args):
        calls.append(1)
        if len(calls)==1:return {'role':'assistant','tool_calls':[{'function':{'name':'context_expand','arguments':{'path':'schema.py'}}}]},{}
        assert len(calls)==2,'Do not use the executor as its own director'
        return {'role':'assistant','content':'schema.py:1 declares prompt: str. Other behavior is unverified.'},{}
    async def execute(*args):return {'path':'schema.py','ref':'fast/schema:h','start':1,'end':1,'text':'prompt: str'}
    engine.runner.execute=execute
    monkeypatch.setattr('hub.context.runtime.prepare',prepare);engine.chat=chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'
    assert 'semantic review by the director is still pending' in store.get(task['id'])['result']
    assert store.latest_event(task['id'],'source_review_pending_director')['data']['verified'] is False
    assert not store.latest_event(task['id'],'source_answer_review')


def test_director_can_review_existing_source_evidence_without_forced_new_action(store,tmp_path,monkeypatch):
    task=store.create('Read-only: correct the previous source analysis',str(tmp_path),'code','review-existing')
    store.event(task['id'],'chatgpt_action',{'request':'Correct the existing draft','action_id':'correction'})
    for tool,result in [('project_context',{'mode':'fast'}),('context_expand',{'path':'schema.py','ref':'fast/schema:h','start':1,'end':1,'text':'prompt: str'})]:
        aid=store.begin_action(task['id'],tool,{})
        store.end_action(aid,result)
    engine=Engine(store);calls=[]
    async def prepare(*args):pass
    async def chat(*args):
        calls.append(1)
        assert len(calls)==1,'Existing read evidence must not trigger repeated answer attempts'
        return {'role':'assistant','content':'schema.py:1 declares prompt: str; awaiting independent review.'},{}
    monkeypatch.setattr('hub.context.runtime.prepare',prepare)
    engine.chat=chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'
    assert len(store.actions(task['id']))==2
    assert 'semantic review by the director is still pending' in store.get(task['id'])['result']


def test_unknown_action_blocks_resume(store,tmp_path):
    task=make(store,tmp_path)
    store.update(task['id'],state='paused')
    store.begin_action(task['id'],'run_shell',{'command':'unknown'})
    with pytest.raises(Conflict):
        asyncio.run(Engine(store).control(task['id'],'resume',2))

def test_stop_cancels_pending_model(store,tmp_path):
    async def scenario():
        task=make(store,tmp_path)
        engine=Engine(store)
        entered=asyncio.Event()
        async def hung(*args):
            entered.set()
            await asyncio.sleep(60)
        engine.chat=hung
        engine.enqueue(task['id'])
        await entered.wait()
        await engine.stop_all()
        assert store.get(task['id'])['state']=='paused'
        assert engine.jobs[task['id']].done()
    asyncio.run(scenario())

def test_tool_errors_are_bounded(store,tmp_path):
    task=make(store,tmp_path)
    engine=Engine(store)
    async def bad_chat(*args):
        return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'missing_tool','arguments':{}}}]},{}
    engine.chat=bad_chat
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_user'
    assert len([a for a in store.actions(task['id']) if a['tool']=='missing_tool'])==3


def test_bridge_cannot_report_imaginary_computer_success(store,tmp_path):
    task=store.create('Close the requested application',str(tmp_path),'desktop','no-fake-success')
    store.event(task['id'],'chatgpt_action',{'action_id':'close'})
    engine=Engine(store);attempts=[]
    async def fake_chat(*args):
        attempts.append(True)
        return {'role':'assistant','content':'Closed successfully. closed_verified: true. Zero processes.'},{}
    engine.chat=fake_chat
    asyncio.run(engine.run(task['id']))
    result=store.get(task['id'])
    assert result['state']=='waiting_user' and 'closed_verified' not in result['result']
    assert len(attempts)==3
    assert any(e['kind']=='completion_unverified' for e in store.events(task['id']))


def test_close_summary_comes_from_observed_result_not_model_claim(store,tmp_path):
    task=store.create('Close requested application',str(tmp_path),'desktop','verified-close-summary')
    store.event(task['id'],'chatgpt_action',{'action_id':'close'})
    engine=Engine(store);attempts=[]
    async def fake_chat(*args):
        attempts.append(True)
        if len(attempts)==1:return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'app_close','arguments':{'name':'Editor'}}}]},{}
        return {'role':'assistant','content':'Successfully closed everything.'},{}
    async def execute(*args):return {'closed_verified':False,'windows':[{'hwnd':42}],'process_count':1}
    engine.chat=fake_chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert 'הסגירה לא הושלמה' in store.get(task['id'])['result']

def test_duplicate_url_open_reuses_task_window_after_restart(store,tmp_path):
    task=store.create('Open requested site',str(tmp_path),'desktop','dedup-open')
    args={'name':'Edge','url':'https://example.com'}
    action=store.begin_action(task['id'],'app_open',args)
    store.end_action(action,{'opened_verified':True,'window':{'hwnd':42}})
    engine=Engine(store);calls=[];turns=[]
    async def chat(*unused):
        turns.append(1)
        return ({'role':'assistant','content':'','tool_calls':[{'function':{'name':'app_open','arguments':args}}]} if len(turns)==1 else {'role':'assistant','content':'Observed'}),{}
    async def execute(task,name,args):calls.append((name,args));return {'hwnd':42,'elements':[]}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert calls==[('window_inspect',{'hwnd':42}),('window_inspect',{'hwnd':42})]

def test_repeat_errors_trigger_guidance_even_between_successful_observations(store,tmp_path):
    from hub.errors import ObservationError
    task=store.create('Find requested page',str(tmp_path),'desktop','guidance-fallback')
    store.event(task['id'],'chatgpt_action',{'action_id':'navigate'})
    engine=Engine(store);engine.runner.visual_targets[task['id']]=42
    names=iter(['desktop_action','window_inspect','desktop_action']);calls=[]
    async def chat(*unused):
        name=next(names,None)
        if not name:return {'role':'assistant','content':'Guidance received'},{}
        return {'role':'assistant','content':'','tool_calls':[{'function':{'name':name,'arguments':{}}}]},{}
    async def execute(task,name,args):
        calls.append(name)
        if name=='desktop_action':raise ObservationError('Covered by a popup')
        return {'observed':True}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert calls[:4]==['desktop_action','window_inspect','desktop_action','chatgpt_ask']
    assert store.get(task['id'])['state']=='waiting_user'  # advice alone is not completion


def test_screenshot_evidence_does_not_repeat_the_user_request(store,tmp_path):
    goal='Please take another fresh screenshot and send it here'
    task=store.create(goal,str(tmp_path),'desktop','capture-once')
    engine=Engine(store);calls=[]
    shot=tmp_path/'screen.png'
    from PIL import Image
    Image.new('RGB',(10,10),'white').save(shot)
    async def chat(messages,*args):
        if not calls:
            return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'capture_screenshot','arguments':{'scope':'desktop','share_with_chatgpt':True}}}]},{}
        assert sum(goal in m.get('content','') for m in messages)==1
        assert 'ALREADY captured' in messages[-1]['content']
        return {'role':'assistant','content':'Screenshot prepared'},{}
    async def execute(task,name,args):
        calls.append(name)
        return {'name':'screen.png','share_with_chatgpt':True,'after':{'id':'shot','path':str(shot),'width':10,'height':10,'left':0,'top':0}}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert calls==['capture_screenshot']
    assert store.get(task['id'])['state']=='waiting_review'


def test_failed_file_share_requires_real_retry_before_handoff_finishes(store,tmp_path):
    task=store.create('Return the requested screenshot',str(tmp_path),'desktop','file-retry')
    store.event(task['id'],'chatgpt_action',{'action_id':'share'})
    engine=Engine(store);turns=[];calls=[]
    async def chat(messages,*args):
        turns.append(1)
        if len(turns)==1:tool,args='files_list',{}
        elif len(turns)==2:tool,args='file_share',{'file_id':'task-id','path':'wrong'}
        elif len(turns)==3:return {'role':'assistant','content':'Let me try again'},{}
        elif len(turns)==4:
            assert 'actually CALL' in messages[-1]['content']
            tool,args='file_share',{'file_id':'real-file'}
        else:return {'role':'assistant','content':'Prepared'},{}
        return {'role':'assistant','tool_calls':[{'function':{'name':tool,'arguments':args}}]},{}
    async def execute(task,name,args):
        calls.append(name)
        if name=='files_list':return {'files':[{'id':'real-file','name':'desktop.png'}]}
        if 'path' in args:raise ValueError('Supply exactly one file_id or workspace path')
        return {'id':'real-file','name':'desktop.png','share_with_chatgpt':True}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    result=store.get(task['id'])
    assert calls==['files_list','file_share','file_share']
    assert result['state']=='waiting_review' and 'Files prepared' in result['result']


def test_failed_file_share_cannot_finish_with_promises_only(store,tmp_path):
    task=store.create('Return screenshot',str(tmp_path),'desktop','file-no-retry')
    store.event(task['id'],'chatgpt_action',{'action_id':'share'})
    engine=Engine(store);turns=[]
    async def chat(*args):
        turns.append(1)
        if len(turns)<=2:
            return {'role':'assistant','tool_calls':[{'function':{'name':'files_list' if len(turns)==1 else 'file_share','arguments':{}}}]},{}
        return {'role':'assistant','content':'I will try again'},{}
    async def execute(task,name,args):
        if name=='files_list':return {'files':[]}
        raise ValueError('Missing file')
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_user'
    assert len(turns)==5


def test_progressing_task_can_pass_thirty_steps(store,tmp_path):
    task=store.create('Inspect the requested files',str(tmp_path),'code','long-progress')
    engine=Engine(store);calls=[]
    async def chat(*unused):
        if len(calls)>=35:return {'role':'assistant','content':'Inspected'},{}
        return {'role':'assistant','tool_calls':[{'function':{'name':'read_file','arguments':{'path':str(len(calls))}}}]},{}
    async def execute(task,name,args):
        calls.append(args);return {'text':'evidence '+args['path']}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert len(calls)==35
    assert store.get(task['id'])['state']=='waiting_review'


def test_task_status_exposes_actual_pending_command(store,tmp_path):
    from hub.task_status import task_status
    t=store.create('Inspect',str(tmp_path),'code','status-detail')
    store.update(t['id'],state='running')
    store.event(t['id'],'model_start',{'step':4})
    aid=store.begin_action(t['id'],'run_shell',{'command':'Get-Item -LiteralPath C:\\test'})
    store.event(t['id'],'tool_start',{'name':'run_shell','action_id':aid})
    s=task_status(store,t['id'])['execution']
    assert s['phase']=='tool_start' and s['waiting_for']=='tool_execution'
    assert s['current_action']['id']==aid and s['step']==4 and s['needs_poll']
    assert s['recent_actions'][-1]['outcome']=='running'
    assert s['total_steps'] is None and 'exit status' in s['expectation']
    store.update(t['id'],state='waiting_user',result='Precise failure')
    s=task_status(store,t['id'])
    assert not s['execution']['needs_poll'] and s['execution']['current_action'] is None
    assert 'Precise failure' in s['text']


def test_desktop_unavailable_replans_then_reads_file(store,tmp_path):
    from hub.errors import DesktopUnavailable
    task=store.create('Read existing file',str(tmp_path),'desktop','background-recovery')
    engine=Engine(store); calls=[]
    names=iter(['observe_screen','read_file'])
    async def chat(messages,*unused):
        name=next(names,None)
        if not name:return {'role':'assistant','content':'File read'},{}
        return {'role':'assistant','content':'','tool_calls':[{'function':{'name':name,'arguments':{}}}]},{}
    async def execute(task,name,args):
        calls.append(name)
        if name=='observe_screen':raise DesktopUnavailable('locked fixture')
        return {'text':'existing file content'}
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert calls==['observe_screen','read_file']
    assert store.get(task['id'])['state']=='waiting_review'
    assert store.latest_event(task['id'],'background_replan')
    from hub.task_status import task_status
    status=task_status(store,task['id'])
    assert status['execution']['recent_actions'][0]['outcome']=='deferred'


@pytest.mark.parametrize('result',[{'error':'Worker failed'}, {'candidate_id':'fixture','revision':2,'test':{'exit_code':1,'verified':False,'output':'4 failed, 8 passed'}}])
def test_supervised_repair_returns_evidence_without_executor_loop(store,tmp_path,result):
    task=store.create('Repair only a.py',str(tmp_path),'desktop','director-repair')
    store.event(task['id'],'chatgpt_action',{'action_id':'repair'})
    engine=Engine(store);turns=[]
    async def chat(*args):
        turns.append(1)
        return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'candidate_repair','arguments':{'candidate_id':'fixture','revision':1}}}]},{}
    async def execute(*args):return result
    engine.chat=chat;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    final=store.get(task['id'])
    assert final['state']=='waiting_review' and len(turns)==1
    assert 'overall task is not complete' in final['result']
    assert result.get('error',result.get('test',{}).get('output')) in final['result']


def test_read_large_utf8_file_pages_without_file_size_rejection(store,tmp_path):
    import hashlib
    text=('שלום אבג\n'*180000)+'unique_tail'
    (tmp_path/'large.txt').write_text(text,encoding='utf8')
    runner=ToolRunner();task=make(store,tmp_path)
    for offset in (65533,len(text)-20):
        page=asyncio.run(runner.execute(task,'read_file',{'path':'large.txt','offset':offset,'chars':40}))
        assert page['content']==text[offset:offset+40]
        assert page['total_characters']==len(text)
        assert page['sha256']==hashlib.sha256(text.encode('utf8')).hexdigest()
    assert page['next_offset'] is None


def test_exhausted_source_review_preserves_draft_for_director(store,tmp_path,monkeypatch):
    from hub.task_answer import task_answer
    task=store.create('Read-only: map the project',str(tmp_path),'code','review-draft-preservation')
    engine=Engine(store);calls=[]
    async def prepare(*args):pass
    async def ground(*args):return []
    async def chat(*args):
        calls.append(1)
        return {'role':'assistant','content':f'Observed draft {len(calls)}; runtime unknown.'},{}
    async def review(*args):
        return {'verdict':'needs_correction','actionable':True,'reason':'Local reviewer disputes interpretation.'}
    monkeypatch.setattr('hub.context.runtime.prepare',prepare)
    monkeypatch.setattr('hub.context.exploration.ground_named_sources',ground)
    monkeypatch.setattr('hub.context.exploration.review',review)
    engine.chat=chat
    asyncio.run(engine.run(task['id']))
    final=store.get(task['id'])
    assert len(calls)==3 and final['state']=='waiting_review'
    assert task_answer(final)['text']=='Observed draft 3; runtime unknown.'
    assert 'Observed draft 3' in final['result']
    assert store.latest_event(task['id'],'source_review_exhausted')['data']['verified'] is False


@pytest.mark.parametrize('stale',[False,True])
def test_director_exact_patch_uses_real_runner_without_model(store,tmp_path,monkeypatch,stale):
    from hub.development.guidance import Guidance
    from hub.development.service import Development
    workspace=tmp_path/'project';workspace.mkdir()
    original='def total(a, b):\n    return a + b\n'
    replacement='def total(a, b):\n    return a * b  # exact director code\n'
    (workspace/'billing.py').write_text(original,encoding='utf-8')
    task=store.create('Apply the director correction in an isolated candidate',str(workspace),'code','exact')
    monkeypatch.setattr('hub.tools.ROOT',tmp_path)
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    patch={'candidate_id':candidate['id'],'expected_revision':candidate['revision'],
           'changes':[{'path':'billing.py','base_hash':'0'*64 if stale else candidate['files']['billing.py'],'content':replacement}]}
    Guidance(store).submit(task['id'],task['revision'],0,'','exact','Apply verbatim and return diff',exact_patch=patch)
    engine=Engine(store)
    async def no_model(*args,**kwargs):raise AssertionError('Exact patch must not invoke a model')
    engine.chat=no_model
    asyncio.run(engine.run(task['id']))
    actions=store.actions(task['id'])
    assert [a['tool'] for a in actions]==(['candidate_patch'] if stale else ['candidate_patch','candidate_diff'])
    assert store.get(task['id'])['state']=='waiting_review'
    assert (workspace/'billing.py').read_text(encoding='utf-8')==original
    directory=dev.workspaces.directory(candidate['id'],dev.inspect(task,candidate['id']))
    assert (directory/'billing.py').read_text(encoding='utf-8')==(original if stale else replacement)
    if stale:assert actions[0]['result']['error']
    else:assert store.latest_event(task['id'],'director_patch_evidence')['data']['model_inference'] is False
