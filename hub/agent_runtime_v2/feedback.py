"""P06 normalized, bounded tool/user feedback with safe, fresh evidence.

Model output and page text are untrusted data, never instructions. Conversion is
pure: no network, browser input, SQLite writes or automatic retry.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit
import uuid

from .contracts import Evidence, FeedbackEvent, FeedbackStatus


_SECRET_KEYS = re.compile(r"(?i)(?:^|[_\-.])(password|passwd|passcode|authorization|cookie|set.cookie|access.token|refresh.token|id.token|token|secret|api.key|client.secret|oauth.code|auth.code|credential|bearer)(?:$|[_\-.])")
_ASSIGN = re.compile(r"(?i)\b(password|passwd|passcode|access_token|refresh_token|id_token|api[_-]?key|token|secret|authorization|cookie)\s*[:=]\s*([^\s,;&]+)")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}")
_MAX_DEPTH = 6
_MAX_ITEMS = 60
_MAX_TEXT = 900


def _clean_string(value: str) -> str:
    text = value[:_MAX_TEXT]
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _ASSIGN.sub(lambda m: m.group(1)+"=[REDACTED]", text)
    # URLs can embed authorization codes and one-time OAuth state. Remove
    # *all* query/fragment values even if a parameter is not recognized.
    text = re.sub(r"https?://[^\s\"'<>]+", lambda m: _safe_url(m.group(0)), text)
    return text


def _safe_url(url: str) -> str:
    try:
        pieces = urlsplit(url)
        if pieces.scheme not in ("http", "https"):
            return "[REDACTED_URL]"
        if "@" in pieces.netloc:
            # userinfo is never safe as evidence or prompt context
            return "[REDACTED_URL]"
        return urlunsplit((pieces.scheme, pieces.netloc, pieces.path, "", ""))
    except ValueError:
        return "[REDACTED_URL]"


def sanitize(value: Any, *, _depth: int = 0) -> Any:
    """Return a bounded, JSON-compatible safe copy, never mutate source."""
    if _depth >= _MAX_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in list(value.items())[:_MAX_ITEMS]:
            name = str(key)[:100]
            if _SECRET_KEYS.search(name) or name.casefold() in {
                "code", "authorization", "cookies", "set-cookie", "oauth_state",
                "reasoning_content", "private_reasoning", "chain_of_thought",
            }:
                clean[name] = "[REDACTED]"
            else:
                clean[name] = sanitize(item, _depth=_depth+1)
        return clean
    if isinstance(value, (list, tuple)):
        return [sanitize(item, _depth=_depth+1) for item in value[:_MAX_ITEMS]]
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clean_string(str(value))


def normalize_feedback(
    *,
    task_id: str,
    step_id: str,
    source: str,
    tool_name: str,
    action_state: str,
    result: Mapping[str, Any] | None,
    action_id: str | None = None,
    observed_at: datetime | None = None,
    target_id: str | None = None,
    freshness_ms: int = 5000,
) -> tuple[FeedbackEvent, Evidence | None]:
    """Preserve the difference between input dispatch and verified effect.

    SUCCESS means this tool's own observed result is coherent or effect-verified.
    It is NEVER equivalent to task-goal success; a separate verifier must check
    the original acceptance criteria and fresh evidence.
    """
    if not task_id or not step_id or not tool_name:
        raise ValueError("Missing feedback task/step/tool identity")
    if source not in ("browser", "desktop", "tool", "user", "worker", "file", "process"):
        raise ValueError("Invalid feedback source")
    if freshness_ms < 0 or freshness_ms > 86400000:
        raise ValueError("Invalid evidence freshness")
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Feedback timestamp must be timezone-aware")
    safe = sanitize(dict(result or {}))
    state = str(action_state).casefold().strip()
    verified_effect = bool(
        isinstance(result, Mapping)
        and (result.get("closed_verified") is True
             or result.get("effect_verified") is True
             or (isinstance(result.get("after"), Mapping)
                 and result["after"].get("coherent") is True))
    )
    input_sent = bool(isinstance(result, Mapping) and result.get("input_sent") is True)
    coherent_observation = bool(
        isinstance(result, Mapping)
        and result.get("coherent") is True
        and (result.get("url") or result.get("title") or result.get("elements"))
    )
    result_error = bool(isinstance(result, Mapping) and result.get("error"))
    if source == "user" and state in ("override", "correction"):
        status, reason = FeedbackStatus.USER_OVERRIDE, "user_goal_revision"
    elif state in ("failed", "error") or result_error:
        status, reason = FeedbackStatus.FAILURE, "tool_failure"
    elif state not in ("complete", "completed", "success", "done"):
        status, reason = FeedbackStatus.UNCERTAIN, "tool_outcome_unknown"
    elif input_sent and not verified_effect:
        status, reason = FeedbackStatus.UNCERTAIN, "input_dispatched_effect_unverified"
    elif tool_name in ("browser_observe", "browser_frame", "browser_tabs"):
        status, reason = ((FeedbackStatus.SUCCESS, "coherent_observation")
                          if coherent_observation else
                          (FeedbackStatus.UNCERTAIN, "observation_incomplete"))
    elif verified_effect or (isinstance(result, Mapping)
                             and result.get("verified") is True
                             and result.get("status") == "success"):
        status, reason = FeedbackStatus.SUCCESS, "tool_result_verified"
    elif source == "user":
        status, reason = FeedbackStatus.SUCCESS, "user_message_recorded"
    else:
        status, reason = FeedbackStatus.UNCERTAIN, "tool_completion_without_effect_proof"

    tool_call_id = action_id or uuid.uuid4().hex
    feedback_id = uuid.uuid4().hex
    evidence: Evidence | None = None
    # Raw incomplete/failed result is not accepted as evidence of a successful
    # effect, but may contain safe observed fact for downstream inspection.
    if isinstance(result, Mapping) and bool(result) and state not in ("pending", "queued"):
        content = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",",":"))
        evidence = Evidence(
            evidence_id=uuid.uuid4().hex,
            task_id=task_id, step_id=step_id, source=source,
            observed_at=now, tool_call_id=tool_call_id,
            target_id=(target_id or None),
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            sanitized_payload=safe,
            provenance={
                "tool_name":tool_name, "action_state":state,
                "untrusted":source in ("browser", "tool", "worker", "file"),
                "status":status.value, "reason_code":reason,
            },
            freshness_deadline=now+timedelta(milliseconds=freshness_ms),
        )
    event = FeedbackEvent(
        feedback_id=feedback_id,task_id=task_id,step_id=step_id,
        source=source,status=status,reason_code=reason,
        evidence_ids=[evidence.evidence_id] if evidence is not None else [],
        observed_at=now,
    )
    return event, evidence
