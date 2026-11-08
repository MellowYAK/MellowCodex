import asyncio
import json
from hub.development.service import Development
from hub.store import Store

def test_latest_exact_command_correction_reaches_worker(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir()
    (source/'a.py').write_text('value=1')
    (source/'test_a.py').write_text('from a import value\ndef test_value(): assert value==2')
    store=Store(tmp_path/'state.db');task=store.create('Original objective',str(source),'code','correction')
    dev=Development(store,tmp_path/'candidates');candidate=dev.create(task)
    store.event(task['id'],'director_exact_command',{'request_id':'older','reason':'Old critique','arguments':{'command':'private payload'}})
    store.event(task['id'],'director_exact_command',{'request_id':'newer','reason':'Restore validation; keep timeout fix','arguments':{'command':'private payload'}})
    async def proposal(packet,timeout):
        assert packet['human_request_original']=='Original objective'
        assert packet['director_correction']=={'request_id':'newer','reason':'Restore validation; keep timeout fix'}
        assert 'private payload' not in json.dumps(packet)
        return {'proposal':{'changes':[{'path':'a.py','content':'value=2'}]},'model':'fixture'}
    monkeypatch.setattr('hub.development.worker_runner.run',proposal)
    result=asyncio.run(dev.repair(task,candidate['id'],0,['a.py'],['test_a.py']))
    assert result['test']['verified']
