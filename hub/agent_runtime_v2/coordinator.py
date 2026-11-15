"""P08 shadow-only deterministic state coordinator.

This reducer never sends model requests, clicks the browser, writes SQLite,
or approves a user action. The old Engine remains authoritative until an
explicit guarded integration proves these transitions end-to-end.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from pydantic import Field

from .contracts import Contract, Evidence, TaskLifecycle, TaskPlan, ToolRisk
from .verifier import verify_plan


class TransitionError(RuntimeError):
    """Invalid transition, revision conflict, or exhausted transition budget."""


class Signal(str, Enum):
    START = "start"
    PLAN_READY = "plan_ready"
    DISPATCH = "dispatch"
    TOOL_OBSERVED = "tool_observed"
    TOOL_FAILED = "tool_failed"
    EFFECT_UNKNOWN = "effect_unknown"
    RECONCILE = "reconcile"
    VERIFY = "verify"
    FINAL_VERIFY = "final_verify"
    RETRY = "retry"
    USER_CHANGE = "user_change"
    ADOPT_PLAN = "adopt_plan"
    REQUIRE_APPROVAL = "require_approval"
    APPROVE = "approve"
    DENY = "deny"
    REQUIRE_USER = "require_user"
    USER_PROVIDED = "user_provided"
    CANCEL = "cancel"


class ExecutionSnapshot(Contract):
    task_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    revision: int = Field(default=0, ge=0)
    state: TaskLifecycle = TaskLifecycle.CREATED
    current_step_id: str | None = None
    verified_steps: tuple[str, ...] = ()
    retry_counts: dict[str, int] = Field(default_factory=dict)
    pending_uncertain_action: str | None = None
    transition_count: int = Field(default=0, ge=0)
    last_reason_code: str = "created"


def initial_snapshot(plan: TaskPlan) -> ExecutionSnapshot:
    return ExecutionSnapshot(
        task_id=plan.task_id,
        plan_version=plan.version,
        current_step_id=plan.steps[0].id,
    )


def _changed(snapshot: ExecutionSnapshot, **changes: object) -> ExecutionSnapshot:
    fields = {**snapshot.model_dump(mode="python"), **changes,
              "revision": snapshot.revision + 1,
              "transition_count": snapshot.transition_count + 1}
    return ExecutionSnapshot.model_validate(fields)


def _current_step(plan: TaskPlan, snapshot: ExecutionSnapshot):
    for step in plan.steps:
        if step.id == snapshot.current_step_id:
            return step
    raise TransitionError("Unknown current step")


def advance(
    plan: TaskPlan,
    snapshot: ExecutionSnapshot,
    signal: Signal | str,
    *,
    expected_revision: int,
    evidence: Iterable[Evidence] = (),
    at: datetime | None = None,
    new_plan: TaskPlan | None = None,
    action_id: str | None = None,
    action_risk: ToolRisk = ToolRisk.READ_ONLY,
    reconciled: bool = False,
    max_retries: int = 2,
    max_transitions: int = 150,
) -> ExecutionSnapshot:
    """Reduce one bounded event. A caller persists returned state with CAS.

    No external side effect happens here. Uncertain R2/R3 effects halt until
    reconciled; no automatic replay is authorized.
    """
    if plan.task_id != snapshot.task_id or plan.version != snapshot.plan_version:
        raise TransitionError("Plan/task identity or version mismatch")
    if expected_revision != snapshot.revision:
        raise TransitionError("Stale snapshot revision")
    if max_retries < 0 or max_transitions < 1:
        raise ValueError("Invalid safety budget")
    if snapshot.transition_count >= max_transitions:
        raise TransitionError("Transition budget exhausted")
    try:
        signal = Signal(signal)
    except ValueError as exc:
        raise TransitionError("Unknown signal") from exc
    state = snapshot.state
    if state in (TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED,
                 TaskLifecycle.FAILED):
        raise TransitionError("Terminal task state cannot be changed")
    if signal == Signal.CANCEL:
        return _changed(snapshot,state=TaskLifecycle.CANCELLED,
                        last_reason_code="explicit_cancel")
    if signal == Signal.USER_CHANGE:
        if snapshot.pending_uncertain_action:
            return _changed(snapshot,state=TaskLifecycle.WAITING_USER,
                            last_reason_code="reconcile_before_replan")
        return _changed(snapshot,state=TaskLifecycle.REPLAN,
                        last_reason_code="user_goal_revision")
    if signal == Signal.ADOPT_PLAN:
        if state != TaskLifecycle.REPLAN or new_plan is None:
            raise TransitionError("Replan requires a new TaskPlan")
        if (new_plan.task_id != plan.task_id or
                new_plan.version != plan.version + 1):
            raise TransitionError("A replan must advance exactly one plan version")
        if snapshot.pending_uncertain_action:
            raise TransitionError("Cannot replan with an uncertain external effect")
        # Previously observed evidence remains in the history but MUST be
        # revalidated against the new plan version before marking any step done.
        return _changed(snapshot,plan_version=new_plan.version,
                        state=TaskLifecycle.READY,
                        current_step_id=new_plan.steps[0].id,
                        verified_steps=(),retry_counts={},
                        last_reason_code="new_plan_version")
    if signal == Signal.REQUIRE_APPROVAL:
        if state != TaskLifecycle.READY:
            raise TransitionError("Approval can only gate a ready step")
        return _changed(snapshot,state=TaskLifecycle.WAITING_APPROVAL,
                        last_reason_code="approval_required")
    if signal == Signal.APPROVE:
        if state != TaskLifecycle.WAITING_APPROVAL:
            raise TransitionError("No approval pending")
        return _changed(snapshot,state=TaskLifecycle.READY,
                        last_reason_code="approval_granted")
    if signal == Signal.DENY:
        if state != TaskLifecycle.WAITING_APPROVAL:
            raise TransitionError("No approval pending")
        return _changed(snapshot,state=TaskLifecycle.FAILED,
                        last_reason_code="approval_denied")
    if signal == Signal.REQUIRE_USER:
        if state not in (TaskLifecycle.READY, TaskLifecycle.EXECUTING_STEP,
                         TaskLifecycle.VERIFYING, TaskLifecycle.REPLAN):
            raise TransitionError("User input cannot be requested from this phase")
        return _changed(snapshot,state=TaskLifecycle.WAITING_USER,
                        last_reason_code="user_input_required")
    if signal == Signal.USER_PROVIDED:
        if state != TaskLifecycle.WAITING_USER or snapshot.pending_uncertain_action:
            raise TransitionError("Unknown external effect must first be reconciled")
        return _changed(snapshot,state=TaskLifecycle.REPLAN,
                        last_reason_code="user_input_received")
    if signal == Signal.START:
        if state != TaskLifecycle.CREATED:
            raise TransitionError("Start only from created")
        return _changed(snapshot,state=TaskLifecycle.PLANNING,
                        last_reason_code="planning_started")
    if signal == Signal.PLAN_READY:
        if state != TaskLifecycle.PLANNING:
            raise TransitionError("Plan ready only after planning")
        return _changed(snapshot,state=TaskLifecycle.READY,
                        last_reason_code="plan_ready")
    if signal == Signal.DISPATCH:
        if state != TaskLifecycle.READY or snapshot.pending_uncertain_action:
            raise TransitionError("Cannot dispatch from this state")
        _current_step(plan,snapshot)
        return _changed(snapshot,state=TaskLifecycle.EXECUTING_STEP,
                        last_reason_code="step_dispatched")
    if signal == Signal.EFFECT_UNKNOWN:
        if state != TaskLifecycle.EXECUTING_STEP or not action_id:
            raise TransitionError("Unknown effect requires dispatched action ID")
        return _changed(snapshot,state=TaskLifecycle.WAITING_USER,
                        pending_uncertain_action=action_id,
                        last_reason_code="effect_unknown_reconciliation_required")
    if signal == Signal.RECONCILE:
        if state != TaskLifecycle.WAITING_USER or not snapshot.pending_uncertain_action:
            raise TransitionError("No uncertain effect to reconcile")
        if not reconciled:
            raise TransitionError("Unknown result cannot be declared reconciled")
        return _changed(snapshot,state=TaskLifecycle.VERIFYING,
                        pending_uncertain_action=None,
                        last_reason_code="effect_reconciled_verify")
    if signal == Signal.TOOL_FAILED:
        if state != TaskLifecycle.EXECUTING_STEP:
            raise TransitionError("Tool failure requires executing state")
        if action_risk in (ToolRisk.EXTERNAL_EFFECT,ToolRisk.HIGH_RISK):
            return _changed(snapshot,state=TaskLifecycle.WAITING_USER,
                            pending_uncertain_action=action_id or "unknown_external_effect",
                            last_reason_code="unsafe_failure_requires_reconciliation")
        sid=_current_step(plan,snapshot).id
        count=snapshot.retry_counts.get(sid,0)+1
        updated={**snapshot.retry_counts,sid:count}
        return _changed(snapshot,retry_counts=updated,
                        state=(TaskLifecycle.REPLAN if count>max_retries else TaskLifecycle.RETRY),
                        last_reason_code="tool_failed_retry" if count<=max_retries else "retry_budget_exhausted")
    if signal == Signal.TOOL_OBSERVED:
        if state != TaskLifecycle.EXECUTING_STEP:
            raise TransitionError("Observation requires executing state")
        return _changed(snapshot,state=TaskLifecycle.VERIFYING,
                        last_reason_code="tool_observed_not_yet_verified")
    if signal == Signal.RETRY:
        if state != TaskLifecycle.RETRY or snapshot.pending_uncertain_action:
            raise TransitionError("Retry not allowed")
        return _changed(snapshot,state=TaskLifecycle.READY,
                        last_reason_code="retry_ready")
    if signal in (Signal.VERIFY,Signal.FINAL_VERIFY):
        desired = (TaskLifecycle.VERIFYING if signal == Signal.VERIFY
                   else TaskLifecycle.FINAL_VERIFICATION)
        if state != desired:
            raise TransitionError("Verification signal not valid for state")
        now = at or datetime.now(timezone.utc)
        report=verify_plan(plan,evidence,at=now)
        if signal == Signal.FINAL_VERIFY:
            return _changed(snapshot,
                            state=(TaskLifecycle.COMPLETED if report.completed
                                   else TaskLifecycle.REPLAN),
                            last_reason_code=("original_goal_verified" if report.completed
                                              else "final_acceptance_failed"))
        step_states=dict(report.steps)
        sid=_current_step(plan,snapshot).id
        if not step_states.get(sid,False):
            count=snapshot.retry_counts.get(sid,0)+1
            updated={**snapshot.retry_counts,sid:count}
            return _changed(snapshot,retry_counts=updated,
                            state=(TaskLifecycle.REPLAN if count>max_retries
                                   else TaskLifecycle.RETRY),
                            last_reason_code=("verification_failed_retry"
                                              if count<=max_retries
                                              else "verification_budget_exhausted"))
        verified=tuple(step.id for step in plan.steps
                       if step_states.get(step.id,False))
        next_step=next((step.id for step in plan.steps
                        if not step_states.get(step.id,False)),None)
        if next_step is None:
            return _changed(snapshot,state=TaskLifecycle.FINAL_VERIFICATION,
                            verified_steps=verified,last_reason_code="all_steps_verified")
        return _changed(snapshot,state=TaskLifecycle.READY,
                        current_step_id=next_step,verified_steps=verified,
                        last_reason_code="advance_to_next_step")
    raise TransitionError("Unhandled signal")
