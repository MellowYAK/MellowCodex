import asyncio
from types import SimpleNamespace
from hub import mcp_gateway as gateway
from hub.bridge_controller import BridgeController

def test_mcp_wait_returns_completion(monkeypatch):
    states=iter(['running','waiting_review'])
    async def status(_):return {'task':{'state':next(states)},'recent_actions':[]}
    monkeypatch.setattr(gateway,'get_task',status)
    result=asyncio.run(gateway.wait_for_task('task',2))
    assert result['task']['state']=='waiting_review'
    assert 'get_file' in result['next_action']

def test_mcp_wait_does_not_claim_timeout_is_success(monkeypatch):
    async def status(_):return {'task':{'state':'queued'}}
    monkeypatch.setattr(gateway,'get_task',status)
    result=asyncio.run(gateway.wait_for_task('task',0))
    assert result['task']['state']=='queued'
    assert 'Call wait_task' in result['next_action']

def test_listener_timeout_releases_runner(monkeypatch):
    async def scenario():
        controller=object.__new__(BridgeController)
        controller.state={'enabled':True,'continuous':True,'phase':'listening'}
        controller.engine=SimpleNamespace(jobs={},lock=asyncio.Lock())
        controller.save=lambda:None
        entered=asyncio.Event()
        async def tick():
            async with controller.engine.lock:
                entered.set()
                await asyncio.Event().wait()
        controller.tick=tick
        original=asyncio.timeout
        monkeypatch.setattr(asyncio,'timeout',lambda _:original(.02))
        watcher=asyncio.create_task(controller.watch())
        await asyncio.wait_for(entered.wait(),2)
        async with original(1):
            async with controller.engine.lock:pass
        assert controller.state['connection']=='reconnecting'
        assert 'TimeoutError' in controller.state['error']
        watcher.cancel()
        await asyncio.gather(watcher,return_exceptions=True)
    asyncio.run(scenario())


def test_progress_reports_stage_changes(monkeypatch):
    states=iter([('queued',1),('running',2),('waiting_review',3)])
    async def status(_):
        state,seq=next(states)
        return {'task':{'state':state},'status':{'event_seq':seq,'text':state}}
    class Context:
        def __init__(self):self.messages=[]
        async def report_progress(self,n,message):self.messages.append((n,message))
    ctx=Context()
    monkeypatch.setattr(gateway,'get_task',status)
    asyncio.run(gateway.wait_for_task('task',5,ctx))
    assert ctx.messages==[(1,'queued'),(2,'running'),(3,'waiting_review')]

def test_progress_failure_does_not_fail_task(monkeypatch):
    async def status(_):return {'task':{'state':'waiting_review'}}
    class Context:
        async def report_progress(self,*args,**kwargs):raise RuntimeError('disconnected')
    monkeypatch.setattr(gateway,'get_task',status)
    assert asyncio.run(gateway.wait_for_task('task',1,Context()))['task']['state']=='waiting_review'


def test_pending_memory_review_returns_to_caller_without_poll_delay(monkeypatch):
    async def status(_):
        return {'task':{'state':'running'},'memory_review_next_action':'Check original context and reply.'}
    async def no_sleep(_):raise AssertionError('Feedback must be exposed before polling again')
    monkeypatch.setattr(gateway,'get_task',status)
    monkeypatch.setattr(asyncio,'sleep',no_sleep)
    result=asyncio.run(gateway.wait_for_task('task',20))
    assert result['task']['state']=='running'
    assert result['next_action'].startswith('Check original context')
    assert 'same task' in result['next_action']


def test_task_fetches_fresh_deduplicated_memory_review(monkeypatch):
    task='1'*32;chat='2'*32;review='3'*32;calls=[]
    action={'tool':'conversation_memory_review','state':'done','result':{'id':review,'chat_id':chat,'status':'pending'}}
    async def local(path):
        calls.append(path)
        if path.endswith('/diagnostics'):return {'diagnostics':{'actions':[action,action]}}
        if '/memory-review/' in path:return {'id':review,'status':'reviewed','response':{'verdict':'unavailable'}}
        return {'id':task,'state':'waiting_review'}
    monkeypatch.setattr(gateway,'local',local)
    result=asyncio.run(gateway.get_task(task))
    assert len(result['memory_reviews'])==1
    assert result['memory_reviews'][0]['response']['verdict']=='unavailable'
    assert result['memory_review_next_action'] is None
    assert sum('/memory-review/' in path for path in calls)==1
