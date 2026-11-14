"""MCP status reply is short and never waits for model task machinery."""
import asyncio
from hub import mcp_gateway

def test_status_mcp_returns_compact_done_without_task_wait(monkeypatch):
    observed=[]
    async def fake_local(path,data=None,timeout=15):
        observed.append((path,data))
        return {"id":"a"*32,"state":"done","result":"Hub: operational; Guard: operational"}
    async def should_not_wait(*args,**kwargs):
        raise AssertionError("status reply must not invoke wait_for_task")
    monkeypatch.setattr(mcp_gateway,"local",fake_local)
    monkeypatch.setattr(mcp_gateway,"wait_for_task",should_not_wait)
    result=asyncio.run(mcp_gateway.submit_task("b"*32,"סטטוס","status-test-1234",mode="inspect"))
    assert result["state"]=="done"
    assert result["model_inference"] is False
    assert "Hub: operational" in result["status_report"]
    assert observed[0][0].endswith("/messages")
    assert observed[0][1]["text"]=="סטטוס"

def test_russian_status_mcp_is_immediate(monkeypatch):
    async def fake_local(path,data=None,timeout=15):
        return {"id":"a"*32,"state":"done","result":"Отчёт"}
    monkeypatch.setattr(mcp_gateway,"local",fake_local)
    async def should_not_wait(*args,**kwargs):raise AssertionError("unexpected wait")
    monkeypatch.setattr(mcp_gateway,"wait_for_task",should_not_wait)
    assert asyncio.run(mcp_gateway.submit_task("b"*32,"статус","status-test-ru",mode="inspect"))["state"]=="done"
