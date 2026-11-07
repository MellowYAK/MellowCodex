"""Live pipe-backed command sessions; not a graphical terminal emulator."""
import subprocess,threading,uuid,os
from pathlib import Path
from .shell_commands import prepare

class Terminals:
    def __init__(self):self.sessions={}
    def start(self,task,folder,command,shell='powershell'):
        script,argv=prepare(folder,command,shell)
        log=script.with_suffix('.log');out=log.open('wb')
        try:p=subprocess.Popen(argv,cwd=task['workspace'],stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,creationflags=0x08000000 if os.name=='nt' else 0)
        finally:out.close()
        sid=uuid.uuid4().hex
        self.sessions[sid]={'process':p,'log':log,'task_id':task['id'],'shell':shell}
        return self.read(task,sid)
    def get(self,task,sid):
        s=self.sessions[sid]
        if s['task_id']!=task['id']:raise ValueError('Session belongs to a different task')
        return s
    def read(self,task,session_id,offset=0):
        s=self.get(task,session_id);p=s['process']
        if offset<0:raise ValueError('Offset must be nonnegative')
        with s['log'].open('rb') as f:f.seek(offset);data=f.read(20000);end=f.tell()
        return {'session_id':session_id,'shell':s['shell'],'state':'running' if p.poll() is None else 'exited','exit_code':p.poll(),'output':data.decode('utf-8',errors='replace'),'next_offset':end,'artifact':str(s['log']),'note':'Running does not prove waiting for input. Inspect output; no automatic password or host-key acceptance. Pipe session, not a terminal screen.'}
    def write(self,task,session_id,text):
        s=self.get(task,session_id);p=s['process']
        if p.poll() is not None:raise ValueError('Session has exited')
        p.stdin.write(text.encode('utf-8'));p.stdin.flush()
        return self.read(task,session_id)
    def stop(self,task,session_id):
        s=self.get(task,session_id);p=s['process']
        if p.poll() is None:
            import psutil
            parent=psutil.Process(p.pid)
            for child in parent.children(recursive=True):
                try:child.terminate()
                except psutil.NoSuchProcess:pass
            p.terminate();p.wait(timeout=10)
        return self.read(task,session_id)
