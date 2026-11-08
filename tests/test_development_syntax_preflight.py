import asyncio
import pytest
from hub.development.syntax import python_errors
from hub.development.workspaces import Workspaces

def test_detects_broken_route_without_import():
    assert python_errors({'hub/app.py':b"task_id=Field(pattern='broken\n"})[0]['path']=='hub/app.py'
    assert python_errors({'fine.py':b'x=1\n','other.js':b'not python'})==[]

def test_bad_patch_does_not_publish_revision(tmp_path):
    src=tmp_path/'repo';src.mkdir()
    (src/'a.py').write_text('x=1\n')
    ws=Workspaces(tmp_path/'candidates')
    m=ws.create(src)
    with pytest.raises(ValueError,match='syntax preflight'):
        ws.propose(m['id'],[{'path':'a.py','base_hash':m['files']['a.py'],'content':"x='broken\n"}],0)
    assert ws.inspect(m['id'])['revision']==0

def test_candidate_test_cannot_hide_broken_unselected_module(tmp_path):
    from hub.store import Store
    from hub.development.service import Development
    src=tmp_path/'repo';src.mkdir()
    (src/'broken.py').write_text("x='broken\n")
    (src/'test_ok.py').write_text('def test_ok(): assert True\n')
    store=Store(tmp_path/'state.db')
    task=store.create('Check',str(src),'code','syntax-check')
    dev=Development(store,tmp_path/'candidates');m=dev.create(task)
    result=asyncio.run(dev.test(task,m['id'],0,['test_ok.py']))
    assert not result['verified'] and result['syntax_errors'][0]['path']=='broken.py'
