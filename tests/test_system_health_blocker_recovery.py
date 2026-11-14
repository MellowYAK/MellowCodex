"""Regression: live status self-recovers transient probes without inventing green."""
import asyncio
import time
from types import SimpleNamespace

def test_local_readonly_retry(monkeypatch):
    from hub import service_health, system_health
    count = []
    def probe():
        count.append(True)
        if len(count)==1: raise TimeoutError("temporary")
        return {"checked_at":time.time(),"schema_version":2,
                "overall_status":"operational","services":[],"connectors":{}}
    monkeypatch.setattr(service_health,"snapshot",probe)
    report, metadata=system_health.collect_report()
    assert len(count)==2
    assert metadata["diagnostic_recovery"]["recovered"] is True
    assert "ניסיון חוזר" in report

def test_local_auth_failure_never_retried(monkeypatch,tmp_path):
    from hub import service_health, system_health
    count=[]
    monkeypatch.setattr(service_health,"STATE",tmp_path)
    def fail():
        count.append(True)
        raise PermissionError("owner approval required")
    monkeypatch.setattr(service_health,"snapshot",fail)
    report, metadata=system_health.collect_report()
    assert len(count)==1
    assert metadata["probe_outcome"]=="failed"
    assert metadata["diagnostic_recovery"]["restart_performed"] is False
    assert "לא הושלמה" in report

def test_mcp_transient_retry_retains_real_round_trip():
    from hub.service_health import register_mcp
    handlers={}
    class MCP:
        def tool(self,**kw):
            def register(f):
                handlers[f.__name__]=f
                return f
            return register
    calls=[]
    async def local(path,data=None,timeout=None):
        calls.append(timeout)
        if len(calls)==1: raise TimeoutError("transient")
        return {"schema_version":2,"services":[],"overall_status":"operational"}
    register_mcp(MCP(),local,SimpleNamespace(),SimpleNamespace())
    result=asyncio.run(handlers["system_health_check"]())
    assert len(calls)==2
    assert result["overall_status"]=="operational"
    assert result["diagnostic_recovery"]["recovered"] is True
    assert result["current_mcp_call"]["source"]=="authenticated_mcp_to_hub"

def test_mcp_backend_unavailable_unverified_not_failed():
    from hub.service_health import register_mcp,LABELS
    handlers={}
    class MCP:
        def tool(self,**kw):
            def register(f):
                handlers[f.__name__]=f
                return f
            return register
    calls=[]
    async def local(path,data=None,timeout=None):
        calls.append(path)
        raise ConnectionError("down")
    register_mcp(MCP(),local,SimpleNamespace(),SimpleNamespace())
    result=asyncio.run(handlers["system_health_check"]())
    assert len(calls)==2
    assert result["overall_status"]=="unverified"
    assert len(result["services"])==len(LABELS)
    assert all(r["status"]=="unverified" for r in result["services"])
    assert result["current_mcp_call"]["source"]=="authenticated_mcp_gateway_only"
    assert result["diagnostic_recovery"]["restart_performed"] is False
