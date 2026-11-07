"""Local recurring chat tasks; only explicitly enabled schedules are dispatched."""
import asyncio,time,uuid
from .conversations import Conversations
from .store import Conflict

class Schedules:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,chat_id TEXT NOT NULL,prompt TEXT NOT NULL,mode TEXT NOT NULL,interval_minutes INTEGER NOT NULL,next_run REAL NOT NULL,enabled INTEGER NOT NULL,last_task TEXT)')
    def list(self):
        with self.store.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM schedules ORDER BY next_run')]
    def create(self,project_id,prompt,mode,minutes):
        c=Conversations(self.store);chat=c.create(project_id,'Scheduled: '+prompt[:60]);sid=uuid.uuid4().hex
        with self.store.connect() as db:db.execute('INSERT INTO schedules VALUES(?,?,?,?,?,?,1,NULL)',(sid,chat['id'],prompt,mode,minutes,time.time()+minutes*60))
        return next(s for s in self.list() if s['id']==sid)
    def enable(self,sid,enabled):
        with self.store.connect() as db:
            result=db.execute('UPDATE schedules SET enabled=? WHERE id=?',(enabled,sid))
            if not result.rowcount:raise KeyError('Schedule not found')
    def tick(self,stamp=None):
        stamp=time.time() if stamp is None else stamp;ids=[]
        for s in self.list():
            if not s['enabled'] or s['next_run']>stamp:continue
            try:task=Conversations(self.store).submit(s['chat_id'],s['prompt'],s['mode'],'scheduled-'+s['id']+'-'+str(int(s['next_run'])))
            except Conflict:continue
            with self.store.connect() as db:db.execute('UPDATE schedules SET next_run=?,last_task=? WHERE id=?',(stamp+s['interval_minutes']*60,task['id'],s['id']))
            ids.append(task['id'])
        return ids

async def watch_schedules(engine):
    schedules=Schedules(engine.store)
    while True:
        for task_id in schedules.tick():engine.enqueue(task_id)
        await asyncio.sleep(10)
