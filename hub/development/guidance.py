"""Durable director guidance with revision and consumer-epoch fencing."""
import json
import uuid
from ..store import Conflict, now

class Guidance:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS development_consumers(task_id TEXT PRIMARY KEY,epoch TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS development_guidance(task_id TEXT NOT NULL,revision INTEGER NOT NULL,request_id TEXT NOT NULL,text TEXT NOT NULL,epoch TEXT NOT NULL,consumed_epoch TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,PRIMARY KEY(task_id,revision),UNIQUE(task_id,request_id));
''')
            if 'required_tools' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN required_tools TEXT NOT NULL DEFAULT '[]'")

    def begin(self,task_id):
        epoch=uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute('INSERT INTO development_consumers VALUES(?,?) ON CONFLICT(task_id) DO UPDATE SET epoch=excluded.epoch',(task_id,epoch))
        return epoch

    def status(self,task_id):
        task=self.store.get(task_id)
        with self.store.connect() as db:
            consumer=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            rows=db.execute('SELECT * FROM development_guidance WHERE task_id=? ORDER BY revision',(task_id,)).fetchall()
        return {'task_id':task_id,'task_revision':task['revision'],'task_state':task['state'],'human_request_original':task['goal'],'consumer_epoch':consumer['epoch'] if consumer else '', 'guidance_revision':len(rows),'guidance':[dict(r) for r in rows]}

    def submit(self,task_id,expected_task_revision,expected_revision,consumer_epoch,request_id,text,required_tools=None):
        required_tools=list(dict.fromkeys(required_tools or []))
        import re
        if len(required_tools)>20 or any(not re.fullmatch('[a-z][a-z0-9_]{0,79}',n) for n in required_tools):raise ValueError('Invalid required tool names')
        if not text.strip() or len(text)>8000 or not 1<=len(request_id)<=100:raise ValueError('Invalid guidance text or request identity')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not task:raise KeyError('Task not found')
            old=db.execute('SELECT * FROM development_guidance WHERE task_id=? AND request_id=?',(task_id,request_id)).fetchone()
            if old:
                if old['text']!=text or json.loads(old['required_tools'])!=required_tools:raise Conflict('Guidance request identity reused with different content')
                return dict(old)
            consumer=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            epoch=consumer['epoch'] if consumer else ''
            count,size=db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(text)),0) FROM development_guidance WHERE task_id=?',(task_id,)).fetchone()
            if task['mode']!='code' or task['state'] in ('done','cancelled'):raise Conflict('Task does not accept coding guidance')
            if task['revision']!=expected_task_revision or count!=expected_revision or epoch!=consumer_epoch:raise Conflict('Stale task, guidance revision or consumer epoch; read current guidance status')
            if size+len(text)>20000:raise Conflict('Mandatory guidance budget exceeded; split the task')
            db.execute('INSERT INTO development_guidance(task_id,revision,request_id,text,epoch,created,required_tools) VALUES(?,?,?,?,?,?,?)',(task_id,count+1,request_id,text,epoch,now(),json.dumps(required_tools)))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',(task_id,task['revision'],'guidance_received',json.dumps({'guidance_revision':count+1,'request_id':request_id,'consumer_epoch':epoch}),now()))
        return self.status(task_id)

    def consume(self,task_id,epoch):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            if not current or current['epoch']!=epoch:raise Conflict('Coding consumer was replaced')
            rows=db.execute('SELECT * FROM development_guidance WHERE task_id=? ORDER BY revision',(task_id,)).fetchall()
            fresh=[r for r in rows if r['consumed_epoch']!=epoch]
            if fresh:
                db.execute('UPDATE development_guidance SET consumed_epoch=? WHERE task_id=?',(epoch,task_id))
                db.execute('INSERT INTO events(task_id,revision,kind,data,at) SELECT id,revision,?,?,? FROM tasks WHERE id=?',('guidance_in_packet',json.dumps({'consumer_epoch':epoch,'revisions':[r['revision'] for r in fresh],'meaning':'included in next model packet; not execution confirmation'}),now(),task_id))
        return [dict(r) for r in rows]

    def missing_evidence(self,task_id,actions):
        records=self.status(task_id)['guidance'];missing=[]
        for record in records:
            for name in json.loads(record['required_tools']):
                good=[a for a in actions if a['tool']==name and a['state']=='complete' and a['created']>=record['created'] and isinstance(a.get('result'),dict) and not a['result'].get('error') and a['result'].get('verified') is not False]
                if not good and name not in missing:missing.append(name)
        return missing
