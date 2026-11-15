"""SelfDevelop global safe same-chat retarget and cross-chat resume guarantees."""
import pytest
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop


def service(tmp_path):
    return SelfDevelop(Store(tmp_path/"hub.sqlite"))


def history(svc, chat_id):
    with svc.store.connect() as db:
        return [tuple(row) for row in db.execute(
            "SELECT revision,objective,event FROM selfdevelop_objective_history "
            "WHERE chat_id=? ORDER BY revision",(chat_id,),
        ).fetchall()]


def test_same_chat_idle_retarget_audits_old_goal_and_survives_restart(tmp_path):
    svc=service(tmp_path)
    a=svc.start("Repair Guard","persistent:chat","mcp")
    b=svc.start("Complete Agent Runtime V2","persistent:chat","mcp")
    assert a["chat_id"]==b["chat_id"]
    assert b["objective"]=="Complete Agent Runtime V2"
    assert history(svc,b["chat_id"])==[
        (1,"Repair Guard","created"),
        (2,"Complete Agent Runtime V2","retargeted"),
    ]
    reopened=service(tmp_path).start("Complete Agent Runtime V2","persistent:chat","mcp")
    assert reopened["chat_id"]==a["chat_id"]
    assert history(svc,a["chat_id"])==history(service(tmp_path),a["chat_id"])
    assert len(history(svc,a["chat_id"]))==2


def test_legacy_session_history_is_backfilled_on_retarget(tmp_path):
    svc=service(tmp_path)
    first=svc.start("Old objective","legacy:chat","mcp")
    with svc.store.connect() as db:
        db.execute("DELETE FROM selfdevelop_objective_history WHERE chat_id=?",(first["chat_id"],))
    second=svc.start("New objective","legacy:chat","mcp")
    assert second["chat_id"]==first["chat_id"]
    assert [(r[0],r[1]) for r in history(svc,first["chat_id"])]==[
        (1,"Old objective"),(2,"New objective"),
    ]


def test_unreviewed_previous_task_blocks_retarget(tmp_path):
    svc=service(tmp_path)
    s=svc.start("Original task","gate:chat","mcp")
    task=svc.step(s["chat_id"],"step-one","Inspect files",["project_context"])
    with pytest.raises(Conflict,match="Finish, review or cancel"):
        svc.start("Different objective","gate:chat","mcp")
    assert svc.status(s["chat_id"])["objective"]=="Original task"
    assert len(history(svc,s["chat_id"]))==1
    svc.store.update(task["id"],state="cancelled")
    assert svc.start("Different objective","gate:chat","mcp")["objective"]=="Different objective"


def test_pending_action_still_blocks_after_task_ends(tmp_path):
    svc=service(tmp_path)
    s=svc.start("First","effects:chat","mcp")
    task=svc.step(s["chat_id"],"step-one","Read files",["project_context"])
    svc.store.update(task["id"],state="done")
    # Use the real Store API and production actions schema, not a synthetic row.
    action_id=svc.store.begin_action(task["id"],"browser_act",{})
    assert action_id
    with pytest.raises(Conflict,match="Reconcile"):
        svc.start("Next","effects:chat","mcp")


def test_objective_level_run_blocks_retarget(tmp_path):
    svc=service(tmp_path)
    s=svc.start("Old","objective:chat","mcp")
    with svc.store.connect() as db:
        db.execute("""INSERT INTO selfdevelop_objective_runs
            (chat_id,request_id,task_id,phase,plan,updated)
            VALUES(?,?,?,?,?,?)""",
            (s["chat_id"],"request-old","x","semantic_review_required","{}","2026-11-15"))
    with pytest.raises(Conflict,match="objective-level"):
        svc.start("New","objective:chat","mcp")
    assert svc.status(s["chat_id"])["objective"]=="Old"


def test_new_chat_in_same_project_can_resume_independently(tmp_path):
    svc=service(tmp_path)
    a=svc.start("Old objective","external:chat:first","mcp")
    b=svc.start("Continue Runtime V2","external:chat:second","mcp")
    assert a["chat_id"]!=b["chat_id"]
    assert svc.status(a["chat_id"])["objective"]=="Old objective"
    assert svc.status(b["chat_id"])["objective"]=="Continue Runtime V2"
    assert len(history(svc,a["chat_id"]))==1
    assert len(history(svc,b["chat_id"]))==1


def test_same_chat_transport_change_rejected_without_side_effects(tmp_path):
    svc=service(tmp_path)
    a=svc.start("Goal","transport:chat","mcp")
    with pytest.raises(Conflict,match="another transport"):
        svc.start("Goal next","transport:chat","play")
    assert svc.status(a["chat_id"])["objective"]=="Goal"
    assert len(history(svc,a["chat_id"]))==1


def test_multiple_idle_retargets_have_monotonic_revisions(tmp_path):
    svc=service(tmp_path)
    a=svc.start("Goal one","revision:chat","mcp")
    for goal in ("Goal two","Goal three","Goal four"):
        assert svc.start(goal,"revision:chat","mcp")["objective"]==goal
    assert [item[0] for item in history(svc,a["chat_id"])]==[1,2,3,4]
    assert svc.start("Goal four","revision:chat","mcp")["objective"]=="Goal four"
    assert len(history(svc,a["chat_id"]))==4
