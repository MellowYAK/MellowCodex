"""Single local inference owner with durable diagnostics and resident-model policy."""
import json
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager,contextmanager
import httpx
import psutil
from .config import STATE,OLLAMA
from .development.ownership import candidate_owner


class Resources:
    def __init__(self,state=None):
        self.root=(state or STATE)/'resources';self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'leases.sqlite3'
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS leases(id TEXT PRIMARY KEY,model TEXT,purpose TEXT,pid INTEGER,created REAL,state TEXT,updated REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS managed_models(name TEXT PRIMARY KEY)')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def status(self):
        with self.db() as db:rows=db.execute('SELECT * FROM leases ORDER BY updated DESC LIMIT 20').fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            try:alive=psutil.Process(item['pid']).create_time()==item['created']
            except psutil.Error:alive=False
            item['owner_alive']=alive
            if item['state']=='active' and not alive:item['state']='owner_exited_outcome_unverified'
            result.append(item)
        return {'leases':result,'policy':'one inference request; one managed resident model; never evict unknown external models'}

    @contextmanager
    def owner(self,model,purpose):
        with candidate_owner(self.root,'Model resource'):
            identifier=uuid.uuid4().hex
            with self.db() as db:
                db.execute('INSERT INTO leases VALUES(?,?,?,?,?,?,?)',(identifier,model,purpose,os.getpid(),psutil.Process().create_time(),'active',time.time()))
            state='released'
            try:yield identifier
            except BaseException:
                state='interrupted';raise
            finally:
                with self.db() as db:db.execute('UPDATE leases SET state=?,updated=? WHERE id=?',(state,time.time(),identifier))

    def managed(self,name):
        with self.db() as db:db.execute('INSERT OR IGNORE INTO managed_models VALUES(?)',(name,))

    @asynccontextmanager
    async def inference(self,model,purpose,enabled):
        from .model_memory import matches
        with self.owner(model,purpose):
            if not enabled():raise RuntimeError('Local inference disabled by user; explicit load required')
            with self.db() as db:managed=[r[0] for r in db.execute('SELECT name FROM managed_models')]
            async with httpx.AsyncClient(timeout=30,trust_env=False) as client:
                response=await client.get(OLLAMA+'/api/ps');response.raise_for_status()
                residents=response.json().get('models',[])
                others=[m['name'] for m in residents if not matches(m['name'],model)]
                unknown=[n for n in others if not any(matches(n,m) for m in managed)]
                if unknown:raise RuntimeError('Other externally owned models are resident: '+', '.join(unknown)+'. Explicitly unload or finish that work before loading another model.')
                for name in others:
                    response=await client.post(OLLAMA+'/api/generate',json={'model':name,'keep_alive':0,'stream':False});response.raise_for_status()
                if others:
                    response=await client.get(OLLAMA+'/api/ps');response.raise_for_status()
                    if any(not matches(m['name'],model) for m in response.json().get('models',[])):raise RuntimeError('Previous model is still resident; switch not verified')
            # Persist intent before invoking Ollama so interrupted loads remain traceable.
            if not any(matches(m['name'],model) for m in residents):self.managed(model)
            yield
            # A completed Hub request makes this selected model part of our
            # managed workload even when it was already warm at startup. Other
            # resident models still require explicit ownership before eviction.
            self.managed(model)
