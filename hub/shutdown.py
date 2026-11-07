"""Explicit whole-Hub shutdown; never terminate shared services by process name."""
import asyncio
import json
import signal
import sys

import httpx

from .config import STATE, OLLAMA
from .model_settings import load_settings, save_settings
from .model_memory import matches
from .resources import Resources


class Shutdown:
    def __init__(self, engine, catalog, monitors):
        self.engine, self.catalog, self.monitors = engine, catalog, monitors
        self.task = None
        self.status = {'state': 'idle', 'steps': [], 'errors': []}

    def start(self):
        if self.task and not self.task.done():
            return self.status
        if not callable(signal.getsignal(signal.SIGTERM)):
            raise RuntimeError('Server has no graceful shutdown handler')
        self.status = {'state': 'stopping', 'steps': [], 'errors': []}
        self.task = asyncio.create_task(self.run())
        return self.status

    def record(self):
        path = STATE / 'last-shutdown.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.status, ensure_ascii=False), encoding='utf-8')
        temporary.replace(path)

    async def step(self, name, action):
        try:
            await action()
            self.status['steps'].append(name)
        except Exception as exc:
            self.status['errors'].append({'stage': name, 'error': str(exc)})
        self.record()

    async def unload(self):
        resources = Resources()
        with resources.owner('', 'shutdown'):
            with resources.db() as db:
                managed = [r[0] for r in db.execute('SELECT name FROM managed_models')]
            async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
                r = await client.get(OLLAMA + '/api/ps'); r.raise_for_status()
                targets = [m['name'] for m in r.json().get('models', [])
                           if any(matches(m['name'], n) for n in managed)]
                for name in targets:
                    r = await client.post(OLLAMA + '/api/generate', json={'model': name, 'keep_alive': 0, 'stream': False})
                    r.raise_for_status()
                r = await client.get(OLLAMA + '/api/ps'); r.raise_for_status()
                if any(any(matches(m['name'], n) for n in targets) for m in r.json().get('models', [])):
                    raise RuntimeError('Managed model is still resident')
                self.status['unloaded_models'] = targets

    async def terminals(self):
        manager = self.engine.runner.terminals
        for sid, session in list(manager.sessions.items()):
            await asyncio.to_thread(manager.stop, {'id': session['task_id']}, sid)

    async def close_desktop(self):
        process = await asyncio.create_subprocess_exec(sys.executable, '-m', 'hub.browser_ipc', '--quit',
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try:
            _, error = await asyncio.wait_for(process.communicate(), 10)
        except asyncio.TimeoutError:
            process.kill(); await process.wait(); raise
        if process.returncode:
            raise RuntimeError(error.decode(errors='replace')[-500:])

    async def run(self):
        # Let HTTP/MCP deliver the accepted response before disconnecting transports.
        await asyncio.sleep(2)
        settings = load_settings()
        save_settings(settings.model_copy(update={'inference_enabled': False}))
        for monitor in self.monitors:
            if monitor:
                monitor.cancel()
        await asyncio.gather(*(m for m in self.monitors if m), return_exceptions=True)
        await self.step('tasks_stopped', self.engine.stop_all)
        await self.step('terminals_stopped', self.terminals)
        await self.step('downloads_stopped', self.catalog.close)
        await self.step('models_unloaded', self.unload)
        if self.status['errors']:
            self.status['state'] = 'failed'; self.record(); return
        await self.step('desktop_closed', self.close_desktop)
        self.status['state'] = 'server_exit_requested'
        self.record()
        signal.raise_signal(signal.SIGTERM)
