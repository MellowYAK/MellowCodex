import asyncio
import pytest
from hub.development.service import Development
from hub.store import Store


def test_unchanged_worker_response_does_not_create_revision(tmp_path,monkeypatch):
    source=tmp_path/'src';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state/hub.sqlite3');task=store.create('Fix value',str(source),'code','worker')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    async def unchanged(packet,timeout):return {'proposal':{'changes':[{'path':'a.py','content':'value=1'}]}}
    monkeypatch.setattr('hub.development.worker_runner.run',unchanged)
    with pytest.raises(ValueError,match='unchanged source'):
        asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert dev.inspect(task,candidate['id'])['revision']==0
    assert not any(e['kind']=='candidate_staged' for e in store.events(task['id']))


def test_worker_scope_rejection_preserves_candidate(tmp_path,monkeypatch):
    source=tmp_path/'src';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('def test_value(): assert True')
    store=Store(tmp_path/'state/hub.sqlite3');task=store.create('Fix a.py only',str(source),'code','worker')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    async def malicious(packet,timeout):
        assert packet['human_request_original']==task['goal']
        assert not packet['sources']['test_a.py']['writable']
        return {'proposal':{'changes':[{'path':'test_a.py','content':'# removed'}]}}
    monkeypatch.setattr('hub.development.worker_runner.run',malicious)
    with pytest.raises(ValueError,match='outside'):
        asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert dev.inspect(task,candidate['id'])['revision']==0
    assert (source/'test_a.py').read_text()=='def test_value(): assert True'


def test_worker_hash_patch_test_and_original_preservation(tmp_path,monkeypatch):
    source=tmp_path/'src';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state/hub.sqlite3');task=store.create('Fix value',str(source),'code','worker')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    async def proposal(packet,timeout):return {'proposal':{'changes':[{'path':'a.py','content':'value=2'}]},'model':'fixture'}
    monkeypatch.setattr('hub.development.worker_runner.run',proposal)
    result=asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert result['test']['verified'] and result['revision']==1
    assert (source/'a.py').read_text()=='value=1'
    assert result['activated'] is False


def test_invalid_python_is_corrected_before_candidate_changes(tmp_path,monkeypatch):
    source=tmp_path/'src';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state/hub.sqlite3');task=store.create('Fix value',str(source),'code','worker')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task);attempts=[]
    async def proposal(packet,timeout):
        attempts.append(1)
        assert dev.inspect(task,candidate['id'])['revision']==0
        if len(attempts)==2:assert packet['correction_feedback']['parser_errors'][0]['path']=='a.py'
        return {'proposal':{'changes':[{'path':'a.py','content':'value=2' if len(attempts)==2 else '"""unclosed'}]},'model':'fixture'}
    monkeypatch.setattr('hub.development.worker_runner.run',proposal)
    result=asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert result['test']['verified'] and result['revision']==1 and len(attempts)==2
    assert (source/'a.py').read_text()=='value=1'
    assert any(e['kind']=='coding_worker_rejected' for e in store.events(task['id']))
