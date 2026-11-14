"""Unprivileged Hub adapter: owner broker is NOT installed or impersonated.

All effects must pass the final ToolRunner gate, including SelfDevelop and PLAY.
This cannot defend against a same-user arbitrary shell bypass; installing a real
OS-isolated broker and restricting the executor token is a separate owner step.
"""
from __future__ import annotations

import hashlib
import json

from .owner_broker import owner_status
from .owner_policy import (BrokerReadOnly, Operation, Risk, enforce)


PUBLIC_READ = frozenset((
    "agent_environment", "project_context", "project_brief",
    "context_search", "context_expand", "context_related", "context_refresh",
    "recovery_context", "conversation_history", "conversation_anchors",
    "project_index_status", "upgrade_status", "extensions_list",
    "model_catalog", "model_catalog_details", "model_catalog_search",
    "model_memory_status", "session_status",
))
PRIVATE_READ = frozenset((
    'desktop_status',
    'computer_power_preview','computer_power_status','agent_startup_status',
    "read_file", "list_files", "files_list", "image_ocr",
    "capture_screenshot", "observe_screen", "window_inspect",
    "list_windows", "inspect_accessibility", "browser_observe",
    "browser_tabs", "browser_frame", "browser_extract",
    "document_read", "project_git_status",
))
# Explicit operation classes; all unlisted operations, opaque shell/scripts and
# installed Python skills are UNKNOWN until a reviewed, version-pinned adapter
# can describe their exact arguments and side effects.
REVERSIBLE = frozenset((
    'desktop_open',
    "app_open", "app_find", "app_close", "window_act",
    "browser_navigate", "browser_act", "browser_select_tab",
    "browser_pointer", "focus_window", "desktop_action",
    "document_write", "write_file", "browser_upload",
    "window_new_document", "terminal_start", "terminal_write",
))
DESTRUCTIVE = frozenset((
    'computer_power',
    "file_copy", "file_share", "browser_save_media", "browser_save_pdf",
    "browser_close_tabs", "candidate_patch", "candidate_repair",
))
PROTECTED = frozenset((
    'agent_startup_set',
    "model_install", "model_install_huggingface", "model_install_cancel",
    "upgrade_activate", "upgrade_recover", "candidate_stage_release",
    "extension_register", "tools_enable",
))


def classify(name: str, arguments: dict) -> tuple[Risk, bool]:
    if name=='action_routes':
        action=arguments.get('action')
        if action in ('list','get','step','prepare'):return Risk.PRIVATE_READ,True
        if action in ('create','save','learn'):return Risk.REVERSIBLE_ACTION,True
        if action=='delete':return Risk.DESTRUCTIVE,True
    if name in PUBLIC_READ:
        return Risk.PUBLIC_READ, True
    if name in PRIVATE_READ:
        return Risk.PRIVATE_READ, True
    if name in REVERSIBLE:
        return Risk.REVERSIBLE_ACTION, True
    if name in DESTRUCTIVE:
        return Risk.DESTRUCTIVE, True
    if name in PROTECTED:
        return Risk.PROTECTED, True
    # run_shell, browser_script, extension_run, arbitrary user code and future
    # tools remain UNKNOWN: a signed/tested skill is not automatically safe.
    return Risk.UNKNOWN, False


def chat_for_task(store, task: dict) -> str:
    if store is None:
        return task.get("chat_id", "")
    with store.connect() as db:
        row = db.execute(
            "SELECT chat_id FROM chat_tasks WHERE task_id=?",
            (task["id"],)).fetchone()
    return row[0] if row else ""


def check_native_action(task: dict, name: str, arguments: dict, spec: dict,
                        *, action_id: str | None, context_store,
                        allowed_tools: set[str] | None) -> dict | None:
    risk, reviewed = classify(name, arguments)
    if not action_id and risk > Risk.PRIVATE_READ:
        return {"error": "Effectful action lacks durable action_id",
                "failure_kind": "unbound_action",
                "input_sent": False, "effect_started": False}
    schema = spec["function"]
    schema_hash = hashlib.sha256(json.dumps(
        schema["parameters"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    operation = Operation.from_action(
        task_id=task["id"], task_revision=task["revision"],
        chat_id=chat_for_task(context_store, task),
        action_id=action_id or "read:" + task["id"] + ":" + name,
        name=name, args=arguments, target=str(arguments.get("hwnd") or
                   arguments.get("url") or arguments.get("path") or
                   arguments.get("scope") or "default"),
        version_hash=schema_hash, schema_hash=schema_hash,
        risk=risk, approved_descriptor=reviewed, scope=str(task.get("mode", "")),
        may_elevate=False)
    # This untrusted Hub must NOT interpret an in-process bearer or bool as
    # owner approval. Missing or unauthenticated broker falls back to Safe.
    from .owner_broker import owner_snapshot, authorize_action
    snapshot = owner_snapshot(operation.chat_id)
    permitted = set(allowed_tools) if allowed_tools is not None else {name}
    decision = enforce(snapshot, operation, allowed_tools=permitted)
    if decision.allowed and decision.tier.value == "safe":
        return None
    # Owner control-plane authority is never granted to arbitrary agent requests.
    if name in {'owner_policy_change','owner_broker_install','owner_grant','owner_revoke'}:
        return {'error':'Owner control-plane changes require protected native UI',
                'failure_kind':'owner_control_plane_denied','input_sent':False,'effect_started':False}
    if name in permitted and snapshot.broker_verified and snapshot.effective(operation.chat_id)[0].value in ('ask','full'):
        request={'command':'authorize','chat_id':operation.chat_id,'task_id':operation.task_id,
                 'action_id':operation.action_id,'operation':name,
                 'policy_revision':snapshot.policy_revision,'task_revision':operation.task_revision,
                 'args':arguments,'arguments_hash':operation.arguments_hash,
                 'target':operation.target,'version_hash':operation.version_hash,
                 'schema_hash':operation.schema_hash,'scope':operation.scope,
                 'risk':operation.risk.name,'elevation_requested':False}
        answer=authorize_action(request)
        if answer.get('allowed') is True and answer.get('policy_revision')==snapshot.policy_revision:
            return None
        return {'error':answer.get('reason') or answer.get('error') or 'Owner approval unavailable',
                'failure_kind':'owner_approval_required','waiting_owner':answer.get('reason')=='owner_approval_required',
                'owner_request_id':answer.get('request_id'),'owner_policy_revision':snapshot.policy_revision,
                'input_sent':False,'effect_started':False}
    return {
        "error": "Protected owner approval is required: " + decision.code,
        "failure_kind": decision.code,
        "owner_policy_revision": decision.policy_revision,
        "effective_tier": decision.tier.value,
        "owner_broker": owner_status(),
        "input_sent": False, "effect_started": False,
    }
