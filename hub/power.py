"""Owned service drain before Windows power, plus shared logon policy."""
import contextlib
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from . import service_health as h

SETTINGS=h.STATE/'power-settings.json'
TRANSITION=h.STATE/'power-transition.json'
SESSION=h.STATE/'agent-session-boot.json'
EMBER=Path('E:/EmberVideo/app')

@contextlib.contextmanager
def lock():
 k=ctypes.windll.kernel32
 k.CreateMutexW.restype=ctypes.c_void_p;k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
 k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
 handle=k.CreateMutexW(None,False,'Local\\MellowCodexPowerSettings')
 if not handle:raise RuntimeError('Power settings lock unavailable')
 acquired=k.WaitForSingleObject(handle,0) in (0,128)
 try:
  if not acquired:raise RuntimeError('Another startup setting operation is active')
  yield
 finally:
  if acquired:k.ReleaseMutex(handle)
  k.CloseHandle(handle)

def settings():
 d=h.read(SETTINGS)
 return dict(schema_version=1,revision=d.get('revision',0),start_with_windows=d.get('start_with_windows',True))

def scheduled(action='Status'):
 p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(h.SOURCE/'manage-agent-startup.ps1'),'-Action',action],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 if p.returncode:raise RuntimeError('Owned startup task '+action+' failed; Windows authorization or task ownership needs attention. '+p.stderr[-400:])
 return json.loads(p.stdout)

def startup_status():
 d=settings()
 try:actual=scheduled()
 except Exception as exc:actual=dict(verified=False,reason=str(exc))
 d['scheduled_task']=actual
 d['effective']=bool(actual.get('exists') and actual.get('owned') and actual.get('enabled')) if actual.get('verified') else None
 d['registration_required']=not actual.get('exists',False)
 d['consistent']=d['effective']==d['start_with_windows']
 d['applies']='Next user logon; existing running services are not stopped. Protected OwnerBroker remains Windows-managed.'
 return d

def set_startup(enabled,expected_revision):
 if type(enabled) is not bool:raise ValueError('start_with_windows must be boolean')
 with lock():
  old=settings()
  if expected_revision!=old['revision']:raise RuntimeError('Startup revision changed; refresh before saving')
  h.write(h.STATE/'startup-operation.json',dict(state='prepared',before=old,desired=enabled,at=time.time()))
  try:
   actual=scheduled('Enable' if enabled else 'Disable')
   if not actual.get('owned') or actual.get('enabled')!=enabled:raise RuntimeError('Scheduled task readback mismatch')
   # Disabling next-logon startup does not suspend recovery of this live session.
   if h.inventory().get('hub'):manual_session()
   h.write(SETTINGS,{**old,'revision':old['revision']+1,'start_with_windows':enabled})
   h.write(h.STATE/'startup-operation.json',dict(state='applied',revision=old['revision']+1,at=time.time()))
  except Exception as exc:
   h.write(h.STATE/'startup-operation.json',dict(state='failed',reason=str(exc)[:500],at=time.time()))
   raise
 return startup_status()

def manual_session():
 h.write(SESSION,dict(boot_time=h.psutil.boot_time(),at=time.time()))

def same_boot(recorded):
 # Windows boot_time samples can differ by microseconds across processes.
 # A 10ms tolerance covers clock sampling jitter, not another boot.
 if type(recorded) not in (int,float) or not math.isfinite(recorded):return False
 return abs(recorded-h.psutil.boot_time())<.01

def transition_active():
 d=h.read(TRANSITION)
 return same_boot(d.get('boot_time')) and d.get('state') in ('draining','dispatch_intent','windows_requested')

def recovery_allowed():
 return not transition_active() and (settings()['start_with_windows'] or same_boot(h.read(SESSION).get('boot_time')))

def ember(action='status'):
 if not EMBER.exists():return dict(ok=True,not_installed=True,services={})
 python=EMBER/'.venv/Scripts/python.exe'
 adapter=h.SOURCE/'scripts/skills/ember-video-services/tool.py'
 if not python.is_file() or not adapter.is_file():raise RuntimeError('Ember lifecycle adapter unavailable; cannot verify safe shutdown')
 p=subprocess.run([str(python),str(adapter),action,'all'],cwd=EMBER,capture_output=True,text=True,encoding='utf8',timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 try:d=json.loads(p.stdout)
 except ValueError:raise RuntimeError('Ember lifecycle returned no valid status')
 if p.returncode or not d.get('ok'):raise RuntimeError('Ember refused '+action+': '+str(d.get('error','service state not verified'))[:300])
 return d

def preview(action):
 if action not in ('shutdown','restart'):raise ValueError('Choose shutdown or restart')
 try:e=ember();ember_state={k:dict(running=v.get('running'),installed=v.get('installed')) for k,v in e.get('services',{}).items()};error=None
 except Exception as exc:ember_state={};error=str(exc)
 return dict(action=action,active_tasks=h.active_tasks(),ember=ember_state,blocker=error,
  order=['Ember idle/busy checks and owned service stop','Hub task/terminal/download drain and managed model unload','MCP gateways, Guard, owned SSH relay and Ollama stop','Owned desktop quit','Windows '+action],
  policy='No forced Windows close. Busy Ember or unverified service stop blocks Windows power. OwnerBroker and unrelated Windows services are stopped by Windows, not killed by the agent.',
  startup=settings())

def submit(action,request_id,confirm_tasks=False):
 if action not in ('shutdown','restart'):raise ValueError('Choose shutdown or restart')
 if transition_active():
  prior=h.read(TRANSITION);existing=h.job_status(prior['operation_id'])
  if existing['action']==('ShutdownComputer' if action=='shutdown' else 'RestartComputer'):return existing
  raise RuntimeError('Previous computer power outcome unresolved; no new power action dispatched')
 if not confirm_tasks:raise RuntimeError('Computer power requires explicit impact confirmation')
 tasks=h.active_tasks()
 if (tasks is None or tasks) and not confirm_tasks:raise RuntimeError('Active or unknown task impact: inspect power preview and confirm before requesting computer power')
 return h.submit('ShutdownComputer' if action=='shutdown' else 'RestartComputer','all',request_id,confirm_tasks)

def os_command(action):
 if action not in ('shutdown','restart'):raise ValueError('Invalid power action')
 return [str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/shutdown.exe'),'/s' if action=='shutdown' else '/r','/t','0']

def close_desktop():
 inv=h.inventory().get('desktop',[])
 if any(not p['owned'] for p in inv):raise RuntimeError('Desktop ownership unverified; Windows power blocked')
 if not inv:return
 p=subprocess.run([sys.executable,'-m','hub.browser_ipc','--quit'],cwd=h.SOURCE,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 if p.returncode:raise RuntimeError('Desktop did not accept graceful quit')
 for _ in range(30):
  if not h.inventory().get('desktop'):return
  time.sleep(.5)
 raise RuntimeError('Desktop still running; Windows power blocked')

def execute(job_id):
 rec=h.job_status(job_id)
 action='shutdown' if rec['action']=='ShutdownComputer' else 'restart'
 path=h.JOBS/(job_id+'.json')
 if rec.get('power_dispatch_intent'):raise RuntimeError('Power dispatch outcome uncertain; never replay automatically')
 rec.update(state='running',phase='ember',steps=[],started_at=time.time())
 def record():h.write(path,rec)
 def transition(state):h.write(TRANSITION,dict(operation_id=job_id,boot_time=h.psutil.boot_time(),state=state,at=time.time()))
 record();transition('draining')
 try:
  # Existing Ember manager checks active generation/training before owned stops.
  e=ember('stop')
  if any(x.get('running') for x in e.get('services',{}).values()):raise RuntimeError('Ember stop not verified')
  rec['steps'].append('ember_stopped');rec['phase']='agent_drain';record()
  command=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(h.SOURCE/'reconcile-services.ps1'),'-Action','Stop','-Service','all','-ConfirmTasks','-PowerTransition']
  p=h.execute_controller(command,job_id)
  if p.returncode:
   rec['failure']=h.diagnostics.controller_failure(h,job_id,p.returncode);raise RuntimeError(rec['failure']['reason'])
  observed=h.snapshot();h.verify_result('Stop','all',observed)
  rec['steps'].append('owned_agent_services_stopped');rec['phase']='desktop';record()
  close_desktop();rec['steps'].append('desktop_closed')
  rec.update(phase='windows',power_dispatch_intent=True,reason='All required owned stops verified; dispatching non-forced Windows request');record();transition('dispatch_intent')
  p=subprocess.run(os_command(action),capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  if p.returncode:raise RuntimeError('Windows rejected the power request; exit '+str(p.returncode))
  rec.update(state='windows_requested',reason='Windows accepted '+action+' request. Physical power completion cannot be verified from this running process.')
  transition('windows_requested')
 except Exception as exc:
  rec.update(state='failed',reason=str(exc)[:700])
  transition('failed')
 rec['finished_at']=time.time();record()

def autostart():
 if not settings()['start_with_windows'] or transition_active():return dict(state='disabled')
 if (h.STATE/'agent-manual-stop').exists():return dict(state='intentionally_stopped')
 manual_session()
 for attempt in range(3):
  p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(h.SOURCE/'reconcile-services.ps1'),'-Action','Reconcile','-Service','all'],cwd=h.SOURCE,timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  if p.returncode!=75:break
  time.sleep(2*(attempt+1))
 if p.returncode:raise RuntimeError('Startup reconciliation failed or another lifecycle operation is active; inspect service health')
 if not h.inventory().get('desktop'):
  subprocess.Popen([str(Path(sys.executable).with_name('pythonw.exe')),'-m','hub.desktop_app','--background'],cwd=h.SOURCE,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 return dict(state='started',services='Hub, MCP/Guard gateways, owned SSH relay, Ollama and desktop; intentional service stops remain respected')

def register_mcp(mcp,local,READ,WRITE):
 @mcp.tool(annotations=READ)
 async def computer_power_preview(action:str)->dict:
  """Inspect safe computer shutdown/restart impact. Busy Ember blocks power; local service stop is distinct from powering Windows."""
  return await local('/api/power/preview/'+action,timeout=100)
 @mcp.tool(annotations=WRITE)
 async def computer_power(action:str,request_id:str,confirm_tasks:bool=False)->dict:
  """Explicit user-requested computer shutdown or restart only. Preview impact first; confirm_tasks acknowledges stopping active agent work. Drains Ember/Hub/Ollama/MCP/SSH before non-forced Windows power. Returns durable ID; never repeat uncertain power actions."""
  return await local('/api/power/action',dict(action=action,request_id=request_id,confirm_tasks=confirm_tasks))
 @mcp.tool(annotations=READ)
 async def computer_power_status(operation_id:str)->dict:
  """Read recorded power operation; never replay it."""
  return await local('/api/service-health/action/'+operation_id)
 @mcp.tool(annotations=READ)
 async def agent_startup_status()->dict:
  """Read start-with-Windows preference, actual owned scheduled task and revision."""
  return await local('/api/power/startup')
 @mcp.tool(annotations=WRITE)
 async def agent_startup_set(enabled:bool,expected_revision:int)->dict:
  """Enable/disable agent startup at Windows user logon. Starts the managed agent stack, not optional Ember image models. Does not stop current services or change owner permissions. Read status revision first."""
  return await local('/api/power/startup',dict(enabled=enabled,expected_revision=expected_revision))

if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else ''
 if command=='--recovery-allowed':raise SystemExit(0 if recovery_allowed() else 75)
 elif command=='--manual-session':manual_session()
 elif command=='--autostart':print(json.dumps(autostart()))
 elif command=='--transition-required':raise SystemExit(0 if transition_active() else 1)
 else:raise SystemExit('Unsupported power lifecycle entry')
