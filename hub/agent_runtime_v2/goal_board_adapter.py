"""P05: adapt an existing editable Goal Board to a versioned V2 TaskPlan.

The existing browser_goal_boards SQLite row and user edits remain authoritative.
This pure conversion NEVER marks a goal completed, dispatches a tool or bypasses
Guard. The V2 verifier decides completion from new, fresh evidence.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from hub.browser_goal_board import clean, validate_steps
from .contracts import (
    AcceptanceCriterion, PlanStep, TaskLifecycle, TaskPlan, ToolRisk,
)


TOOLS = {
    "browser": ["browser_navigate", "browser_observe", "browser_act",
                "browser_assess", "browser_pointer"],
    "code": ["context_search", "context_expand", "file_read",
             "candidate_patch", "candidate_test"],
    "desktop": ["desktop_status", "desktop_action", "window_act"],
    "inspect": ["project_context", "context_search", "context_expand"],
}
MODES = frozenset(TOOLS)


def _criterion(step: dict[str, Any], *, mode: str, intent: str,
               host: str) -> AcceptanceCriterion:
    role = step["role"]
    expected: dict[str, Any] = {"role": role, "task_mode": mode}
    if mode == "browser":
        if role == "entry":
            verifier = "url" if host else "structured_output"
            expected.update({"observed_page": True, "coherent": True})
            if host:
                expected["required_host"] = host
        elif role == "discover":
            verifier = "dom"
            expected.update({"observed_control": True,
                             "intent": intent, "required_host": host})
        elif role == "act":
            verifier = "structured_output"
            expected.update({"input_sent": True, "post_action_observed": True})
        elif role == "final" and intent == "login":
            verifier = "dom"
            expected.update({"login_form": True, "required_host": host,
                             "verified_assessment": True,
                             "final_goal_verified": True})
        else:
            verifier = "structured_output"
            expected.update({"required_host": host, "verified_assessment": True,
                             "final_goal_verified": True})
    else:
        verifier = "structured_output"
        if role == "entry":
            expected["source_observed"] = True
        elif role == "discover":
            expected["route_or_evidence_identified"] = True
        elif role == "act":
            expected["tool_effect_verified"] = True
        else:
            expected.update({"terminal_task_state": "done",
                             "final_goal_verified": True})
    return AcceptanceCriterion(
        id="verify_" + step["id"],
        description=clean(step["expected"], 800),
        verifier_type=verifier,
        expected=expected,
        required=True,
        evidence_freshness_ms=5000 if mode == "browser" else 60000,
        risk_level=ToolRisk.READ_ONLY,  # verification risk, NOT execution policy
    )


def adapt_board(
    board: Mapping[str, Any],
    task_id: str,
    *,
    plan_version: int = 1,
    created_from_revision: int | None = None,
) -> TaskPlan:
    """Convert a BoardStore snapshot or seeded dict without mutating either.

    A subsequent user board edit must result in a new TaskPlan.version and
    created_from_revision. The caller persists it via PlanRepository CAS.
    """
    if not isinstance(board, Mapping):
        raise ValueError("Expected a Goal Board mapping")
    mode = str(board.get("task_mode", "browser"))
    if mode not in MODES:
        raise ValueError("Unknown task mode")
    if not task_id or not str(task_id).strip():
        raise ValueError("task_id cannot be blank")
    goal = clean(board.get("goal", ""), 16000)
    if not goal.strip():
        raise ValueError("Goal Board contains no final objective")
    raw_steps = board.get("steps")
    steps = validate_steps(raw_steps)
    intent = str(board.get("intent", "general"))
    host = str(board.get("target_host", "") or "").lower().strip().rstrip(".")
    if host and not re.fullmatch(r"[a-z0-9.-]{1,253}", host):
        raise ValueError("Goal Board target host is malformed")
    board_revision = board.get("revision", 0)
    revision = board_revision if created_from_revision is None else created_from_revision

    adapted: list[PlanStep] = []
    for index, step in enumerate(steps):
        criterion = _criterion(step, mode=mode, intent=intent, host=host)
        alternatives = [clean(value, 160) for value in step.get("alternatives", [])]
        text = clean(step["title"], 160) + " | Expected: " + clean(step["expected"], 240)
        if alternatives:
            text += " | Alternatives: " + "; ".join(alternatives)
        adapted.append(PlanStep(
            id=step["id"],
            plan_version=plan_version,
            objective=text,
            dependencies=[steps[index - 1]["id"]] if index else [],
            allowed_tool_classes=list(TOOLS[mode]),
            acceptance=[criterion],
            max_model_turns=4 if step["role"] != "final" else 2,
            latency_budget_ms=12000,
        ))

    constraints = ["task_mode=" + mode, "intent=" + intent,
                   "feedback_mode=" + str(board.get("feedback_mode", "smart"))]
    if host:
        constraints.append("required_host=" + host)
    if board.get("notes"):
        constraints.append("User notes: " + clean(board["notes"], 1500))
    final = adapted[-1].acceptance[0]
    final_expected = {**final.expected, "original_goal": goal}
    final_criterion = AcceptanceCriterion(
        id="final_goal",
        description=final.description,
        verifier_type=final.verifier_type,
        expected=final_expected,
        evidence_freshness_ms=final.evidence_freshness_ms,
        required=True,
    )
    return TaskPlan(
        task_id=str(task_id).strip(),
        version=plan_version,
        goal=goal,
        constraints=constraints,
        steps=adapted,
        completion_criteria=[final_criterion],
        created_from_revision=revision,
        status=TaskLifecycle.CREATED,
    )
