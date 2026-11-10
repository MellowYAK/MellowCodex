"""Real isolated Hub/MCP-like subprocesses; never touches production ports or repo."""
import json
import socket
import pytest
from hub.guardian.control_plane import stage,activate,Services,sha,read

def ports():
    handles=[socket.socket(),socket.socket()]
    try:
        for s in handles:s.bind(('127.0.0.1',0))
        return tuple(s.getsockname()[1] for s in handles)
    finally:
        for s in handles:s.close()

@pytest.mark.parametrize('fail',[False,True])
def test_real_service_update_and_health_rollback(tmp_path,fail):
    root=tmp_path/'root';root.mkdir()
    live=tmp_path/'live';(live/'hub').mkdir(parents=True)
    old="from fastapi import FastAPI\napp=FastAPI()\n@app.get('/')\ndef home(): return {'version':1}\n"
    (live/'hub'/'__init__.py').write_text('')
    (live/'hub'/'app.py').write_text(old)
    (live/'hub'/'mcp_gateway.py').write_text("from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health(): return {'ok':True}\n")
    source=tmp_path/'source';(source/'hub').mkdir(parents=True)
    new="raise RuntimeError('intentional isolated startup failure')\n" if fail else old.replace("'version':1","'version':2")
    (source/'hub'/'app.py').write_text(new)
    result=stage(root,live,source,{'hub/app.py':sha((source/'hub'/'app.py').read_bytes())},{'verified':True},ports())
    job=root/'control-plane-updates'/result['id'];driver=Services(read(job))
    try:
        observed=activate(job,driver)
        assert observed['state']==('ROLLED_BACK' if fail else 'ACTIVE_VERIFIED'),observed
        assert (live/'hub'/'app.py').read_text()==(old if fail else new)
        assert driver.healthy()
    finally:
        driver.stop()
