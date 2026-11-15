"""P11: local bounded telemetry, safe decision codes and latency budgets."""
from pathlib import Path
import sqlite3
import pytest

from hub.agent_runtime_v2.telemetry import TraceRecorder,TraceConflict


def make(tmp_path):
    path=tmp_path/"trace.sqlite"
    recorder=TraceRecorder(path)
    recorder.ensure_schema()
    return recorder


def test_construction_does_not_create_or_edit_database(tmp_path):
    path=tmp_path/"not-created.sqlite"
    TraceRecorder(path)
    assert not path.exists()


def test_additive_schema_never_drops_legacy_rows(tmp_path):
    path=tmp_path/"legacy.sqlite"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY,body TEXT)")
        c.execute("INSERT INTO tasks VALUES('existing','unchanged')")
    recorder=TraceRecorder(path)
    recorder.ensure_schema()
    recorder.ensure_schema()
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT * FROM tasks").fetchall()==[("existing","unchanged")]


def test_monotonic_span_duration_and_parent_trace(tmp_path):
    t=make(tmp_path)
    root=t.start_span("task","planning",plan_version=3)
    child=t.start_span("task","browser.observe",trace_id=root.trace_id,parent_id=root.span_id,
                       plan_version=3)
    a=t.end_span(child,outcome="success",reason_code="observed",
                 attributes={"tool":"browser_frame","budget_ms":500},
                 elapsed_ms=14.2)
    b=t.end_span(root,outcome="success",reason_code="plan_ready",elapsed_ms=25.1)
    assert a["trace_id"]==b["trace_id"]
    assert a["parent_id"]==root.span_id
    assert a["duration_ms"]==14.2 and b["duration_ms"]==25.1
    assert len(t.spans("task"))==2


def test_secrets_and_untrusted_data_not_logged(tmp_path):
    t=make(tmp_path)
    s=t.start_span("task","browser.navigate")
    t.end_span(s,outcome="success",reason_code="navigated",
        attributes={
            "url":"https://example.com/callback?code=TOPSECRET&token=SECRET123",
            "password":"DO_NOT_LOG", "authorization":"Bearer secretsecret",
            "chain_of_thought":"PRIVATE_MODEL_DATA",
            "tool":"browser_act","model":"qwen",
        },elapsed_ms=2)
    with sqlite3.connect(t.db_path) as c:
        raw=str(c.execute("SELECT * FROM agent_trace_spans").fetchall())
        for secret in ("TOPSECRET","SECRET123","DO_NOT_LOG",
                       "secretsecret","PRIVATE_MODEL_DATA"):
            assert secret not in raw
    d=t.spans("task")[0]
    assert d["attributes"]["url"]=="https://example.com/callback"
    assert d["attributes"]["tool"]=="browser_act"
    assert "password" not in d["attributes"]


def test_identical_span_completion_idempotent(tmp_path):
    t=make(tmp_path)
    s=t.start_span("task","verification")
    one=t.end_span(s,outcome="success",reason_code="verified",elapsed_ms=10)
    two=t.end_span(s,outcome="success",reason_code="verified",elapsed_ms=25)
    assert one==two
    assert len(t.spans("task"))==1
    with pytest.raises(TraceConflict):
        t.end_span(s,outcome="failure",reason_code="error",elapsed_ms=10)


def test_fail_closed_on_invalid_or_oversized_identifiers(tmp_path):
    t=make(tmp_path)
    with pytest.raises(ValueError):
        t.start_span("task","bad phase")
    with pytest.raises(ValueError):
        t.start_span("","model")
    s=t.start_span("task","model.qwen")
    with pytest.raises(ValueError):
        t.end_span(s,outcome="maybe",reason_code="unknown",elapsed_ms=1)
    with pytest.raises(ValueError):
        t.end_span(s,outcome="success",reason_code="raw reasoning sentence",elapsed_ms=1)
    with pytest.raises(ValueError):
        t.end_span(s,outcome="success",reason_code="ok",elapsed_ms=-1)


def test_decision_record_excludes_private_reasoning(tmp_path):
    t=make(tmp_path)
    did=t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                          reason_code="low_uncertainty",selected="fast_local",
                          alternatives=["deep_local","cloud_reasoning"],
                          evidence_ids=["ev_123"],decision_id="decision-1")
    assert did=="decision-1"
    assert t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                          reason_code="low_uncertainty",selected="fast_local",
                          alternatives=["deep_local","cloud_reasoning"],
                          evidence_ids=["ev_123"],decision_id="decision-1")==did
    decisions=t.decisions("task")
    assert decisions[0]["reason_code"]=="low_uncertainty"
    assert decisions[0]["selected"]=="fast_local"
    assert decisions[0]["alternatives"]==["deep_local","cloud_reasoning"]


def test_decision_rejects_free_form_thought_and_collision(tmp_path):
    t=make(tmp_path)
    with pytest.raises(ValueError):
        t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                          reason_code="because I thought deeply",selected="model",
                          alternatives=[])
    t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                      reason_code="safe",selected="fast_local",alternatives=[],
                      decision_id="d")
    with pytest.raises(TraceConflict):
        t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                          reason_code="safe",selected="cloud",alternatives=[],
                          decision_id="d")


def test_latency_p50_p95_and_budget(tmp_path):
    t=make(tmp_path)
    for duration in (100,200,300,400,500):
        s=t.start_span("task","browser.observe")
        t.end_span(s,outcome="success",reason_code="observed",
                   elapsed_ms=duration)
    value=t.latency_summary("task",budgets_ms={"browser.observe":500})
    assert value["browser.observe"]["count"]==5
    assert value["browser.observe"]["p50_ms"]==300
    assert value["browser.observe"]["p95_ms"]==480
    assert value["browser.observe"]["within_budget"] is True
    value=t.latency_summary("task",budgets_ms={"browser.observe":400})
    assert value["browser.observe"]["within_budget"] is False


def test_persist_after_new_recorder_and_isolate_task(tmp_path):
    a=make(tmp_path)
    x=a.start_span("t1","model.fast")
    a.end_span(x,outcome="failure",reason_code="timeout",elapsed_ms=1300)
    db=TraceRecorder(a.db_path)
    assert len(db.spans("t1"))==1
    assert len(db.spans("t2"))==0
    assert db.latency_summary("t1")["model.fast"]["p95_ms"]==1300


def test_evidence_identity_limit(tmp_path):
    t=make(tmp_path)
    with pytest.raises(ValueError):
        t.record_decision(task_id="task",trace_id="trace",plan_version=1,
                          reason_code="route",selected="model",alternatives=[],
                          evidence_ids=["bad\nid"])


def test_unfinished_span_is_not_saved_as_success(tmp_path):
    t=make(tmp_path)
    _token=t.start_span("task","browser.act")
    assert t.spans("task")==[]
