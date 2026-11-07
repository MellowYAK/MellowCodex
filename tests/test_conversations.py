import pytest
from hub.conversations import Conversations,migrate_legacy
from hub.store import Store,Conflict

def test_persistent_chat_context_and_isolation(tmp_path):
    s=Store(tmp_path/'db.sqlite3');c=Conversations(s);p=c.project(str(tmp_path))
    a=c.create(p['id']);b=c.create(p['id'])
    t=c.submit(a['id'],'Remember kiwi','inspect','request-one')
    s.update(t['id'],state='done',result='Remembered kiwi')
    t2=c.submit(a['id'],'What did I say?','inspect','request-two')
    assert any(m['content']=='Remember kiwi' for m in t2['messages'])
    history=[m['content'] for m in t2['messages'] if m['role']=='assistant']
    assert len(history)==1 and 'not verified current state' in history[0]
    assert t['id'] in history[0] and 'Remembered kiwi' in history[0]
    assert s.get(t['id'])['result']=='Remembered kiwi'
    assert c.get(b['id'])['turns']==[]
    assert Conversations(Store(s.path)).get(a['id'])['turns'][-1]['id']==t2['id']
    assert c.submit(a['id'],'What did I say?','inspect','request-two')['id']==t2['id']
    with pytest.raises(Conflict):c.submit(a['id'],'another','inspect','request-three')
    c.update(a['id'],'renamed',True,True)
    assert c.get(a['id'])['pinned']==1

def test_legacy_migration_idempotent(tmp_path):
    s=Store(tmp_path/'db.sqlite3');t=s.create('old',str(tmp_path),'code','legacy-key')
    migrate_legacy(s);migrate_legacy(s)
    c=Conversations(s)
    assert len(c.inventory()['chats'])==1
    assert c.get(c.inventory()['chats'][0]['id'])['turns'][0]['id']==t['id']
