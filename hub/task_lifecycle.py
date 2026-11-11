"""Shared explicit task lifecycle controls; no arbitrary deletion of user files."""
from .store import Conflict,now
def bound(store,chat_id,task_id):
 with store.connect() as db:
  if not db.execute('SELECT 1 FROM chat_tasks WHERE chat_id=? AND task_id=?',(chat_id,task_id)).fetchone():raise Conflict('Task does not belong to this chat')
 return store.get(task_id)
def preview(store,engine,chat_id,task_id):
 task=bound(store,chat_id,task_id);job=engine.jobs.get(task_id)
 blocked=task['state'] not in ('done','failed','cancelled') or bool(job and not job.done()) or any(a['state']=='pending' for a in store.actions(task_id))
 return dict(task_id=task_id,chat_id=chat_id,revision=task['revision'],state=task['state'],can_delete=not blocked,scope='Remove this task from this chat history only. Retain task audit, checkpoints, artifacts, files and memory evidence. This is not secure erasure or forgetting.')
def remove(store,engine,chat_id,task_id,revision,confirm):
 if confirm is not True:raise Conflict('Read deletion preview and explicitly confirm its scope')
 p=preview(store,engine,chat_id,task_id)
 if p['revision']!=revision or not p['can_delete']:raise Conflict('Task changed, active, or has uncertain actions; no deletion')
 with store.connect() as db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT revision,state FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not row or row['revision']!=revision or row['state'] not in ('done','failed','cancelled'):raise Conflict('Task changed')
  if db.execute("SELECT 1 FROM actions WHERE task_id=? AND state='pending'",(task_id,)).fetchone():raise Conflict('Uncertain action')
  cur=db.execute('DELETE FROM chat_tasks WHERE chat_id=? AND task_id=?',(chat_id,task_id))
  if cur.rowcount!=1:raise Conflict('Task no longer in this chat')
  import json
  db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',(task_id,revision,'removed_from_chat',json.dumps(dict(chat_id=chat_id,scope=p['scope'])),now()))
 return dict(task_id=task_id,removed_from_chat=True,scope=p['scope'])
