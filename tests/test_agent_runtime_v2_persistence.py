"""P04: additive plan/evidence/event/checkpoint persistence with CAS and rollback."""
from datetime import datetime, timezone
import sqlite3
import pytest

from hub.agent_runtime_v2.contracts import TaskPlan, PlanStep, AcceptanceCriterion, Evidence
from hub.agent_runtime_v2.persistence import PlanRepository, PlanRevisionConflict, EvidenceConflict


def crit(ident="final"):
    return AcceptanceCriterion(id=ident,description="Verified result",verifier_type="url",
                               expected={"host":"walla.co.il"})

def plan(v=1, goal="Reach login", task_id="task-one"):
    return TaskPlan(task_id=task_id,version=v,goal=goal,
                    steps=[PlanStep(id="enter",plan_version=v,objective="Open page",acceptance=[crit("site")]),
                           PlanStep(id="verify",plan_version=v,objective="Verify login form",
                                    dependencies=["enter"],acceptance=[crit("login")])],
                    completion_criteria=[crit()])

def ev(eid="ev-1", step="verify",task_id="task-one",message="login visible"):
    return Evidence(evidence_id=eid,task_id=task_id,step_id=step,source="browser",
                    observed_at=datetime(2026,11,15,tzinfo=timezone.utc),
                    content_hash="abcdef",sanitized_payload={"message":message})


def test_constructor_does_not_write_database(tmp_path):
    db=tmp_path/"agent.sqlite"
    PlanRepository(db)
    assert not db.exists()


def test_additive_migration_preserves_legacy_user_tables_and_rows(tmp_path):
    db=tmp_path/"hub.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY, goal TEXT)")
        c.execute("INSERT INTO tasks VALUES (?,?)",("preserve-me","Old user goal"))
    repo=PlanRepository(db)
    repo.ensure_schema()
    repo.ensure_schema()
    assert repo.write_plan(plan())==1
    with sqlite3.connect(db) as c:
        rows=c.execute("SELECT id,goal FROM tasks").fetchall()
        assert rows==[("preserve-me","Old user goal")]
        assert c.execute("SELECT COUNT(*) FROM agent_schema_migrations").fetchone()[0]==1


def test_version_history_and_optimistic_concurrency(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema()
    assert repo.read_current("task-one") is None
    assert repo.write_plan(plan(),expected_revision=0)==1
    first,rev=repo.read_current("task-one")
    assert first.version==1 and rev==1
    assert repo.write_plan(plan(v=2,goal="Revised goal"),expected_revision=1)==2
    latest,newrev=repo.read_current("task-one")
    assert latest.goal=="Revised goal" and latest.version==2 and newrev==2
    assert repo.read_version("task-one",1).goal=="Reach login"
    assert [e["kind"] for e in repo.events("task-one")]==["plan.created","plan.revised"]


def test_stale_plan_and_skipped_version_are_rejected_without_partial_write(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema()
    repo.write_plan(plan())
    with pytest.raises(PlanRevisionConflict):
        repo.write_plan(plan(v=2),expected_revision=0)
    with pytest.raises(PlanRevisionConflict):
        repo.write_plan(plan(v=3),expected_revision=1)
    with pytest.raises(PlanRevisionConflict):
        repo.write_plan(plan(v=2),expected_revision=None)
    assert repo.read_current("task-one")[1]==1
    assert repo.read_version("task-one",2) is None
    assert len(repo.events("task-one"))==1


def test_evidence_unique_idempotency_and_conflict(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema();repo.write_plan(plan())
    assert repo.add_evidence(ev()) is True
    assert repo.add_evidence(ev()) is False
    assert len(repo.evidence_for_step("task-one","verify"))==1
    with pytest.raises(EvidenceConflict):
        repo.add_evidence(ev(message="different"))
    with pytest.raises(ValueError):
        repo.add_evidence(ev(eid="bad",step="unknown"))
    assert len(repo.evidence_for_step("task-one","verify"))==1


def test_event_idempotency_and_causal_order(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema();repo.write_plan(plan())
    seq=repo.append_event("event-1","task-one",1,"tool.completed",{"ok":True})
    assert repo.append_event("event-1","task-one",1,"tool.completed",{"ok":True})==seq
    with pytest.raises(EvidenceConflict):
        repo.append_event("event-1","task-one",1,"tool.completed",{"ok":False})
    assert repo.events("task-one")[-1]["payload"]=={"ok":True}


def test_checkpoint_revision_cas_resume_after_reopen(tmp_path):
    db=tmp_path/"db.sqlite";repo=PlanRepository(db)
    repo.ensure_schema();repo.write_plan(plan())
    assert repo.read_checkpoint("task-one") is None
    assert repo.save_checkpoint("task-one",1,{"phase":"verify"},expected_revision=0)==1
    other=PlanRepository(db)
    assert other.read_checkpoint("task-one")==(1,1,{"phase":"verify"})
    assert other.save_checkpoint("task-one",1,{"phase":"done"},expected_revision=1)==2
    with pytest.raises(PlanRevisionConflict):
        repo.save_checkpoint("task-one",1,{"phase":"stale"},expected_revision=1)
    assert repo.read_checkpoint("task-one")==(2,1,{"phase":"done"})


def test_cannot_checkpoint_superseded_plan_version(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema();repo.write_plan(plan())
    repo.save_checkpoint("task-one",1,{"phase":"ready"})
    repo.write_plan(plan(v=2),expected_revision=1)
    with pytest.raises(PlanRevisionConflict):
        repo.save_checkpoint("task-one",1,{"phase":"invalid"},expected_revision=1)
    assert repo.save_checkpoint("task-one",2,{"phase":"replanned"},expected_revision=1)==2


def test_reject_new_plan_that_skips_version_one(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema()
    with pytest.raises(PlanRevisionConflict):
        repo.write_plan(plan(v=2),expected_revision=0)
    assert repo.read_current("task-one") is None


def test_injection_string_is_only_parameter_value(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema()
    odd="x'); DROP TABLE tasks; --"
    repo.write_plan(plan(task_id=odd))
    assert repo.read_current(odd)[0].task_id==odd
    with sqlite3.connect(repo.db_path) as c:
        assert c.execute("SELECT COUNT(*) FROM agent_plans").fetchone()[0]==1


def test_schema_tables_still_queryable_after_schema_rerun(tmp_path):
    repo=PlanRepository(tmp_path/"db.sqlite")
    repo.ensure_schema();repo.write_plan(plan())
    repo.ensure_schema()
    assert repo.read_current("task-one")[1]==1
    assert len(repo.events("task-one"))==1
