"""The completed bounded SelfDevelop step records verifiable approval-gate evidence."""
import asyncio
import json
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop
from hub.engine import Engine


def test_director_receipt_has_approval_gate_evidence(tmp_path):
    store=Store(tmp_path/'state.sqlite3')
    director=SelfDevelop(store)
    chat=director.start('Test evidence gate','test:director-gate-v2','mcp')
    task=director.step(chat['chat_id'],'director-gate-001','Snapshot only.',
                       ['candidate_create'],required_tools=['candidate_create'])
    engine=Engine(store)
    calls=[]
    async def fake_chat(*args,**kwargs):
        calls.append('model')
        if len(calls)>1:raise AssertionError('Unnecessary model continuation')
        return {'role':'assistant','content':'','tool_calls':[{'function':{
            'name':'candidate_create','arguments':{}}}]},{}
    async def fake_execute(*args,**kwargs):
        calls.append('candidate_create')
        return {'id':'f'*32,'revision':0,'state':'prepared'}
    engine.chat=fake_chat
    engine.runner.execute=fake_execute
    asyncio.run(engine.run(task['id']))
    outcome=store.get(task['id'])
    assert outcome['state']=='waiting_review'
    receipt=json.loads(outcome['result'])
    assert receipt['semantic_verified'] is False
    assert receipt['actions'][0]['result']['id']=='f'*32
    event=store.latest_event(task['id'],'verification')
    assert event is not None
    assert event['data']['checks']==engine.verify(outcome)
    assert event['data']['evidence']==engine.evidence(outcome)
    assert calls==['model','candidate_create']
