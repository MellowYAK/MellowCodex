import pytest
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop


def test_persistent_session_scoped_steps_and_review_gate(tmp_path):
    store=Store(tmp_path/'test.db');svc=SelfDevelop(store)
    session=svc.start('Inspect the Hub without changing files','test:selfdevelop','mcp')
    assert session['state']=='waiting_director'
    assert session['control_plane_restart_supported']
    assert svc.start('Inspect the Hub without changing files','test:selfdevelop','mcp')['chat_id']==session['chat_id']
    args=dict(chat_id=session['chat_id'],request_id='first-step',instruction='Read the Hub map',
              allowed_tools=['project_brief'],context_read={'operation':'brief'})
    task=svc.step(**args)
    svc.guard(task['id'])
    assert svc.step(**args)['id']==task['id']
    store.update(task['id'],state='waiting_review',result='Observed evidence')
    with pytest.raises(Conflict):svc.step(**{**args,'request_id':'next-step'})
    assert SelfDevelop(Store(tmp_path/'test.db')).status(session['chat_id'])['state']=='waiting_review'
    store.update(task['id'],state='done')
    assert svc.step(**{**args,'request_id':'next-step'})['id']!=task['id']


def test_ordinary_submission_cannot_run_without_director_scope(tmp_path):
    store=Store(tmp_path/'test.db');svc=SelfDevelop(store)
    session=svc.start('Inspect source','test:unguarded','play')
    task=Conversations(store).submit(session['chat_id'],'Do something','code','unguarded')
    with pytest.raises(Conflict):svc.guard(task['id'])
