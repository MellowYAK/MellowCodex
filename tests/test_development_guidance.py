import pytest
from hub.store import Store,Conflict
from hub.development.guidance import Guidance

def test_guidance_fences_restarts_and_replays_without_duplicate_submission(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('original human objective',str(tmp_path),'code','guidance')
    service=Guidance(store);epoch=service.begin(task['id'])
    args=dict(task_id=task['id'],expected_task_revision=task['revision'],expected_revision=0,consumer_epoch=epoch,request_id='request1',text='Preserve tests; repair implementation.')
    status=service.submit(**args)
    assert status['guidance_revision']==1
    assert status['human_request_original']=='original human objective'
    service.submit(**args)
    assert service.status(task['id'])['guidance_revision']==1
    assert service.consume(task['id'],epoch)[0]['consumed_epoch']==''
    assert service.status(task['id'])['guidance'][0]['consumed_epoch']==epoch
    next_epoch=service.begin(task['id'])
    with pytest.raises(Conflict):service.consume(task['id'],epoch)
    with pytest.raises(Conflict):service.submit(**{**args,'expected_revision':1,'request_id':'request2'})
    assert service.consume(task['id'],next_epoch)[0]['text']==args['text']
    assert service.status(task['id'])['guidance'][0]['consumed_epoch']==next_epoch
    with pytest.raises(Conflict):service.submit(**{**args,'text':'different'})

def test_guidance_rejects_stale_task_and_retains_original_goal(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('שלום',str(tmp_path),'code','guidance2')
    service=Guidance(store)
    store.update(task['id'],state='running')
    with pytest.raises(Conflict):service.submit(task['id'],task['revision'],0,'','one','Change code')
    assert service.status(task['id'])['human_request_original']=='שלום'

def test_guidance_requires_observed_success_after_receipt(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('check diff',str(tmp_path),'code','evidence')
    service=Guidance(store)
    service.submit(task['id'],task['revision'],0,'','one','Inspect the diff',required_tools=['candidate_diff'])
    action={'tool':'candidate_diff','state':'complete','result':{},'created':'2000-01-01T00:00:00+00:00'}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['created']='2099-01-01T00:00:00+00:00'
    action['result']={'error':'failure'}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['result']={'verified':False}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['result']={'revision':1,'files':[]}
    assert service.missing_evidence(task['id'],[action])==[]
