"""Local rescue status and durable actions over the existing reconciler."""
import concurrent.futures
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
import threading
from . import health_diagnostics as diagnostics
import urllib.request
import urllib.error
import psutil
from .config import ROOT, STATE, PORT, OLLAMA
SOURCE=Path(__file__).resolve().parents[1]
JOBS=STATE/'service-actions'
GUARD=Path('C:/ProgramData/MellowGuard')
MANAGED=('hub','gateway','guard','guard_gateway','relay','ollama')
LABELS={
 'hub':('Hub','מנוע משימות ושיחות'),
 'gateway':('MCP gateway','חיבור ChatGPT לסוכן'),
 'guard':('Guard','פריסה והתאוששות עצמאית'),
 'guard_gateway':('Guard gateway / OAuth','חיבור והרשאות Guard'),
 'relay':('SSH relay','תיווך מוצפן לחיבור מרחוק'),
 'ollama':('Ollama','שרת המודל המקומי'),
 'model':('מודל','המודל שנבחר והאם הוא טעון'),
 'broker':('OwnerBroker','הרשאות בעלים מוגנות'),
 'recovery':('התאוששות מתוזמנת','בדיקה בכניסה ובכל דקה'),
 'desktop':('מעטפת','הממשק והדפדפן הפנימי')}
def read(path,default=None):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {} if default is None else default
def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def ps(script,timeout=12):
 return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
def api(url):
 try:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=2) as r:
   raw=r.read(300000);return r.status,json.loads(raw) if raw.startswith(b'{') else {}
 except urllib.error.HTTPError as e:return e.code,{}
 except Exception:return None,{}
def config():
 return read(GUARD/'current.json')
def active_tasks():
 import sqlite3
 try:
  with sqlite3.connect('file:'+str(STATE/'hub.sqlite3').replace('\\','/')+'?mode=ro',uri=True,timeout=2) as db:
   rows=db.execute("SELECT id,state FROM tasks WHERE state IN ('running','queued','verifying','waiting_desktop')").fetchall()
  return [{'id':i,'state':s} for i,s in rows]
 except Exception:return None
def verified_venv_launcher(process,expected_source,launcher_executables,interpreter_executables):
 # Windows venv launchers can report a temp cwd while their actual Python
 # child owns the configured source. Require the exact direct-child chain.
 try:
  if Path(process.exe()).resolve() not in launcher_executables:return False
  argv=process.cmdline()
  if len(argv)<3:return False
  for child in process.children():
   if (child.ppid()==process.pid and child.cmdline()[1:]==argv[1:]
       and Path(child.exe()).resolve() in interpreter_executables
       and Path(child.cwd()).resolve()==expected_source):
    return True
 except (psutil.Error,OSError):pass
 return False

def inventory():
 cfg=config();out={}
 modules={'hub':'hub.app:app','gateway':'hub.mcp_gateway','guard':'mellow_guard.mcp_server','guard_gateway':'mellow_guard.gateway','desktop':'hub.desktop_app'}
 for p in psutil.process_iter(['pid','exe','cmdline','cwd']):
  try:
   info=p.info;argv=info['cmdline'] or [];exe=Path(info['exe'] or '.');cwd=Path(info['cwd'] or '.')
   for key,mod in modules.items():
    if any(a==mod or (key=='gateway' and a=='hub.mcp_gateway:app') for a in argv):
     expected=Path(cfg.get('hub_source',str(SOURCE))) if key in ('hub','gateway','desktop') else GUARD/'releases'/str(cfg.get('release_id',''))
     owned=cwd.resolve()==expected.resolve() and exe.resolve() in (Path(cfg.get('hub_python',sys.executable)).resolve(),Path(cfg.get('trusted_base_python',sys.executable)).resolve(),Path(cfg.get('hub_python',sys.executable)).with_name('pythonw.exe').resolve(),Path(cfg.get('trusted_base_python',sys.executable)).with_name('pythonw.exe').resolve()) if key in ('hub','gateway','desktop') else cwd.resolve()==expected.resolve() and exe.resolve() in (Path(cfg.get('trusted_base_python','')).resolve(),(expected/'venv/Scripts/python.exe').resolve())
     out.setdefault(key,[]).append({'pid':p.pid,'owned':owned})
   if exe.resolve()==(ROOT/'tools/ollama/ollama.exe').resolve() and 'serve' in argv:out.setdefault('ollama',[]).append({'pid':p.pid,'owned':True})
  except (psutil.Error,OSError):continue
 # Do not classify an unrelated launcher by name/cwd alone.
 expected=Path(cfg.get('hub_source',str(SOURCE))).resolve()
 launcher=Path(cfg.get('hub_python',sys.executable)).resolve()
 interpreter=Path(cfg.get('trusted_base_python',sys.executable)).resolve()
 launchers={launcher,launcher.with_name('pythonw.exe')}
 interpreters={interpreter,interpreter.with_name('pythonw.exe')}
 for key in ('hub','gateway','desktop'):
  for item in out.get(key,[]):
   if not item['owned']:
    try:item['owned']=verified_venv_launcher(psutil.Process(item['pid']),expected,launchers,interpreters)
    except psutil.Error:pass
 return out

def port_identity(port):
 # Verify the PID accepting our exact loopback TCP connection. New Windows
 # builds can expose bound listeners as NONE and stale LISTEN entries as PID 0.
 try:client=socket.create_connection(('127.0.0.1',port),timeout=.7)
 except OSError:return False,set()
 try:
  # Materialize deferred accept while keeping this bounded probe connection open.
  client.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\n')
  client_port=client.getsockname()[1]
  for _ in range(8):
   owners={c.pid for c in psutil.net_connections(kind='tcp') if c.pid and c.laddr.ip=='127.0.0.1' and c.laddr.port==port and c.raddr and c.raddr.ip=='127.0.0.1' and c.raddr.port==client_port and c.status==psutil.CONN_ESTABLISHED}
   if owners:return True,owners
   time.sleep(.15)
  return True,set()
 except (psutil.Error,OSError):return True,set()
 finally:client.close()

def network(cfg):
 return diagnostics.network(sys.modules[__name__],cfg)

def guard_status(cfg):
 import asyncio
 async def fetch():
  from mcp import ClientSession
  from mcp.client.streamable_http import streamable_http_client, httpx2
  auth=Path(cfg.get('auth_file',''))
  if auth.is_symlink():raise ValueError('Invalid installed credential link')
  auth=auth.resolve(strict=True)
  if not auth.is_relative_to(GUARD.resolve()):raise ValueError('Invalid installed credential path')
  token=auth.read_text(encoding='utf8').strip()
  async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+token},timeout=8,trust_env=False) as client:
   async with streamable_http_client('http://127.0.0.1:'+str(cfg.get('port',8898))+'/mcp',http_client=client) as (rd,wr):
    async with ClientSession(rd,wr) as session:
     await session.initialize()
     result=await session.call_tool('status',{'service_id':'hub'})
     if result.is_error:raise RuntimeError('Guard status rejected')
     data=result.structured_content
     if not data:
      data=json.loads(next(x.text for x in result.content if getattr(x,'type',None)=='text'))
     return {k:data.get(k) for k in ('healthy','owned_pids','started_pids','service_id')}
 async def bounded():return await asyncio.wait_for(fetch(),12)
 try:
  data=asyncio.run(bounded())
  return dict(state='verified',checked_at=time.time(),**data,reason='Authenticated Guard status. healthy describes its supervised Hub pair, not Guard transport reachability.')
 except Exception as exc:return dict(state='unknown',checked_at=time.time(),reason='Guard authenticated status unavailable: '+type(exc).__name__)

def _snapshot():
 now=time.time();cfg=config();inv=inventory()
 probes=concurrent.futures.ThreadPoolExecutor(max_workers=3)
 guard_future=probes.submit(guard_status,cfg);relay_future=probes.submit(relay_status,cfg);network_future=probes.submit(network,cfg)
 guard=guard_future.result()
 ports={'hub':int(cfg.get('hub_port',PORT)),'gateway':int(cfg.get('gateway_port',8897)),'guard':int(cfg.get('port',8898)),'guard_gateway':int(cfg.get('gateway',{}).get('port',8896)),'ollama':int(OLLAMA.rsplit(':',1)[1])}
 paths={'hub':'/','gateway':'/health','guard':'/health','guard_gateway':'/health','ollama':'/api/ps'}
 def probe(key):
  port=ports[key]
  opened,listeners=port_identity(port)
  for attempt in range(2):
   if not opened or listeners:break
   time.sleep(.2*(attempt+1));opened,listeners=port_identity(port)
  status,data=api('http://127.0.0.1:'+str(port)+paths[key]) if opened else (None,{})
  processes=inv.get(key,[])
  owned=bool(listeners) and listeners.issubset({p['pid'] for p in processes if p['owned']})
  state='available' if owned and status==200 else 'unknown' if opened else 'stopped'
  reason='API מגיב ובעלות תהליך אומתה' if state=='available' else 'פורט פתוח; API/בעלות לא אומתו' if opened else 'אין מאזין מקומי'
  if processes and not opened:state='error';reason='תהליך קיים אך אינו מאזין; אין להפעיל עותק נוסף'
  if opened and not owned:reason='פורט תפוס; בעלות על המאזין לא אומתה'
  if key=='guard' and status in (401,404,405):reason='תהליך/פורט זמינים; endpoint הבריאות אינו מאמת MCP. נדרש אימות Guard מרחוק'
  return key,dict(id=key,name=LABELS[key][0],description=LABELS[key][1],state=state,reason=reason,checked_at=now,process_exists=bool(processes),owned=owned,port_open=opened,http_status=status,pids=[p['pid'] for p in processes],actions=['Check','Start','Stop','Restart','Repair']),data
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:probed=list(pool.map(probe,ports))
 services=[s for _,s,_ in probed]
 guard_row=next(x for x in services if x['id']=='guard')
 if guard['state']=='verified':
  guard_row['mcp_api_verified']=True;guard_row['supervisor_healthy']=guard.get('healthy')
  guard_row['state']='available'
  guard_row['reason']='Guard MCP responds; supervised Hub pair healthy' if guard.get('healthy') is True else 'Guard MCP responds, but healthy=false: no pair started by this supervisor' if guard.get('started_pids')==[] else 'Guard MCP responds, but supervised Hub health check failed'
 modeldata=next(d for k,_,d in probed if k=='ollama')
 def row(key,state,reason,**extra):services.append(dict(id=key,name=LABELS[key][0],description=LABELS[key][1],state=state,reason=reason,checked_at=now,actions=['Check'],**extra))
 loaded=bool(modeldata.get('models'));row('model','unknown' if 'models' not in modeldata else 'available' if loaded else 'idle','מודל טעון' if loaded else 'מודל לא טעון — אינו תקלה ב־Ollama',loaded=loaded)
 try:
  b=psutil.win_service_get('MellowOwnerBroker').as_dict();row('broker','available' if b['status']=='running' else 'stopped','שירות בעלים '+b['status']+'; שינוי רק דרך בקרת הבעלים')
 except Exception:row('broker','unknown','לא ניתן לקרוא שירות בעלים')
 try:
  rr=ps("Get-ScheduledTask -TaskName 'MellowCodex Service Recovery' -ErrorAction Stop | Select-Object State | ConvertTo-Json -Compress",5)
  state=json.loads(rr.stdout)['State'];row('recovery','available' if state in (3,4,'Ready','Running') else 'warning','מצב המשימה המתוזמנת: '+str(state))
 except Exception:row('recovery','unknown','מצב המשימה המתוזמנת אינו זמין')
 row('desktop','available' if inv.get('desktop') else 'stopped','תהליך מעטפת קיים' if inv.get('desktop') else 'המעטפת אינה פועלת',process_exists=bool(inv.get('desktop')))
 relay=relay_future.result()
 row('relay',relay['state'],relay['reason'],owned=relay.get('owned'),process_exists=relay.get('running'),tunnel_verified=relay.get('verified',False))
 services[-1]['actions']=['Check','Start','Stop','Restart','Repair']
 report=read(STATE/'service-reconcile.json');remote=read(STATE/'mcp-remote-proof.json')
 remote_age=now-remote.get('verified_at',0);remote_ok=bool(remote.get('verified_at')) and 0<=remote_age<=120
 net=network_future.result();probes.shutdown(wait=True)
 return dict(checked_at=now,services=services,network=net,manual_stop=(STATE/'mcp-manual-stop').exists(),agent_manual_stop=(STATE/'agent-manual-stop').exists(),report={'time':report.get('time'),'state':report.get('state'),'listeners':report.get('listeners'),'error_count':len(report.get('errors',[]))},report_file_mtime=(STATE/'service-reconcile.json').stat().st_mtime if (STATE/'service-reconcile.json').exists() else None,
 remote={'state':'verified' if remote_ok else 'stale' if remote else 'unknown','verified_at':remote.get('verified_at'),'reason':'קריאת MCP וחזרת אישור אושרו' if remote_ok else 'אין אימות MCP מרחוק עדכני; פורט מקומי אינו הוכחה. אם OAuth פג: חבר מחדש את MellowCodex ב־ChatGPT.'},
 guard_supervisor=guard,active_tasks=active_tasks())
_snapshot_lock=threading.Lock()
_snapshot_cache=None

def snapshot():
 global _snapshot_cache
 requested_at=time.time()
 # Share one bounded probe per process. Native UI also serializes requests.
 if not _snapshot_lock.acquire(timeout=45):
  raise RuntimeError('Health inspection busy; previous check still running')
 try:
  if _snapshot_cache and _snapshot_cache['checked_at']>=requested_at:
   import copy
   result=copy.deepcopy(_snapshot_cache)
   result['connectors']={k:diagnostics.connector(sys.modules[__name__],k) for k in diagnostics.CONNECTORS}
   return result
  result=diagnostics.enrich(sys.modules[__name__],_snapshot())
  _snapshot_cache=result
  write(STATE/'health-snapshot.json',result)
  return result
 finally:_snapshot_lock.release()

def compact_status(data):
 keys=('id','name','status','reason','checked_at','evidence_age_seconds','last_success_at','recommended_action','capabilities')
 return {**{k:data.get(k) for k in ('schema_version','checked_at','overall_status','connectors','network','guard_supervisor','active_tasks','reset_scope')},
         'services':[{k:r.get(k) for k in keys} for r in data['services']]}

def job_status(job_id):
 if not isinstance(job_id,str) or len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise ValueError('Invalid action id')
 result=read(JOBS/(job_id+'.json'))
 if not result:raise ValueError('Unknown action id')
 return result
def submit(action,service='mcp',request_id='',confirm_tasks=False):
 if action not in ('Check','Repair','Start','Stop','Restart','Reconnect','Reset','ShutdownComputer','RestartComputer'):raise ValueError('Unknown service action')
 if service not in ('mcp','all',*MANAGED):raise ValueError('This component requires its existing dedicated control')
 if action in ('ShutdownComputer','RestartComputer'):
  if service!='all' or not confirm_tasks:raise ValueError('Computer power requires all-service impact confirmation')
  from .power import transition_active
  if transition_active():raise RuntimeError('Power transition already active; inspect recorded outcome, do not replay')
 if action=='Reset' and service!='all':raise ValueError('Reset applies only to disposable global diagnostic state')
 if not request_id or len(request_id)>120:raise ValueError('Stable request_id required')
 import hashlib
 job_id=hashlib.sha256(request_id.encode()).hexdigest()[:32];JOBS.mkdir(exist_ok=True)
 kernel=ctypes.windll.kernel32
 kernel.CreateMutexW.restype=ctypes.c_void_p
 kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
 kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
 kernel.ReleaseMutex.argtypes=[ctypes.c_void_p]
 kernel.CloseHandle.argtypes=[ctypes.c_void_p]
 handle=kernel.CreateMutexW(None,False,'Local\\MellowCodexServiceActionAdmission')
 if not handle:raise RuntimeError('Cannot acquire action admission mutex')
 if ctypes.windll.kernel32.WaitForSingleObject(handle,0) not in (0,128):ctypes.windll.kernel32.CloseHandle(handle);raise RuntimeError('Another service action is being admitted')
 try:
  path=JOBS/(job_id+'.json')
  if path.exists():
   old=job_status(job_id)
   if (old['action'],old['service'],old.get('confirm_tasks',False))!=(action,service,confirm_tasks):raise ValueError('request_id already used for different action')
   return old
  for p in JOBS.glob('*.json'):
   old=read(p)
   if old.get('state') in ('queued','running'):
    pid=old.get('worker_pid')
    if worker_alive(old):
     if (old.get('action'),old.get('service'),old.get('confirm_tasks',False))==(action,service,confirm_tasks):return old
     raise RuntimeError('Another service action is active: '+old['id'])
    if time.time()-old.get('created_at',0)<15:
     if (old.get('action'),old.get('service'),old.get('confirm_tasks',False))==(action,service,confirm_tasks):return old
     raise RuntimeError('Another service action is starting')
    old.update(state='interrupted',reason='המחשב או המבצע הופסקו; לא בוצע ניסיון חוזר אוטומטי');write(p,old)
  record=dict(id=job_id,action=action,service=service,confirm_tasks=confirm_tasks,state='queued',created_at=time.time(),reason='ממתין לביצוע מקומי מתמשך')
  write(path,record)
  flags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
  proc=subprocess.Popen([sys.executable,'-m','hub.service_health','--run',job_id],cwd=SOURCE,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
  record['worker_pid']=proc.pid;record['worker_created_at']=psutil.Process(proc.pid).create_time();write(path,record);return record
 finally:ctypes.windll.kernel32.ReleaseMutex(handle);ctypes.windll.kernel32.CloseHandle(handle)

def execute_controller(command,job_id):
 # Services outlive this controller. File handles may be inherited safely;
 # PIPE capture can wait forever for EOF after the controller already exited.
 with (JOBS/(job_id+'.controller.log')).open('w',encoding='utf8') as log:
  return subprocess.run(command,timeout=240,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def run(job_id):
 time.sleep(2)
 rec=job_status(job_id)
 if rec.get('power_dispatch_intent'):return
 rec.update(state='running',phase='controller',started_at=time.time(),reason='Executing local service action');write(JOBS/(job_id+'.json'),rec)
 if rec['action'] in ('ShutdownComputer','RestartComputer'):
  from .power import execute
  execute(job_id);return
 try:
  action=rec['action'];service=rec['service']
  if action=='Check':
   if service in ('mcp','all','relay'):rec['ssh_diagnostic']=diagnostics.inspect_ssh(sys.modules[__name__],config())
   result=snapshot()
  elif action=='Reconnect':
   result=snapshot();rec['outcome']='requires_user_action'
   rec['reconnect']={'connector':'guard' if service in ('guard','guard_gateway') else 'mellowcodex','url':'https://chatgpt.com/#settings/Connectors','instruction':'Reconnect only the affected connector in ChatGPT, then run an actual MCP call. Local code cannot complete consent.'}
  elif action=='Reset':
   rec['reset']=diagnostics.reset(sys.modules[__name__],job_id);result=snapshot();rec['outcome']=rec['reset']['outcome']
  elif action=='Repair':
   result=snapshot();steps=diagnostics.plan(result,service);rec['steps']=steps
   for step in steps:
    if step['outcome']!='repair':continue
    command=['powershell.exe','-NoProfile','-NonInteractive','-File',str(SOURCE/'reconcile-services.ps1'),'-Action','Reconcile','-Service',step['service']]
    rec.update(phase='repair_'+step['service']);write(JOBS/(job_id+'.json'),rec)
    p=execute_controller(command,job_id+'-'+step['service'])
    # Recheck without replaying a side effect. Bounded observation backoff only.
    for attempt in range(3):
     time.sleep(attempt+1);result=snapshot()
     row=next(x for x in result['services'] if x['id']==step['service'])
     if row.get('status')=='operational':break
    if p.returncode:step['failure']=diagnostics.controller_failure(sys.modules[__name__],job_id+'-'+step['service'],p.returncode)
    step['outcome']='repaired' if p.returncode==0 and row.get('status')=='operational' else 'failed'
    step['evidence']=dict(status=row.get('status'),reason=row['reason'],checked_at=row['checked_at'])
   rec['outcome']='failed' if any(x['outcome']=='failed' for x in steps) else 'requires_user_action' if any(x['outcome']=='requires_user_action' for x in steps) else 'repaired' if any(x['outcome']=='repaired' for x in steps) else 'unchanged'
   rec['external_verification']={k:v['status'] for k,v in result.get('connectors',{}).items()}
  else:
   tasks=active_tasks()
   if service in ('hub','ollama','all') and action in ('Stop','Restart','Reconnect') and (tasks is None or tasks) and not (service=='all' and rec.get('confirm_tasks')):
    raise RuntimeError('Active tasks or unknown task state; use explicit whole-agent shutdown with task-impact confirmation')
   # Invalidate freshness for affected transports, retaining last successful evidence.
   affected=('mellowcodex',) if service in ('hub','gateway') else ('mellowcodex','guard') if service in ('mcp','all','relay','guard_gateway','guard') else ()
   for name in affected:write(STATE/('connector-invalidated-'+name+'.json'),dict(checked_at=time.time(),operation_id=job_id))

   actual={'Repair':'Reconcile','Reconnect':'Restart'}.get(action,action)
   command=['powershell.exe','-NoProfile','-NonInteractive','-File',str(SOURCE/'reconcile-services.ps1'),'-Action',actual,'-Service',service]
   if rec.get('confirm_tasks') and service=='all':command.append('-ConfirmTasks')
   p=execute_controller(command,job_id)
   if p.returncode:
    rec['failure']=diagnostics.controller_failure(sys.modules[__name__],job_id,p.returncode)
    raise RuntimeError(rec['failure']['reason'])
   rec.update(phase='postconditions');write(JOBS/(job_id+'.json'),rec)
   for attempt in range(3):
    result=snapshot();rec.update(result=result,verification_attempt=attempt+1);write(JOBS/(job_id+'.json'),rec)
    try:
     verify_result(actual,service,result)
     break
    except RuntimeError:
     if attempt==2:raise
     time.sleep(attempt+1)
  rec.update(state='completed',result=result,reason='הפעולה המקומית הסתיימה; יש לבדוק כל רכיב. חיבור מרחוק דורש אימות נפרד')
 except Exception as exc:rec.update(state='failed',reason=str(exc)[:500])
 rec['finished_at']=time.time();write(JOBS/(job_id+'.json'),rec)

def worker_alive(record):
 try:
  p=psutil.Process(record['worker_pid'])
  return abs(p.create_time()-record.get('worker_created_at',0))<.05 and p.cmdline()[-3:]==['hub.service_health','--run',record['id']]
 except (KeyError,psutil.Error):return False

def relay_status(cfg):
 release=GUARD/'releases'/str(cfg.get('release_id',''))
 if release.resolve().parent!=(GUARD/'releases').resolve():return dict(state='error',reason='Invalid installed Guard release')
 script=f"""
$ErrorActionPreference='Stop'
. '{release}/scripts/common.ps1'
$c=(Read-GuardRelease '{GUARD}').config
$env:MELLOW_GUARD_HOME='{GUARD}'
$env:MELLOW_GUARD_AUTH_FILE=$c.auth_file
Set-GuardRelayEnvironment -Config $c
Set-Location '{release}'
& '{release}/venv/Scripts/python.exe' -m mellow_guard.relay status
exit $LASTEXITCODE
"""
 try:
  r=ps(script,12);d=json.loads(r.stdout)
  owned=d.get('owned') is True;running=d.get('state')=='running'
  return dict(state='available' if owned and running else 'stopped' if d.get('state') in ('stopped','disabled') else 'unknown',
   reason='Owned SSH process running; remote MCP must be verified separately' if owned and running else 'Relay state: '+str(d.get('state','unknown')),
   owned=owned,running=running,verified=False,process_verified=owned and running)
 except Exception as exc:return dict(state='unknown',reason='Installed relay status unavailable; '+type(exc).__name__+'; receipt alone is not proof',diagnostic_code=type(exc).__name__)

def challenge():
 nonce=uuid.uuid4().hex
 write(STATE/'mcp-health-challenge.json',dict(nonce=nonce,created_at=time.time()))
 return dict(nonce=nonce,expires_in=120,instruction='Acknowledge this nonce in a second MCP call after receiving it; local ports are not remote proof.')

def acknowledge(nonce):
 d=read(STATE/'mcp-health-challenge.json')
 if nonce!=d.get('nonce') or not 0<=time.time()-d.get('created_at',0)<=120:raise ValueError('Expired or invalid round-trip challenge')
 write(STATE/'mcp-remote-proof.json',dict(verified_at=time.time(),method='authenticated_mcp_client_round_trip'))
 (STATE/'mcp-health-challenge.json').unlink(missing_ok=True)
 return dict(verified=True,expires_in=120)

def register_mcp(mcp,local,READ,WRITE):
 @mcp.tool(annotations=READ)
 async def service_health_status()->dict:
  """Read service health separately: ownership, API, tunnel and fresh remote MCP proof. Also returns task impact and durable action state."""
  return await local('/api/service-health?compact=true',timeout=45)
 @mcp.tool(annotations=WRITE)
 async def service_health_action(action:str,service:str,request_id:str,confirm_tasks:bool=False)->dict:
  """Check/Repair/Start/Stop/Restart/Reset through the existing shared manager. Reconnect returns connector-specific consent instructions without restarting healthy services. MCP stop disconnects this call path; retain durable id and inspect after reconnect. Never changes network or owner permissions."""
  return await local('/api/service-health/action',dict(action=action,service=service,request_id=request_id,confirm_tasks=confirm_tasks))
 @mcp.tool(annotations=READ)
 async def service_health_action_status(action_id:str)->dict:
  """Read durable local service action result after reconnecting. Never replays the action."""
  return await local('/api/service-health/action/'+action_id)
 @mcp.tool(annotations=READ)
 async def service_health_connection_challenge()->dict:
  """Issue a nonce for a two-call MCP round trip; receive it before acknowledging."""
  return await local('/api/service-health/connection/challenge',{})
 @mcp.tool(annotations=WRITE)
 async def service_health_connection_ack(nonce:str)->dict:
  """Acknowledge a nonce actually received through MCP. Never derives success from a local open port."""
  return await local('/api/service-health/connection/ack',dict(nonce=nonce))

 @mcp.tool(annotations=WRITE)
 async def service_health_connector_observation(connector:str,outcome:str,checked_at:float)->dict:
  """Record an ACTUALLY observed external MCP call, naming mellowcodex or guard. Outcome success/oauth_token_invalid_grant/transport_error. Supply actual check time (Unix seconds); never infer from local listeners."""
  return await local('/api/service-health/connector-observation',dict(connector=connector,outcome=outcome,checked_at=checked_at))


def verify_result(action,service,result):
 if action=='Reconcile':action='Start'
 targets={'mcp':['gateway','guard','guard_gateway','relay'],'all':['hub','gateway','guard','guard_gateway','relay','ollama'],'guard':['guard','guard_gateway','relay'],'guard_gateway':['guard_gateway','relay']}.get(service,[service])
 for key in targets:
  row=next(x for x in result['services'] if x['id']==key)
  if action=='Stop':
   if row.get('port_open') or row.get('process_exists') or row.get('state') not in ('stopped','idle'):
    raise RuntimeError('Stop postcondition not verified for '+key)
  elif action in ('Start','Restart'):
   okay=row.get('owned') and (row.get('mcp_api_verified') if key=='guard' else row.get('owned') and row.get('process_exists') if key=='relay' else row.get('http_status')==200)
   if not okay:raise RuntimeError('Start postcondition not verified for '+key)

def preflight(action,service,confirm=False):
 if service=='all' and action in ('Stop','Restart') and not confirm:raise RuntimeError('Whole-agent shutdown requires explicit task-impact confirmation')
 tasks=active_tasks()
 if service in ('hub','ollama','all') and action in ('Stop','Restart') and (tasks is None or tasks) and not (service=='all' and confirm):
  raise RuntimeError('Active tasks or unknown task state; stop refused before changing any service')
 cfg=config();inv=inventory()
 ports={'hub':int(cfg.get('hub_port',PORT)),'gateway':int(cfg.get('gateway_port',8897)),'guard':int(cfg.get('port',8898)),'guard_gateway':int(cfg.get('gateway',{}).get('port',8896)),'ollama':int(OLLAMA.rsplit(':',1)[1])}
 targets=list(ports) if service=='all' else ['gateway','guard','guard_gateway'] if service=='mcp' else ['guard','guard_gateway'] if service in ('guard','guard_gateway') else [service]
 for key in targets:
  if key not in ports:continue
  opened,listeners=port_identity(ports[key])
  owned={p['pid'] for p in inv.get(key,[]) if p['owned']}
  # Windows may transiently omit the accepting PID. Retry observations only;
  # a foreign PID is never retried, adopted or terminated.
  for attempt in range(2):
   if not opened or listeners:break
   time.sleep(.2*(attempt+1))
   opened,listeners=port_identity(ports[key])
   owned={p['pid'] for p in inventory().get(key,[]) if p['owned']}
  if opened and (not listeners or not listeners.issubset(owned)):
   raise RuntimeError('Port ownership unverified for '+key+'; accepting_pids='+str(sorted(listeners))+'; verified_pids='+str(sorted(owned))+'; no mutation performed')
 return {'accepted':True}

def quiesce():
 key=(STATE/'hub.key').read_text(encoding='utf8').strip()
 req=urllib.request.Request('http://127.0.0.1:'+str(PORT)+'/api/service-health/quiesce',data=b'{}',headers={'x-hub-key':key,'Content-Type':'application/json'})
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=8) as response:
  if response.status!=200:raise RuntimeError('Graceful shutdown rejected')
 deadline=time.monotonic()+100
 while time.monotonic()<deadline:
  status,_=api('http://127.0.0.1:'+str(PORT)+'/')
  if status is None:
   tasks=active_tasks()
   if tasks is None or tasks:raise RuntimeError('Hub stopped but task quiescence not verified')
   return
  time.sleep(1)
 raise RuntimeError('Graceful shutdown did not finish; remaining services preserved')

if __name__=='__main__':
 if len(sys.argv)==3 and sys.argv[1]=='--run':run(sys.argv[2])
 elif len(sys.argv)==2 and sys.argv[1]=='--status':print(json.dumps(snapshot(),ensure_ascii=False))
 elif len(sys.argv)==5 and sys.argv[1]=='--preflight':
  print(json.dumps(preflight(sys.argv[2],sys.argv[3],sys.argv[4].lower()=='true')))
 else:raise SystemExit('Expected --status, --preflight ACTION SERVICE true|false, or --run ID')
