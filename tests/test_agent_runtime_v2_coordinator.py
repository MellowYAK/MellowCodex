"""P08: pure shadow lifecycle, retry, cancellation and checkpoint behavior."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest

from hub.agent_runtime_v2.contracts import (
    TaskPlan,PlanStep,AcceptanceCriterion,Evidence,ToolRisk,TaskLifecycle,
)
from hub.agent_runtime_v2.coordinator import (
    ExecutionSnapshot,Signal,TransitionError,initial_snapshot,advance,
)
from hub.agent_runtime_v2.persistence import PlanRepository

NOW=datetime(2026,11,15,12,0,tzinfo=timezone.utc)


def plan(version=1):
    steps=[]
    for i,name in enumerate(("open","verify")):
        steps.append(PlanStep(
            id=name,plan_version=version,objective=name,
            dependencies=[] if i==0 else ["open"],
            acceptance=[AcceptanceCriterion(
                id="criterion-"+name,description="Prove "+name,
                verifier_type="structured_output",
                expected={"source_observed":True} if i==0 else
                         {"final_goal_verified":True,"terminal_task_state":"done"},
            )],
        ))
    return TaskPlan(task_id="task",version=version,goal="Actual user goal",
                    steps=steps,completion_criteria=[
                        AcceptanceCriterion(id="final",description="Actual final result",
                          verifier_type="structured_output",
                          expected={"final_goal_verified":True,"terminal_task_state":"done"},
                        )])


def evidence(step,version=1):
    body={"source_observed":True} if step=="open" else {
        "final_goal_verified":True,"terminal_task_state":"done",
    }
    return Evidence(evidence_id=step+str(version),task_id="task",step_id=step,
                    source="tool",observed_at=NOW,content_hash="abcdef",
                    provenance={"plan_version":version,"status":"SUCCESS",
                                "verified_by":"deterministic","tool_name":"independent_verifier"},
                    sanitized_payload=body,
                    freshness_deadline=NOW+timedelta(seconds=3))


def go(p,s,signal,**kwargs):
    return advance(p,s,signal,expected_revision=s.revision,at=NOW+timedelta(milliseconds=500),**kwargs)


def ready():
    p=plan()
    s=go(p,initial_snapshot(p),Signal.START)
    s=go(p,s,Signal.PLAN_READY)
    assert s.state==TaskLifecycle.READY
    return p,s


def test_first_step_and_actual_goal_completion_requires_all_fresh_evidence():
    p,s=ready()
    s=go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.TOOL_OBSERVED)
    s=go(p,s,Signal.VERIFY,evidence=[evidence("open")])
    assert s.state==TaskLifecycle.READY
    assert s.current_step_id=="verify"
    assert s.verified_steps==("open",)
    s=go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.TOOL_OBSERVED)
    s=go(p,s,Signal.VERIFY,evidence=[evidence("open"),evidence("verify")])
    assert s.state==TaskLifecycle.FINAL_VERIFICATION
    assert s.verified_steps==("open","verify")
    s=go(p,s,Signal.FINAL_VERIFY,evidence=[evidence("open"),evidence("verify")])
    assert s.state==TaskLifecycle.COMPLETED
    assert s.last_reason_code=="original_goal_verified"
    with pytest.raises(TransitionError):
        go(p,s,Signal.DISPATCH)


def test_model_saying_done_without_acceptance_evidence_cannot_complete():
    p,s=ready()
    s=go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.TOOL_OBSERVED)
    s=go(p,s,Signal.VERIFY,evidence=[])
    assert s.state==TaskLifecycle.RETRY
    assert s.last_reason_code=="verification_failed_retry"


def test_false_final_verification_replans():
    p,s=ready()
    for sig in (Signal.DISPATCH,Signal.TOOL_OBSERVED):
        s=go(p,s,sig)
    s=go(p,s,Signal.VERIFY,evidence=[evidence("open")])
    for sig in (Signal.DISPATCH,Signal.TOOL_OBSERVED):
        s=go(p,s,sig)
    s=go(p,s,Signal.VERIFY,evidence=[evidence("open"),evidence("verify")])
    s=go(p,s,Signal.FINAL_VERIFY,evidence=[evidence("open")])
    assert s.state==TaskLifecycle.REPLAN
    assert not s.pending_uncertain_action


def test_readonly_failure_retry_budget_is_bounded():
    p,s=ready()
    for attempt in range(3):
        s=go(p,s,Signal.DISPATCH)
        s=go(p,s,Signal.TOOL_FAILED,max_retries=2)
        assert s.retry_counts["open"]==attempt+1
        if attempt<2:
            assert s.state==TaskLifecycle.RETRY
            s=go(p,s,Signal.RETRY)
        else:
            assert s.state==TaskLifecycle.REPLAN


def test_external_uncertain_action_blocks_retry_until_reconciled():
    p,s=ready()
    s=go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.TOOL_FAILED,action_risk=ToolRisk.EXTERNAL_EFFECT,action_id="external-1")
    assert s.state==TaskLifecycle.WAITING_USER
    assert s.pending_uncertain_action=="external-1"
    with pytest.raises(TransitionError):
        go(p,s,Signal.RETRY)
    with pytest.raises(TransitionError):
        go(p,s,Signal.RECONCILE,reconciled=False)
    s=go(p,s,Signal.RECONCILE,reconciled=True)
    assert s.state==TaskLifecycle.VERIFYING
    assert s.pending_uncertain_action is None


def test_explicit_unknown_effect_requires_action_id():
    p,s=ready()
    s=go(p,s,Signal.DISPATCH)
    with pytest.raises(TransitionError):
        go(p,s,Signal.EFFECT_UNKNOWN)
    s=go(p,s,Signal.EFFECT_UNKNOWN,action_id="post-123")
    assert s.pending_uncertain_action=="post-123"


def test_user_correction_creates_replan_not_automatic_navigation():
    p,s=ready()
    s=go(p,s,Signal.USER_CHANGE)
    assert s.state==TaskLifecycle.REPLAN
    assert s.plan_version==1
    with pytest.raises(TransitionError):
        go(p,s,Signal.ADOPT_PLAN,new_plan=plan(version=3))
    revised=plan(version=2)
    s=go(p,s,Signal.ADOPT_PLAN,new_plan=revised)
    assert s.state==TaskLifecycle.READY
    assert s.plan_version==2
    assert not s.verified_steps
    with pytest.raises(TransitionError):
        go(p,s,Signal.DISPATCH)


def test_approval_gates_are_explicit():
    p,s=ready()
    s=go(p,s,Signal.REQUIRE_APPROVAL)
    assert s.state==TaskLifecycle.WAITING_APPROVAL
    with pytest.raises(TransitionError):
        go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.APPROVE)
    assert s.state==TaskLifecycle.READY
    s=go(p,s,Signal.REQUIRE_APPROVAL)
    s=go(p,s,Signal.DENY)
    assert s.state==TaskLifecycle.FAILED


def test_cancel_terminal_and_invalid_order():
    p,s=ready()
    s=go(p,s,Signal.CANCEL)
    assert s.state==TaskLifecycle.CANCELLED
    with pytest.raises(TransitionError):
        go(p,s,Signal.PLAN_READY)
    with pytest.raises(TransitionError):
        go(p,initial_snapshot(p),Signal.DISPATCH)


def test_revision_compare_and_swap_and_transition_budget():
    p,s=ready()
    with pytest.raises(TransitionError):
        advance(p,s,Signal.DISPATCH,expected_revision=s.revision-1)
    with pytest.raises(TransitionError):
        advance(p,s,Signal.DISPATCH,expected_revision=s.revision,
                max_transitions=s.transition_count)


def test_checkpoint_serialized_and_restored_after_new_repository_instance(tmp_path):
    p,s=ready()
    db=tmp_path/"runtime.db"
    r=PlanRepository(db)
    r.ensure_schema()
    assert r.write_plan(p,expected_revision=0)==1
    assert r.save_checkpoint("task",1,s.model_dump(mode="json"),expected_revision=0)==1
    reloaded=PlanRepository(db)
    checkpoint=reloaded.read_checkpoint("task")
    assert checkpoint and checkpoint[0]==1
    restored=ExecutionSnapshot.model_validate(checkpoint[2])
    assert restored==s
    restored=go(p,restored,Signal.DISPATCH)
    assert reloaded.save_checkpoint("task",1,restored.model_dump(mode="json"),
                                   expected_revision=checkpoint[0])==2
    with pytest.raises(Exception):
        r.save_checkpoint("task",1,s.model_dump(mode="json"),expected_revision=1)


def test_user_change_while_external_effect_unknown_preserves_reconciliation_gate():
    p,s=ready()
    s=go(p,s,Signal.DISPATCH)
    s=go(p,s,Signal.EFFECT_UNKNOWN,action_id="upload-xyz")
    s=go(p,s,Signal.USER_CHANGE)
    assert s.state==TaskLifecycle.WAITING_USER
    assert s.pending_uncertain_action=="upload-xyz"
    with pytest.raises(TransitionError):
        go(p,s,Signal.ADOPT_PLAN,new_plan=plan(version=2))
