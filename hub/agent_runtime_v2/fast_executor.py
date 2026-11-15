"""P12: deterministic, no-model fast path for *verified read-only navigation*.

Uses the existing embedded Browser.observe/act primitives rather than replacing
Qt/Playwright/Guard. A recipe must match a unique fresh observed href and
known destination host/path. Only one click is ever dispatched per step.
Unknown result => stop for observation/replanning, NEVER automatic retry.
This component does not claim the user's task is completed; P07 must verify
the original acceptance criteria from independently sourced evidence.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlsplit
import re

from .verifier import _form_visible

_UNSAFE = frozenset((
    "delete","remove","pay","purchase","buy","checkout","submit","send",
    "publish","transfer","approve","confirm","disconnect","unsubscribe",
    "logout","signout","reset","disable","cancel","close-account",
))
_NAME = re.compile(r"\s+")


@dataclass(frozen=True)
class KnownNavigation:
    """Explicitly trusted recipe: no form fill, credential entry or mutation."""
    target_name: str
    source_host: str
    destination_host: str
    destination_path: str
    post_condition: str = "page"  # page or login_form


@dataclass(frozen=True)
class FastExecution:
    chain_verified: bool
    goal_verified: bool  # intentionally always False until P07 final gate
    reason_code: str
    verified_steps: int
    dispatches: int
    observations: int
    model_calls: int
    elapsed_ms: float


class ObservedBrowser(Protocol):
    async def observe(self, folder: Any, query: str = "") -> dict[str, Any]: ...
    async def act(self, args: dict[str, Any], folder: Any) -> dict[str, Any]: ...


def _host(url: str, required: str) -> bool:
    try:
        parsed=urlsplit(url)
        if parsed.scheme not in ("http","https") or parsed.username or parsed.password:
            return False
        host=(parsed.hostname or "").lower().rstrip(".")
        required=required.lower().rstrip(".")
        return bool(host and required and (host==required or host.endswith("."+required)))
    except ValueError:
        return False


def _safe_navigation(href: str, step: KnownNavigation) -> bool:
    try:
        parsed=urlsplit(href)
        target_path=parsed.path or "/"
        if parsed.scheme not in ("http","https") or parsed.username or parsed.password:
            return False
        if parsed.query or parsed.fragment:
            return False  # do not replay opaque OAuth/session/action URLs
        if not _host(href,step.destination_host):
            return False
        if target_path != step.destination_path:
            return False
        segments={p.lower() for p in target_path.split("/") if p}
        if segments & _UNSAFE:
            return False
        return True
    except ValueError:
        return False


def _matching_ref(observation: Mapping[str, Any],
                  step: KnownNavigation) -> str | None:
    if observation.get("coherent") is not True or not observation.get("id"):
        return None
    if not _host(str(observation.get("url","")),step.source_host):
        return None
    elements=observation.get("elements")
    if not isinstance(elements,list):
        return None
    expected=_NAME.sub(" ",step.target_name.strip()).casefold()
    matches=[]
    for element in elements:
        if not isinstance(element,Mapping):
            continue
        if element.get("visible") is False or element.get("enabled") is not True:
            continue
        if str(element.get("tag","")).lower()!="a":
            continue
        name=_NAME.sub(" ",str(element.get("name","")).strip()).casefold()
        if name != expected:
            continue
        href=element.get("href")
        if not isinstance(href,str) or not _safe_navigation(href,step):
            continue
        ref=element.get("ref")
        if isinstance(ref,str) and ref:
            matches.append(ref)
    return matches[0] if len(matches)==1 else None


def _post_verified(observation: Any, step: KnownNavigation) -> bool:
    if not isinstance(observation,Mapping) or observation.get("coherent") is not True:
        return False
    if not observation.get("id") or not _host(str(observation.get("url","")),
                                               step.destination_host):
        return False
    try:
        parsed=urlsplit(str(observation["url"]))
    except ValueError:
        return False
    if parsed.path != step.destination_path:
        return False
    if step.post_condition=="login_form":
        return _form_visible(observation)
    return step.post_condition=="page"


class DeterministicBrowserRunner:
    """Small no-LLM observe => unique known link => one click => verify loop."""

    def __init__(self, browser: ObservedBrowser, *, timeout_seconds: float = 12,
                 max_steps: int = 12):
        if timeout_seconds<=0 or timeout_seconds>60 or not 1<=max_steps<=30:
            raise ValueError("Invalid deterministic browser safety limits")
        self.browser=browser
        self.timeout_seconds=timeout_seconds
        self.max_steps=max_steps

    async def execute(self, recipe: Sequence[KnownNavigation], folder: Any,
                      *, budget_ms: float = 20000) -> FastExecution:
        if not recipe or len(recipe)>self.max_steps:
            raise ValueError("No recipe or too many steps")
        if budget_ms<=0 or budget_ms>180000:
            raise ValueError("Invalid execution budget")
        for item in recipe:
            if (not isinstance(item,KnownNavigation) or not item.target_name.strip()
                or not item.source_host or not item.destination_host
                or not item.destination_path.startswith("/")
                or item.post_condition not in ("page","login_form")
                or any(part in _UNSAFE for part in item.destination_path.lower().split("/"))):
                raise ValueError("Unsafe or malformed navigation recipe")
        started=perf_counter_ns()
        dispatches=0
        observations=0
        verified=0
        current:dict[str,Any]|None=None

        def result(ok: bool,reason: str) -> FastExecution:
            return FastExecution(
                chain_verified=ok, goal_verified=False,reason_code=reason,
                verified_steps=verified,dispatches=dispatches,
                observations=observations,model_calls=0,
                elapsed_ms=round((perf_counter_ns()-started)/1e6,3),
            )

        for step in recipe:
            if (perf_counter_ns()-started)/1e6>budget_ms:
                return result(False,"budget_exceeded_without_retry")
            if current is None:
                observations+=1
                try:
                    current=await asyncio.wait_for(
                        self.browser.observe(folder,query=step.target_name),
                        self.timeout_seconds)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    return result(False,"observe_failed_needs_agent")
            ref=_matching_ref(current,step)
            if ref is None:
                return result(False,"no_unique_fresh_control")
            payload={"action":"click","observation_id":current["id"],"ref":ref}
            dispatches+=1
            try:
                outcome=await asyncio.wait_for(
                    self.browser.act(payload,folder),self.timeout_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                # A timeout/cancelled Chromium input may have taken effect.
                # It is always unsafe to issue the same click again blindly.
                return result(False,"action_unknown_effect_no_retry")
            if not isinstance(outcome,Mapping) or outcome.get("input_sent") is not True:
                return result(False,"action_not_confirmed_no_retry")
            current=outcome.get("after")
            observations+=1 if isinstance(current,Mapping) else 0
            if not _post_verified(current,step):
                return result(False,"post_action_evidence_missing")
            verified+=1
        return result(True,"all_known_navigation_steps_verified")
