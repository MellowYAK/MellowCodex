"""Durable, bounded project indexing queue. No model is required."""
import asyncio
import json
import time
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from ..i18n import CapabilityError

class Indexing:
    def __init__(self,service):
        self.service=service;self.store=service.conversations.store
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS project_index_jobs(project TEXT PRIMARY KEY,enabled INTEGER NOT NULL,state TEXT NOT NULL,updated REAL NOT NULL,result TEXT NOT NULL)''')

            columns={r[1] for r in db.execute('PRAGMA table_info(project_index_jobs)')}
            if 'generation' not in columns:
                db.execute('ALTER TABLE project_index_jobs ADD COLUMN generation INTEGER NOT NULL DEFAULT 0')
            for name,kind,default in [('mode','TEXT',"'apc_baseline'"),('fingerprint','TEXT',"''"),('last_full','REAL','0'),('failures','INTEGER','0'),('retry_after','REAL','0')]:
                if name not in columns:db.execute(f'ALTER TABLE project_index_jobs ADD COLUMN {name} {kind} NOT NULL DEFAULT {default}')

    @contextmanager
    def exclusive(self,project_id):
        self.service.project(project_id)
        folder=self.service.state/'context-locks';folder.mkdir(exist_ok=True)
        lock=sqlite3.connect(folder/(hashlib.sha256(project_id.encode()).hexdigest()+'.sqlite3'),timeout=30)
        try:
            lock.execute('BEGIN IMMEDIATE')
            yield
        finally:
            lock.rollback();lock.close()

    def settings(self,project_id,enabled,mode=None):
        with self.exclusive(project_id):return self._settings(project_id,enabled,mode)

    def _settings(self,project_id,enabled,mode=None):
        self.service.project(project_id)
        if mode not in (None,'fast','apc_baseline'):raise ValueError('Unknown index mode')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT mode,state FROM project_index_jobs WHERE project=?',(project_id,)).fetchone()
            if current and mode and mode!=current['mode'] and current['state']=='running':
                raise ValueError('Index scan running; wait for it to finish before switching mode')
            db.execute("INSERT INTO project_index_jobs(project,enabled,state,updated,result) VALUES(?,?,'not_indexed',?,'{}') ON CONFLICT(project) DO UPDATE SET enabled=excluded.enabled",(project_id,int(enabled),time.time()))
            if mode and (not current or mode!=current['mode']):
                db.execute("UPDATE project_index_jobs SET mode=?,state='queued',result='{}',fingerprint='',last_full=0,generation=generation+1 WHERE project=?",(mode,project_id))
        return self.status(project_id)

    def selected(self,project_id):
        mode=self.status(project_id).get('mode','apc_baseline')
        if mode=='fast':
            from .fast import FastContext
            return FastContext(self.service.state,self.service.conversations)
        return self.service

    def request(self,project_id,enabled=None):
        self.service.project(project_id)
        with self.store.connect() as db:
            db.execute("INSERT INTO project_index_jobs(project,enabled,state,updated,result) VALUES(?,?,'queued',?,'{}') ON CONFLICT(project) DO UPDATE SET generation=project_index_jobs.generation+1,failures=0,retry_after=0,state=CASE WHEN project_index_jobs.state='running' THEN 'running' ELSE 'queued' END",(project_id,int(enabled is not False),time.time()))
        return self.status(project_id)

    def register(self,path,name=None):
        root=Path(path).resolve()
        if root==Path(root.anchor) or not root.is_dir():raise CapabilityError('context.invalid_path')
        project=self.service.conversations.project(str(root),name)
        return {'project':project,'indexing':self.request(project['id'])}

    def record_refresh(self,project_id,result):
        """Direct local/MCP scans update the same visible status as queued scans."""
        with self.store.connect() as db:
            db.execute("INSERT INTO project_index_jobs(project,enabled,state,updated,result,last_full) VALUES(?,1,'ready',?,?,?) ON CONFLICT(project) DO UPDATE SET state='ready',updated=excluded.updated,result=excluded.result,last_full=excluded.last_full,failures=0,retry_after=0 WHERE project_index_jobs.state NOT IN ('queued','running')",(project_id,time.time(),json.dumps(result),time.time()))

    def status(self,project_id):
        self.service.project(project_id)
        with self.store.connect() as db:row=db.execute('SELECT * FROM project_index_jobs WHERE project=?',(project_id,)).fetchone()
        return dict(row)|{'result':json.loads(row['result']),'enabled':bool(row['enabled'])} if row else {'project':project_id,'state':'not_indexed','enabled':False,'mode':'apc_baseline'}

    async def once(self):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT * FROM project_index_jobs WHERE state='queued' OR (enabled=1 AND state='ready' AND updated<?) OR (enabled=1 AND state='failed' AND failures<3 AND retry_after<?) ORDER BY updated LIMIT 1",(time.time()-60,time.time())).fetchone()
            if not row:return False
            db.execute("UPDATE project_index_jobs SET state='running',updated=? WHERE project=?",(time.time(),row['project']))
        try:
            worker=asyncio.create_task(asyncio.to_thread(self._refresh,row))
            try:
                result,fingerprint,last_full,dirty=await asyncio.shield(worker)
            except asyncio.CancelledError:
                # A Python thread cannot be cancelled: retain ownership until it exits.
                try: await worker
                finally:
                    with self.store.connect() as db:
                        db.execute("UPDATE project_index_jobs SET state='queued' WHERE project=?",(row['project'],))
                raise
            state='queued' if dirty else 'ready';failures=0;retry_after=0
        except Exception as exc:
            failures=row['failures']+1;retry_after=time.time()+min(300,30*2**failures)
            result={'error':str(exc),'attempts':failures,'automatic_retry_remaining':max(0,3-failures)};state='failed'
            fingerprint=row['fingerprint'];last_full=row['last_full']
        with self.store.connect() as db:
            db.execute("UPDATE project_index_jobs SET state=CASE WHEN generation>? THEN 'queued' ELSE ? END,updated=?,result=?,fingerprint=?,last_full=?,failures=?,retry_after=? WHERE project=?",(row['generation'],state,time.time(),json.dumps(result),fingerprint,last_full,failures,retry_after,row['project']))
        return True

    def fingerprint(self,project_id):
        from .inventory import walk
        from .service import allowed,safe_path,EXCLUDED
        root=Path(self.service.project(project_id)['path'])
        if not root.is_dir():raise OSError('Project root unavailable; existing index retained')
        selected=self.selected(project_id)
        records=[]
        for rel in walk(root,EXCLUDED,time.monotonic()+30):
            if not selected.allowed(rel):continue
            stat=selected.safe_path(root,rel).stat();records.append((rel,stat.st_size,stat.st_mtime_ns))
        # Parser changes force reconciliation even when source metadata is unchanged.
        parser_hash=hashlib.sha256(Path(__file__).with_name('service.py').read_bytes()+Path(__file__).with_name('fast.py').read_bytes()).hexdigest()
        return hashlib.sha256(json.dumps([parser_hash,sorted(records)],ensure_ascii=False).encode()).hexdigest()

    def _refresh(self,row):
        with self.exclusive(row['project']):return self._refresh_locked(row)

    def _refresh_locked(self,row):
        before=self.fingerprint(row['project'])
        if row['state']=='ready' and before==row['fingerprint'] and time.time()-row['last_full']<600:
            result=json.loads(row['result']);result['background_check']='metadata unchanged; full content reconciliation at least every 10 minutes'
            return result,before,row['last_full'],False
        result=self.selected(row['project']).refresh(row['project'])
        after=self.fingerprint(row['project'])
        return result,after,time.time(),before!=after

    async def watch(self):
        with self.store.connect() as db:db.execute("UPDATE project_index_jobs SET state='queued' WHERE state='running'")
        while True:
            await self.once()
            await asyncio.sleep(2)
