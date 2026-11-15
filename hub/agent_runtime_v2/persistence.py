"""Additive SQLite storage for Agent Runtime V2 plan, evidence and checkpoints.

Not wired to the existing Hub Store until explicit shadow-mode migration.
Instantiation does not create tables or touch the active user database.
Every write runs under BEGIN IMMEDIATE with revision checks.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any, Iterator

from .contracts import Evidence, TaskPlan


class PlanRevisionConflict(RuntimeError):
    """Concurrent or stale plan/checkpoint update."""


class EvidenceConflict(RuntimeError):
    """An existing evidence/event identifier was reused with different content."""


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",",":"))


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanRepository:
    """Dedicated additive tables; never modifies legacy messages/tasks/actions/events."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise
        finally:
            connection.close()

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        """Explicit opt-in: schema v1 only adds agent_* objects."""
        with self._tx() as c:
            # Execute each DDL inside the same BEGIN IMMEDIATE transaction.
            # sqlite3.executescript() implicitly commits and breaks rollback.
            schema_sql = """
                CREATE TABLE IF NOT EXISTS agent_schema_migrations (
                    version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_plan_heads (
                    task_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_plans (
                    task_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    revision INTEGER NOT NULL,
                    document TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, version)
                );
                CREATE TABLE IF NOT EXISTS agent_plan_steps (
                    task_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    step_id TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY(task_id, version, step_id)
                );
                CREATE TABLE IF NOT EXISTS agent_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    document TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS agent_evidence_task_step
                    ON agent_evidence(task_id, step_id, observed_at);
                CREATE TABLE IF NOT EXISTS agent_runtime_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    task_id TEXT NOT NULL,
                    plan_version INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    document TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS agent_runtime_events_task
                    ON agent_runtime_events(task_id, seq);
                CREATE TABLE IF NOT EXISTS agent_checkpoints (
                    task_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    plan_version INTEGER NOT NULL,
                    document TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
            """
            for statement in schema_sql.split(";"):
                if statement.strip():
                    c.execute(statement)
            c.execute("INSERT OR IGNORE INTO agent_schema_migrations VALUES (?,?)",
                      (1, _utc()))

    def write_plan(self, plan: TaskPlan, expected_revision: int | None = None) -> int:
        with self._tx() as c:
            row = c.execute("SELECT version,revision FROM agent_plan_heads WHERE task_id=?",
                            (plan.task_id,)).fetchone()
            if row is None:
                if expected_revision not in (None, 0) or plan.version != 1:
                    raise PlanRevisionConflict("New task must start with plan v1 and expected revision 0")
                revision = 1
                c.execute("INSERT INTO agent_plan_heads VALUES (?,?,?)",
                          (plan.task_id, plan.version, revision))
                kind = "plan.created"
            else:
                if expected_revision is None or expected_revision != row["revision"]:
                    raise PlanRevisionConflict("Stale or missing expected plan revision")
                if plan.version != row["version"] + 1:
                    raise PlanRevisionConflict("New plan version must advance by exactly one")
                revision = row["revision"] + 1
                c.execute("UPDATE agent_plan_heads SET version=?,revision=? WHERE task_id=? AND revision=?",
                          (plan.version, revision, plan.task_id, expected_revision))
                if c.execute("SELECT changes()").fetchone()[0] != 1:
                    raise PlanRevisionConflict("Concurrent plan write")
                kind = "plan.revised"
            c.execute("INSERT INTO agent_plans VALUES (?,?,?,?,?)",
                      (plan.task_id, plan.version, revision, _json(plan), _utc()))
            for step in plan.steps:
                c.execute("INSERT INTO agent_plan_steps VALUES (?,?,?,?)",
                          (plan.task_id, plan.version, step.id, _json(step)))
            c.execute("INSERT INTO agent_runtime_events (event_id,task_id,plan_version,kind,document,observed_at) VALUES (?,?,?,?,?,?)",
                      (uuid.uuid4().hex, plan.task_id, plan.version, kind,
                       _json({"plan_version":plan.version,"revision":revision}), _utc()))
            return revision

    def read_current(self, task_id: str) -> tuple[TaskPlan, int] | None:
        with self._read() as c:
            r = c.execute("""
                SELECT p.document, h.revision FROM agent_plan_heads h
                JOIN agent_plans p ON p.task_id=h.task_id AND p.version=h.version
                WHERE h.task_id=?
            """, (task_id,)).fetchone()
        return (TaskPlan.model_validate_json(r["document"]), r["revision"]) if r else None

    def read_version(self, task_id: str, version: int) -> TaskPlan | None:
        with self._read() as c:
            r = c.execute("SELECT document FROM agent_plans WHERE task_id=? AND version=?",
                          (task_id, version)).fetchone()
        return TaskPlan.model_validate_json(r["document"]) if r else None

    def add_evidence(self, evidence: Evidence) -> bool:
        document = _json(evidence)
        with self._tx() as c:
            valid = c.execute("SELECT 1 FROM agent_plan_steps WHERE task_id=? AND step_id=? LIMIT 1",
                              (evidence.task_id, evidence.step_id)).fetchone()
            if not valid:
                raise ValueError("Evidence refers to unknown plan step")
            previous = c.execute("SELECT document FROM agent_evidence WHERE evidence_id=?",
                                 (evidence.evidence_id,)).fetchone()
            if previous:
                if previous["document"] != document:
                    raise EvidenceConflict("Evidence ID reused for different payload")
                return False
            c.execute("INSERT INTO agent_evidence VALUES (?,?,?,?,?)",
                      (evidence.evidence_id, evidence.task_id, evidence.step_id,
                       document, evidence.observed_at.isoformat()))
            return True

    def evidence_for_step(self, task_id: str, step_id: str) -> list[Evidence]:
        with self._read() as c:
            rows = c.execute("""
                SELECT document FROM agent_evidence WHERE task_id=? AND step_id=?
                ORDER BY observed_at,evidence_id
            """, (task_id, step_id)).fetchall()
        return [Evidence.model_validate_json(r["document"]) for r in rows]

    def append_event(self, event_id: str, task_id: str, version: int,
                     kind: str, payload: dict[str, Any]) -> int:
        if not event_id or not task_id or not kind or version < 1:
            raise ValueError("Invalid event identity")
        body = _json(payload)
        with self._tx() as c:
            previous = c.execute("SELECT * FROM agent_runtime_events WHERE event_id=?",
                                 (event_id,)).fetchone()
            if previous:
                if (previous["task_id"], previous["plan_version"], previous["kind"],
                    previous["document"]) != (task_id, version, kind, body):
                    raise EvidenceConflict("Event ID reused with different content")
                return previous["seq"]
            cur = c.execute("""
                INSERT INTO agent_runtime_events(event_id,task_id,plan_version,kind,document,observed_at)
                VALUES (?,?,?,?,?,?)
            """, (event_id, task_id, version, kind, body, _utc()))
            return cur.lastrowid

    def events(self, task_id: str) -> list[dict[str, Any]]:
        with self._read() as c:
            rows = c.execute("SELECT seq,event_id,plan_version,kind,document,observed_at FROM agent_runtime_events WHERE task_id=? ORDER BY seq",
                             (task_id,)).fetchall()
        return [dict(seq=r["seq"],event_id=r["event_id"],plan_version=r["plan_version"],
                     kind=r["kind"],payload=json.loads(r["document"]),at=r["observed_at"])
                for r in rows]

    def save_checkpoint(self, task_id: str, plan_version: int,
                        state: dict[str, Any], expected_revision: int | None = None) -> int:
        body = _json(state)
        with self._tx() as c:
            head = c.execute("SELECT version FROM agent_plan_heads WHERE task_id=?",
                             (task_id,)).fetchone()
            if not head or head["version"] != plan_version:
                raise PlanRevisionConflict("Checkpoint must target current plan version")
            old = c.execute("SELECT revision FROM agent_checkpoints WHERE task_id=?",
                            (task_id,)).fetchone()
            if old is None:
                if expected_revision not in (None, 0):
                    raise PlanRevisionConflict("First checkpoint expected revision must be 0")
                revision = 1
                c.execute("INSERT INTO agent_checkpoints VALUES (?,?,?,?,?)",
                          (task_id, revision, plan_version, body, _utc()))
            else:
                if expected_revision is None or old["revision"] != expected_revision:
                    raise PlanRevisionConflict("Stale or absent checkpoint revision")
                revision = old["revision"] + 1
                c.execute("UPDATE agent_checkpoints SET revision=?,plan_version=?,document=?,observed_at=? WHERE task_id=? AND revision=?",
                          (revision, plan_version, body, _utc(), task_id, expected_revision))
                if c.execute("SELECT changes()").fetchone()[0] != 1:
                    raise PlanRevisionConflict("Concurrent checkpoint update")
            return revision

    def read_checkpoint(self, task_id: str) -> tuple[int, int, dict[str, Any]] | None:
        with self._read() as c:
            row = c.execute("SELECT revision,plan_version,document FROM agent_checkpoints WHERE task_id=?",
                            (task_id,)).fetchone()
        return (row["revision"], row["plan_version"], json.loads(row["document"])) if row else None
