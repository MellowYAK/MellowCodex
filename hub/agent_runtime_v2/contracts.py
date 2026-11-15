"""Strict, versioned Agent Runtime V2 contracts.

These value objects do not replace the current Hub Engine, Store, Goal Board or
Guard. They are additive primitives for a future shadow runtime and verifier.
Never store raw model private reasoning in DecisionRecord.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ToolRisk(str, Enum):
    READ_ONLY = "R0"
    REVERSIBLE = "R1"
    EXTERNAL_EFFECT = "R2"
    HIGH_RISK = "R3"


class FeedbackStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNCERTAIN = "UNCERTAIN"
    USER_OVERRIDE = "USER_OVERRIDE"


class PlanStepState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"


class TaskLifecycle(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING_STEP = "executing_step"
    COLLECTING_EVIDENCE = "collecting_evidence"
    VERIFYING = "verifying"
    RETRY = "retry"
    REPLAN = "replan"
    WAITING_USER = "waiting_user"
    WAITING_APPROVAL = "waiting_approval"
    FINAL_VERIFICATION = "final_verification"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AcceptanceCriterion(Contract):
    id: str = Field(min_length=1, max_length=96)
    description: str = Field(min_length=1, max_length=800)
    verifier_type: str = Field(pattern=r"^(dom|url|visual|file|process|structured_output|user_confirmation|custom)$")
    expected: dict[str, Any] = Field(default_factory=dict)
    required: bool = True
    evidence_freshness_ms: int = Field(default=10000, ge=0, le=86400000)
    risk_level: ToolRisk = ToolRisk.READ_ONLY


class PlanStep(Contract):
    id: str = Field(min_length=1, max_length=96)
    plan_version: int = Field(ge=1)
    objective: str = Field(min_length=1, max_length=2400)
    dependencies: list[str] = Field(default_factory=list)
    allowed_tool_classes: list[str] = Field(default_factory=list)
    acceptance: list[AcceptanceCriterion] = Field(min_length=1)
    retry_policy_id: str = "safe-default"
    max_model_turns: int = Field(default=4, ge=0, le=200)
    latency_budget_ms: int = Field(default=12000, ge=100, le=3600000)
    state: PlanStepState = PlanStepState.PENDING

    @model_validator(mode="after")
    def validate_local_uniqueness(self) -> "PlanStep":
        ids = [criterion.id for criterion in self.acceptance]
        if len(ids) != len(set(ids)):
            raise ValueError("Acceptance criterion IDs must be unique within a step")
        if self.id in self.dependencies or len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("Step dependencies cannot include itself or duplicates")
        return self


class TaskPlan(Contract):
    task_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    goal: str = Field(min_length=1, max_length=16000)
    constraints: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(min_length=1)
    completion_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    created_from_revision: int = Field(default=0, ge=0)
    status: TaskLifecycle = TaskLifecycle.CREATED

    @field_validator("goal")
    @classmethod
    def nonblank_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Task goal cannot be whitespace only")
        return value

    @model_validator(mode="after")
    def valid_graph(self) -> "TaskPlan":
        steps = {step.id: step for step in self.steps}
        if len(steps) != len(self.steps):
            raise ValueError("Duplicate step ID")
        for step in self.steps:
            if step.plan_version != self.version:
                raise ValueError("Step plan version must equal TaskPlan.version")
            if any(dep not in steps for dep in step.dependencies):
                raise ValueError("Unknown step dependency")
        visited: set[str] = set()
        active: set[str] = set()

        def visit(sid: str) -> None:
            if sid in active:
                raise ValueError("Cyclic step dependencies")
            if sid in visited:
                return
            active.add(sid)
            for dep in steps[sid].dependencies:
                visit(dep)
            active.remove(sid)
            visited.add(sid)

        for sid in steps:
            visit(sid)
        finals = [criterion.id for criterion in self.completion_criteria]
        if len(finals) != len(set(finals)):
            raise ValueError("Duplicate final acceptance criterion ID")
        if not any(c.required for c in self.completion_criteria):
            raise ValueError("Final task requires at least one mandatory acceptance criterion")
        return self


def _require_aware(dt: datetime, field_name: str) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(field_name + " must be timezone-aware")
    return dt


class Evidence(Contract):
    evidence_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    source: str = Field(pattern=r"^(browser|desktop|tool|user|worker|file|process)$")
    observed_at: datetime
    tool_call_id: str | None = None
    target_id: str | None = None
    content_hash: str = Field(min_length=1)
    sanitized_payload: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    freshness_deadline: datetime | None = None

    @model_validator(mode="after")
    def valid_timestamps(self) -> "Evidence":
        _require_aware(self.observed_at, "observed_at")
        if self.freshness_deadline is not None:
            _require_aware(self.freshness_deadline, "freshness_deadline")
            if self.freshness_deadline < self.observed_at:
                raise ValueError("Freshness deadline cannot precede observation")
        return self

    def is_fresh(self, at: datetime | None = None, max_age_ms: int | None = None) -> bool:
        at = _require_aware(at or datetime.now(timezone.utc), "at")
        if at < self.observed_at:
            return False
        if self.freshness_deadline is not None and at > self.freshness_deadline:
            return False
        if max_age_ms is not None:
            if max_age_ms < 0:
                raise ValueError("max_age_ms must be nonnegative")
            if (at-self.observed_at).total_seconds()*1000 > max_age_ms:
                return False
        return True


class FeedbackEvent(Contract):
    feedback_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    step_id: str | None = None
    source: str = Field(pattern=r"^(browser|desktop|tool|user|worker|file|process)$")
    status: FeedbackStatus
    reason_code: str = Field(min_length=1, max_length=120)
    evidence_ids: list[str] = Field(default_factory=list)
    observed_at: datetime


class ActionRecord(Contract):
    action_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=16, max_length=128)
    task_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    effect_name: str = Field(min_length=1)
    risk_level: ToolRisk
    dispatch_state: str = Field(pattern=r"^(planned|dispatched|acknowledged|unknown|cancelled)$")
    outcome_state: FeedbackStatus = FeedbackStatus.UNCERTAIN
    evidence_ids: list[str] = Field(default_factory=list)


class DecisionRecord(Contract):
    decision_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    decision: str = Field(min_length=1, max_length=160)
    reason_code: str = Field(min_length=1, max_length=160)
    input_evidence_ids: list[str] = Field(default_factory=list)
    chosen_strategy: str = Field(min_length=1, max_length=160)
    model_reference: str | None = None
    elapsed_ms: int = Field(default=0, ge=0)


def stable_action_key(task_id: str, effect_name: str, target: str, arguments: dict[str, Any]) -> str:
    """Semantic idempotency key stable across plan revisions and dict key order.

    A replan must not produce a new key for the same external effect merely
    because it changed plan_version or step_id. Caller must supply stable
    target/effect identity; never put tokens or passwords in arguments.
    """
    if not task_id or not effect_name or not target:
        raise ValueError("Idempotency key requires task, effect and target")
    canonical = json.dumps(
        {"task_id":task_id,"effect":effect_name,"target":target,"args":arguments},
        sort_keys=True, separators=(",",":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
