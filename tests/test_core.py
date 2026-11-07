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
