"""Return exact completed required tools for director review without another model turn."""
import asyncio
import json
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop
from hub.engine import Engine


def test_single_required_tool_returns_director_receipt(tmp_path):
    store=Store(tmp_path/'state.sqlite3')
    service=SelfDevelop(store)
    chat=service.start('Bounded step acceptance','test:bounded-receipt','mcp')
    task=service.step(chat['chat_id'],'bounded-receipt-001',
                      'Create isolated candidate only.',
                      ['candidate_create'],required_tools=['candidate_create'])
    engine=Engine(store)
    seen=[]
    async def chat_func(*args,**kwargs):
        seen.append('chat')
        if seen.count('chat')>1:raise AssertionError('Unexpected second model call')
        return {'role':'assistant','content':'','tool_calls':[
            {'function':{'name':'candidate_create','arguments':{}}}]},{}
    async def execute(task,name,args,**kwargs):
        seen.append(name)
        assert name=='candidate_create'
        return {'id':'c'*32,'revision':0,'state':'prepared'}
    engine.chat=chat_func;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    updated=store.get(task['id'])
    assert updated['state']=='waiting_review'
    data=json.loads(updated['result'])
    assert data['status']=='awaiting_director_review'
    assert data['semantic_verified'] is False
    assert data['required_tools_executed']==['candidate_create']
    assert data['actions'][0]['result']['id']=='c'*32
    assert seen==['chat','candidate_create']
    assert any(e['kind']=='director_required_tools_completed' for e in store.events(task['id']))
    verified=store.latest_event(task['id'],'verification')['data']
    assert verified['checks']==engine.verify(store.get(task['id']))
    assert verified['evidence']==engine.evidence(store.get(task['id']))


def test_tool_error_never_claims_director_completion(tmp_path):
    store=Store(tmp_path/'state.sqlite3')
    service=SelfDevelop(store)
    chat=service.start('Bounded failure','test:bounded-receipt-fail','mcp')
    task=service.step(chat['chat_id'],'bounded-receipt-002',
                      'Create isolated candidate only.',
                      ['candidate_create'],required_tools=['candidate_create'])
    engine=Engine(store)
    turns=[]
    async def chat_func(*args,**kwargs):
        turns.append('chat')
        if len(turns)>1:return {'role':'assistant','content':'Failed'},{}
        return {'role':'assistant','content':'','tool_calls':[
            {'function':{'name':'candidate_create','arguments':{}}}]},{}
    async def execute(task,name,args,**kwargs):
        return {'error':'snapshot refused','input_sent':False}
    engine.chat=chat_func;engine.runner.execute=execute
    asyncio.run(engine.run(task['id']))
    assert not any(e['kind']=='director_required_tools_completed' for e in store.events(task['id']))
