"""Align existing agent services with an explicitly elevated launcher."""
import ctypes,sqlite3
import psutil
from .config import STATE

def elevated(pid):
    import win32api,win32con,win32security
    process=win32api.OpenProcess(0x1000,False,pid)
    try:
        token=win32security.OpenProcessToken(process,win32con.TOKEN_QUERY)
        try:return bool(win32security.GetTokenInformation(token,win32security.TokenElevation))
        finally:token.Close()
    finally:process.Close()

def main():
    is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    from . import __version__
    import httpx
    outdated=set()
    for marker,url in [('hub.app:app','http://127.0.0.1:8876/openapi.json'),('hub.mcp_gateway','http://127.0.0.1:8897/health')]:
        try:
            response=httpx.get(url,timeout=3,trust_env=False);response.raise_for_status()
            data=response.json();version=data.get('info',data).get('version')
            if version and version!=__version__:outdated.add(marker)
        except httpx.HTTPError:pass
    if not is_admin:
        # The launcher requests UAC only when replacing a stale service.
        if outdated:
            raise SystemExit(75)
        return
    targets=[]
    for p in psutil.process_iter(['name','cmdline']):
        cmd=' '.join(p.info['cmdline'] or [])
        if (p.info['name'] or '').lower() in ('python.exe','pythonw.exe') and any(x in cmd for x in ('hub.app:app','hub.mcp_gateway','-m hub.desktop_app')):
            if not elevated(p.pid) or any(marker in cmd for marker in outdated):targets.append(p)
    if not targets:return
    with sqlite3.connect(STATE/'hub.sqlite3') as db:
        active=db.execute("SELECT id FROM tasks WHERE state IN ('running','queued','verifying')").fetchall()
    if active:raise RuntimeError('Agent tasks are active. Stop or finish them before restarting as administrator.')
    # Ask the owned browser to save/close normally before replacing its runtime.
    import subprocess,sys
    if any('hub.desktop_app' in ' '.join(p.cmdline()) for p in targets):
        subprocess.run([sys.executable,'-m','hub.browser_ipc','--quit'],timeout=10,capture_output=True)
        desktop=[p for p in targets if p.is_running() and 'hub.desktop_app' in ' '.join(p.cmdline())]
        _,alive=psutil.wait_procs(desktop,timeout=8)
        if alive:raise RuntimeError('Desktop did not exit normally. Close the agent window before elevating.')
    for p in targets:
        try:
            if p.is_running():p.terminate()
        except psutil.NoSuchProcess:pass
    _,alive=psutil.wait_procs(targets,timeout=8)
    if alive:raise RuntimeError('Existing service did not stop; no duplicate elevated service launched.')

if __name__=='__main__':main()
