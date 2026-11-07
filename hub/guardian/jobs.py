"""Durable requests to an independent supervisor, without a long MCP call."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import psutil
from . import Guardian
from .service import atomic
from ..development.ownership import candidate_owner


class UpgradeJobs:
    def __init__(self,root):
        self.guardian=Guardian(root)
        self.requests=self.guardian.control/'requests';self.requests.mkdir(exist_ok=True)

    def status(self):
        jobs=[]
        for path in sorted(self.requests.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
            job=json.loads(path.read_text(encoding='utf-8'))
            result=self.guardian.control/(job['id']+'.result.json')
            if result.exists():
                job['result']=json.loads(result.read_text(encoding='utf-8'));job['state']=job['result'].get('state','finished')
            elif job.get('pid'):
                try:alive=psutil.Process(job['pid']).create_time()==job['process_created']
                except psutil.Error:alive=False
                job['state']='running' if alive else 'interrupted_outcome_unverified'
            else:job['state']='launch_outcome_unverified'
            jobs.append(job)
        recovered=max((j['created'] for j in jobs if j['operation']=='recover' and j.get('result',{}).get('recovery_verified') is True),default=0)
        for job in jobs:
            if job['created']<recovered and job['state'] in ('launch_outcome_unverified','interrupted_outcome_unverified'):
                job['state']='interrupted_reconciled'
        return {**self.guardian.status(),'requests':jobs}

    def submit(self,operation,release_id,request_id):
        if operation not in ('activate','recover'):raise ValueError('Unsupported upgrade operation')
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100:raise ValueError('Stable request identity required')
        identifier=hashlib.sha256(request_id.encode()).hexdigest()[:32]
        path=self.requests/(identifier+'.json')
        with candidate_owner(self.requests,'Upgrade request'):
            if path.exists():
                old=json.loads(path.read_text(encoding='utf-8'))
                if old['operation']!=operation or old['release_id']!=release_id:raise ValueError('Request identity conflict')
                return next(j for j in self.status()['requests'] if j['id']==identifier)
            if operation=='activate':self.guardian.verify(release_id)
            for job in self.status()['requests']:
                if job['state']=='running':raise ValueError('Another supervisor request is running')
                if operation=='activate' and job['state'] in ('launch_outcome_unverified','interrupted_outcome_unverified'):raise ValueError('Reconcile interrupted supervisor request before activation')
            job={'id':identifier,'operation':operation,'release_id':release_id,'state':'launching','created':time.time()}
            atomic(path,job)
            env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC'}}
            env.update(LOCAL_AGENT_ROOT=str(self.guardian.root),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
            command=[sys.executable,'-m','hub.guardian',operation,'--result',str(self.guardian.control/(identifier+'.result.json'))]
            if release_id:command+=['--release',release_id]
            process=subprocess.Popen(command,cwd=Path(__file__).resolve().parents[2],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            job.update(pid=process.pid,process_created=psutil.Process(process.pid).create_time(),state='running');atomic(path,job)
            return job


def router(root):
    from fastapi import APIRouter
    from pydantic import BaseModel,ConfigDict,Field
    import asyncio
    jobs=UpgradeJobs(root);routes=APIRouter(prefix='/api/upgrades')
    class Activation(BaseModel):
        model_config=ConfigDict(extra='forbid')
        release_id:str=Field(pattern='^[a-f0-9]{32}$')
        request_id:str=Field(min_length=1,max_length=100)
    class Recovery(BaseModel):
        request_id:str=Field(min_length=1,max_length=100)
    @routes.get('/status')
    async def status():return await asyncio.to_thread(jobs.status)
    @routes.post('/activate')
    async def activate(body:Activation):return await asyncio.to_thread(jobs.submit,'activate',body.release_id,body.request_id)
    @routes.post('/recover')
    async def recover(body:Recovery):return await asyncio.to_thread(jobs.submit,'recover',None,body.request_id)
    return routes
