"""P11: bounded local trace and decision ledger for agent execution.

This is an additive, opt-in telemetry primitive, not a model reasoning log.
No raw prompts, private chain-of-thought, passwords, authorization headers,
page contents or user messages are persisted. Safe structured decision codes
and time budgets explain what happened without revealing model internals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from statistics import median
from time import perf_counter_ns
import uuid
from typing import Any, Mapping

from .feedback import sanitize


_ALLOWED_ATTRS = frozenset((
    "operation", "tool", "provider", "model", "route", "outcome",
    "risk", "status_code", "retry_count", "input_tokens", "output_tokens",
    "context_tokens", "budget_ms", "result_code", "hostname", "url",
))
_PHASE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,119}$")


@dataclass(frozen=True)
class SpanToken:
    span_id: str
    trace_id: str
    task_id: str
    plan_version: int
    phase: str
    parent_id: str | None
    started_at: str
    start_monotonic_ns: int


class TraceConflict(RuntimeError):
    """Trace ID collision, invalid phase, or duplicate incompatible result."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attrs(source: Mapping[str, Any] | None) -> str:
    values = {
        key: sanitize(value)
        for key, value in dict(source or {}).items()
        if key in _ALLOWED_ATTRS
    }
    return json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",",":"))


def _label(value: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError("Decision label must be a structured identifier")
    return value


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered)-1)*fraction
    lower=int(index)
    upper=min(len(ordered)-1,lower+1)
    return round(ordered[lower]+(ordered[upper]-ordered[lower])*(index-lower),3)


class TraceRecorder:
    """Local SQLite/OTel-compatible trace projection.

    Calls are explicit. Existing Hub database tables remain untouched.
    A span records after completion, and a crash before completion cannot
    be misreported as a finished action.
    """
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def ensure_schema(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS agent_trace_spans (
                    span_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    plan_version INTEGER NOT NULL,
                    parent_id TEXT,
                    phase TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    outcome TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    attrs TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS agent_trace_spans_task
                ON agent_trace_spans(task_id,started_at)
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS agent_trace_decisions (
                    decision_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    plan_version INTEGER NOT NULL,
                    reason_code TEXT NOT NULL,
                    selected TEXT NOT NULL,
                    alternatives TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL,
                    at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS agent_trace_decisions_task
                ON agent_trace_decisions(task_id,at)
            """)

    def start_span(self, task_id: str, phase: str, *,
                   plan_version: int = 1, trace_id: str | None = None,
                   parent_id: str | None = None) -> SpanToken:
        if not task_id or plan_version < 1 or not _PHASE.fullmatch(phase):
            raise ValueError("Invalid task/version/phase")
        if trace_id is not None and not trace_id.strip():
            raise ValueError("Invalid trace id")
        return SpanToken(
            uuid.uuid4().hex, trace_id or uuid.uuid4().hex, task_id,
            plan_version, phase, parent_id, _timestamp(), perf_counter_ns(),
        )

    def end_span(self, token: SpanToken, *, outcome: str,
                 reason_code: str, attributes: Mapping[str, Any] | None = None,
                 elapsed_ms: float | None = None) -> dict[str, Any]:
        if outcome not in ("success","failure","uncertain","cancelled"):
            raise ValueError("Invalid span outcome")
        _label(reason_code)
        duration = (max(0,(perf_counter_ns()-token.start_monotonic_ns)/1e6)
                    if elapsed_ms is None else float(elapsed_ms))
        if duration < 0 or duration > 86400000:
            raise ValueError("Invalid elapsed duration")
        document={
            "span_id":token.span_id,"trace_id":token.trace_id,
            "task_id":token.task_id,"plan_version":token.plan_version,
            "parent_id":token.parent_id,"phase":token.phase,
            "started_at":token.started_at,"ended_at":_timestamp(),
            "duration_ms":round(duration,3),"outcome":outcome,
            "reason_code":reason_code,"attributes":json.loads(_attrs(attributes)),
        }
        with self._connect() as db:
            previous=db.execute(
                "SELECT * FROM agent_trace_spans WHERE span_id=?",(token.span_id,)
            ).fetchone()
            if previous:
                if previous["outcome"]!=outcome or previous["reason_code"]!=reason_code:
                    raise TraceConflict("Incompatible repeated span completion")
                return self._decode_span(previous)
            db.execute("""
                INSERT INTO agent_trace_spans VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,(
                token.span_id,token.trace_id,token.task_id,token.plan_version,
                token.parent_id,token.phase,token.started_at,document["ended_at"],
                document["duration_ms"],outcome,reason_code,
                json.dumps(document["attributes"],sort_keys=True,ensure_ascii=False),
            ))
        return document

    @staticmethod
    def _decode_span(row: sqlite3.Row) -> dict[str, Any]:
        d=dict(row)
        d["attributes"]=json.loads(d.pop("attrs"))
        return d

    def record_decision(self, *, task_id: str, trace_id: str,
                        plan_version: int, reason_code: str,
                        selected: str, alternatives: list[str],
                        evidence_ids: list[str] | None = None,
                        decision_id: str | None = None) -> str:
        if not task_id or not trace_id or plan_version < 1:
            raise ValueError("Decision missing task/trace/version")
        for value in [reason_code,selected,*alternatives]:
            _label(value)
        if len(alternatives)>20 or len(evidence_ids or [])>30:
            raise ValueError("Decision references exceed bound")
        if any(not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}",e) for e in (evidence_ids or [])):
            raise ValueError("Invalid evidence identity")
        did=decision_id or uuid.uuid4().hex
        with self._connect() as db:
            old=db.execute("SELECT * FROM agent_trace_decisions WHERE decision_id=?",
                           (did,)).fetchone()
            if old:
                if (old["task_id"],old["trace_id"],old["plan_version"],
                    old["reason_code"],old["selected"],json.loads(old["alternatives"]),
                    json.loads(old["evidence_ids"])) != (
                    task_id,trace_id,plan_version,reason_code,selected,
                    alternatives,evidence_ids or [],
                ):
                    raise TraceConflict("Decision ID has incompatible content")
                return did
            db.execute("""
                INSERT INTO agent_trace_decisions VALUES(?,?,?,?,?,?,?,?,?)
            """,(
                did,trace_id,task_id,plan_version,reason_code,selected,
                json.dumps(alternatives),json.dumps(evidence_ids or []),_timestamp(),
            ))
        return did

    def spans(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows=db.execute("""
                SELECT * FROM agent_trace_spans WHERE task_id=?
                ORDER BY started_at,span_id
            """,(task_id,)).fetchall()
        return [self._decode_span(row) for row in rows]

    def decisions(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows=db.execute("""
                SELECT * FROM agent_trace_decisions WHERE task_id=?
                ORDER BY at,decision_id
            """,(task_id,)).fetchall()
        return [{
            **{k:r[k] for k in ("decision_id","trace_id","task_id",
                                 "plan_version","reason_code","selected","at")},
            "alternatives":json.loads(r["alternatives"]),
            "evidence_ids":json.loads(r["evidence_ids"]),
        } for r in rows]

    def latency_summary(self, task_id: str, *,
                        budgets_ms: Mapping[str, float] | None = None) -> dict[str, Any]:
        groups: dict[str,list[float]]={}
        for item in self.spans(task_id):
            groups.setdefault(item["phase"],[]).append(item["duration_ms"])
        return {
            phase:{
                "count":len(values),"p50_ms":_percentile(values,0.5),
                "p95_ms":_percentile(values,0.95),
                "max_ms":round(max(values),3),
                "budget_ms":(budgets_ms or {}).get(phase),
                "within_budget":(None if phase not in (budgets_ms or {})
                                 else _percentile(values,0.95)<=float(budgets_ms[phase])),
            }
            for phase,values in sorted(groups.items())
        }
