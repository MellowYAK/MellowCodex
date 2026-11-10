"""Independent Hub/MCP updater. This file is copied before changing live code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

def sha(data):return hashlib.sha256(data).hexdigest()

def atomic(path,value):
    temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    with temp.open('w',encoding='utf-8') as out:
        json.dump(value,out);out.flush();os.fsync(out.fileno())
    os.replace(temp,path)

def safe(root,rel):
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts or ':' in rel:raise ValueError('Invalid relative release path')
    result=root/p
    for ancestor in [result,*result.parents]:
        if ancestor==root.parent:break
        if ancestor.is_symlink() or ancestor.is_junction():raise ValueError('Linked release path')
    if not result.resolve().is_relative_to(root.resolve()):raise ValueError('Path leaves release')
    return result

def stage(root,live,source,files,evidence,ports=(8876,8897)):
    root=Path(root).resolve();live=Path(live).resolve();source=Path(source).resolve()
    if not evidence.get('verified'):raise ValueError('Verified candidate tests required')
    for rel,digest in files.items():
        data=safe(source,rel).read_bytes()
        if sha(data)!=digest:raise ValueError('Candidate changed')
        if rel.endswith('.py'):ast.parse(data,filename=rel)
    # Dependency/environment replacement requires an independently prepared venv.
    for rel in ('requirements.lock.txt','pyproject.toml'):
        if rel in files and safe(live,rel).is_file() and sha(safe(live,rel).read_bytes())!=files[rel]:
            raise ValueError('Dependency changes need a separately prepared environment')
    parent=root/'control-plane-updates';parent.mkdir(exist_ok=True)
    identifier=uuid.uuid4().hex;job=parent/identifier;job.mkdir()
    changes=[]
    for rel,digest in files.items():
        new=safe(source,rel).read_bytes();target=safe(live,rel)
        old=target.read_bytes() if target.is_file() else None
        if old is not None and sha(old)==digest:continue
        for folder,data in [('new',new),('old',old)]:
            if data is not None:
                p=safe(job/folder,rel);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        changes.append({'path':rel,'old':sha(old) if old is not None else None,'new':digest})
    if not changes:raise ValueError('No changes to stage')
    (job/'supervisor.py').write_bytes(Path(__file__).read_bytes())
    manifest={'id':identifier,'live':str(live),'root':str(root),'python':sys.executable,'runtime_python':str(Path(getattr(sys,'_base_executable',sys.executable)).resolve()),
              'ports':list(ports),'changes':changes,'supervisor_sha256':sha((job/'supervisor.py').read_bytes())}
    atomic(job/'manifest.json',manifest)
    atomic(job/'status.json',{'state':'PREPARED','id':identifier})
    return {'id':identifier,'state':'PREPARED','changed_paths':[c['path'] for c in changes]}

def read(job):
    manifest=json.loads((job/'manifest.json').read_text())
    if manifest['id']!=job.name:raise ValueError('Release identity mismatch')
    if sha((job/'supervisor.py').read_bytes())!=manifest['supervisor_sha256']:raise ValueError('Supervisor changed')
    for c in manifest['changes']:
        for version in ('new','old'):
            if c[version] and sha(safe(job/version,c['path']).read_bytes())!=c[version]:
                raise ValueError('Release backup/content changed')
    return manifest

def record(job,state,**fields):
    old=json.loads((job/'status.json').read_text())
    old.update(state=state,updated=time.time(),**fields)
    atomic(job/'status.json',old)
    if state in ('ACTIVE_VERIFIED','ROLLED_BACK'):
        gate=job.parent.parent/'state'/'control-plane-admission.json'
        if gate.exists() and json.loads(gate.read_text()).get('update_id')==job.name:gate.unlink()
    return old

def install(job,manifest,rollback=False):
    live=Path(manifest['live'])
    # Validate every file before any mutation; never overwrite unrelated edits.
    for c in manifest['changes']:
        p=safe(live,c['path']);actual=sha(p.read_bytes()) if p.exists() else None
        allowed=(c['old'],c['new']) if rollback else (c['old'],)
        if actual not in allowed:raise ValueError('Live source changed: '+c['path'])
    for c in manifest['changes']:
        p=safe(live,c['path']);digest=c['old'] if rollback else c['new']
        if digest is None:
            if p.exists():p.unlink()
        else:
            data=safe(job/('old' if rollback else 'new'),c['path']).read_bytes()
            p.parent.mkdir(parents=True,exist_ok=True)
            temporary=p.with_name(p.name+'.update-'+uuid.uuid4().hex)
            temporary.write_bytes(data);os.replace(temporary,p)

def listener_owners(connections,ports):
    owners={}
    for entry in connections:
        if entry.pid and entry.status in ('LISTEN','NONE') and not entry.raddr and entry.laddr.port in ports:
            owners.setdefault(entry.laddr.port,set()).add(entry.pid)
    return owners

class Services:
    def __init__(self,manifest):
        self.m=manifest;self.started=[]
    def idle(self):
        dbpath=Path(self.m['root'])/'state'/'hub.sqlite3'
        if dbpath.exists():
            with sqlite3.connect(dbpath) as db:
                if db.execute("SELECT 1 FROM tasks WHERE state IN ('queued','running','verifying','waiting_desktop') LIMIT 1").fetchone():
                    raise ValueError('Active tasks; update refused')
    def owned(self):
        import psutil
        result=[]
        for p in psutil.process_iter():
            try:
                args=p.cmdline()
                if p.pid==os.getpid() or not args:continue
                if Path(p.exe()).resolve() not in {Path(self.m['python']).resolve(),Path(self.m.get('runtime_python',self.m['python'])).resolve()}:continue
                if Path(p.cwd()).resolve()!=Path(self.m['live']).resolve():continue
                if 'hub.app:app' in args or 'hub.mcp_gateway:app' in args or ('-m' in args and 'hub.mcp_gateway' in args):result.append(p)
            except (psutil.Error,OSError):continue
        return result
    def stop(self):
        import psutil
        targets=self.owned()
        for p in targets:
            try:p.terminate()
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(targets,timeout=10)
        if alive:raise RuntimeError('Owned services did not stop')
    def gateway_managed_by_hub(self):
        config=Path(self.m['root'])/'state'/'relay.json'
        return config.is_file() and bool(json.loads(config.read_text(encoding='utf-8')).get('enabled'))
    def start(self):
        import psutil
        if self.owned():raise RuntimeError('Existing owned services still running')
        env=os.environ.copy();env['LOCAL_AGENT_ROOT']=self.m['root'];env['PYTHONUTF8']='1'
        commands=[['-m','uvicorn','hub.app:app','--host','0.0.0.0','--port',str(self.m['ports'][0]),'--no-access-log']]
        if not self.gateway_managed_by_hub():
            commands.append(['-m','uvicorn','hub.mcp_gateway:app','--host','127.0.0.1','--port',str(self.m['ports'][1]),'--no-access-log'])
        self.started=[]
        log=Path(self.m['root'])/'state'/'mellow-guard-services.log'
        log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('ab') as output:
            for args in commands:
                p=subprocess.Popen([self.m['python'],*args],cwd=self.m['live'],env=env,
                    stdin=subprocess.DEVNULL,stdout=output,stderr=output,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.started.append((p.pid,psutil.Process(p.pid).create_time()))
    def healthy(self):
        import httpx,psutil
        until=time.monotonic()+45;stable_since=None
        while time.monotonic()<until:
            if not self.started:return False
            try:
                if not all(psutil.Process(pid).create_time()==created for pid,created in self.started):return False
                expected={pid for pid,_ in self.started}
                for pid,_ in self.started:
                    expected.update(p.pid for p in psutil.Process(pid).children(recursive=True))
                listeners=listener_owners(psutil.net_connections(kind='tcp'),self.m['ports'])
                if set(listeners)!=set(self.m['ports']) or not set().union(*listeners.values()).issubset(expected):
                    stable_since=None;time.sleep(.5);continue
                with httpx.Client(timeout=2,trust_env=False) as client:
                    if client.get('http://127.0.0.1:'+str(self.m['ports'][0])+'/').status_code==200 and client.get('http://127.0.0.1:'+str(self.m['ports'][1])+'/health').status_code==200:
                        if stable_since is None:stable_since=time.monotonic()
                        elif time.monotonic()-stable_since>=2:return True
                    else:stable_since=None
            except psutil.NoSuchProcess:return False
            except (psutil.Error,httpx.HTTPError):pass
            time.sleep(.5)
        return False

def activate(job,driver=None,recover=False):
    job=Path(job);m=read(job);driver=driver or Services(m)
    # All updaters use the same OS-owned fence, outside the replaceable source.
    import msvcrt
    lock=job.parent/'update.lock'
    with lock.open('a+b') as handle:
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        state=json.loads((job/'status.json').read_text())['state']
        if state in ('ACTIVE_VERIFIED','ROLLED_BACK'):return json.loads((job/'status.json').read_text())
        driver.idle()
        if not recover and state!='PREPARED':raise ValueError('Interrupted update requires explicit recovery')
        # Precondition failure must not stop services.
        if not recover:
            for c in m['changes']:
                p=safe(Path(m['live']),c['path'])
                if (sha(p.read_bytes()) if p.exists() else None)!=c['old']:raise ValueError('Live source changed')
        try:
            record(job,'STOPPING');driver.stop()
            if recover:raise RuntimeError('Recovering interrupted update')
            record(job,'INSTALLING');install(job,m)
            record(job,'STARTING');driver.start()
            if not driver.healthy():raise RuntimeError('Updated services failed health check')
            return record(job,'ACTIVE_VERIFIED')
        except Exception as exc:
            record(job,'ROLLING_BACK',error=str(exc))
            try:
                driver.stop();install(job,m,rollback=True);driver.start()
                if not driver.healthy():raise RuntimeError('Previous services failed health check')
                return record(job,'ROLLED_BACK')
            except Exception as rollback:
                return record(job,'RECOVERY_REQUIRED',rollback_error=str(rollback))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('job');parser.add_argument('--recover',action='store_true')
    args=parser.parse_args()
    try:print(json.dumps(activate(Path(args.job),recover=args.recover)))
    except Exception as exc:
        record(Path(args.job),'RECOVERY_REQUIRED',error=str(exc));raise
