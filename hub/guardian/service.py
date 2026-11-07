"""Journaled immutable patch-worker releases. Never overwrites running source.

This update unit cannot migrate the task DB or replace the control plane/guardian.
The current interpreter environment is fingerprinted; dependency changes require
a separately prepared environment, and are rejected by this first backend.
"""
import hashlib
import asyncio
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from ..development.ownership import candidate_owner
from ..context.service import safe_path


def digest(data):return hashlib.sha256(data).hexdigest()


def atomic(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('x',encoding='utf-8') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
    os.replace(temporary,path)


class Guardian:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.control=self.root/'guardian-control';self.releases=self.root/'releases'
        self.journals=self.control/'upgrades'
        for path in (self.control,self.releases,self.journals):
            if path.is_symlink() or path.is_junction():raise ValueError('Linked guardian storage')
            path.mkdir(parents=True,exist_ok=True)

    def release(self,identifier):
        if not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Invalid release identity')
        path=self.releases/identifier
        if path.is_symlink() or path.is_junction():raise ValueError('Linked release')
        return path

    def verify(self,identifier):
        path=self.release(identifier)
        if (path/'source').is_symlink() or (path/'source').is_junction() or (path/'manifest.json').is_symlink():raise ValueError('Linked release content')
        manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
        if manifest['id']!=identifier or manifest['protocol']!=1:raise ValueError('Release identity/protocol mismatch')
        if manifest.get('interpreter')!=self.interpreter():raise ValueError('Release interpreter environment changed')
        actual=set()
        for folder,dirs,names in os.walk(path/'source',followlinks=False):
            for name in dirs+names:
                p=Path(folder)/name
                if p.is_symlink() or p.is_junction():raise ValueError('Linked release content')
            actual.update((Path(folder)/name).relative_to(path/'source').as_posix() for name in names)
            if len(actual)>15000:raise ValueError('Release inventory exceeded limit')
        if actual!=set(manifest['files']):raise ValueError('Release inventory changed')
        for rel,expected in manifest['files'].items():
            if digest(safe_path(path/'source',rel).read_bytes())!=expected:raise ValueError('Release hash mismatch: '+rel)
        return manifest

    @staticmethod
    def interpreter():
        return {'path':str(Path(sys.executable).resolve()),'version':sys.version,'sha256':digest(Path(sys.executable).read_bytes())}

    def stage(self,source,files,evidence):
        source=Path(source).resolve()
        if not evidence or not evidence.get('verified'):raise ValueError('Verified test evidence required')
        if 'hub/development/worker.py' not in files:raise ValueError('This backend updates only the Hub patch worker')
        trusted=Path(__file__).resolve().parents[2]
        for rel,expected in files.items():
            if rel.startswith('hub/guardian/') or rel in ('requirements.lock.txt','pyproject.toml'):
                baseline=safe_path(trusted,rel)
                if not baseline.is_file() or digest(baseline.read_bytes())!=expected:
                    raise ValueError('Guardian/dependency updates require a separately prepared release')
        identifier=uuid.uuid4().hex;target=self.release(identifier);target.mkdir()
        copied={};total=0
        for rel,expected in files.items():
            data=safe_path(source,rel).read_bytes();total+=len(data)
            if len(data)>1_000_000 or total>50_000_000 or len(copied)>=15000:raise ValueError('Release source budget exceeded')
            if digest(data)!=expected:raise ValueError('Source changed while staging: '+rel)
            output=target/'source'/rel;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data);copied[rel]=expected
        manifest={'id':identifier,'protocol':1,'files':copied,'source_digest':digest(json.dumps(copied,sort_keys=True).encode()),'created':time.time(),'test_evidence':evidence,'unit':'patch-worker','database_migrations':False,'environment':'current-interpreter-unchanged-dependencies','interpreter':self.interpreter()}
        atomic(target/'manifest.json',manifest);self.verify(identifier)
        return manifest

    def pointer(self):
        path=self.control/'active.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'release_id':None,'epoch':0}

    def status(self):
        records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(self.journals.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:20]]
        return {'active':self.pointer(),'updates':records,'unit':'patch-worker','control_plane_replaced':False}

    @contextmanager
    def worker(self):
        # A running short-lived worker holds this fence until its result is collected.
        # Activation fails before mutation while busy; queued work remains queued.
        with candidate_owner(self.control,'Worker routing'):
            if any(j['state'] not in ('ACTIVE_VERIFIED','ROLLED_BACK') for j in self.status()['updates']):
                raise ValueError('Guardian recovery required before admitting another worker')
            pointer=self.pointer()
            if pointer['release_id']:
                manifest=self.verify(pointer['release_id'])
                yield self.release(manifest['id'])/'source',pointer
            else:yield Path(__file__).resolve().parents[2],pointer

    def _record(self,job,state,**fields):
        job.update(fields,state=state,updated=time.time())
        job.setdefault('transitions',[]).append({'state':state,'time':job['updated']})
        atomic(self.journals/(job['id']+'.json'),job)

    def _backup(self,job):
        source=self.root/'state'/'hub.sqlite3'
        if not source.exists():return {'database':'absent; synthetic state'}
        destination=self.journals/(job['id']+'.sqlite3')
        with sqlite3.connect(source) as src,sqlite3.connect(destination) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity failed')
        return {'path':str(destination),'sha256':digest(destination.read_bytes())}

    @staticmethod
    def baseline_identity():
        source=Path(__file__).resolve().parents[2]
        files={p.relative_to(source).as_posix():digest(p.read_bytes()) for p in (source/'hub').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json')}
        return digest(json.dumps(files,sort_keys=True).encode())

    async def _restore(self,job,probe,error):
        old=job['old'];identifier=old['release_id'];nonce=uuid.uuid4().hex
        try:
            if identifier:self.verify(identifier);directory=self.release(identifier)/'source'
            else:
                if job.get('baseline_identity')!=self.baseline_identity():raise ValueError('Baseline source changed; automatic rollback cannot certify it')
                directory=Path(__file__).resolve().parents[2]
            health=await probe(directory,identifier or 'baseline',nonce)
            if not health.get('ready') or health.get('release_id')!=(identifier or 'baseline') or health.get('nonce')!=nonce:raise ValueError('Rollback health identity failed')
            atomic(self.control/'active.json',old)
            self._record(job,'ROLLED_BACK',error=error,rollback_health=health)
        except Exception as exc:
            self._record(job,'RECOVERY_REQUIRED',error=error,rollback_error=type(exc).__name__+': '+str(exc)[:1000])

    async def activate(self,identifier,probe,*,checkpoint=None,stabilization_seconds=60):
        with candidate_owner(self.control,'Worker routing'):
            self.verify(identifier)
            if any(j['state'] not in ('ACTIVE_VERIFIED','ROLLED_BACK') for j in self.status()['updates']):raise ValueError('Recover the previous update first')
            old=self.pointer();job={'id':uuid.uuid4().hex,'old':old,'release_id':identifier,'nonce':uuid.uuid4().hex,'baseline_identity':self.baseline_identity() if old['release_id'] is None else None}
            async def step(state,**fields):
                self._record(job,state,**fields)
                if checkpoint:await checkpoint(state)
            try:
                await step('PREPARED');await step('DRAINED')
                await step('BACKUP_VERIFIED',backup=self._backup(job))
                health=await probe(self.release(identifier)/'source',identifier,job['nonce'])
                if health.get('release_id')!=identifier or health.get('nonce')!=job['nonce'] or not health.get('ready'):
                    raise ValueError('Candidate health identity not verified')
                await step('CANDIDATE_HEALTHY',health=health)
                atomic(self.control/'active.json',{'release_id':identifier,'epoch':old['epoch']+1,'nonce':job['nonce']})
                await step('SWITCHED')
                await step('OBSERVING',stabilization_seconds=stabilization_seconds)
                until=time.monotonic()+stabilization_seconds
                while True:
                    self.verify(identifier)
                    health=await probe(self.release(identifier)/'source',identifier,job['nonce'])
                    if health.get('release_id')!=identifier or health.get('nonce')!=job['nonce'] or not health.get('ready'):raise ValueError('Post-switch health failed')
                    if time.monotonic()>=until:break
                    await asyncio.sleep(min(5,until-time.monotonic()))
                await step('ACTIVE_VERIFIED',health=health)
            except Exception as exc:
                await self._restore(job,probe,type(exc).__name__+': '+str(exc)[:1000])
            return job

    async def recover(self,probe):
        with candidate_owner(self.control,'Worker routing'):
            recovered=[]
            for job in self.status()['updates']:
                if job['state'] in ('ACTIVE_VERIFIED','ROLLED_BACK'):continue
                await self._restore(job,probe,'Interrupted activation. Task database was not restored or overwritten.')
                recovered.append(job)
            return {'recovered':recovered,'recovery_verified':all(j['state']=='ROLLED_BACK' for j in recovered),'active':self.pointer()}
