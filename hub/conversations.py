"""Persistent projects and chat-to-task relationships, stored with the task database."""
import json,uuid
from pathlib import Path
from .store import now,Conflict

class Conversations:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,path TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL,pinned INTEGER DEFAULT 0,archived INTEGER DEFAULT 0,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_notes(project_id TEXT PRIMARY KEY,notes TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_tasks(chat_id TEXT NOT NULL,task_id TEXT UNIQUE NOT NULL,position INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS chat_tasks_order ON chat_tasks(chat_id,position);
CREATE TABLE IF NOT EXISTS external_chat_bindings(conversation_key TEXT PRIMARY KEY,chat_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS selfdevelop_chat_modes(chat_id TEXT PRIMARY KEY,mode TEXT NOT NULL CHECK(mode IN ('selfdevelop','normal')),revision INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS selfdevelop_mode_audit(chat_id TEXT NOT NULL,request_id TEXT NOT NULL,from_mode TEXT NOT NULL,to_mode TEXT NOT NULL,from_revision INTEGER NOT NULL,to_revision INTEGER NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(chat_id,request_id));
 CREATE INDEX IF NOT EXISTS actions_task_state ON actions(task_id,state);''')

    def mode_status(self,chat_id):
        with self.store.connect() as db:
            if not db.execute('SELECT 1 FROM chats WHERE id=?',(chat_id,)).fetchone():raise KeyError('Chat not found')
            has_session=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='selfdevelop_sessions'").fetchone()
            session=db.execute('SELECT objective FROM selfdevelop_sessions WHERE chat_id=?',(chat_id,)).fetchone() if has_session else None
            row=db.execute('SELECT mode,revision FROM selfdevelop_chat_modes WHERE chat_id=?',(chat_id,)).fetchone()
            active=[dict(r) for r in db.execute("SELECT t.id,t.state FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND t.state NOT IN ('done','cancelled')",(chat_id,))]
            pending=[r[0] for r in db.execute("SELECT a.id FROM chat_tasks c JOIN actions a ON a.task_id=c.task_id WHERE c.chat_id=? AND a.state='pending'",(chat_id,))]
            audit=db.execute('SELECT COUNT(*) FROM selfdevelop_mode_audit WHERE chat_id=?',(chat_id,)).fetchone()[0]
        return {'chat_id':chat_id,'mode':row['mode'] if row else ('selfdevelop' if session else 'normal'),
                'revision':row['revision'] if row else 0,'selfdevelop_session':bool(session),
                'objective':session['objective'] if session else None,'active_tasks':active,
                'pending_actions':pending,'transitions':audit,'history_preserved':True}

    def mode_for_task(self,task_id):
        with self.store.connect() as db:
            row=db.execute('SELECT chat_id FROM chat_tasks WHERE task_id=?',(task_id,)).fetchone()
            if not row:return 'normal'
        return self.mode_status(row['chat_id'])['mode']

    def switch_mode(self,chat_id,mode,expected_revision,request_id,reason):
        if mode not in ('selfdevelop','normal'):raise ValueError('Invalid mode')
        if type(expected_revision) is not int or expected_revision<0:raise ValueError('Invalid revision')
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise ValueError('Invalid request identity')
        if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise ValueError('Reason required')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM chats WHERE id=?',(chat_id,)).fetchone():raise KeyError('Chat not found')
            if not db.execute('SELECT 1 FROM selfdevelop_sessions WHERE chat_id=?',(chat_id,)).fetchone():raise Conflict('Existing SelfDevelop session required')
            prior=db.execute('SELECT to_mode,reason FROM selfdevelop_mode_audit WHERE chat_id=? AND request_id=?',(chat_id,request_id)).fetchone()
            if prior:
                if prior['to_mode']!=mode or prior['reason']!=reason:raise Conflict('Request ID reused with different intent')
            else:
                row=db.execute('SELECT mode,revision FROM selfdevelop_chat_modes WHERE chat_id=?',(chat_id,)).fetchone()
                original=row['mode'] if row else 'selfdevelop';rev=row['revision'] if row else 0
                if rev!=expected_revision:raise Conflict('Stale chat mode revision')
                if original==mode:raise Conflict('Chat is already in requested mode')
                if db.execute("SELECT 1 FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND t.state NOT IN ('done','cancelled') LIMIT 1",(chat_id,)).fetchone():raise Conflict('Finish or review all active tasks before switching mode')
                if db.execute("SELECT 1 FROM chat_tasks c JOIN actions a ON a.task_id=c.task_id WHERE c.chat_id=? AND a.state='pending' LIMIT 1",(chat_id,)).fetchone():raise Conflict('Reconcile uncertain actions before switching mode')
                has_run=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='selfdevelop_objective_runs'").fetchone()
                if has_run:
                    run=db.execute('SELECT phase FROM selfdevelop_objective_runs WHERE chat_id=?',(chat_id,)).fetchone()
                    if run and run['phase'] not in ('completed','cancelled','reported','failed'):raise Conflict('Active development objective must complete or be explicitly resolved')
                db.execute('INSERT INTO selfdevelop_chat_modes VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET mode=excluded.mode,revision=excluded.revision',(chat_id,mode,rev+1))
                db.execute('INSERT INTO selfdevelop_mode_audit VALUES(?,?,?,?,?,?,?,?)',(chat_id,request_id,original,mode,rev,rev+1,reason,now()))
        return self.mode_status(chat_id)

    def project(self,path,name=None):
        path=str(Path(path).resolve())
        if not Path(path).is_dir():raise ValueError('Choose an existing folder on this computer')
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?)',(uuid.uuid4().hex,name or Path(path).name or path,path))
            return dict(db.execute('SELECT * FROM projects WHERE path=?',(path,)).fetchone())
    def bind_project(self,chat_id,path,active_task_id=None):
        """Bind future turns without rewriting historical task workspaces."""
        self.get(chat_id)
        project=self.project(path)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            busy=db.execute("SELECT t.id FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND t.state IN ('queued','running','verifying','waiting_desktop')",(chat_id,)).fetchall()
            if any(r['id']!=active_task_id for r in busy):raise Conflict('Finish the active task before changing its project')
            if active_task_id and not db.execute('SELECT 1 FROM chat_tasks WHERE chat_id=? AND task_id=?',(chat_id,active_task_id)).fetchone():raise ValueError('Task does not belong to chat')
            db.execute('UPDATE chats SET project_id=? WHERE id=?',(project['id'],chat_id))
        if active_task_id:self.store.event(active_task_id,'project_binding_changed',{'project':project,'effective':'next_task'})
        return {'chat_id':chat_id,'project':project,'effective':'next_task','history_preserved':True}

    def create(self,project_id,title='New chat',conversation_key=None):
        if conversation_key is not None:
            conversation_key=conversation_key.strip()
            if not 8<=len(conversation_key)<=512:raise ValueError('Use a stable external conversation key of 8–512 characters')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():raise KeyError('Project not found')
            bound=db.execute('SELECT chat_id FROM external_chat_bindings WHERE conversation_key=?',(conversation_key,)).fetchone() if conversation_key else None
            if bound:
                chat_id=bound['chat_id']
                current=db.execute('SELECT project_id FROM chats WHERE id=?',(chat_id,)).fetchone()
                if not current or current['project_id']!=project_id:raise Conflict('This external conversation already belongs to another project. Use bind_chat_project on its existing chat; do not create a duplicate.')
            else:
                chat_id=uuid.uuid4().hex
                db.execute('INSERT INTO chats(id,project_id,title,created) VALUES(?,?,?,?)',(chat_id,project_id,title,now()))
                if conversation_key:db.execute('INSERT INTO external_chat_bindings VALUES(?,?)',(conversation_key,chat_id))
        return self.get(chat_id)
    def get(self,chat_id):
        with self.store.connect() as db:
            row=db.execute('SELECT c.*,p.path workspace FROM chats c JOIN projects p ON p.id=c.project_id WHERE c.id=?',(chat_id,)).fetchone()
            if not row:raise KeyError('Chat not found')
            result=dict(row)
            ids=[r[0] for r in db.execute('SELECT task_id FROM chat_tasks WHERE chat_id=? ORDER BY position',(chat_id,))]
        result['turns']=[self.store.get(i) for i in ids]
        return result
    def inventory(self):
        with self.store.connect() as db:
            return {'projects':[dict(r) for r in db.execute('SELECT * FROM projects ORDER BY name')], 'chats':[dict(r) for r in db.execute('SELECT * FROM chats ORDER BY pinned DESC,created DESC')]}
    def page(self,chat_id,before=None,limit=30):
        """A bounded chronological viewport; no task-message arrays or history deletion."""
        if not 1<=limit<=60 or before is not None and before<0:raise ValueError('Invalid conversation page')
        with self.store.connect() as db:
            row=db.execute('SELECT c.*,p.path workspace FROM chats c JOIN projects p ON p.id=c.project_id WHERE c.id=?',(chat_id,)).fetchone()
            if not row:raise KeyError('Chat not found')
            result=dict(row)
            total=db.execute('SELECT COUNT(*) FROM chat_tasks WHERE chat_id=?',(chat_id,)).fetchone()[0]
            rows=db.execute('SELECT c.position,t.id,t.revision,t.goal,t.result,t.state,t.mode,t.created,t.updated FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND (? IS NULL OR c.position<?) ORDER BY c.position DESC LIMIT ?', (chat_id,before,before,limit+1)).fetchall()
        result.update(turns=[dict(r) for r in rows[:limit]][::-1],total_turns=total,has_older=len(rows)>limit,
                      next_before=rows[limit-1]['position'] if len(rows)>limit else None,before=before)
        with self.store.connect() as db:
            for task in result['turns']:
                task['attachments']=[]
                for event in db.execute("SELECT kind,data FROM events WHERE task_id=? AND kind IN ('attachments','request_presentation') ORDER BY seq",(task['id'],)):
                    data=json.loads(event['data'])
                    if event['kind']=='attachments':task['attachments'].extend(data.get('files',[]))
                    else:task['presentation']=data
        return result
    def update(self,chat_id,title,pinned,archived):
        self.get(chat_id)
        with self.store.connect() as db:
            db.execute('UPDATE chats SET title=?,pinned=?,archived=? WHERE id=?',(title,pinned,archived,chat_id))
        return self.get(chat_id)
    def append_objective_report(self,chat_id,request_id,message):
        """Atomically persist one completed report turn, never a runnable job."""
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:
            raise ValueError('Invalid report identity')
        if not isinstance(message,str) or not message.strip() or len(message)>8000:
            raise ValueError('A bounded report is required')
        idem='chat:'+chat_id+':objective-report:'+request_id
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            chat=db.execute('SELECT p.path workspace FROM chats c JOIN projects p ON p.id=c.project_id WHERE c.id=?',
                            (chat_id,)).fetchone()
            if not chat:raise KeyError('Chat not found')
            existing=db.execute('SELECT id,goal,result,state FROM tasks WHERE idem=?',(idem,)).fetchone()
            if existing:
                if existing['result']!=message or existing['state']!='done':
                    raise Conflict('Report identity reused with different content')
                return existing['id']
            if db.execute("SELECT 1 FROM chat_tasks c JOIN actions a ON a.task_id=c.task_id WHERE c.chat_id=? AND a.state='pending' LIMIT 1",(chat_id,)).fetchone():
                raise Conflict('Reconcile uncertain chat actions before reporting completion')
            task_id=uuid.uuid4().hex
            stamp=now()
            db.execute('INSERT INTO tasks(id,idem,revision,state,created,updated,goal,workspace,mode,result) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (task_id,idem,1,'done',stamp,stamp,'SelfDevelop objective completion report',
                        chat['workspace'],'inspect',message))
            pos=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM chat_tasks WHERE chat_id=?',
                           (chat_id,)).fetchone()[0]
            db.execute('INSERT INTO chat_tasks VALUES(?,?,?)',(chat_id,task_id,pos))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',
                       (task_id,1,'selfdevelop_objective_report',
                        json.dumps({'request_id':request_id,'source':'supervised_driver'},ensure_ascii=False),stamp))
            return task_id

    def submit(self,chat_id,goal,mode,idem,attachments=None,isolated=False,presentation=None):
        idem='chat:'+chat_id+':'+idem
        # A new turn must not deserialize a year's worth of task message arrays.
        # Retained history remains accessible via the chronological paging API.
        with self.store.connect() as db:
            row=db.execute('SELECT c.*,p.path workspace FROM chats c JOIN projects p ON p.id=c.project_id WHERE c.id=?',(chat_id,)).fetchone()
            if not row:raise KeyError('Chat not found')
            chat=dict(row)
            existing=db.execute('SELECT id,goal,mode FROM tasks WHERE idem=?',(idem,)).fetchone()
            busy=db.execute("SELECT 1 FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND t.state IN ('queued','running','verifying','waiting_desktop') LIMIT 1",(chat_id,)).fetchone()
            uncertain=[r[0] for r in db.execute("SELECT DISTINCT c.task_id FROM chat_tasks c JOIN actions a ON a.task_id=c.task_id WHERE c.chat_id=? AND a.state='pending'",(chat_id,))]
            recent=[dict(r) for r in db.execute('SELECT t.id,t.goal,t.result,t.state FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? ORDER BY c.position DESC LIMIT 12',(chat_id,))][::-1]
            position=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM chat_tasks WHERE chat_id=?',(chat_id,)).fetchone()[0]
        if existing:
            if existing['goal']!=goal or existing['mode']!=mode:raise Conflict('Different message for existing request')
            return self.store.get(existing['id'])
        if not existing:
            with self.store.connect() as db:
                has_sessions=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='selfdevelop_sessions'").fetchone()
                selfdevelop=has_sessions and db.execute('SELECT 1 FROM selfdevelop_sessions WHERE chat_id=?',(chat_id,)).fetchone()
                if selfdevelop and db.execute("SELECT 1 FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND t.state NOT IN ('done','cancelled') LIMIT 1",(chat_id,)).fetchone():
                    raise Conflict('Review or correct the existing SelfDevelop step before creating another task')
        if busy:raise Conflict('This chat is still working; stop or wait before sending another message')
        if uncertain and not isolated:raise Conflict('Reconcile the uncertain previous action before continuing')
        context=[]
        with self.store.connect() as db:
            notes=db.execute('SELECT notes FROM project_notes WHERE project_id=?',(chat['project_id'],)).fetchone()
        if notes and notes[0]:context.append({'role':'user','content':'User-saved project instructions: '+notes[0]})
        for t in ([] if isolated else recent):
            context.extend([{'role':'user','content':t['goal']},
                {'role':'assistant','content':'Historical assistant report (not verified current state; may contain errors). '
                    'Use the original user request and recorded tool evidence when checking this report. '+
                    json.dumps({'source_task_id':t['id'],'state':t['state'],
                                'reported_text':t['result'] or None},ensure_ascii=False)}])
        # File references must survive follow-up turns without embedding binary bytes.
        for t in recent:
            for event in self.store.events(t['id']):
                if event['kind']=='attachments':
                    context.append({'role':'user','content':'Previously attached files (data): '+json.dumps(event['data'],ensure_ascii=False)})
        from .attachments import prepare_attachments
        attached_text,images=prepare_attachments(attachments or [])
        task=self.store.create(goal,chat['workspace'],mode,idem)
        if isolated and uncertain:
            self.store.event(task['id'],'isolated_request',{'unresolved_previous_tasks':uncertain,'replayed':False})
            context.append({'role':'user','content':'This is a separate NEW human request. Earlier tasks have unresolved effects and must not be resumed or replayed. Obtain fresh observations for this request; if it depends on an unresolved effect, stop and explain that dependency.'})
        current={'role':'user','content':goal+('\n\n'+attached_text if attached_text else '')}
        if images:current['images']=images
        self.store.update(task['id'],messages=context+[current])
        if presentation:self.store.event(task['id'],'request_presentation',presentation)
        file_ids=[i['file_id'] for i in attachments or [] if i.get('file_id')]
        if file_ids:
            from .file_library import FileLibrary
            self.store.event(task['id'],'attachments',{'files':[FileLibrary().get(i,ready=True) for i in file_ids]})
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_tasks VALUES(?,?,?)',(chat_id,task['id'],position))
            if position==0:db.execute('UPDATE chats SET title=? WHERE id=?',((presentation or {}).get('text',goal)[:70],chat_id))
        return self.store.get(task['id'])

def migrate_legacy(store):
    c=Conversations(store)
    with store.connect() as db:
        old=[dict(r) for r in db.execute('SELECT t.id,t.goal,t.workspace,t.created FROM tasks t LEFT JOIN chat_tasks ct ON ct.task_id=t.id WHERE ct.task_id IS NULL')]
    for t in old:
        if not Path(t['workspace']).is_dir():continue
        p=c.project(t['workspace']);chat=c.create(p['id'],t['goal'][:70])
        with store.connect() as db:
            db.execute('INSERT OR IGNORE INTO chat_tasks VALUES(?,?,0)',(chat['id'],t['id']))
