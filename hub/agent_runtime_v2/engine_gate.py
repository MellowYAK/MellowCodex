"""Opt-in original browser-goal completion gate for the real Engine.

This is a deterministic read-only predicate. A model saying "done", a page
opening, or an input dispatch cannot prove a different requested destination.
The existing guarded login path remains active even when V2 is disabled.
"""
from __future__ import annotations

import re
import time
from typing import Any, Mapping
from urllib.parse import urlsplit

from ..browser_goal_board import progress


_SIMPLE_HOMEPAGE = re.compile(
    r"(?i)\b(?:open|visit|show)\b.*\b(?:homepage|home page|website|site)\b"
)


def _host_matches(url: object, requested: object) -> bool:
    host = str(requested or "").casefold().rstrip(".")
    if not host:
        return False
    try:
        parts = urlsplit(str(url or ""))
        if parts.scheme not in ("http", "https"):
            return False
        actual = (parts.hostname or "").casefold().rstrip(".")
        return actual == host or actual.endswith("." + host)
    except ValueError:
        return False


def _last_page(actions: list[dict[str, Any]]) -> Mapping[str, Any] | None:
    for action in reversed(actions):
        if action.get("state") != "complete":
            continue
        result = action.get("result")
        if not isinstance(result, dict):
            continue
        for page in (result.get("after"), result):
            if (isinstance(page, dict) and page.get("coherent") is True
                    and page.get("url")):
                return page
    return None


def browser_goal_complete(
    board: Mapping[str, Any] | None,
    actions: list[dict[str, Any]],
    *,
    strict: bool = False,
    now: float | None = None,
) -> bool:
    """Accept only a grounded original-goal result.

    Legacy login still uses the existing hard gate. Strict mode is opt-in for
    other browser intents while the integration rollout is verified.
    """
    if board is None:
        return not strict
    if board.get("task_mode", "browser") != "browser":
        return False
    if board.get("intent") == "login":
        return bool(progress(board, actions).get("done"))
    if not strict:
        return True

    if any(a.get("state") in ("pending", "queued") for a in actions):
        return False

    goal = str(board.get("goal", ""))
    host = str(board.get("target_host", ""))
    page = _last_page(actions)
    if not page or not _host_matches(page.get("url"), host):
        return False

    # Known read-only homepage goals can be proven from a coherent observed
    # page. Search/find results need stronger outcome evidence than an opened
    # homepage, even if the task state was formerly marked "done".
    if (board.get("intent") == "general"
            and _SIMPLE_HOMEPAGE.search(goal)
            and not any(
                a.get("tool") in ("browser_act", "browser_pointer")
                and isinstance(a.get("result"), dict)
                and a["result"].get("input_sent") is True
                for a in actions
            )):
        return True

    # For all other intents a final assessment is needed, explicitly bound
    # to the *same original goal* and a recent verified browser result.
    now = time.time() if now is None else now
    for action in reversed(actions):
        if action.get("tool") != "browser_assess" or action.get("state") != "complete":
            continue
        result = action.get("result")
        if not isinstance(result, dict):
            return False
        checked_at = result.get("checked_at")
        if not isinstance(checked_at, (float, int)):
            return False
        if not 0 <= now - checked_at <= 120:
            return False
        if (result.get("verified") is True
                and result.get("status") == "success"
                and result.get("goal_verified") is True
                and result.get("original_goal") == goal):
            return True
        return False
    return False
