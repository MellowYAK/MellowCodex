import asyncio
from hub.store import Store
from hub.conversations import Conversations
from hub.schedules import Schedules
from hub.engine import Engine

def test_schedule_dispatch_and_stop(tmp_path):
    store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path))
    schedules=Schedules(store);s=schedules.create(project['id'],'Read files','inspect',5)
    assert schedules.tick(s['next_run']-1)==[]
    ids=schedules.tick(s['next_run']+1);assert len(ids)==1
    assert schedules.tick(s['next_run']+2)==[]
    assert schedules.list()[0]['last_task']==ids[0]
    asyncio.run(Engine(store).stop_all())
    assert schedules.list()[0]['enabled']==0
    assert store.get(ids[0])['state']=='paused'
