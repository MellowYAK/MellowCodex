"""Evidence projection and bounded, read-only recovery diagnostics.

No credentials, raw HTTP headers or prompt content are persisted here.
The existing lifecycle controller remains the sole service mutator.
"""
import concurrent.futures
import json
import socket
import time
import uuid
from pathlib import Path

CONNECTORS = ('mellowcodex', 'guard')
TTL = 120
STATES = {'available':'operational','unknown':'unverified','error':'failed',
          'warning':'degraded','stopped':'failed','idle':'operational'}

def connector(h, name, now=None):
 if name not in CONNECTORS: raise ValueError('Unknown connector')
 now = time.time() if now is None else now
 records=[]
 for p in sorted((h.STATE/'connector-evidence'/name).glob('*.json'))[-256:]:
  d=h.read(p)
  if isinstance(d.get('checked_at'),(int,float)) and d['checked_at']<=now+5: records.append(d)
 if name=='mellowcodex':
  old=h.read(h.STATE/'mcp-remote-proof.json')
  if old.get('verified_at'):records.append(dict(checked_at=old['verified_at'],outcome='success',source='mcp_challenge_ack'))
 records=sorted(records,key=lambda d:d['checked_at'])
 latest=records[-1] if records else {}
 checked=latest.get('checked_at');age=max(0,now-checked) if checked else None
 outcome=latest.get('outcome')
 invalidated=h.read(h.STATE/('connector-invalidated-'+name+'.json')).get('checked_at',0)
 fresh=age is not None and age<=TTL and checked>=invalidated
 state=('operational' if outcome=='success' else 'reauthentication_required' if outcome=='oauth_token_invalid_grant' else 'degraded') if fresh else 'stale' if checked else 'unverified'
 last=max((d['checked_at'] for d in records if d.get('outcome')=='success'),default=None)
 reason=('External MCP response acknowledged' if outcome=='success' else 'Connector rejected OAuth refresh; reconnect this connector in ChatGPT' if outcome=='oauth_token_invalid_grant' else 'External MCP call failed; inspect network and transport separately') if fresh else 'No current external round-trip evidence; this is not a confirmed disconnection'
 return dict(id=name,status=state,checked_at=checked,evidence_age_seconds=age,
             last_success_at=last,reason=reason,source=latest.get('source'),
             recommended_action='Check again' if state=='operational' else 'Reconnect '+name+' in ChatGPT, then verify an actual MCP call' if state=='reauthentication_required' else 'Run a fresh external MCP round trip',
             oauth_state='accepted_at_last_call' if fresh and outcome=='success' else 'reauthentication_required' if fresh and outcome=='oauth_token_invalid_grant' else 'unverified',
             external_round_trip='verified' if fresh and outcome=='success' else 'unverified')


def refresh_connector_evidence(h,data,now=None):
 """Reconcile real external proofs with an already sampled local health snapshot.

 No port, process or local relay response is ever promoted into external proof.
 A previously verified MCP call expires normally; its local service can remain
 healthy without claiming that ChatGPT was seen recently.
 """
 now=time.time() if now is None else now
 connectors={k:connector(h,k,now) for k in CONNECTORS}
 data['connectors']=connectors
 externally_verified=any(c['external_round_trip']=='verified' for c in connectors.values())
 for row in data.get('services',()):
  key=row.get('id')
  dimensions=row.setdefault('dimensions',{})
  if key=='relay':
   dimensions['tunnel']='verified_by_external_call' if externally_verified else 'unverified'
   row['tunnel_verified']=externally_verified
  elif key in ('gateway','guard_gateway'):
   dimensions['connector']=connectors['mellowcodex' if key=='gateway' else 'guard']
  elif key=='guard':
   # Guard returns HTTP 401 to unauthenticated probes on purpose.
   # Upgrade its local evidence only with a fresh ACTUAL authenticated MCP
   # exchange plus verified live process ownership and the protected port.
   proof=connectors['guard']
   dimensions['connector']=proof
   if (row.get('status')=='unverified'
       and row.get('owned') is True and row.get('port_open') is True
       and row.get('http_status')==401
       and proof['external_round_trip']=='verified'):
    row['status']='operational'
    row['reason']='Guard MCP verified externally; owned local protected API responds.'
 local=([ 'degraded' ] if data.get('network',{}).get('state')=='error' else [])+[r.get('status','unverified') for r in data.get('services',())]
 external=[c['status'] for c in connectors.values()]
 priority=('failed','reauthentication_required','degraded','starting','unverified','stale')
 data['local_overall_status']=next((s for s in priority if s in local),'operational')
 data['external_connectors_status']=next((s for s in priority if s in external),'operational')
 data['overall_status']=next((s for s in priority if s in local+external),'operational')
 return data

def observe(h,name,outcome,checked_at,source='external_director'):
 if name not in CONNECTORS:raise ValueError('Unknown connector')
 if outcome not in ('success','oauth_token_invalid_grant','transport_error'):raise ValueError('Unsupported observation')
 if not isinstance(checked_at,(int,float)) or not 0<=time.time()-checked_at<=TTL:raise ValueError('Observation must be current, with its actual check time')
 # Append-only unique events prevent out-of-order clients overwriting newer evidence.
 d=dict(connector=name,outcome=outcome,checked_at=checked_at,source=source)
 h.write(h.STATE/'connector-evidence'/name/(str(int(checked_at*1000000)).zfill(20)+'-'+uuid.uuid4().hex+'.json'),d)
 return connector(h,name)

def capability(service,action):
 managed=('hub','gateway','guard','guard_gateway','relay','ollama','mcp','all')
 if action=='Check':return dict(enabled=True,reason='Read-only inspection')
 if action=='Reconnect':return dict(enabled=service in ('mcp','guard','guard_gateway'),reason='Open ChatGPT connector settings; consent cannot be completed locally')
 if action=='Reset':return dict(enabled=service=='all',reason='Mark dead action workers interrupted and rebuild disposable health cache only')
 return dict(enabled=service in managed,reason='Existing owned-service lifecycle controller' if service in managed else {'broker':'Use Owner Control / Windows authorization','model':'Use Models controls; unloaded is not an outage','recovery':'Use registered recovery task control','desktop':'Use desktop lifecycle controls'}.get(service,'Unsupported service'))

def enrich(h,data):
 now=data['checked_at'];previous=h.read(h.STATE/'health-last-success.json')
 settings=h.read(h.STATE/'model-settings.json')
 connectors={k:connector(h,k,now) for k in CONNECTORS}
 for row in data['services']:
  key=row['id'];status=STATES.get(row['state'],'unverified')
  stopped=(h.STATE/('service-manual-stop-'+key)).exists() or (data.get('agent_manual_stop') and key in h.MANAGED) or (data.get('manual_stop') and key in ('gateway','guard','guard_gateway','relay'))
  if stopped:
   status='degraded' if row.get('process_exists') or row.get('port_open') else 'intentionally_stopped'
  if key=='guard' and row.get('mcp_api_verified'):
   status='operational'
   row['reason']='Authenticated Guard API responds. Supervisor coverage is reported separately.'
  if key=='model':
   row['inference_enabled']=settings.get('inference_enabled')
   status='intentionally_stopped' if settings.get('inference_enabled') is False else 'operational' if row['state']=='idle' else status
   row['reason']='Inference disabled by owner; loaded='+str(row.get('loaded')) if settings.get('inference_enabled') is False else row['reason']
  if row.get('process_exists') and not row.get('port_open') and key in ('hub','gateway','guard','guard_gateway','ollama'):
   ages=[]
   for pid in row.get('pids',[]):
    try:ages.append(now-h.psutil.Process(pid).create_time())
    except h.psutil.Error:pass
   if ages and max(ages)<30:status='starting'
  row['status']=status;row['evidence_age_seconds']=max(0,time.time()-row['checked_at'])
  if status=='operational':previous[key]=now
  row['last_success_at']=previous.get(key)
  row['recommended_action']='None' if status=='operational' else 'Explicit Start to resume' if status=='intentionally_stopped' else 'Inspect evidence before Repair'
  row['capabilities']={a:capability(key,a) for a in ('Check','Start','Stop','Restart','Repair','Reconnect')}
  row['dimensions']=dict(process=dict(exists=row.get('process_exists'),ownership_verified=row.get('owned')),
                         local_api=dict(http_status=row.get('http_status'),authenticated_mcp=row.get('mcp_api_verified')),
                         network=data.get('network',{}).get('state','unknown'))
  if key=='guard':
   row['dimensions']['supervisor']=data['guard_supervisor']
  if key=='relay':
   row['dimensions']['ssh_authentication']=data.get('network',{}).get('ssh_authentication',{'status':'unverified'})
   row['dimensions']['tunnel']='verified_by_external_call' if any(c['external_round_trip']=='verified' for c in connectors.values()) else 'unverified'
   # An owned SSH process alone proves neither authentication nor forwarding.
   row['tunnel_verified']=any(c['external_round_trip']=='verified' for c in connectors.values())
  if key in ('gateway','guard_gateway'):
   row['dimensions']['connector']=connectors['mellowcodex' if key=='gateway' else 'guard']
 h.write(h.STATE/'health-last-success.json',previous)
 data['schema_version']=2
 data['reset_scope']=reset_scope(h)
 return refresh_connector_evidence(h,data,now)

def reset_scope(h):
 records=[]
 for p in h.JOBS.glob('*.json'):
  d=h.read(p)
  if d.get('state') in ('queued','running') and time.time()-d.get('created_at',0)>=15 and not h.worker_alive(d):
   records.append(d.get('id'))
 return dict(stale_operation_ids=records,disposable_files=['health-snapshot.json'],
             preserved='All conversations, projects, skills, credentials, permissions, stop markers, action logs and user work',
             operation='Mark verified dead workers interrupted; delete only the disposable snapshot. No replay.')

def reset(h,own_id):
 scope=reset_scope(h);changed=[]
 for ident in scope['stale_operation_ids']:
  if ident==own_id:continue
  d=h.job_status(ident)
  if d.get('state') in ('queued','running') and not h.worker_alive(d):
   d.update(state='interrupted',reason='Reset verified worker absent; action was not replayed',finished_at=time.time())
   h.write(h.JOBS/(ident+'.json'),d);changed.append(ident)
 (h.STATE/'health-snapshot.json').unlink(missing_ok=True)
 return dict(outcome='repaired' if changed else 'unchanged',scope=scope,changed_operation_ids=changed)

def plan(data,service):
 targets={'all':('hub','gateway','guard','guard_gateway','relay','ollama'),'mcp':('hub','gateway','guard','guard_gateway','relay')}.get(service,(service,))
 steps=[]
 for row in data['services']:
  if row['id'] not in targets:continue
  status=row.get('status',STATES.get(row['state'],'unverified'))
  if status=='intentionally_stopped':outcome='unchanged';reason='Owner stop marker preserved'
  elif status=='operational':outcome='unchanged';reason='Service already operational'
  elif status=='starting':outcome='unchanged';reason='Startup grace period; do not duplicate launch'
  elif row.get('process_exists') or row.get('port_open'):outcome='requires_user_action';reason='Live or unverified owner; inspect before explicit Restart'
  elif row['id']=='relay' and data.get('network',{}).get('ssh_reachable') is not True:outcome='requires_user_action';reason='SSH endpoint not verified reachable; no relay restart'
  elif row['state']=='unknown':outcome='requires_user_action';reason='Diagnostic unavailable is not a confirmed outage'
  else:outcome='repair';reason='Absent service; reconcile owned dependencies once'
  steps.append(dict(service=row['id'],outcome=outcome,reason=reason))
 for name,c in data.get('connectors',{}).items():
  if c['status']!='operational':steps.append(dict(connector=name,outcome='requires_user_action',reason=c['recommended_action']))
 return steps

def network(h,cfg):
 result=dict(state='unknown',checked_at=time.time(),dns=None,ssh_reachable=None,ipv4_conflict=None,
             ipv4_route=None,ipv6_route=None,reason='Network evidence incomplete')
 try:
  r=h.ps("$d=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object AddressState -eq 'Duplicate');$r4=@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue);$r6=@(Get-NetRoute -DestinationPrefix '::/0' -ErrorAction SilentlyContinue);@{duplicate=($d.Count -gt 0);ipv4_route=($r4.Count -gt 0);ipv6_route=($r6.Count -gt 0)}|ConvertTo-Json -Compress",8)
  d=json.loads(r.stdout);result.update(ipv4_conflict=d['duplicate'],ipv4_route=d['ipv4_route'],ipv6_route=d['ipv6_route'])
 except Exception:pass
 def tcp(addr,port,family):
  try:
   with socket.socket(family,socket.SOCK_STREAM) as s:s.settimeout(2);s.connect((addr,port))
   return True
  except OSError:return False
 host=cfg.get('relay',{}).get('host')
 addresses=[]
 if host:
  # DNS resolution has its own process deadline, unlike getaddrinfo's OS timeout.
  import subprocess,sys
  try:
   from .remote_config import PUBLIC
   from urllib.parse import urlsplit
   resolver="import socket,json,sys\nr={}\nfor n,h in [('relay',sys.argv[1]),('public',sys.argv[2])]:\n try:r[n]=[(x[0],x[4][0]) for x in socket.getaddrinfo(h,22,type=socket.SOCK_STREAM)]\n except OSError:r[n]=[]\nprint(json.dumps(r))"
   r=subprocess.run([sys.executable,'-c',resolver,str(host),str(urlsplit(PUBLIC).hostname)],capture_output=True,text=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   resolved=json.loads(r.stdout);addresses=resolved['relay'];result['dns']=bool(resolved['public']);result['relay_name_resolved']=bool(addresses)
  except Exception:
   result['dns']=False
   import ipaddress
   try:
    ip=ipaddress.ip_address(host);addresses=[(socket.AF_INET if ip.version==4 else socket.AF_INET6,str(ip))]
   except ValueError:pass
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  probes=[pool.submit(tcp,ip,443,f) for ip,f in [('1.1.1.1',socket.AF_INET),('8.8.8.8',socket.AF_INET),('2606:4700:4700::1111',socket.AF_INET6),('2001:4860:4860::8888',socket.AF_INET6)]]
  ssh=[pool.submit(tcp,ip,22,f) for f,ip in addresses[:4]]
  values=[p.result() for p in probes]
  result.update(public_ipv4=any(values[:2]),public_ipv6=any(values[2:]),public_probe_results=values)
  result['ssh_reachable']=any(p.result() for p in ssh) if ssh else None
 if result['ipv4_conflict']:result.update(state='error',reason='Windows reports duplicate IPv4 address; owner/network repair required')
 elif result['dns'] is False:result.update(state='error',reason='Relay name resolution failed or timed out; inspect DNS')
 elif result['ipv4_route'] is False:result.update(state='error',reason='No default IPv4 route observed; IPv6 availability is separate')
 elif not result['public_ipv4']:result.update(state='error',reason='Both public IPv4 TCP probes failed; IPv6 '+('works' if result['public_ipv6'] else 'also failed')+'. Router versus host cause is not established.')
 elif result['ssh_reachable'] is False:result.update(state='error',reason='Public IPv4 works but relay SSH endpoint is unreachable')
 elif result['ssh_reachable']:result.update(state='available',reason='Public IPv4 and SSH endpoint reachable; authentication, forwarding and connector OAuth require separate evidence')
 from .remote_config import PUBLIC
 code,payload=h.api(PUBLIC.rstrip('/')+'/health')
 result['forwarded_http_status']=code
 result['forwarding']='verified_http' if code==200 and payload.get('product')=='local_agent' else 'failed' if code in (502,503,504) else 'unverified'
 if result['forwarding']=='failed':result.update(state='error',reason='Public relay returned '+str(code)+'; forwarding/routing/upstream path failed. This does not identify SSH authentication as the cause.')
 result['ssh_authentication']=ssh_evidence(h)
 result['recommended_action']='Inspect route/DNS/adapter and relay; no automatic network changes' if result['state']!='available' else 'Verify external MCP round trip'
 return result

def classify_ssh(returncode,stderr):
 text=stderr.lower()
 if 'authenticated to ' in text:
  return dict(status='operational',code='ssh_authentication_verified',reason='SSH accepted the configured identity. Remote command exit and tunnel forwarding are separate.')
 if 'host key verification failed' in text or 'remote host identification has changed' in text:
  return dict(status='failed',code='ssh_host_key_verification_failed',reason='Verify the relay host key through the existing trusted channel. Host checking remains enabled.')
 if 'permission denied' in text or 'no more authentication methods' in text:
  return dict(status='failed',code='ssh_authentication_failed',reason='SSH rejected the configured identity; inspect key/account authorization. No credentials were changed.')
 if 'connection timed out' in text or 'network is unreachable' in text or 'no route to host' in text:
  return dict(status='failed',code='ssh_network_unreachable',reason='SSH connection did not reach authentication; inspect route and reachability.')
 return dict(status='unverified',code='ssh_authentication_unverified',reason='No authenticated SSH evidence was observed; exit code '+str(returncode))

def inspect_ssh(h,cfg):
 import subprocess
 c=cfg.get('relay',{})
 required=('ssh','identity_file','known_hosts','user','host')
 if not all(c.get(k) for k in required):return dict(status='unverified',code='ssh_configuration_unavailable',checked_at=time.time())
 # Read-only remote command, strict existing host-key policy; never forward,
 # change network settings, prompt for a password, or rewrite known_hosts.
 args=[str(c['ssh']),'-v','-T','-i',str(c['identity_file']),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(c['known_hosts']),'-o','ConnectTimeout=4','-o','ConnectionAttempts=1',str(c['user'])+'@'+str(c['host']),'true']
 try:
  p=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  result=classify_ssh(p.returncode,p.stderr[-32000:])
 except subprocess.TimeoutExpired as exc:
  raw=exc.stderr or b''
  result=classify_ssh(None,raw.decode('utf8',errors='replace') if isinstance(raw,bytes) else raw)
 except OSError:
  result=dict(status='unverified',code='ssh_probe_unavailable',reason='Configured SSH executable could not be started; inspect local installation.')
 result['checked_at']=time.time()
 h.write(h.STATE/'ssh-health-evidence.json',result)
 return result

def ssh_evidence(h):
 d=h.read(h.STATE/'ssh-health-evidence.json')
 if not d:return dict(status='unverified',reason='Use Check all to inspect configured SSH authentication',checked_at=None)
 d['evidence_age_seconds']=max(0,time.time()-d['checked_at'])
 if d['evidence_age_seconds']>TTL:d['status']='stale'
 return d

def controller_failure(h,job_id,code):
 # Only classified reason codes leave the log. Never expose arbitrary stderr.
 path=h.JOBS/(job_id+'.controller.log')
 try:
  with path.open('rb') as f:
   f.seek(max(0,path.stat().st_size-32000));raw=f.read(32000).decode('utf8',errors='replace').lower()
 except OSError:raw=''
 patterns=[('port ownership unverified','ownership_unverified','Listener ownership could not be verified; no unrelated process may be stopped. Inspect accepting PID and retry the check.'),
 ('active tasks','active_work_blocked','Active or unknown work prevents this operation. Inspect tasks and use graceful whole-agent confirmation if intended.'),
 ('ssh relay unreachable','relay_unreachable','Relay SSH endpoint is unreachable. Inspect IPv4/IPv6 and route; healthy services are preserved.'),
 ('ipv4 address conflict','ipv4_address_conflict','Windows reports an IPv4 address conflict. Owner network action is required.'),
 ('intentionally stopped','dependency_intentionally_stopped','A dependency was intentionally stopped; explicitly start that dependency if intended.'),
 ('another service operation','operation_busy','Another controller operation holds the lifecycle mutex; wait for its recorded outcome.'),
 ('restart budget exhausted','relay_retry_budget_exhausted','Relay retry budget is exhausted. Diagnose network/authentication before a further explicit action.')]
 for needle,ident,reason in patterns:
  if needle in raw:return dict(code=ident,reason=reason,controller_log=str(path),exit_code=code)
 return dict(code='controller_failed',reason='Service controller failed; inspect the retained local operation log.',controller_log=str(path),exit_code=code)
