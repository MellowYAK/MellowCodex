"""Fixed-purpose, bounded desktop startup; no arbitrary executable or elevation."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from .config import ROOT, STATE, CDP_PORT
from . import service_health as health

def _ipc(show=False):
    result = subprocess.run(
        [sys.executable, '-m', 'hub.browser_ipc', '--show-runtime' if show else '--runtime-status'],
        cwd=health.SOURCE, capture_output=True, text=True, timeout=8,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Desktop IPC unavailable')
    data = json.loads(result.stdout)
    if not data.get('ready'):
        raise RuntimeError('Desktop IPC not ready')
    return data

def _cdp():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{CDP_PORT}/json/version', timeout=2) as response:
        data = json.loads(response.read(32000))
    return bool(data.get('webSocketDebuggerUrl'))

def status():
    rows = health.inventory().get('desktop', [])
    result = dict(state='stopped', ready=False, checked_at=time.time(),
                  process_count=len(rows), owned=bool(rows) and all(r['owned'] for r in rows),
                  recommended_action='desktop_open')
    if not rows:
        return result
    if not result['owned']:
        return dict(result, state='blocked', reason='Desktop process ownership could not be verified')
    try:
        native = _ipc()
        if native.get('pid') not in {r['pid'] for r in rows}:
            return dict(result, state='blocked', reason='IPC responder is not the verified desktop process')
        if not _cdp():
            raise RuntimeError('Browser protocol not ready')
        return dict(result, state='operational', ready=True, pid=native['pid'],
                    visible=native.get('visible'), recommended_action=None)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return dict(result, state='unverified', reason=str(exc),
                    recommended_action='Inspect the existing desktop; do not start another profile owner')

def _session():
    value = ctypes.c_ulong()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(value)):
        raise RuntimeError('Cannot determine Windows session')
    return value.value

@contextmanager
def _admission():
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    suffix = hashlib.sha256(str(ROOT.resolve()).casefold().encode()).hexdigest()[:16]
    handle = kernel.CreateMutexW(None, False, 'Local\\MellowCodexDesktopLaunch-' + suffix)
    if not handle:
        raise RuntimeError('Desktop launch admission unavailable')
    acquired = kernel.WaitForSingleObject(handle, 0) in (0, 128)
    try:
        yield acquired
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)

def _launch():
    cfg = health.config()
    source = Path(cfg.get('hub_source', str(health.SOURCE))).resolve()
    if source != health.SOURCE.resolve():
        raise RuntimeError('Installed source differs from launcher; reconcile deployment first')
    python = Path(cfg.get('hub_python', sys.executable)).resolve().with_name('pythonw.exe')
    if not python.is_file() or not (source/'hub/desktop_app.py').is_file():
        raise RuntimeError('Installed desktop launcher missing')
    with (STATE/'desktop-launch.stdout.log').open('ab') as out, (STATE/'desktop-launch.stderr.log').open('ab') as err:
        return subprocess.Popen([str(python), '-m', 'hub.desktop_app', '--background'],
            cwd=source, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)).pid

def open_desktop(request_id, show=True, timeout=25):
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 120:
        raise ValueError('Stable request_id of 1-120 characters required')
    if type(show) is not bool:
        raise ValueError('show must be boolean')
    operation_id = hashlib.sha256(('desktop:'+request_id).encode()).hexdigest()[:32]
    path = STATE/'desktop-launch-operations'/(operation_id+'.json')
    from .power import transition_active
    if transition_active():
        return dict(operation_id=operation_id, state='blocked', ready=False, reason='Computer power transition is active')
    with _admission() as acquired:
        if not acquired:
            return dict(operation_id=operation_id, state='starting', ready=False,
                        reason='Another desktop launch is being verified; inspect desktop_status')
        previous = health.read(path)
        if previous:
            if previous['show'] != show:
                raise ValueError('request_id already used with different show value')
            return dict(previous, replayed=False, current=status())
        before = status()
        record = dict(operation_id=operation_id, show=show, started_at=time.time(), state='starting', ready=False)
        def finish(**values):
            record.update(values, finished_at=time.time())
            health.write(path, record)
            return record
        health.write(path, record)
        if not before['ready']:
            if before['process_count']:
                return finish(state='blocked', reason=before.get('reason', 'Existing desktop not ready'), evidence=before)
            if _session() == 0:
                return finish(state='requires_user_action', reason='No interactive user session for this service; open MellowCodex after Windows sign-in')
            # A previous uncertain launch is not permission to spawn another.
            recent = health.read(STATE/'desktop-launch-last.json')
            if time.time()-recent.get('started_at', 0) < 45:
                return finish(state='starting', reason='Previous launch is still within its startup grace period; inspect desktop_status')
            health.write(STATE/'desktop-launch-last.json', record)
            try:
                record['launched_pid'] = _launch()
                health.write(path, record)
            except (OSError, RuntimeError) as exc:
                return finish(state='failed', reason=str(exc))
            deadline = time.monotonic()+max(1, min(timeout, 30))
            while time.monotonic() < deadline:
                before = status()
                if before['ready']:
                    break
                if before['state'] == 'blocked':
                    break
                time.sleep(.5)
        if not before['ready']:
            return finish(state='unverified', reason='Desktop launch has not passed IPC and browser readiness checks', evidence=before)
        if show:
            try:
                native = _ipc(show=True)
                if native.get('pid') != before['pid'] or not native.get('visible'):
                    raise RuntimeError('Window visibility not verified')
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                return finish(state='unverified', reason=str(exc), evidence=before)
        return finish(state='operational', ready=True, shown=show, evidence=before)
