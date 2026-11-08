import asyncio
from types import SimpleNamespace
import pytest
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop

@pytest.mark.parametrize('extra',[
    {'context_read':{'operation':'invalid'}},
    {'required_tools':['read_file']},
    {'allowed_tools':['invalid tool']},
])
def test_invalid_step_does_not_leave_task(tmp_path,extra):
    store=Store(tmp_path/'test.db');svc=SelfDevelop(store)
    chat=svc.start('Repair','test:repair','mcp')['chat_id']
    args=dict(chat_id=chat,request_id='invalid',instruction='Read',allowed_tools=['project_context'])
    args.update(extra)
    with pytest.raises(ValueError):svc.step(**args)
    assert Conversations(store).get(chat)['turns']==[]

def test_ordinary_followup_does_not_leave_orphan(tmp_path):
    store=Store(tmp_path/'test.db');svc=SelfDevelop(store)
    chat=svc.start('Repair','test:repair','mcp')['chat_id']
    task=svc.step(chat,'first','Read',['project_context'])
    store.update(task['id'],state='waiting_user')
    with pytest.raises(Conflict):
        Conversations(store).submit(chat,'Next','code','second')
    assert len(Conversations(store).get(chat)['turns'])==1

@pytest.mark.parametrize('decision,pending,stale,accepted',[
    ('request_changes',False,False,True),
    ('request_changes',True,False,False),
    ('request_changes',False,True,False),
    ('approve',False,False,False),
])
def test_failed_step_review_preserves_guards(tmp_path,monkeypatch,decision,pending,stale,accepted):
    import hub.app as module
    store=Store(tmp_path/'test.db');queued=[]
    task=store.create('Repair',str(tmp_path),'code','review')
    if pending:store.begin_action(task['id'],'write_file',{'path':'example'})
    task=store.update(task['id'],state='waiting_user')
    monkeypatch.setattr(module,'store',store)
    monkeypatch.setattr(module,'engine',SimpleNamespace(verify=lambda task:[],enqueue=queued.append))
    monkeypatch.setattr(module.app.state,'bridge',SimpleNamespace(state={}),raising=False)
    body=module.Review(decision=decision,reason='Correct the observed failure',expected_revision=task['revision']-int(stale))
    if accepted:
        result=asyncio.run(module.review(task['id'],body))
        assert result['id']==task['id'] and result['state']=='queued'
        assert queued==[task['id']]
        assert store.get(task['id'])['goal']=='Repair'
    else:
        with pytest.raises(Conflict):asyncio.run(module.review(task['id'],body))
        assert store.get(task['id'])['state']=='waiting_user'
        assert queued==[]
