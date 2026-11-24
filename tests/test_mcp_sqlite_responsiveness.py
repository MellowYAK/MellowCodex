import asyncio,threading,time,sqlite3
from types import SimpleNamespace
import pytest,httpx
from hub import app as a
from hub.store import Store
from hub.conversations import Conversations
from hub.bridge_transcript import BridgeTranscript

def test_actual_sqlite_lock_does_not_block_asgi_and_sync_dedupes(tmp_path,monkeypatch):
    store=Store(tmp_path/"isolated.sqlite3")
    conv=Conversations(store)
    project=conv.project(str(tmp_path))["id"]
    transcript=BridgeTranscript(store)
    monkeypatch.setattr(a,"store",store)
    monkeypatch.setattr(a.app.state,"bridge",SimpleNamespace(transcript=transcript),raising=False)
    # Hold a real SQLite writer; it previously blocked the ASGI loop.
    held=threading.Event();release=threading.Event()
    def hold():
        with sqlite3.connect(store.path) as db:
            db.execute("BEGIN IMMEDIATE");held.set()
            assert release.wait(4)
    worker=threading.Thread(target=hold);worker.start()
    assert held.wait(2)
    body=dict(project_id=project,conversation_key="test-lock-chat",message_id="same-id",text="isolated",speaker="user")
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a.app),base_url="http://127.0.0.1:8876",headers={"x-hub-key":a.TOKEN,"origin":"http://127.0.0.1:8876"}) as client:
            t=asyncio.create_task(client.post("/api/mcp/conversation-message",json=body))
            try:
                await asyncio.sleep(.05)
                assert not t.done()
                result=await asyncio.wait_for(client.get("/"),1.5)
                assert result.status_code==200 and not t.done()
            finally:release.set()
            result=await asyncio.wait_for(t,3)
            assert result.status_code==200,result.text
            repeat=await client.post("/api/mcp/conversation-message",json=body)
            assert repeat.json()==result.json()
            return result.json()["chat_id"]
    try:chat=asyncio.run(check())
    finally:release.set();worker.join(5)
    assert len(transcript.list(chat))==1
    assert len(conv.inventory()["chats"])==1

def test_lightweight_binding_does_not_read_turns(tmp_path,monkeypatch):
    conv=Conversations(Store(tmp_path/"isolated.sqlite3"))
    p=conv.project(str(tmp_path))["id"]
    monkeypatch.setattr(conv,"get",lambda *_:pytest.fail("full history read"))
    x=conv.create(p,conversation_key="test-binding",include_history=False)
    assert x==conv.create(p,conversation_key="test-binding",include_history=False)
