import asyncio
import json
from hub.development.service import Development,worker_guidance
from hub.store import Store

def test_worker_guidance_keeps_instructions_without_archived_payloads():
    snapshot={'guidance_revision':7,'guidance':[{
        'revision':7,'request_id':'fix-7','text':'Fix only a.py; preserve public API.',
        'required_sources':'[{"path":"a.py"}]','allowed_tools':'["candidate_repair"]',
        'exact_patch':'x'*100000,'context_read':'y'*100000,
        'consumed_epoch':'old-worker'}]}
    result=worker_guidance(snapshot)
    assert len(json.dumps(result))<1000
    assert result['instructions'][0]['text']==snapshot['guidance'][0]['text']
    assert result['instructions'][0]['required_sources']==snapshot['guidance'][0]['required_sources']
    assert result['guidance_revision']==7

def test_compact_packet_still_rejects_changed_director_guidance(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state.db');task=store.create('Fix value',str(source),'code','compact')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    state={'guidance_revision':1,'guidance':[{'text':'Keep API','exact_patch':'x'*100000}]}
    monkeypatch.setattr('hub.development.guidance.Guidance.status',lambda self,identifier:json.loads(json.dumps(state)))
    async def proposal(packet,timeout):
        assert len(json.dumps(packet['guidance']))<1000
        assert packet['guidance']['instructions'][0]['text']=='Keep API'
        state['guidance_revision']=2
        return {'proposal':{'changes':[{'path':'a.py','content':'value=2'}]}}
    monkeypatch.setattr('hub.development.worker_runner.run',proposal)
    import pytest
    with pytest.raises(ValueError,match='guidance changed'):
        asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert dev.inspect(task,candidate['id'])['revision']==0
