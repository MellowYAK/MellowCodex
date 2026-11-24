import asyncio,concurrent.futures,threading,time,ast
from pathlib import Path
from unittest.mock import Mock
import pytest,httpx
from hub import service_health as h
from hub import mcp_gateway as g

def test_concurrent_health_shares_completed_scan(tmp_path,monkeypatch):
    monkeypatch.setattr(h,"STATE",tmp_path)
    monkeypatch.setattr(h,"_snapshot_cache",None)
    monkeypatch.setattr(h,"_snapshot_completed_at",0.)
    monkeypatch.setattr(h,"_snapshot_lock",threading.Lock())
    monkeypatch.setattr(h.diagnostics,"enrich",lambda module,data:data)
    monkeypatch.setattr(h.diagnostics,"refresh_connector_evidence",lambda module,data:data)
    started=threading.Event()
    release=threading.Event()
    calls=[]
    def scan():
        stamp=time.time()
        calls.append(stamp)
        started.set()
        assert release.wait(3)
        return {"checked_at":stamp,"services":[]}
    monkeypatch.setattr(h,"_snapshot",scan)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as p:
        first=p.submit(h.snapshot)
        assert started.wait(2)
        others=[p.submit(h.snapshot) for _ in range(5)]
        time.sleep(.1)
        release.set()
        result=[first.result(3)]+[f.result(3) for f in others]
    assert len(calls)==1
    assert all(x["checked_at"]==calls[0] for x in result)
    h.snapshot()
    assert len(calls)==2

def test_uncertain_write_not_replayed(tmp_path,monkeypatch):
    (tmp_path/"hub.key").write_text("test-only")
    monkeypatch.setattr(g,"STATE",tmp_path)
    calls=[]
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):
            calls.append(1)
            raise httpx.ReadTimeout("mock")
    monkeypatch.setattr(g.httpx,"AsyncClient",lambda **kw:Client())
    with pytest.raises(g.LocalTransportError,match="write_outcome_uncertain"):
        asyncio.run(g.local("/api/test",{"request_id":"stable"}))
    assert calls==[1]

def test_sync_route_releases_event_loop():
    # Execute exact route body from candidate source, without app lifespan or live storage.
    from types import SimpleNamespace
    src=Path(__file__).parents[1]/"hub"/"app.py"
    tree=ast.parse(src.read_text(encoding="utf-8"))
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="mcp_conversation_message")
    node.decorator_list=[];node.args.args[0].annotation=None
    entered=threading.Event();release=threading.Event()
    def create(*a,**kw):
        assert kw["include_history"] is False
        entered.set()
        assert release.wait(2)
        return {"id":"test"}
    transcript=Mock()
    env={"asyncio":asyncio,"conversations":lambda:SimpleNamespace(create=create),"app":SimpleNamespace(state=SimpleNamespace(bridge=SimpleNamespace(transcript=transcript)))}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),"exec"),env)
    async def check():
        b=SimpleNamespace(project_id="p",conversation_key="test-key",message_id="stable",speaker="user",text="test")
        t=asyncio.create_task(env["mcp_conversation_message"](b))
        try:
            for _ in range(100):
                if entered.is_set():break
                await asyncio.sleep(.005)
            assert entered.is_set() and not t.done()
            await asyncio.sleep(.02)
            assert not t.done()
        finally:release.set()
        assert (await t)["recorded"]
    asyncio.run(check())
    transcript.append.assert_called_once()
