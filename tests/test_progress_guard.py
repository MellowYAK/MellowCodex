from hub.progress_guard import stalled_reads


def action(i, tool='read_file', path='a', content='same'):
    return dict(id=str(i),tool=tool,args={'path':path},state='complete',result={'text':content})


def test_successful_alternating_read_cycle_and_novel_evidence():
    calls=[action(i,path=str(i%2)) for i in range(6)]
    assert stalled_reads(calls)['consecutive_redundant_reads']==4
    assert stalled_reads(calls+[action(6,content='changed')]) is None
    assert stalled_reads([action(i,path=str(i)) for i in range(40)]) is None
    assert stalled_reads(calls,{'3'}) is None
    assert stalled_reads(calls+[action(6,tool='write_file')]) is None
    assert stalled_reads([action(i,tool='run_shell') for i in range(20)]) is None


def test_runner_returns_successful_read_loop_to_director(tmp_path,monkeypatch):
    import asyncio
    from hub.store import Store
    from hub.engine import Engine
    from hub.model_settings import ModelSettings
    monkeypatch.setattr('hub.model_settings.load_settings',lambda:ModelSettings())
    store=Store(tmp_path/'db.sqlite3')
    (tmp_path/'note.txt').write_text('source evidence')
    task=store.create('Read note.txt and return its content',str(tmp_path),'inspect','read-loop-fixture')
    engine=Engine(store)
    async def repeated(*args,**kwargs):
        return {'role':'assistant','content':'Reading','tool_calls':[{'function':{'name':'read_file','arguments':{'path':'note.txt'}}}]},{}
    engine.chat=repeated
    asyncio.run(engine.run(task['id']))
    assert store.get(task['id'])['state']=='waiting_review'
    assert store.latest_event(task['id'],'progress_stalled')
    assert len(store.actions(task['id']))==6
    assert not store.latest_event(task['id'],'verification')
