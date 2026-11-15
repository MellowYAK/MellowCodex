"""P09 durable, fail-closed action idempotency and reconciliation ledger.

Standalone adapter. No tool dispatch happens here, and it never supersedes
Guard or OwnerBroker approval. Effects marked dispatched/unknown must be
independently reconciled before any retry. Stores no raw args, target or secret.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from .contracts import ToolRisk, stable_action_key


class ActionConflict(RuntimeError):
    """Idempotency conflict, uncertain effect or stale transition."""


class IntentState(str, Enum):
    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    UNKNOWN = "unknown"
    APPLIED = "confirmed_applied"
    NOT_APPLIED = "confirmed_not_applied"


class RecoveryDecision(str, Enum):
    READY_TO_DISPATCH = "ready_to_dispatch"
    WAIT_APPROVAL = "wait_approval"
    WAIT_EFFECT_RECONCILIATION = "wait_effect_reconciliation"
    SKIP_DUPLICATE = "skip_duplicate"
    RETRY_SAFE = "retry_safe"
    REQUIRE_REAPPROVAL = "require_reapproval"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class ActionIntent:
    idempotency_key: str
    task_id: str
    first_step_id: str
    effect_name: str
    target_hash: str
    risk_level: ToolRisk
    state: IntentState
    revision: int
    attempts: int
    evidence_id: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActionLedger:
    """Serializes effect reservations and CAS transitions across workers.

    Call ensure_schema() explicitly. Construction or querying must not create
    tables. The active Hub Engine is NOT wired to this module yet.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self._transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_action_intents(
                    idempotency_key TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    first_step_id TEXT NOT NULL,
                    effect_name TEXT NOT NULL,
                    target_hash TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    state TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    attempts INTEGER NOT NULL,
                    evidence_id TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS agent_action_intents_task
                ON agent_action_intents(task_id)
            """)

    @staticmethod
    def _convert(row: sqlite3.Row) -> ActionIntent:
        return ActionIntent(
            idempotency_key=row["idempotency_key"],
            task_id=row["task_id"],
            first_step_id=row["first_step_id"],
            effect_name=row["effect_name"],
            target_hash=row["target_hash"],
            risk_level=ToolRisk(row["risk_level"]),
            state=IntentState(row["state"]),
            revision=row["revision"],
            attempts=row["attempts"],
            evidence_id=row["evidence_id"],
        )

    def get(self, key: str) -> ActionIntent | None:
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise ValueError("Invalid action key")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_action_intents WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        return self._convert(row) if row else None

    def reserve(
        self,
        *,
        task_id: str,
        step_id: str,
        effect_name: str,
        target: str,
        arguments: dict[str, Any],
        risk_level: ToolRisk,
    ) -> tuple[ActionIntent, bool]:
        if not step_id or not isinstance(risk_level, ToolRisk):
            raise ValueError("Missing step or invalid risk")
        key = stable_action_key(task_id, effect_name, target, arguments)
        target_hash = hashlib.sha256(target.encode("utf-8")).hexdigest()
        with self._transaction() as conn:
            previous = conn.execute(
                "SELECT * FROM agent_action_intents WHERE idempotency_key=?",
                (key,),
            ).fetchone()
            if previous:
                entry = self._convert(previous)
                if (entry.task_id != task_id or entry.effect_name != effect_name
                    or entry.target_hash != target_hash
                    or entry.risk_level != risk_level):
                    raise ActionConflict("Existing action key refers to another effect")
                # The first step ID stays as historical provenance. Replans
                # can have new step IDs but MUST share the same effect key.
                return entry, False
            conn.execute("""
                INSERT INTO agent_action_intents
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                key,task_id,step_id,effect_name,target_hash,risk_level.value,
                IntentState.RESERVED.value,1,0,None,_now(),
            ))
            row = conn.execute(
                "SELECT * FROM agent_action_intents WHERE idempotency_key=?",
                (key,),
            ).fetchone()
            return self._convert(row), True

    def _change(self, conn: sqlite3.Connection, entry: ActionIntent,
                new_state: IntentState, *, attempts: int | None = None,
                evidence_id: str | None = None) -> ActionIntent:
        result = conn.execute("""
            UPDATE agent_action_intents
            SET state=?,revision=?,attempts=?,evidence_id=?,updated_at=?
            WHERE idempotency_key=? AND revision=? AND state=?
        """, (
            new_state.value,entry.revision+1,
            entry.attempts if attempts is None else attempts,
            evidence_id,_now(),entry.idempotency_key,entry.revision,entry.state.value,
        ))
        if result.rowcount != 1:
            raise ActionConflict("Stale action reservation or concurrent writer")
        row = conn.execute(
            "SELECT * FROM agent_action_intents WHERE idempotency_key=?",
            (entry.idempotency_key,),
        ).fetchone()
        return self._convert(row)

    def _require(self, conn: sqlite3.Connection, key: str,
                 expected_revision: int) -> ActionIntent:
        row = conn.execute(
            "SELECT * FROM agent_action_intents WHERE idempotency_key=?",
            (key,),
        ).fetchone()
        if not row:
            raise ActionConflict("No action reservation")
        entry = self._convert(row)
        if entry.revision != expected_revision:
            raise ActionConflict("Stale action revision")
        return entry

    def begin_dispatch(self, key: str, *, expected_revision: int,
                       approved: bool = False, max_attempts: int = 3) -> ActionIntent:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        with self._transaction() as conn:
            e = self._require(conn,key,expected_revision)
            if e.state != IntentState.RESERVED:
                raise ActionConflict("Action already dispatched or reconciled")
            if e.attempts >= max_attempts:
                raise ActionConflict("Dispatch retry budget exhausted")
            if e.risk_level in (ToolRisk.EXTERNAL_EFFECT,ToolRisk.HIGH_RISK) and not approved:
                raise ActionConflict("Current external approval required")
            return self._change(conn,e,IntentState.DISPATCHED,attempts=e.attempts+1)

    def mark_unknown(self, key: str, *, expected_revision: int) -> ActionIntent:
        with self._transaction() as conn:
            e = self._require(conn,key,expected_revision)
            if e.state == IntentState.UNKNOWN:
                return e
            if e.state != IntentState.DISPATCHED:
                raise ActionConflict("Only a dispatched action can be marked unknown")
            return self._change(conn,e,IntentState.UNKNOWN)

    def reconcile(self, key: str, *, expected_revision: int,
                  effect: str, evidence_id: str) -> ActionIntent:
        """Requires independently verified outcome; does not execute or retry."""
        if effect not in ("applied","not_applied") or not evidence_id.strip():
            raise ValueError("Reconciliation needs a specific verified effect and evidence ID")
        target = IntentState.APPLIED if effect=="applied" else IntentState.NOT_APPLIED
        with self._transaction() as conn:
            e = self._require(conn,key,expected_revision)
            if e.state == target and e.evidence_id == evidence_id:
                return e
            if e.state not in (IntentState.UNKNOWN,IntentState.DISPATCHED):
                raise ActionConflict("Effect cannot be reconciled from this state")
            return self._change(conn,e,target,evidence_id=evidence_id)

    @staticmethod
    def recommend(entry: ActionIntent, *, max_attempts: int = 3) -> RecoveryDecision:
        if entry.state == IntentState.APPLIED:
            return RecoveryDecision.SKIP_DUPLICATE
        if entry.state in (IntentState.DISPATCHED,IntentState.UNKNOWN):
            return RecoveryDecision.WAIT_EFFECT_RECONCILIATION
        if entry.attempts >= max_attempts:
            return RecoveryDecision.EXHAUSTED
        if entry.risk_level in (ToolRisk.EXTERNAL_EFFECT,ToolRisk.HIGH_RISK):
            return (RecoveryDecision.REQUIRE_REAPPROVAL
                    if entry.state==IntentState.NOT_APPLIED
                    else RecoveryDecision.WAIT_APPROVAL)
        if entry.state == IntentState.NOT_APPLIED:
            return RecoveryDecision.RETRY_SAFE
        return RecoveryDecision.READY_TO_DISPATCH

    def prepare_retry(self, key: str, *, expected_revision: int,
                      approved: bool=False, max_attempts: int=3) -> ActionIntent:
        with self._transaction() as conn:
            e = self._require(conn,key,expected_revision)
            if e.state != IntentState.NOT_APPLIED or not e.evidence_id:
                raise ActionConflict("Cannot retry before independently proven non-effect")
            if e.attempts >= max_attempts:
                raise ActionConflict("Retry attempt budget exhausted")
            if e.risk_level in (ToolRisk.EXTERNAL_EFFECT,ToolRisk.HIGH_RISK) and not approved:
                raise ActionConflict("Reapproval required for an external retry")
            return self._change(conn,e,IntentState.RESERVED)

    def for_task(self, task_id: str) -> list[ActionIntent]:
        with self._connect() as conn:
            rows=conn.execute("""
                SELECT * FROM agent_action_intents WHERE task_id=?
                ORDER BY updated_at,idempotency_key
            """,(task_id,)).fetchall()
        return [self._convert(row) for row in rows]
