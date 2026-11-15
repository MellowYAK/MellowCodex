"""P09: durable exactly-once dispatch intent and unknown-effect recovery."""
import sqlite3
import pytest

from hub.agent_runtime_v2.contracts import ToolRisk, stable_action_key
from hub.agent_runtime_v2.recovery import (
    ActionLedger, ActionConflict, IntentState, RecoveryDecision,
)


def make(tmp_path):
    path=tmp_path/"runtime.db"
    led=ActionLedger(path)
    led.ensure_schema()
    return led


def reserve(led, risk=ToolRisk.EXTERNAL_EFFECT, step="publish-step",
            target="youtube/channel", name="publish", args=None):
    return led.reserve(task_id="t",step_id=step,effect_name=name,target=target,
                       arguments=args or {"video":"v1"},risk_level=risk)


def test_constructor_is_readonly(tmp_path):
    db=tmp_path/"not_created.db"
    led=ActionLedger(db)
    assert not db.exists()


def test_additive_schema_never_changes_legacy_tasks(tmp_path):
    db=tmp_path/"legacy.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY, goal TEXT)")
        c.execute("INSERT INTO tasks VALUES('old','preserve')")
    led=ActionLedger(db)
    led.ensure_schema()
    led.ensure_schema()
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT id,goal FROM tasks").fetchall()==[("old","preserve")]
        assert c.execute("SELECT COUNT(*) FROM agent_action_intents").fetchone()[0]==0


def test_same_external_effect_registered_once_across_replan_and_process_restart(tmp_path):
    db=tmp_path/"db.sqlite"
    led=ActionLedger(db);led.ensure_schema()
    first,created=reserve(led)
    assert created and first.state==IntentState.RESERVED
    new=ActionLedger(db)
    again,created2=reserve(new,step="new-plan-step")
    assert not created2 and first.idempotency_key==again.idempotency_key
    assert again.first_step_id=="publish-step"
    assert len(new.for_task("t"))==1
    assert led.recommend(again)==RecoveryDecision.WAIT_APPROVAL


def test_external_requires_explicit_approval_before_dispatch(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led)
    with pytest.raises(ActionConflict):
        led.begin_dispatch(a.idempotency_key,expected_revision=1)
    a=led.begin_dispatch(a.idempotency_key,expected_revision=1,approved=True)
    assert a.state==IntentState.DISPATCHED and a.attempts==1
    with pytest.raises(ActionConflict):
        led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)


def test_unknown_result_blocks_duplicate_post_after_restart(tmp_path):
    db=tmp_path/"runtime.sqlite"
    led=ActionLedger(db);led.ensure_schema()
    a,_=reserve(led)
    a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    after_crash=ActionLedger(db).get(a.idempotency_key)
    assert after_crash.state==IntentState.DISPATCHED
    assert led.recommend(after_crash)==RecoveryDecision.WAIT_EFFECT_RECONCILIATION
    with pytest.raises(ActionConflict):
        led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    a=ActionLedger(db).mark_unknown(a.idempotency_key,expected_revision=a.revision)
    assert led.recommend(a)==RecoveryDecision.WAIT_EFFECT_RECONCILIATION
    with pytest.raises(ActionConflict):
        led.prepare_retry(a.idempotency_key,expected_revision=a.revision,approved=True)


def test_verified_applied_effect_makes_repeated_publish_skip(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led)
    a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    a=led.reconcile(a.idempotency_key,expected_revision=a.revision,
                    effect="applied",evidence_id="youtube-post-id-123")
    assert a.state==IntentState.APPLIED
    assert led.recommend(a)==RecoveryDecision.SKIP_DUPLICATE
    again,created=reserve(led,step="after-replan")
    assert not created and again.state==IntentState.APPLIED
    assert led.recommend(again)==RecoveryDecision.SKIP_DUPLICATE
    a2=led.reconcile(a.idempotency_key,expected_revision=a.revision,
                     effect="applied",evidence_id="youtube-post-id-123")
    assert a2==a
    with pytest.raises(ActionConflict):
        led.reconcile(a.idempotency_key,expected_revision=a.revision,
                      effect="not_applied",evidence_id="different")


def test_reconcile_requires_effect_proof(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led)
    with pytest.raises(ActionConflict):
        led.reconcile(a.idempotency_key,expected_revision=a.revision,
                      effect="applied",evidence_id="proof")
    a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    with pytest.raises(ValueError):
        led.reconcile(a.idempotency_key,expected_revision=a.revision,
                      effect="applied",evidence_id="")
    assert led.get(a.idempotency_key).state==IntentState.DISPATCHED


def test_transient_readonly_proven_noneffect_allows_bounded_retry(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led,risk=ToolRisk.READ_ONLY,name="fetch",target="walla")
    for attempt in range(3):
        a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,max_attempts=3)
        assert a.attempts==attempt+1
        a=led.reconcile(a.idempotency_key,expected_revision=a.revision,
                        effect="not_applied",evidence_id="fetch-no-effect-"+str(attempt))
        if attempt<2:
            assert led.recommend(a)==RecoveryDecision.RETRY_SAFE
            a=led.prepare_retry(a.idempotency_key,expected_revision=a.revision)
        else:
            assert led.recommend(a)==RecoveryDecision.EXHAUSTED
            with pytest.raises(ActionConflict):
                led.prepare_retry(a.idempotency_key,expected_revision=a.revision)


def test_external_proven_noneffect_still_requires_reapproval(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led)
    a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    a=led.reconcile(a.idempotency_key,expected_revision=a.revision,
                    effect="not_applied",evidence_id="external-check-failed")
    assert led.recommend(a)==RecoveryDecision.REQUIRE_REAPPROVAL
    with pytest.raises(ActionConflict):
        led.prepare_retry(a.idempotency_key,expected_revision=a.revision)
    a=led.prepare_retry(a.idempotency_key,expected_revision=a.revision,approved=True)
    assert a.state==IntentState.RESERVED
    with pytest.raises(ActionConflict):
        led.begin_dispatch(a.idempotency_key,expected_revision=a.revision)


def test_revision_conflict_does_not_mutate_intent(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led,risk=ToolRisk.READ_ONLY)
    with pytest.raises(ActionConflict):
        led.begin_dispatch(a.idempotency_key,expected_revision=0)
    assert led.get(a.idempotency_key)==a


def test_no_user_args_or_target_stored_in_sqlite(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led,target="https://private.example/callback?token=SEC_123",
                args={"password":"VERY_SECRET_PASSWORD","token":"KEY_123"})
    with sqlite3.connect(led.db_path) as conn:
        all_fields=conn.execute("SELECT * FROM agent_action_intents").fetchone()
        serialized=str(tuple(all_fields))
        for raw in ("SEC_123","VERY_SECRET_PASSWORD","KEY_123","https://private.example"):
            assert raw not in serialized
    assert len(a.target_hash)==64


def test_semantically_distinct_effects_have_distinct_intents(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led,args={"video":"v1"})
    b,_=reserve(led,args={"video":"v2"})
    assert a.idempotency_key!=b.idempotency_key
    assert len(led.for_task("t"))==2


def test_idempotency_key_dict_order_preserved(tmp_path):
    led=make(tmp_path)
    args1={"visibility":"private","video":"v1"}
    args2={"video":"v1","visibility":"private"}
    a,_=reserve(led,args=args1)
    b,created=reserve(led,args=args2)
    assert not created and b.idempotency_key==a.idempotency_key


def test_stale_reconciliation_cannot_overwrite_effect(tmp_path):
    led=make(tmp_path)
    a,_=reserve(led)
    a=led.begin_dispatch(a.idempotency_key,expected_revision=a.revision,approved=True)
    a=led.mark_unknown(a.idempotency_key,expected_revision=a.revision)
    with pytest.raises(ActionConflict):
        led.reconcile(a.idempotency_key,expected_revision=a.revision-1,
                      effect="applied",evidence_id="proof")
    assert led.get(a.idempotency_key).state==IntentState.UNKNOWN
