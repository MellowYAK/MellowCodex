import asyncio
import pytest
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.development.commands import dispatch, next_command, command_receipt
from hub import mcp_gateway

def normal_chat(tmp_path):
    store=Store(tmp_path/'audit.db')
    chats=Conversations(store)
    project=chats.project(tmp_path)
    return store,chats.create(project['id'])['id']

def test_atomic_normal_direct_command(tmp_path):
    store,chat=normal_chat(tmp_path)
    task=dispatch(store,chat,'direct-001','Exact command','Write-Output DIRECT_OK',normal_direct=True)
    event=store.latest_event(task['id'],'director_exact_command')['data']
    assert event['route']=='mcp_direct' and event['model_inference'] is False
    assert task['workspace']==str(tmp_path.resolve())
    assert dispatch(store,chat,'direct-001','Exact command','Write-Output DIRECT_OK',normal_direct=True)['id']==task['id']
    with pytest.raises(Conflict):
        dispatch(store,chat,'direct-001','Exact command','different',normal_direct=True)
    with pytest.raises(Conflict):
        dispatch(store,chat,'direct-002','Other','Write-Output other',normal_direct=True)
    call,_=next_command(store,task['id'])
    aid=store.begin_action(task['id'],'run_shell',call['tool_calls'][0]['function']['arguments'])
    assert next_command(store,task['id'])==(None,True)
    assert not command_receipt(store,task['id'])['execution_succeeded']
    store.end_action(aid,{'exit_code':0})
    assert command_receipt(store,task['id'])['execution_succeeded']

def test_gateway_no_implicit_model(monkeypatch):
    async def audit_only(path,data=None,**kwargs):
        assert path.endswith('/direct-required') and data['use_local_model'] is False
        return {'state':'blocked','code':'DIRECT_ACTION_REQUIRED','model_inference':False}
    monkeypatch.setattr(mcp_gateway,'local',audit_only)
    result=asyncio.run(mcp_gateway.submit_task('a'*32,'Create folder','direct-003'))
    assert result['code']=='DIRECT_ACTION_REQUIRED' and not result['model_inference']

def test_exact_normal_runner_no_inference(tmp_path,monkeypatch):
    from hub.engine import Engine
    store,chat=normal_chat(tmp_path)
    task=dispatch(store,chat,'direct-004','Exact command','Write-Output DIRECT_NORMAL_OK',normal_direct=True)
    engine=Engine(store)
    async def forbidden(*args,**kwargs):raise AssertionError('No model allowed')
    monkeypatch.setattr(engine,'chat',forbidden)
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review',store.get(task['id'])['result']
    actions=store.actions(task['id'])
    assert len(actions)==1 and 'DIRECT_NORMAL_OK' in actions[0]['result']['output']
    asyncio.run(engine.run(task['id']))
    assert len(store.actions(task['id']))==1

def test_native_read_no_model(tmp_path,monkeypatch):
    from hub.development.commands import dispatch_native
    from hub.engine import Engine
    store,chat=normal_chat(tmp_path)
    path=tmp_path/'direct.txt';path.write_text('DIRECT_NATIVE_OK')
    task=dispatch_native(store,chat,'native-001','Read exact file','read_file',{'path':str(path)})
    assert task['mode']=='desktop'
    event=store.latest_event(task['id'],'director_exact_command')['data']
    assert event['tool']=='read_file' and event['model_inference'] is False
    engine=Engine(store)
    async def forbidden(*args,**kwargs):raise AssertionError('No model allowed')
    monkeypatch.setattr(engine,'chat',forbidden)
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review',store.get(task['id'])['result']
    actions=store.actions(task['id'])
    assert len(actions)==1 and 'DIRECT_NATIVE_OK' in str(actions[0]['result'])
    asyncio.run(engine.run(task['id']))
    assert len(store.actions(task['id']))==1

def test_native_rejects_model_and_policy_tools(tmp_path):
    from hub.development.commands import dispatch_native
    store,chat=normal_chat(tmp_path)
    for tool in ('coding_ask','computer_power','model_memory_control','extension_run'):
        with pytest.raises(ValueError):
            dispatch_native(store,chat,'native-bad','Not direct',tool,{})
