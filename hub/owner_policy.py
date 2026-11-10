"""Candidate only: shared per-operation owner policy. NOT INSTALLED.

This module is NOT an owner identity boundary. The actual owner broker must run under
a distinct protected Windows security principal and authenticate user presence.
Untrusted Hub, MCP, Guard, PLAY and extension processes cannot grant themselves
authority by instantiating these value objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
import hashlib
import json
import time
from typing import Mapping, Sequence


class Tier(str, Enum):
    SAFE = "safe"
    ASK = "ask"
    FULL = "full"


class Risk(IntEnum):
    PUBLIC_READ = 0
    PRIVATE_READ = 1
    REVERSIBLE_ACTION = 2
    DESTRUCTIVE = 3
    PROTECTED = 4
    UNKNOWN = 5


@dataclass(frozen=True)
class Override:
    tier: Tier
    revision: int
    expires_at: float | None = None


@dataclass(frozen=True)
class Snapshot:
    policy_revision: int = 0
    default: Tier = Tier.SAFE
    overrides: Mapping[str, Override] = field(default_factory=dict)
    broker_verified: bool = False
    broker_install_identity: str | None = None
    broker_key_id: str | None = None
    expires_at: float | None = None

    def effective(self, chat_id: str, now: float | None = None) -> tuple[Tier, str]:
        at = time.time() if now is None else now
        override = self.overrides.get(chat_id)
        if override and (override.expires_at is None or override.expires_at > at):
            tier = override.tier
            source = "chat"
        else:
            tier = self.default
            source = "global"
        if tier is Tier.FULL and (
            not self.broker_verified or not self.broker_install_identity
            or not self.broker_key_id or
            (self.expires_at is not None and self.expires_at <= at)
        ):
            return Tier.SAFE, "broker_unavailable"
        return tier, source


def digest_arguments(arguments: Mapping) -> str:
    canonical = json.dumps(arguments, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Operation:
    task_id: str
    task_revision: int
    chat_id: str
    action_id: str
    name: str
    arguments_hash: str
    target: str
    version_hash: str
    risk: Risk
    approved_descriptor: bool = False
    schema_hash: str = ""
    scope: str = ""
    may_elevate: bool = False

    @classmethod
    def from_action(cls, *, task_id: str, task_revision: int, chat_id: str,
                    action_id: str, name: str, args: Mapping, target: str,
                    version_hash: str, risk: Risk,
                    approved_descriptor: bool, schema_hash: str = "",
                    scope: str = "", may_elevate: bool = False):
        return cls(task_id, task_revision, chat_id, action_id, name,
                   digest_arguments(args), target, version_hash, risk,
                   approved_descriptor, schema_hash, scope, may_elevate)


@dataclass(frozen=True)
class Grant:
    """Untrusted representation until verified by protected OS broker."""
    grant_id: str
    task_id: str
    task_revision: int
    chat_id: str
    action_id: str
    name: str
    arguments_hash: str
    target: str
    version_hash: str
    schema_hash: str
    policy_revision: int
    expires_at: float
    scope: str
    broker_identity: str


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    tier: Tier
    source: str
    policy_revision: int
    requires_owner: bool = False


def enforce(snapshot: Snapshot, operation: Operation, *,
            allowed_tools: Sequence[str], verified_grant: Grant | None = None,
            grant_verified_by_protected_broker: bool = False,
            consumed_grants: frozenset[str] = frozenset(),
            now: float | None = None) -> Decision:
    """Fail-closed pure evaluator. Only an external protected broker verifies grants.

    This NEVER interprets a user-supplied Grant object as proof. The caller must
    independently authenticate the broker over an OS-protected channel.
    """
    tier, source = snapshot.effective(operation.chat_id, now)
    def result(allow: bool, code: str, owner: bool = False):
        return Decision(allow, code, tier, source, snapshot.policy_revision, owner)

    if operation.name not in allowed_tools:
        return result(False, "tool_scope_denied")
    if operation.risk is Risk.UNKNOWN or not operation.approved_descriptor:
        return result(False, "unreviewed_operation")
    if not operation.version_hash or not operation.arguments_hash or not operation.action_id:
        return result(False, "unbound_operation")
    if operation.may_elevate or operation.risk is Risk.PROTECTED:
        # Full is not a bypass for Windows UAC, OS account consent or Guard review.
        return result(False, "separate_os_authority_required", True)
    if tier is Tier.SAFE and operation.risk <= Risk.PRIVATE_READ:
        return result(True, "safe_read")
    if tier is Tier.FULL and operation.risk <= Risk.DESTRUCTIVE and snapshot.broker_verified:
        return result(True, "owner_full_scope")
    if tier is Tier.SAFE:
        return result(False, "owner_approval_required", True)

    if not grant_verified_by_protected_broker or verified_grant is None:
        return result(False, "owner_approval_required", True)
    grant = verified_grant
    if grant.grant_id in consumed_grants:
        return result(False, "approval_replayed", True)
    at = time.time() if now is None else now
    if grant.expires_at <= at:
        return result(False, "approval_expired", True)
    fields = (
        (grant.task_id, operation.task_id),
        (grant.task_revision, operation.task_revision),
        (grant.chat_id, operation.chat_id),
        (grant.action_id, operation.action_id),
        (grant.name, operation.name),
        (grant.arguments_hash, operation.arguments_hash),
        (grant.target, operation.target),
        (grant.version_hash, operation.version_hash),
        (grant.schema_hash, operation.schema_hash),
        (grant.scope, operation.scope),
        (grant.policy_revision, snapshot.policy_revision),
        (grant.broker_identity, snapshot.broker_install_identity),
    )
    if any(left != right for left, right in fields):
        return result(False, "approval_binding_mismatch", True)
    return result(True, "owner_action_approved")


def public_status(snapshot: Snapshot, chat_id: str) -> dict:
    tier, source = snapshot.effective(chat_id)
    override = snapshot.overrides.get(chat_id)
    return {"effective": tier.value, "source": source,
            "global_default": snapshot.default.value,
            "override": override.tier.value if override and (override.expires_at is None or override.expires_at > time.time()) else None,
            "override_expires_at": override.expires_at if override else None,
            "revision": snapshot.policy_revision,
            "owner_broker_verified": snapshot.broker_verified,
            "full_available": snapshot.broker_verified and bool(snapshot.broker_install_identity),
            "owner_write_via_mcp": False}


class BrokerNotInstalled(PermissionError):
    pass


class BrokerReadOnly:
    """Adapter intentionally without policy-write methods in untrusted Hub.

    An OS-protected broker may supply authenticated snapshots/one-use decisions.
    Until that service is installed and mutually authenticated, do NOT claim
    Windows owner approval, Full mode or Ask grants.
    """
    def snapshot(self) -> Snapshot:
        return Snapshot()

    def authorize(self, *_args, **_kwargs):
        raise BrokerNotInstalled("Protected Windows owner broker is not installed")

    def change_mode(self, *_args, **_kwargs):
        raise BrokerNotInstalled("Policy changes require native owner-only broker")
