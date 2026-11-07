"""SQLite is authoritative; checkpoint files are projections of committed revisions."""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

class Conflict(ValueError):
    pass

class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, idem TEXT UNIQUE NOT NULL, revision INTEGER NOT NULL,
              state TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL,
              goal TEXT NOT NULL, workspace TEXT NOT NULL, mode TEXT NOT NULL,
              result TEXT NOT NULL DEFAULT '', messages TEXT NOT NULL DEFAULT '[]',
              criteria TEXT NOT NULL DEFAULT '[]', checkpoint TEXT);
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
              revision INTEGER NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS actions (
              id TEXT PRIMARY KEY, task_id TEXT NOT NULL, tool TEXT NOT NULL,
              args TEXT NOT NULL, state TEXT NOT NULL, result TEXT, created TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _decode(self, row):
        if row is None:
            raise KeyError('Task not found')
        item = dict(row)
        for k in ('messages', 'criteria'):
            item[k] = json.loads(item[k])
        return item

    def get(self, task_id):
        with self.connect() as db:
            return self._decode(db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone())

    def list(self):
        with self.connect() as db:
            return [self._decode(r) for r in db.execute('SELECT * FROM tasks ORDER BY created DESC LIMIT 200')]

    def create(self, goal, workspace, mode, idem, criteria=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT * FROM tasks WHERE idem=?', (idem,)).fetchone()
            if existing:
                task = self._decode(existing)
                if (task['goal'], task['workspace'], task['mode'], task['criteria']) != (goal, workspace, mode, criteria or []):
                    raise Conflict('Idempotency key already belongs to a different request')
                return task
            task_id = uuid.uuid4().hex
            stamp = now()
            db.execute('INSERT INTO tasks(id,idem,revision,state,created,updated,goal,workspace,mode,criteria) VALUES(?,?,1,?,?,?,?,?,?,?)',
                       (task_id, idem, 'queued', stamp, stamp, goal, workspace, mode, json.dumps(criteria or [])))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,1,?,?,?)', (task_id,'created',json.dumps({'goal':goal}),stamp))
        return self.get(task_id)

    def update(self, task_id, *, expected=None, kind='state', **fields):
        allowed = {'state','result','messages','checkpoint'}
        if not fields.keys() <= allowed:
            raise ValueError('Unknown task field')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task = self._decode(db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone())
            if expected is not None and expected != task['revision']:
                raise Conflict('Stale revision; refresh the task')
            revision = task['revision'] + 1
            values = {**fields, 'revision': revision, 'updated': now()}
            if 'messages' in values:
                values['messages'] = json.dumps(values['messages'],ensure_ascii=False)
            db.execute('UPDATE tasks SET '+','.join(f'{k}=?' for k in values)+' WHERE id=?', (*values.values(),task_id))
            event_fields = {k:v for k,v in fields.items() if k != 'messages'}
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)', (task_id,revision,kind,json.dumps(event_fields,ensure_ascii=False),now()))
        return self.get(task_id)

    def event(self, task_id, kind, data):
        with self.connect() as db:
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) SELECT id,revision,?,?,? FROM tasks WHERE id=?', (kind,json.dumps(data,ensure_ascii=False),now(),task_id))

    def checkpoint_ref(self, task_id, revision, checkpoint_id):
        with self.connect() as db:
            db.execute('UPDATE tasks SET checkpoint=? WHERE id=? AND revision=?',(checkpoint_id,task_id,revision))

    def latest_event(self, task_id, kind):
        with self.connect() as db:
            row=db.execute('SELECT * FROM events WHERE task_id=? AND kind=? ORDER BY seq DESC LIMIT 1',(task_id,kind)).fetchone()
            return {**dict(row),'data':json.loads(row['data'])} if row else None

    def events(self, task_id, after=0):
        with self.connect() as db:
            return [{**dict(r), 'data':json.loads(r['data'])} for r in db.execute('SELECT * FROM events WHERE task_id=? AND seq>? ORDER BY seq LIMIT 500', (task_id,after))]

    def begin_action(self, task_id, tool, args):
        action_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO actions VALUES(?,?,?,?,?,?,?)', (action_id,task_id,tool,json.dumps(args,ensure_ascii=False),'pending',None,now()))
        return action_id

    def end_action(self, action_id, result):
        with self.connect() as db:
            db.execute('UPDATE actions SET state=?,result=? WHERE id=?', ('complete',json.dumps(result,ensure_ascii=False),action_id))

    def actions(self, task_id):
        with self.connect() as db:
            return [{**dict(r),'args':json.loads(r['args']),'result':json.loads(r['result']) if r['result'] else None} for r in db.execute('SELECT * FROM actions WHERE task_id=? ORDER BY created',(task_id,))]

    def recover(self):
        for task in self.list():
            if task['state'] in ('running','verifying'):
                self.update(task['id'],state='waiting_user',result='Runner restarted. Inspect recorded actions before resuming; uncertain actions are never replayed automatically.')

def file_hash(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()
