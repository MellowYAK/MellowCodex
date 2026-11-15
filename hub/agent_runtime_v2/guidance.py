"""P10: safe, versioned user guidance merge for an active agent plan.

Pure planning adapter only. No model call, tool dispatch, DB write, or
approval. Does not automatically promote old evidence to the new plan version.
Existing Chat/Bridge remains the authoritative source for raw user messages.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Iterable, Literal

from pydantic import Field

from .contracts import (
    AcceptanceCriterion, Contract, Evidence, PlanStep, TaskLifecycle, TaskPlan,
)
from .coordinator import (
    ExecutionSnapshot, Signal, TransitionError, advance,
)
from .feedback import sanitize
from .persistence import PlanRepository
from .verifier import verify_plan


class GuidanceConflict(RuntimeError):
    """Unsafe, ambiguous, stale, or unverified user-plan revision."""


class GuidanceKind(str, Enum):
    CORRECTION = "correction"
    EXTENSION = "extension"
    CLARIFICATION = "clarification"
    NEW_TASK = "new_task"
    CANCEL = "cancel"
    NEEDS_REVIEW = "needs_review"


class UserGuidance(Contract):
    guidance_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    source: Literal["user"] = "user"
    message: str = Field(min_length=1, max_length=2000)
    expected_plan_version: int = Field(ge=1)
    expected_snapshot_revision: int = Field(ge=0)
    explicit_kind: GuidanceKind | None = None


@dataclass(frozen=True)
class GuidanceProposal:
    kind: GuidanceKind
    reason_code: str
    safe_message: str
    plan: TaskPlan | None
    carryover_candidates: tuple[str, ...]
    requires_reverification: tuple[str, ...]
    superseded_steps: tuple[str, ...]


def classify_guidance(message: str) -> GuidanceKind:
    """Conservative language hints only; never autonomously act on ambiguity."""
    value = str(message).strip().casefold()
    if not value:
        return GuidanceKind.NEEDS_REVIEW
    checks: tuple[tuple[GuidanceKind, tuple[str, ...]], ...] = (
        (GuidanceKind.NEW_TASK, (
            "משימה חדשה", "new task", "separate task", "новая задача",
        )),
        (GuidanceKind.CANCEL, (
            "עצור את המשימה", "בטל את המשימה", "cancel task",
            "stop this task", "отмени задачу", "останови задачу",
        )),
        (GuidanceKind.CORRECTION, (
            "לא,", "לא ", "במקום", "בעצם", "תשנה", "תקן",
            "instead", "rather than", "no,", "change to",
            "вместо", "нет,", "измени",
        )),
        (GuidanceKind.EXTENSION, (
            "וגם", "בנוסף", "תוסיף", "also ", "add ", "добавь", "и ещё",
        )),
        (GuidanceKind.CLARIFICATION, (
            "הכוונה", "כלומר", "אני מתכוון", "i mean", "to clarify",
            "то есть", "я имею в виду",
        )),
    )
    for kind,prefixes in checks:
        if any(value.startswith(prefix) for prefix in prefixes):
            return kind
    return GuidanceKind.NEEDS_REVIEW


def _safe_text(value: str) -> str:
    output = sanitize(value)
    if not isinstance(output, str):
        raise ValueError("Only user text is supported")
    output = output.strip()
    if not output:
        raise GuidanceConflict("Empty user guidance after redaction")
    return output


def _carryover(
    old: TaskPlan,
    new: TaskPlan,
    snapshot: ExecutionSnapshot,
    evidence: Iterable[Evidence],
    at: datetime,
) -> tuple[str, ...]:
    """Identify proof-backed unchanged steps for later revalidation ONLY.

    Do not mint new-version Evidence or mark TaskPlan steps succeeded here.
    The P07 verifier must independently re-observe/revalidate on resume.
    """
    verified = dict(verify_plan(old, evidence, at=at).steps)
    old_steps = {step.id: step for step in old.steps}
    candidates = []
    for step in new.steps:
        previous = old_steps.get(step.id)
        if not previous or step.id not in snapshot.verified_steps:
            continue
        if not verified.get(step.id,False):
            continue
        if (
            previous.objective == step.objective
            and previous.dependencies == step.dependencies
            and previous.allowed_tool_classes == step.allowed_tool_classes
            and previous.acceptance == step.acceptance
        ):
            candidates.append(step.id)
    return tuple(candidates)


def propose_guidance(
    old_plan: TaskPlan,
    snapshot: ExecutionSnapshot,
    guidance: UserGuidance,
    *,
    new_goal: str | None = None,
    replacement_steps: list[PlanStep] | None = None,
    new_completion_criteria: list[AcceptanceCriterion] | None = None,
    existing_evidence: Iterable[Evidence] = (),
    at: datetime | None = None,
) -> GuidanceProposal:
    if (guidance.task_id != old_plan.task_id or
        snapshot.task_id != old_plan.task_id or
        guidance.expected_plan_version != old_plan.version or
        snapshot.plan_version != old_plan.version or
        guidance.expected_snapshot_revision != snapshot.revision):
        raise GuidanceConflict("Stale or mismatched task/plan/snapshot")
    if snapshot.pending_uncertain_action:
        raise GuidanceConflict("Must reconcile uncertain external effect before plan revision")
    safe_message = _safe_text(guidance.message)
    kind = guidance.explicit_kind or classify_guidance(guidance.message)
    if kind in (GuidanceKind.NEW_TASK,GuidanceKind.CANCEL,GuidanceKind.NEEDS_REVIEW):
        return GuidanceProposal(kind,"separate_or_manual_action",safe_message,
                                None,(),(),())
    if snapshot.state != TaskLifecycle.REPLAN:
        raise GuidanceConflict("Runtime must first enter REPLAN via user correction")
    if kind in (GuidanceKind.CORRECTION,GuidanceKind.EXTENSION):
        if not new_goal or not replacement_steps or not new_completion_criteria:
            raise GuidanceConflict("Changed goal requires freshly planned steps and acceptance criteria")
        proposed_goal = _safe_text(new_goal)
        steps = replacement_steps
        final = new_completion_criteria
    elif kind == GuidanceKind.CLARIFICATION:
        if new_goal is not None or replacement_steps is not None or new_completion_criteria is not None:
            raise GuidanceConflict("Clarification cannot silently alter the task goal")
        proposed_goal = old_plan.goal
        steps = [
            PlanStep.model_validate({
                **s.model_dump(mode="python"),
                "plan_version":old_plan.version+1,
            })
            for s in old_plan.steps
        ]
        final = old_plan.completion_criteria
    else:
        raise GuidanceConflict("Unrecognized guidance kind")
    if not steps or not final:
        raise GuidanceConflict("Revised plan cannot omit steps or acceptance")
    if any(s.plan_version != old_plan.version+1 for s in steps):
        raise GuidanceConflict("Revised steps must reference next plan version")
    new_plan = TaskPlan(
        task_id=old_plan.task_id,
        version=old_plan.version+1,
        goal=proposed_goal,
        constraints=[*old_plan.constraints,"User guidance: "+safe_message],
        steps=steps,
        completion_criteria=final,
        created_from_revision=snapshot.revision,
        status=TaskLifecycle.CREATED,
    )
    now = at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Verification time must be timezone-aware")
    carried = _carryover(old_plan,new_plan,snapshot,existing_evidence,now)
    new_step_ids = {step.id for step in steps}
    superseded = tuple(step.id for step in old_plan.steps if step.id not in new_step_ids)
    return GuidanceProposal(
        kind=kind,reason_code="versioned_plan_revised",
        safe_message=safe_message,plan=new_plan,
        carryover_candidates=carried,
        requires_reverification=tuple(step.id for step in new_plan.steps),
        superseded_steps=superseded,
    )


def persist_proposal(
    store: PlanRepository,
    proposal: GuidanceProposal,
    *,
    expected_store_revision: int,
) -> int:
    """Store plan vN+1 with P04 CAS; does not schedule external actions."""
    if proposal.plan is None:
        raise GuidanceConflict("No plan to persist; route this user message first")
    return store.write_plan(proposal.plan,expected_revision=expected_store_revision)


def adopt_proposal(
    old_plan: TaskPlan,
    snapshot: ExecutionSnapshot,
    proposal: GuidanceProposal,
) -> ExecutionSnapshot:
    """Use P08 replan gate; prior verified candidates still need new proof."""
    if proposal.plan is None:
        raise GuidanceConflict("No revised plan to adopt")
    try:
        return advance(
            old_plan,snapshot,Signal.ADOPT_PLAN,
            expected_revision=snapshot.revision,new_plan=proposal.plan,
        )
    except TransitionError as exc:
        raise GuidanceConflict(str(exc)) from exc
