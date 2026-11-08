import pytest
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop

def make_failed(tmp_path):
    store=Store(tmp_path/'recovery.db')
    service=SelfDevelop(store)
    chat=service.start('Recover failed development safely','test:selfdevelop-close','mcp')['chat_id']
    step=service.step(chat,'first-source-step','Read source',['project_brief'],context_read={'operation':'brief'})
    step=store.update(step['id'],state='failed',result='Synthetic terminal failure')
    return store,service,chat,step

def test_director_closes_failed_then_next_step_succeeds(tmp_path):
    store,service,chat,failed=make_failed(tmp_path)
    old_revision=failed['revision']
    result=service.close_failed(chat,failed['id'],old_revision,'failed-closure-001','Director verified synthetic failure')
    assert result['state']=='cancelled' and result['revision']==old_revision+1
    assert result['goal']==failed['goal'] and result['result']==failed['result']
    audit=store.latest_event(failed['id'],'selfdevelop_failed_closed')
    assert audit['data']['request_id']=='failed-closure-001'
    assert audit['data']['actions_replayed'] is False
    assert service.close_failed(chat,failed['id'],old_revision,'failed-closure-001','Director verified synthetic failure')['revision']==old_revision+1
    followup=service.step(chat,'second-source-step','Read followup',['project_brief'],context_read={'operation':'brief'})
    assert followup['id']!=failed['id']
    followup=store.update(followup['id'],state='waiting_review',result='Synthetic evidence')
    assert store.update(followup['id'],state='done')['state']=='done'
    assert len(Conversations(store).get(chat)['turns'])==2

def test_wrong_chat_and_stale_revision_are_rejected(tmp_path):
    store,service,chat,failed=make_failed(tmp_path)
    other=service.start('Different objective','test:second-chat','mcp')['chat_id']
    with pytest.raises(Conflict):
        service.close_failed(other,failed['id'],failed['revision'],'failed-closure-002','Reviewed')
    with pytest.raises(Conflict):
        service.close_failed(chat,failed['id'],failed['revision']-1,'failed-closure-003','Reviewed')
    assert store.get(failed['id'])['state']=='failed'

def test_pending_action_never_released(tmp_path):
    store,service,chat,failed=make_failed(tmp_path)
    store.begin_action(failed['id'],'run_shell',{'command':'unknown side effect'})
    with pytest.raises(Conflict):
        service.close_failed(chat,failed['id'],failed['revision'],'failed-closure-004','Cannot reconcile pending effect')
    assert store.get(failed['id'])['state']=='failed'

@pytest.mark.parametrize('state',['queued','running','verifying','waiting_review','waiting_user','paused','done','cancelled'])
def test_only_final_failed_is_allowed(tmp_path,state):
    store,service,chat,failed=make_failed(tmp_path)
    target=store.update(failed['id'],state=state)
    with pytest.raises(Conflict):
        service.close_failed(chat,target['id'],target['revision'],'failed-closure-005','Not a final failure')
    assert store.get(target['id'])['state']==state

def test_reason_and_idempotency_are_required(tmp_path):
    store,service,chat,failed=make_failed(tmp_path)
    with pytest.raises(ValueError):
        service.close_failed(chat,failed['id'],failed['revision'],'failed-closure-006',' ')
    assert store.latest_event(failed['id'],'selfdevelop_failed_closed') is None
    service.close_failed(chat,failed['id'],failed['revision'],'failed-closure-007','Concrete review evidence')
    with pytest.raises(Conflict):
        service.close_failed(chat,failed['id'],failed['revision'],'failed-closure-007','Changed reason')
    with pytest.raises(Conflict):
        service.close_failed(chat,failed['id'],failed['revision']+1,'failed-closure-008','Another closure')
