"""Authenticated preparation and durable launch of independent control-plane updates."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
import psutil
from .control_plane import stage,read,atomic
from ..development.ownership import candidate_owner

class ControlPlaneJobs:
    def __init__(self,root):
        self.root=Path(root);self.directory=self.root/'control-plane-updates'
        self.directory.mkdir(exist_ok=True)
    def path(self,identifier):
        if not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Invalid update identity')
        p=self.directory/identifier
        if p.is_symlink() or p.is_junction():raise ValueError('Linked update directory')
        return p
    def prepare(self,dev,task,identifier,revision):
        from ..development.selfdevelop import SelfDevelop
        if not SelfDevelop(dev.store).owns(task['id']):raise ValueError('Requires SelfDevelop task')
        m=dev.inspect(task,identifier)
        if m['revision']!=revision:raise ValueError('Candidate revision changed')
        evidence=next((r for r in m['test_results'] if r['revision']==revision and r['verified']),None)
        if not evidence:raise ValueError('Verified current revision required')
        from .control_plane import sha,safe
        live=Path(task['workspace'])
        selected={}
        for change in dev.diff(task,identifier)['files']:
            path=safe(live,change['path'])
            actual=sha(path.read_bytes()) if path.is_file() else None
            if actual not in (change['base_hash'],change['candidate_hash']):
                raise ValueError('Live source diverged from candidate base: '+change['path'])
            selected[change['path']]=change['candidate_hash']
        return stage(self.root,live,Path(m['candidate_path']),selected,evidence)
    def find_prepared(self,dev,task,candidate_id,revision):
        """Reconcile a lost prepare reply against existing verified Guard journals.

        Unique exact live path and changed-file hashes are mandatory. Never
        create a new stage or launch from this read-only lookup.
        """
        from .control_plane import read
        candidate=dev.inspect(task,candidate_id)
        if candidate['revision']!=revision:
            raise ValueError('Candidate revision changed during Guard reconciliation')
        expected={change['path']:change['candidate_hash']
                  for change in dev.diff(task,candidate_id)['files']}
        if not expected:
            raise ValueError('No candidate changes to reconcile')
        matches=[]
        for folder in self.directory.iterdir():
            if not folder.is_dir() or folder.is_symlink() or folder.is_junction():
                continue
            if not re.fullmatch('[a-f0-9]{32}',folder.name):
                continue
            try:
                manifest=read(folder)
                if Path(manifest['live']).resolve()!=Path(task['workspace']).resolve():
                    continue
                selected={entry['path']:entry['new'] for entry in manifest['changes']}
                if selected!=expected:
                    continue
                matches.append(self.status(folder.name))
            except (OSError,ValueError,KeyError,TypeError):
                continue
        if len(matches)!=1:
            raise ValueError('No unique matching Guard journal; explicit reconciliation required')
        return matches[0]

    def status(self,identifier):
        p=self.path(identifier);read(p)
        status=json.loads((p/'status.json').read_text())
        if (p/'launch.json').exists():
            launch=json.loads((p/'launch.json').read_text());alive=False
            if launch.get('pid'):
                try:alive=psutil.Process(launch['pid']).create_time()==launch['created']
                except psutil.Error:pass
            status.update(supervisor_alive=alive,supervisor_pid=launch.get('pid'))
            if not alive and status['state'] not in ('ACTIVE_VERIFIED','ROLLED_BACK'):
                status['recovery_required']=True
        return status
    def submit(self,identifier,request_id,recover=False):
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise ValueError('Stable request ID required')
        p=self.path(identifier);read(p)
        with candidate_owner(self.directory,'Control plane launch'):
            current=self.status(identifier)
            launchpath=p/'launch.json'
            if launchpath.exists():
                old=json.loads(launchpath.read_text())
                if old['request_id']==request_id:
                    if old['recover']!=recover:raise ValueError('Request identity conflict')
                    return current
                if current.get('supervisor_alive'):raise ValueError('Supervisor is still running')
                if not recover:raise ValueError('Inspect/recover previous launch; do not repeat it')
            if current['state'] in ('ACTIVE_VERIFIED','ROLLED_BACK'):return current
            if not recover and current['state']!='PREPARED':raise ValueError('Explicit recovery required')
            gate=self.root/'state'/'control-plane-admission.json'
            gate.parent.mkdir(exist_ok=True)
            if gate.exists() and json.loads(gate.read_text()).get('update_id')!=identifier:
                raise ValueError('Another update holds task admission')
            atomic(gate,{'update_id':identifier})
            launch={'request_id':request_id,'recover':recover,'requested':time.time()}
            atomic(launchpath,launch)
            command=[sys.executable,str(p/'supervisor.py'),str(p)]
            if recover:command.append('--recover')
            with (p/'supervisor.log').open('ab') as out:
                proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=out,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            launch.update(pid=proc.pid,created=psutil.Process(proc.pid).create_time())
            atomic(launchpath,launch)
            return self.status(identifier)
