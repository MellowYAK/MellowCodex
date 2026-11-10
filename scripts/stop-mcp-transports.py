"""Stop only installed MCP transports, preserving Hub, desktop and inference."""
import argparse
import json
import subprocess
from pathlib import Path

import psutil

parser=argparse.ArgumentParser()
parser.add_argument('--service',choices=('mcp','all','hub','gateway','guard','guard_gateway','relay','ollama'),default='mcp')
parser.add_argument('--confirm-tasks',action='store_true')
args=parser.parse_args()
service=args.service
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.service_health import preflight,quiesce,active_tasks
preflight('Stop',service,args.confirm_tasks)
if service=='all':
    from hub.service_health import api,PORT
    code,_=api('http://127.0.0.1:'+str(PORT)+'/')
    if code==200:quiesce()
    elif active_tasks() is None or active_tasks():raise RuntimeError('Hub unavailable with active/unknown tasks; no service stopped')

home = Path('C:/ProgramData/MellowGuard')
cfg = json.loads((home / 'current.json').read_text(encoding='utf-8-sig'))
release = home / 'releases' / cfg['release_id']
if release.resolve().parent != (home / 'releases').resolve():
    raise RuntimeError('Invalid release path')
# Use the signed relay ownership implementation and installed environment loader.
ps = f'''
$ErrorActionPreference='Stop'
. '{release}/scripts/common.ps1'
$c=(Read-GuardRelease '{home}').config
$env:MELLOW_GUARD_HOME='{home}'
$env:MELLOW_GUARD_AUTH_FILE=$c.auth_file
Set-GuardRelayEnvironment -Config $c
Set-Location '{release}'
& '{release}/venv/Scripts/python.exe' -m mellow_guard.relay stop
exit $LASTEXITCODE
'''
if service in ('mcp','all','guard','guard_gateway','relay'):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps], capture_output=True, text=True, check=True)
    state = json.loads(result.stdout)
    if state['state'] not in ('stopped', 'disabled'):
        raise RuntimeError('Relay ownership conflict; nothing else stopped')

def stop_tree(root, argv):
    children = [p for p in root.children(recursive=True) if p.name().lower() != 'conhost.exe']
    # venv launchers have interpreter children; require identical invocation.
    for child in children:
        if child.cmdline()[1:] != argv[1:] or Path(child.exe()).resolve() not in (Path(cfg['trusted_base_python']).resolve(),Path(root.exe()).resolve()):
            raise RuntimeError('Unexpected child; refusing stop')
    for process in reversed(children):
        process.terminate()
    root.terminate()
    _, alive = psutil.wait_procs(children + [root], timeout=10)
    if alive:
        raise RuntimeError('Transport did not stop')

for filename, module in [('gateway-process.json','mellow_guard.gateway'),('process.json','mellow_guard.mcp_server')]:
    if service not in ('mcp','all','guard') and not (service=='guard_gateway' and filename=='gateway-process.json'):continue
    path = home / 'state' / filename
    if not path.exists():
        continue
    rec = json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        proc = psutil.Process(rec['pid'])
    except psutil.NoSuchProcess:
        continue
    expected_time = (int(rec['started_utc_ticks']) / 10000000) - 62135596800
    if abs(proc.create_time() - expected_time) > .05:
        continue  # stale PID; reconciler archives receipt on next start
    if Path(proc.exe()).resolve() != Path(rec['executable']).resolve() or proc.cmdline()[1:] != ['-m',module]:
        raise RuntimeError('Guard receipt mismatch')
    stop_tree(proc, proc.cmdline())

python = Path(cfg['hub_python']).resolve()
allowed = [
    ['-m','uvicorn','hub.mcp_gateway:app','--host','127.0.0.1','--port',str(cfg['gateway_port']),'--no-access-log'],
    ['-m','hub.mcp_gateway'],
]
for proc in (psutil.process_iter(['exe','cmdline']) if service in ('mcp','all','gateway') else []):
    try:
        if proc.info['exe'] and Path(proc.info['exe']).resolve() == python and proc.info['cmdline'][1:] in allowed:
            stop_tree(proc, proc.info['cmdline'])
    except psutil.NoSuchProcess:
        pass
if service in ('hub','ollama','all'):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from hub.service_health import active_tasks
    tasks=active_tasks()
    if tasks is None or tasks:raise RuntimeError('Active tasks or unknown task state; stop refused')
    targets={'hub':[['-m','uvicorn','hub.app:app','--host','127.0.0.1','--port',str(cfg['hub_port']),'--no-access-log'],['-m','hub.app']], 'ollama':[['serve']]}
    # The existing independent update supervisor uses this exact Hub bind form.
    targets['hub'].append(['-m','uvicorn','hub.app:app','--host','0.0.0.0','--port',str(cfg['hub_port']),'--no-access-log'])
    for key in (('hub','ollama') if service=='all' else (service,)):
        expected=python if key=='hub' else Path(cfg['hub_root'])/'tools/ollama/ollama.exe'
        for proc in psutil.process_iter(['exe','cmdline','cwd']):
            try:
                if proc.info['exe'] and Path(proc.info['exe']).resolve()==expected.resolve() and proc.info['cmdline'][1:] in targets[key]:
                    if key=='hub' and not any(Path(x.cwd()).resolve()==Path(cfg['hub_source']).resolve() and x.cmdline()[1:]==proc.info['cmdline'][1:] for x in [proc]+proc.children()):raise RuntimeError('Hub working directory ownership mismatch')
                    stop_tree(proc,proc.info['cmdline'])
            except psutil.NoSuchProcess:pass
print('Requested owned services stopped; protected OwnerBroker is preserved')
