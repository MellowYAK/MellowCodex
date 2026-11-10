"""Focused regression for Objective request idempotency after task completion."""
import pytest

from hub.store import Store, Conflict
from hub.development.selfdevelop import SelfDevelop


def make_mapping(tmp_path, key="test:objective-idem"):
    store=Store(tmp_path/"hub.db")
    service=SelfDevelop(store)
    chat=service.start("Repair authorized SelfDevelop code",key,"mcp")["chat_id"]
    task=service.step(chat,"read-source","Read authorized source",["project_brief"],
                      context_read={"operation":"brief"})
    store.update(task["id"],state="waiting_review")
    return store,service,chat,task


def authorize(service,chat,task,request="same-run-20261108",paths=None):
    return service.authorize_objective(chat,task["id"],request,
        paths or ["hub/development/selfdevelop.py"],
        ["tests/test_selfdevelop_objective_driver.py"],
        None,2,"gpt",True)


def test_identical_objective_request_after_done_returns_existing_run(tmp_path):
    store,service,chat,task=make_mapping(tmp_path)
    first=authorize(service,chat,task)
    assert first["phase"]=="repair_queued"
    store.update(task["id"],state="done")
    resumed=SelfDevelop(Store(tmp_path/"hub.db"))
    second=authorize(resumed,chat,task)
    assert second["request_id"]==first["request_id"]
    assert second["phase"]==first["phase"]
    assert second["task_id"]==task["id"]
    assert second["original_objective"]==first["original_objective"]
    with store.connect() as db:
        count=db.execute("SELECT count(*) FROM selfdevelop_objective_runs WHERE chat_id=?",(chat,)).fetchone()[0]
        event_count=db.execute("SELECT count(*) FROM events WHERE task_id=? AND kind='selfdevelop_objective_authorized'",(task["id"],)).fetchone()[0]
    assert count==1
    assert event_count==1


def test_same_request_id_changed_payload_still_conflicts_after_done(tmp_path):
    store,service,chat,task=make_mapping(tmp_path)
    authorize(service,chat,task)
    store.update(task["id"],state="done")
    with pytest.raises(Conflict):
        authorize(SelfDevelop(Store(tmp_path/"hub.db")),chat,task,
                  paths=["hub/other.py"])


def test_new_request_still_enforces_task_state_after_done(tmp_path):
    store,service,chat,task=make_mapping(tmp_path)
    store.update(task["id"],state="done")
    with pytest.raises(Conflict):
        authorize(service,chat,task,"brand-new-run-20261108")


def test_other_chat_cannot_replay_existing_objective_request(tmp_path):
    store,service,chat,task=make_mapping(tmp_path)
    authorize(service,chat,task)
    other=service.start("Other original objective","test:objective-other","mcp")["chat_id"]
    store.update(task["id"],state="done")
    with pytest.raises(Conflict):
        authorize(service,other,task)
