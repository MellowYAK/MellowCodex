import pytest
from hub.development.workspaces import Workspaces,sha

def test_candidate_preserves_source_and_rejects_partial_patch(tmp_path):
    source=tmp_path/'repo';source.mkdir();(source/'a.py').write_text('value=1')
    (source/'.env').write_text('do not copy')
    service=Workspaces(tmp_path/'candidates');m=service.create(source)
    assert '.env' not in m['files']
    with pytest.raises(ValueError):
        service.propose(m['id'],[{'path':'a.py','base_hash':m['files']['a.py'],'content':'value=2'}, {'path':'b.py','base_hash':'wrong','content':'bad'}],0)
    assert service.inspect(m['id'])['revision']==0
    updated=service.propose(m['id'],[{'path':'a.py','base_hash':m['files']['a.py'],'content':'value=2'}],0)
    assert updated['files']['a.py']==sha(b'value=2')
    delta=service.diff(m['id'])
    assert delta['revision']==1 and len(delta['files'])==1
    assert '-value=1' in delta['files'][0]['diff'] and '+value=2' in delta['files'][0]['diff']
    assert (source/'a.py').read_text()=='value=1'
    with pytest.raises(ValueError):service.propose(m['id'],[{'path':'a.py','base_hash':m['files']['a.py'],'content':'bad'}],0)

def test_candidate_test_verifies_revision_and_preserves_source(tmp_path):
    import asyncio
    from hub.store import Store
    from hub.development.service import Development
    source=tmp_path/'repo';source.mkdir()
    (source/'test_value.py').write_text('def test_value():\n assert 1 == 1\n')
    store=Store(tmp_path/'state'/'hub.sqlite3')
    task=store.create('verify',str(source),'code','verify-1')
    dev=Development(store,tmp_path/'candidates');manifest=dev.create(task)
    result=asyncio.run(dev.test(task,manifest['id'],0,['test_value.py']))
    assert result['verified'] and result['exit_code']==0
    assert '1 passed' in result['output']
    assert __import__('pathlib').Path(result['evidence']).is_file()
    with pytest.raises(ValueError,match='revision'):
        asyncio.run(dev.test(task,manifest['id'],1,['test_value.py']))

def test_candidate_runner_timeout_failure_and_environment(tmp_path,monkeypatch):
    import asyncio
    from hub.development.runner import run_pytest
    monkeypatch.setenv('LOCAL_AGENT_TEST_SECRET','must-not-inherit')
    test=tmp_path/'test_case.py'
    test.write_text('import os\ndef test_env():\n assert "LOCAL_AGENT_TEST_SECRET" not in os.environ\n')
    assert asyncio.run(run_pytest(tmp_path,['test_case.py']))['exit_code']==0
    assert asyncio.run(run_pytest(tmp_path,['test_case.py::test_env']))['exit_code']==0
    with pytest.raises(ValueError):asyncio.run(run_pytest(tmp_path,['test_case.py::-bad']))
    test.write_text('def test_failure():\n assert False\n')
    assert asyncio.run(run_pytest(tmp_path,['test_case.py']))['exit_code']!=0
    test.write_text('import time\ndef test_wait():\n time.sleep(60)\n')
    assert asyncio.run(run_pytest(tmp_path,['test_case.py'],1))['timed_out']

def test_candidate_rejects_escape(tmp_path):
    source=tmp_path/'repo';source.mkdir();(source/'a.py').write_text('x=1')
    service=Workspaces(tmp_path/'candidates');m=service.create(source)
    for path in ['../escape.py','C:/escape.py','a.py:stream']:
        with pytest.raises(ValueError):service.propose(m['id'],[{'path':path,'base_hash':None,'content':'bad'}],0)

def test_candidate_manifest_cannot_redirect_revision_outside_root(tmp_path):
    import json
    source=tmp_path/'repo';source.mkdir();(source/'a.py').write_text('x=1')
    service=Workspaces(tmp_path/'candidates');m=service.create(source)
    m['directory']='../../repo'
    (service.candidate(m['id'])/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='directory'):service.inspect(m['id'])

def test_changed_existing_test_cannot_certify_original_acceptance(tmp_path):
    import asyncio
    from hub.store import Store
    from hub.development.service import Development
    source=tmp_path/'repo';source.mkdir();(source/'test_case.py').write_text('def test_case():\n assert False\n')
    store=Store(tmp_path/'state'/'hub.sqlite3');task=store.create('fix code',str(source),'code','protect-tests')
    dev=Development(store,tmp_path/'candidates');m=dev.create(task)
    dev.patch(task,{'candidate_id':m['id'],'expected_revision':0,'changes':[{'path':'test_case.py','base_hash':m['files']['test_case.py'],'content':'def test_case():\n assert True\n'}]})
    with pytest.raises(ValueError,match='acceptance test was changed'):
        asyncio.run(dev.test(task,m['id'],1,['test_case.py']))

def test_development_binds_candidate_to_task_and_records_staging(tmp_path):
    from hub.store import Store
    from hub.development.service import Development
    source=tmp_path/'repo';source.mkdir();(source/'a.py').write_text('value=1')
    store=Store(tmp_path/'state'/'hub.sqlite3')
    first=store.create('repair',str(source),'code','req-1')
    second=store.create('other',str(source),'code','req-2')
    dev=Development(store,tmp_path/'candidates');m=dev.create(first)
    with pytest.raises(ValueError):dev.inspect(second,m['id'])
    result=dev.patch(first,{'candidate_id':m['id'],'expected_revision':0,'changes':[{'path':'a.py','base_hash':m['files']['a.py'],'content':'value=2'}]})
    assert result['revision']==1
    assert (source/'a.py').read_text()=='value=1'
