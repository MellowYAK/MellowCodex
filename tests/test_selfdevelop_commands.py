from hub.store import Store,Conflict
from hub.development.selfdevelop import SelfDevelop
from hub.development.commands import dispatch,next_command,command_receipt
import pytest

def setup(tmp_path):
    store=Store(tmp_path/'state.db')
    chat=SelfDevelop(store).start('Repair own code','test:commands','mcp')['chat_id']
    return store,chat

def test_exact_command_and_idempotency(tmp_path):
    store,chat=setup(tmp_path)
    task=dispatch(store,chat,'command-1','Inspect','Write-Output hello')
    call,done=next_command(store,task['id'])
    assert not done and call['tool_calls'][0]['function']['arguments']['command']=='Write-Output hello'
    assert dispatch(store,chat,'command-1','Inspect','Write-Output hello')['id']==task['id']
    with pytest.raises(Conflict):dispatch(store,chat,'command-1','Inspect','Write-Output other')
    aid=store.begin_action(task['id'],'run_shell',call['tool_calls'][0]['function']['arguments'])
    assert next_command(store,task['id'])==(None,True)
    assert not command_receipt(store,task['id'])['execution_succeeded']
    store.end_action(aid,{'exit_code':0,'output':'hello'})
    assert command_receipt(store,task['id'])['execution_succeeded']
    assert next_command(store,task['id'])==(None,True)

@pytest.mark.parametrize('result',[{'exit_code':1},{'error':'failure'},{'exit_code':0,'error':'failure'}])
def test_failed_command_is_not_replayed(tmp_path,result):
    store,chat=setup(tmp_path)
    task=dispatch(store,chat,'command-2','Inspect','Write-Output hello')
    call,_=next_command(store,task['id'])
    aid=store.begin_action(task['id'],'run_shell',call['tool_calls'][0]['function']['arguments'])
    store.end_action(aid,result)
    assert not command_receipt(store,task['id'])['execution_succeeded']
    assert next_command(store,task['id'])==(None,True)

def test_invalid_command_creates_no_task(tmp_path):
    store,chat=setup(tmp_path)
    with pytest.raises(ValueError):dispatch(store,chat,'command-3','Inspect','',timeout=60)
    assert SelfDevelop(store).status(chat)['task_id'] is None


def test_actual_runner_executes_once_without_inference(tmp_path,monkeypatch):
    import asyncio
    from hub.engine import Engine
    store,chat=setup(tmp_path)
    task=dispatch(store,chat,'runner-command','Inspect shell','Write-Output SELFDEVELOP_EXACT_COMMAND_OK')
    engine=Engine(store)
    async def forbidden(*args,**kwargs):
        raise AssertionError('Exact commands must not invoke the model')
    monkeypatch.setattr(engine,'chat',forbidden)
    asyncio.run(engine.run(task['id']))
    observed=store.get(task['id'])
    assert observed['state']=='waiting_review', observed['result']
    actions=store.actions(task['id'])
    assert len(actions)==1 and actions[0]['tool']=='run_shell'
    assert 'SELFDEVELOP_EXACT_COMMAND_OK' in actions[0]['result']['output']
    asyncio.run(engine.run(task['id']))
    assert len(store.actions(task['id']))==1


def test_live_runner_failed_then_corrected_same_task(tmp_path,monkeypatch):
    import asyncio
    from hub.engine import Engine
    from hub.development.commands import correct
    store,chat=setup(tmp_path)
    task=dispatch(store,chat,'runner-failure','Demonstrate correction','exit 7')
    engine=Engine(store)
    async def forbidden(*args,**kwargs):
        raise AssertionError('Exact commands must not invoke model')
    monkeypatch.setattr(engine,'chat',forbidden)
    asyncio.run(engine.run(task['id']))
    failed=store.get(task['id'])
    assert failed['state']=='waiting_user'
    with pytest.raises(Conflict):
        correct(store,chat,task['id'],failed['revision']-1,'correct-1','Correct exit','Write-Output FIXED')
    fixed=correct(store,chat,task['id'],failed['revision'],'correct-1','Correct exit','Write-Output FIXED')
    assert fixed['id']==task['id'] and fixed['goal']=='Demonstrate correction'
    assert correct(store,chat,task['id'],failed['revision'],'correct-1','Correct exit','Write-Output FIXED')['id']==task['id']
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'
    actions=store.actions(task['id'])
    assert len(actions)==2 and actions[0]['result']['exit_code']==7
    assert 'FIXED' in actions[1]['result']['output']
    assert command_receipt(store,task['id'])['execution_succeeded']

def test_correction_rejects_uncertain_effect(tmp_path):
    from hub.development.commands import correct
    store,chat=setup(tmp_path)
    task=dispatch(store,chat,'pending-command','Inspect','Write-Output hello')
    store.begin_action(task['id'],'run_shell',{'command':'Write-Output hello'})
    task=store.update(task['id'],state='waiting_user')
    with pytest.raises(Conflict):
        correct(store,chat,task['id'],task['revision'],'correct-pending','Retry','Write-Output hello')
