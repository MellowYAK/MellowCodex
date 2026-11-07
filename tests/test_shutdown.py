import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from hub import shutdown as module


def test_ordered_shutdown_and_duplicate_request(tmp_path, monkeypatch):
    async def check():
        events=[]
        async def stop(): events.append('stop')
        async def close(): events.append('downloads')
        async def unload(): events.append('unload')
        async def desktop(): events.append('desktop')
        monkeypatch.setattr(module,'STATE',tmp_path)
        monkeypatch.setattr(module.signal,'getsignal',lambda _:lambda:None)
        monkeypatch.setattr(module.signal,'raise_signal',lambda _:events.append('exit'))
        monkeypatch.setattr(module,'load_settings',lambda:SimpleNamespace(model_copy=lambda **kw:kw))
        monkeypatch.setattr(module,'save_settings',lambda _:events.append('disabled'))
        original_sleep=asyncio.sleep
        async def delay(_): await original_sleep(0)
        monkeypatch.setattr(module.asyncio,'sleep',delay)
        engine=SimpleNamespace(stop_all=stop,runner=SimpleNamespace(terminals=SimpleNamespace(sessions={})))
        shutdown=module.Shutdown(engine,SimpleNamespace(close=close),[])
        shutdown.unload=unload;shutdown.close_desktop=desktop
        first=shutdown.start();task=shutdown.task
        assert shutdown.start() is first and shutdown.task is task
        await task
        assert events==['disabled','stop','downloads','unload','desktop','exit']
        assert shutdown.status['state']=='server_exit_requested'
        assert (tmp_path/'last-shutdown.json').exists()
    asyncio.run(check())


def test_failed_unload_preserves_error_and_does_not_exit(tmp_path,monkeypatch):
    async def check():
        monkeypatch.setattr(module,'STATE',tmp_path)
        monkeypatch.setattr(module,'load_settings',lambda:SimpleNamespace(model_copy=lambda **kw:kw))
        monkeypatch.setattr(module,'save_settings',lambda _:None)
        monkeypatch.setattr(module.asyncio,'sleep',AsyncMock())
        engine=SimpleNamespace(stop_all=AsyncMock(),runner=SimpleNamespace(terminals=SimpleNamespace(sessions={})))
        shutdown=module.Shutdown(engine,SimpleNamespace(close=AsyncMock()),[])
        shutdown.unload=AsyncMock(side_effect=RuntimeError('resident'))
        shutdown.close_desktop=AsyncMock()
        await shutdown.run()
        assert shutdown.status['state']=='failed'
        assert shutdown.status['errors']==[{'stage':'models_unloaded','error':'resident'}]
        shutdown.close_desktop.assert_not_awaited()
    asyncio.run(check())
