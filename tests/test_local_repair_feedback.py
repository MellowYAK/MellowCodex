import asyncio
import pytest
from hub.store import Store
from hub.development.service import Development

def setup(tmp_path):
    source=tmp_path/'src';source.mkdir()
    (source/'a.py').write_text('value=0')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state.db');task=store.create('Fix value',str(source),'code','repair-loop')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    return source,store,task,dev,candidate

def test_local_repair_uses_observed_failure_and_current_source(tmp_path,monkeypatch):
    source,store,task,dev,c=setup(tmp_path);packets=[]
    async def proposal(packet,timeout):
        packets.append(packet)
        if len(packets)==2:
            assert 'assert 1 == 2' in packet['test_feedback']['output']
            assert packet['sources']['a.py']['text']=='value=1'
            assert not packet['sources']['test_a.py']['writable']
        return {'proposal':{'changes':[{'path':'a.py','content':'value='+str(len(packets))}]}}
    monkeypatch.setattr('hub.development.worker_runner.run',proposal)
    result=asyncio.run(dev.repair(task,c['id'],0,['a.py'],['test_a.py'],max_attempts=3))
    assert result['test']['verified'] and len(result['attempts'])==2
    assert result['stop_reason']=='tests_passed' and not result['activated']
    assert (source/'a.py').read_text()=='value=0'

def test_no_repeat_after_uncertain_test_timeout(tmp_path,monkeypatch):
    _,store,task,dev,c=setup(tmp_path);calls=[]
    async def once(*args):
        calls.append(1)
        return {'revision':1,'test':{'verified':False,'timed_out':True},'activated':False}
    monkeypatch.setattr(dev,'_repair_once',once)
    result=asyncio.run(dev.repair(task,c['id'],0,['a.py'],['test_a.py'],max_attempts=3))
    assert len(calls)==1 and result['stop_reason']=='uncertain_test_effects'

def test_changed_task_stops_next_attempt(tmp_path,monkeypatch):
    _,store,task,dev,c=setup(tmp_path)
    async def once(*args):
        store.update(task['id'],state='paused')
        return {'revision':1,'test':{'verified':False,'exit_code':1,'output':'fail'},'activated':False}
    monkeypatch.setattr(dev,'_repair_once',once)
    with pytest.raises(ValueError,match='changed'):
        asyncio.run(dev.repair(task,c['id'],0,['a.py'],['test_a.py'],max_attempts=3))
