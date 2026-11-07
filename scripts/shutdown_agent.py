"""Administrator recovery shutdown. --inspect is read-only; default requires --execute."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time

import psutil

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
PYTHON = Path('E:/AI/tools/hub-venv/Scripts/python.exe')
MODULES = {'hub.desktop_app', 'hub.mcp_gateway', 'hub.app:app'}


def owned_processes():
    found = {}
    for process in psutil.process_iter():
        try:
            args = process.cmdline()
            if process.pid == os.getpid() or not any(a in MODULES for a in args):
                continue
            # Match this installation, not another Python application or Hub checkout.
            if Path(process.exe()).resolve() != PYTHON.resolve() and Path(process.cwd()).resolve() != REPO:
                continue
            found[process.pid] = process
            for child in process.children(recursive=True):
                if child.name().lower() in {'python.exe', 'pythonw.exe', 'qtwebengineprocess.exe', 'ssh.exe', 'powershell.exe', 'pwsh.exe', 'cmd.exe'}:
                    found[child.pid] = child
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            # An elevated invocation is required to distinguish protected services.
            continue
    return list(found.values())


async def shutdown():
    from hub.config import STATE
    from hub.model_settings import load_settings, save_settings
    from hub.shutdown import Shutdown
    report = {'started': time.time(), 'stopped_pids': [], 'errors': [], 'state': 'stopping'}
    settings = load_settings()
    save_settings(settings.model_copy(update={'inference_enabled': False}))
    targets = owned_processes()
    # Freeze dispatchers first so they cannot respawn their children during teardown.
    for process in targets:
        try: process.suspend()
        except psutil.NoSuchProcess: pass
        except psutil.Error as exc: report['errors'].append(f'suspend {process.pid}: {exc}')
    for process in targets:
        try: process.kill(); report['stopped_pids'].append(process.pid)
        except psutil.NoSuchProcess: pass
        except psutil.Error as exc: report['errors'].append(f'stop {process.pid}: {exc}')
    _, alive = psutil.wait_procs(targets, timeout=8)
    for process in alive:
        try: process.resume()
        except psutil.Error: pass
    report['remaining_pids'] = sorted({p.pid for p in alive + owned_processes()})
    if report['remaining_pids']:
        report['errors'].append('Agent processes remain; model unload skipped to avoid reload race')
    else:
        lifecycle = Shutdown(None, None, [])
        try:
            await lifecycle.unload()
            report['unloaded_models'] = lifecycle.status.get('unloaded_models', [])
        except Exception as exc:
            report['errors'].append('model unload: ' + str(exc))
    report['state'] = 'failed' if report['errors'] else 'completed'
    path = STATE / 'last-admin-shutdown.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Report:', path)
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--inspect', action='store_true')
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps({'matched_pids': [p.pid for p in owned_processes()], 'executed': False}))
    elif args.execute:
        import ctypes
        if os.name != 'nt' or not ctypes.windll.shell32.IsUserAnAdmin():
            raise SystemExit('Administrator permission is required. Use the desktop shutdown shortcut.')
        raise SystemExit(asyncio.run(shutdown()))
    else:
        parser.error('Choose --inspect or --execute')
