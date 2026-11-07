import asyncio
from types import SimpleNamespace
import pytest
from hub.browser_access import interactive_access
from hub.store import Conflict

def test_reply_wait_allows_frame_but_not_input():
    async def run():
        engine=SimpleNamespace(lock=asyncio.Lock(),jobs={})
        controller=SimpleNamespace(state={'enabled':True,'continuous':True,'phase':'waiting_reply'})
        async with interactive_access(engine,controller,observation_only=True):pass
        with pytest.raises(Conflict):
            async with interactive_access(engine,controller):pass
        controller.state['phase']='sending_feedback'
        with pytest.raises(Conflict):
            async with interactive_access(engine,controller,observation_only=True):pass
    asyncio.run(run())


def test_idle_observation_yields_to_input_but_new_task_blocks_it():
    async def run():
        engine=SimpleNamespace(lock=asyncio.Lock(),jobs={})
        controller=SimpleNamespace(state={'enabled':True,'continuous':True,'phase':'listening'})
        await engine.lock.acquire()
        entered=[]
        async def input_once():
            async with interactive_access(engine,controller):entered.append(True)
        waiter=asyncio.create_task(input_once())
        await asyncio.sleep(0)
        assert not entered
        engine.lock.release()
        await waiter
        assert entered==[True] and not engine.lock.locked()
        await engine.lock.acquire()
        waiter=asyncio.create_task(input_once())
        await asyncio.sleep(0)
        controller.state['phase']='waiting_task'
        engine.lock.release()
        with pytest.raises(Conflict):await waiter
        assert entered==[True] and not engine.lock.locked()
    asyncio.run(run())
