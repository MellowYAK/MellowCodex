"""SelfDevelop must recover scoped progress from its existing audit store."""
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop


def test_status_recovers_candidate_revision_test_and_feedback_after_reconnect(tmp_path):
    store=Store(tmp_path/'hub.db')
    service=SelfDevelop(store)
    session=service.start('Repair Hub without automatic deployment','test:durable-resume','mcp')
    task=service.step(session['chat_id'],'initial-read','Inspect source',['project_brief'],context_read={'operation':'brief'})
    store.event(task['id'],'candidate_created',{'candidate_id':'a'*32})
    store.event(task['id'],'candidate_staged',{'candidate_id':'a'*32,'revision':3,'paths':['hub/a.py']})
    store.event(task['id'],'candidate_tested',{'candidate_id':'a'*32,'revision':3,'verified':True,'evidence':'candidate-test-evidence.json'})
    store.event(task['id'],'coding_worker_test_feedback',{'candidate_id':'a'*32,'revision':3,'next_attempt':2,'evidence':'prior-failure.json'})
    store.update(task['id'],state='waiting_review')
    resumed=SelfDevelop(Store(tmp_path/'hub.db')).status(session['chat_id'])
    assert resumed['objective']=='Repair Hub without automatic deployment'
    assert resumed['progress']['candidate_id']=='a'*32
    assert resumed['progress']['candidate_revision']==3
    assert resumed['progress']['test']['verified'] is True
    assert resumed['progress']['test']['evidence']=='candidate-test-evidence.json'
    assert resumed['progress']['feedback']['next_attempt']==2
    assert resumed['progress']['phase']=='semantic_review_required'
    assert resumed['progress']['semantic_approved'] is False
    assert resumed['progress']['deployment_verified'] is None


def test_status_never_leaks_candidates_from_other_chat(tmp_path):
    store=Store(tmp_path/'hub.db')
    service=SelfDevelop(store)
    first=service.start('First original objective','test:progress-a','mcp')
    other=service.start('Different objective','test:progress-b','mcp')
    task=service.step(other['chat_id'],'other-read','Inspect other source',['project_brief'],context_read={'operation':'brief'})
    store.event(task['id'],'candidate_staged',{'candidate_id':'b'*32,'revision':9})
    a=SelfDevelop(Store(tmp_path/'hub.db')).status(first['chat_id'])
    assert a['progress']['candidate_id'] is None
    assert a['progress']['candidate_revision'] is None
    assert a['progress']['phase']=='waiting_director'


def test_test_pass_is_not_semantic_approval(tmp_path):
    store=Store(tmp_path/'hub.db')
    service=SelfDevelop(store)
    chat=service.start('Keep semantic review separate','test:review-progress','mcp')['chat_id']
    task=service.step(chat,'read-step','Inspect source',['project_brief'],context_read={'operation':'brief'})
    store.event(task['id'],'candidate_staged',{'candidate_id':'c'*32,'revision':1})
    store.event(task['id'],'candidate_tested',{'candidate_id':'c'*32,'revision':1,'verified':True,'evidence':'receipt.json'})
    progress=service.status(chat)['progress']
    assert progress['test']['verified'] is True
    assert progress['semantic_approved'] is False
    store.update(task['id'],state='done')
    assert SelfDevelop(Store(tmp_path/'hub.db')).status(chat)['progress']['semantic_approved'] is False
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Reviewed evidence'})
    assert SelfDevelop(Store(tmp_path/'hub.db')).status(chat)['progress']['semantic_approved'] is True
