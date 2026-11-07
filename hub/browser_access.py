"""Serialize human browser input with idle PLAY observations, not active tasks."""
import asyncio
from contextlib import asynccontextmanager
from .store import Conflict


@asynccontextmanager
async def interactive_access(engine, controller, *, observation_only=False):
    def idle_listener():
        state = controller.state
        return (state.get('enabled') and state.get('continuous')
                and state.get('phase') in (('listening','waiting_reply') if observation_only else ('listening',))
                and not any(not job.done() for job in engine.jobs.values()))

    if engine.lock.locked() and not idle_listener():
        raise Conflict('Agent is using the browser; wait or stop before taking control')
    try:
        await asyncio.wait_for(engine.lock.acquire(), timeout=8)
    except TimeoutError:
        raise Conflict('Browser observation is still busy; no input was sent') from None
    try:
        # A task could have started while this input waited behind an observation.
        if any(not job.done() for job in engine.jobs.values()):
            raise Conflict('Agent started a task; no input was sent')
        if controller.state.get('enabled') and not idle_listener():
            raise Conflict('PLAY is handling a response; no input was sent')
        yield
    finally:
        engine.lock.release()
