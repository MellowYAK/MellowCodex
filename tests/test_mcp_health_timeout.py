"""Status health endpoint can exceed normal short task timeout."""
import asyncio
from hub import mcp_gateway

def test_status_mcp_uses_full_probe_timeout(monkeypatch):
    calls=[]
    async def local(path, data=None, timeout=15):
        calls.append(timeout)
        return {'id':'f'*32,'state':'done','result':'All healthy'}
    async def fail_wait(*a,**kw):
        raise AssertionError('status should bypass generic task polling')
    monkeypatch.setattr(mcp_gateway,'local',local)
    monkeypatch.setattr(mcp_gateway,'wait_for_task',fail_wait)
    r=asyncio.run(mcp_gateway.submit_task('a'*32,'סטטוס','status-health-timeout-v1'))
    assert r['state']=='done'
    assert r['model_inference'] is False
    assert calls==[70]

def test_status_en_russian_timeout(monkeypatch):
    calls=[]
    async def local(path, data=None, timeout=15):
        calls.append(timeout)
        return {'id':'f'*32,'state':'done','result':'ok'}
    monkeypatch.setattr(mcp_gateway,'local',local)
    r=asyncio.run(mcp_gateway.submit_task('a'*32,'статус','status-ru-timeout-v1'))
    assert r['state']=='done' and calls==[70]
