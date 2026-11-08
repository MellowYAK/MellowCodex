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

def test_external_conversation_reuses_chat_but_never_other_thread(tmp_path):
    c=Conversations(Store(tmp_path/'threads.sqlite3'));p=c.project(str(tmp_path))
    a=c.create(p['id'],conversation_key='chatgpt:thread-a')
    task=c.submit(a['id'],'First request','inspect','first-request',presentation={'text':'בקשה פשוטה','source':'mcp'})
    assert c.page(a['id'])['turns'][0]['presentation']=={'text':'בקשה פשוטה','source':'mcp'}
    assert c.store.get(task['id'])['goal']=='First request'
    c.store.update(task['id'],state='done',result='First result')
    restored=Conversations(Store(c.store.path)).create(p['id'],conversation_key='chatgpt:thread-a')
    assert restored['id']==a['id'] and restored['turns'][0]['id']==task['id']
    assert c.create(p['id'],conversation_key='chatgpt:thread-b')['id']!=a['id']
    assert c.create(p['id'])['id']!=a['id']
    other=tmp_path/'other';other.mkdir();p2=c.project(str(other))
    with pytest.raises(Conflict):c.create(p2['id'],conversation_key='chatgpt:thread-a')
