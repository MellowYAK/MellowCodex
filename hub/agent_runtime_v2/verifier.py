"""P07 authoritative *shadow* verifier for versioned plans and fresh evidence.

A page opening, model declaration, tool dispatch, or legacy task.state=done
is not final task success. Only matching evidence for required acceptance
criteria produces a positive result. This is an additive module; active
legacy Engine remains untouched until guarded P08 integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit
import re

from .contracts import AcceptanceCriterion, Evidence, PlanStep, TaskPlan

_LOGIN = re.compile(
    r"(?i)(login|log.?in|sign.?in|account|connexion|כניסה|התחבר|התחברות|войти|вход)"
)
_EMAIL = re.compile(
    r"(?i)(email|e-mail|username|user name|טלפון|טלפונ|אימייל|נייד|courriel|téléphone|почта)"
)
_PASSWORD = re.compile(r"(?i)(password|passwd|סיסמה|пароль|mot de passe)")


@dataclass(frozen=True)
class CriterionDecision:
    criterion_id: str
    passed: bool
    evidence_ids: tuple[str, ...] = ()
    reason_code: str = "evidence_missing"


@dataclass(frozen=True)
class VerificationReport:
    task_id: str
    plan_version: int
    completed: bool
    steps: tuple[tuple[str, bool], ...]
    final: tuple[CriterionDecision, ...]
    missing_criteria: tuple[str, ...]


def _host_matches(url: object, required: str) -> bool:
    try:
        parsed = urlsplit(str(url or ""))
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return False
    required = required.casefold().rstrip(".")
    return bool(host and required and (host == required or host.endswith("." + required)))


def _page(evidence: Evidence) -> Mapping[str, Any] | None:
    p=evidence.sanitized_payload
    if evidence.source != "browser":
        return None
    if evidence.provenance.get("status") != "SUCCESS":
        return None
    if evidence.provenance.get("tool_name") not in (
        "browser_observe", "browser_frame", "browser_act", "browser_navigate"
    ):
        return None
    if evidence.provenance.get("tool_name") == "browser_act":
        p=p.get("after") if isinstance(p.get("after"), Mapping) else {}
    if p.get("coherent") is not True or not (p.get("url") or p.get("title")):
        return None
    return p


def _form_visible(page: Mapping[str, Any]) -> bool:
    controls=page.get("elements", page.get("controls", []))
    if not isinstance(controls,list):
        return False
    email=False
    for item in controls:
        if not isinstance(item,Mapping):
            continue
        if item.get("visible") is False or item.get("enabled") is False:
            continue
        label=" ".join(str(item.get(k,"")) for k in
                       ("name","type","placeholder","aria_label","autocomplete")).casefold()
        tag=str(item.get("tag","")).casefold()
        if not (tag in ("input","textbox","") or item.get("role") in ("textbox","input")):
            continue
        if _PASSWORD.search(label):
            return True
        if _EMAIL.search(label):
            email=True
    context=str(page.get("url",""))+" "+str(page.get("title",""))
    return email and bool(_LOGIN.search(context))


def _has_login_entry(page: Mapping[str, Any]) -> bool:
    for item in page.get("elements",[]) if isinstance(page.get("elements"),list) else []:
        if not isinstance(item,Mapping) or item.get("visible") is False:
            continue
        if _LOGIN.search(str(item.get("name",""))+" "+str(item.get("aria_label",""))):
            return True
    return False


def _eligible(plan:TaskPlan, step_id:str, evidence:Iterable[Evidence],
              criterion:AcceptanceCriterion,now:datetime) -> list[Evidence]:
    out=[]
    for e in evidence:
        if e.task_id!=plan.task_id or e.step_id!=step_id:
            continue
        # No legacy unversioned or superseded evidence may be promoted into
        # completion of a new plan revision.
        if e.provenance.get("plan_version")!=plan.version:
            continue
        if e.provenance.get("status")!="SUCCESS":
            continue
        if not e.is_fresh(now,criterion.evidence_freshness_ms):
            continue
        out.append(e)
    return out


def _assessment_matches(page_ev:Evidence, assessments:list[Evidence]) -> Evidence|None:
    for e in assessments:
        if e.source!="browser" or e.provenance.get("tool_name")!="browser_assess":
            continue
        a=e.sanitized_payload
        if a.get("verified") is not True or a.get("status")!="success":
            continue
        if e.observed_at<page_ev.observed_at:
            continue
        if e.target_id and page_ev.target_id and e.target_id!=page_ev.target_id:
            continue
        return e
    return None


def _criterion(plan:TaskPlan, step_id:str, criterion:AcceptanceCriterion,
               evidence:list[Evidence],now:datetime)->CriterionDecision:
    entries=_eligible(plan,step_id,evidence,criterion,now)
    expect=criterion.expected
    required_host=str(expect.get("required_host","") or "")
    # Read-only browser URL observations.
    if criterion.verifier_type=="url" and expect.get("observed_page"):
        for e in entries:
            p=_page(e)
            if p and (not required_host or _host_matches(p.get("url"),required_host)):
                return CriterionDecision(criterion.id,True,(e.evidence_id,),"observed_page")
    if criterion.verifier_type=="dom":
        if expect.get("observed_control"):
            for e in entries:
                p=_page(e)
                if p and (not required_host or _host_matches(p.get("url"),required_host)) and _has_login_entry(p):
                    return CriterionDecision(criterion.id,True,(e.evidence_id,),"observed_login_entry")
        if expect.get("login_form"):
            pages=[e for e in entries if (p:=_page(e))
                   and (not required_host or _host_matches(p.get("url"),required_host))
                   and _form_visible(p)]
            for e in pages:
                if not expect.get("verified_assessment"):
                    return CriterionDecision(criterion.id,True,(e.evidence_id,),"observed_real_login_form")
                assessor=_assessment_matches(e,entries)
                if assessor:
                    return CriterionDecision(criterion.id,True,
                                             (e.evidence_id,assessor.evidence_id),
                                             "login_form_with_assessment")
    if criterion.verifier_type=="structured_output":
        if expect.get("input_sent") and expect.get("post_action_observed"):
            for e in entries:
                p=e.sanitized_payload
                if e.source!="browser" or e.provenance.get("tool_name") not in ("browser_act","browser_pointer"):
                    continue
                if p.get("input_sent") is not True:
                    continue
                after=p.get("after")
                if not isinstance(after,Mapping) or after.get("coherent") is not True:
                    continue
                if required_host and not _host_matches(after.get("url"),required_host):
                    continue
                return CriterionDecision(criterion.id,True,(e.evidence_id,),"input_effect_observed")
        # These are V2 reviewer attestations, NEVER legacy task.state=done,
        # worker text, or model-only "verified" assertions. Producer must be
        # permitted deterministic runtime verifier, not untrusted webpage.
        criteria_fields=("source_observed","route_or_evidence_identified",
                         "tool_effect_verified","final_goal_verified")
        requested=[field for field in criteria_fields if expect.get(field) is True]
        for e in entries:
            if e.source in ("worker","user","browser"):
                continue
            if e.provenance.get("verified_by")!="deterministic":
                continue
            if all(e.sanitized_payload.get(field) is True for field in requested):
                if expect.get("terminal_task_state") and e.sanitized_payload.get("terminal_task_state")!=expect["terminal_task_state"]:
                    continue
                return CriterionDecision(criterion.id,True,(e.evidence_id,),"trusted_structured_effect")
    # Other domain verifiers require an independent trusted tool assertion.
    if criterion.verifier_type in ("file","process","custom","visual"):
        for e in entries:
            if e.provenance.get("verified_by")!="deterministic" or e.source in ("worker","user"):
                continue
            if e.sanitized_payload.get("criterion_id") != criterion.id:
                continue
            if e.sanitized_payload.get("verified") is True:
                return CriterionDecision(criterion.id,True,(e.evidence_id,),"trusted_domain_verifier")
    if criterion.verifier_type=="user_confirmation":
        for e in entries:
            if e.source=="user" and e.provenance.get("confirmed_criterion_id")==criterion.id:
                return CriterionDecision(criterion.id,True,(e.evidence_id,),"explicit_user_confirmation")
    return CriterionDecision(criterion.id,False,(),"required_evidence_missing")


def verify_plan(plan:TaskPlan, evidence:Iterable[Evidence], *,
                at:datetime|None=None) -> VerificationReport:
    """Pure final gate: no side effects, no inferred task success."""
    now=at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Verification time must be timezone-aware")
    items=list(evidence)
    decisions:dict[str,list[CriterionDecision]]={}
    step_state:dict[str,bool]={}
    missing=[]
    for step in plan.steps:
        checks=[_criterion(plan,step.id,c,items,now) for c in step.acceptance if c.required]
        checks_pass=bool(checks) and all(c.passed for c in checks)
        deps_pass=all(step_state.get(dep,False) for dep in step.dependencies)
        step_state[step.id]=checks_pass and deps_pass
        for c in checks:
            if not c.passed:
                missing.append(step.id+":"+c.criterion_id)
        if checks_pass and not deps_pass:
            missing.append(step.id+":dependency")
        decisions[step.id]=checks
    final_id=plan.steps[-1].id
    finals=tuple(_criterion(plan,final_id,c,items,now)
                 for c in plan.completion_criteria if c.required)
    for c in finals:
        if not c.passed:
            missing.append("final:"+c.criterion_id)
    completed=(all(step_state.values()) and len(step_state)==len(plan.steps)
               and bool(finals) and all(c.passed for c in finals))
    return VerificationReport(plan.task_id,plan.version,completed,
                              tuple(step_state.items()),finals,tuple(missing))
