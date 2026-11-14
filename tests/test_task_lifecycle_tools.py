from types import SimpleNamespace
import pytest
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.task_lifecycle import preview,remove,bound
def test_scope_revision_and_history_removal(tmp_path):
 s=Store(tmp_path/'state.db');Conversations(s)
 t=s.create('disposable','x','inspect','lifecycle-test')
 with s.connect() as db:
  db.execute("INSERT INTO chat_tasks VALUES(?,?,?)",('chat',t['id'],0))
 t=s.update(t['id'],expected=t['revision'],state='cancelled')
 e=SimpleNamespace(jobs={})
 assert preview(s,e,'chat',t['id'])['can_delete']
 with pytest.raises(Conflict):bound(s,'other',t['id'])
 with pytest.raises(Conflict):remove(s,e,'chat',t['id'],t['revision'],False)
 with pytest.raises(Conflict):remove(s,e,'chat',t['id'],t['revision']-1,True)
 assert remove(s,e,'chat',t['id'],t['revision'],True)['removed_from_chat']
 assert s.get(t['id'])['state']=='cancelled'
 with pytest.raises(Conflict):bound(s,'chat',t['id'])
