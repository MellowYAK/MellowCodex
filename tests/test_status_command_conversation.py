"""Local-chat status routing is independent of model, history and active jobs."""
from hub import system_health
from hub.conversations import Conversations
from hub.store import Store


def test_new_chat_status_is_durable_and_no_model_task(tmp_path,monkeypatch):
    store=Store(tmp_path/"tasks.sqlite3")
    chats=Conversations(store)
    project=chats.project(tmp_path)
    chat=chats.create(project["id"])["id"]
    calls=[]
    def inspect():
        calls.append(True)
        return "Hub: תקין, MCP: מחובר", {"checked_at":123.0,"probe_outcome":"completed"}
    monkeypatch.setattr(system_health,"collect_report",inspect)
    task=chats.submit(chat,"סטטוס","desktop","health-request-1")
    assert task["state"]=="done"
    assert task["result"]=="Hub: תקין, MCP: מחובר"
    assert task["mode"]=="inspect"
    assert calls==[True]
    assert any(e["kind"]=="system_health_check" for e in store.events(task["id"]))
    assert chats.submit(chat,"סטטוס","desktop","health-request-1")["id"]==task["id"]
    assert calls==[True]


def test_health_still_works_with_active_task_in_same_chat(tmp_path,monkeypatch):
    store=Store(tmp_path/"tasks.sqlite3")
    chats=Conversations(store)
    project=chats.project(tmp_path)
    chat=chats.create(project["id"])["id"]
    pending=store.create("some other task",str(tmp_path),"desktop","running-job-1")
    with store.connect() as db:
        db.execute("INSERT INTO chat_tasks VALUES(?,?,?)",(chat,pending["id"],0))
    monkeypatch.setattr(system_health,"collect_report",
                        lambda:("MCP live status", {"probe_outcome":"completed"}))
    task=chats.submit(chat,"System Health","desktop","health-request-2")
    assert task["state"]=="done"
    assert task["result"]=="MCP live status"
    assert store.get(pending["id"])["state"]=="queued"
