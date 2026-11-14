"""Safe shutdown skill. Delegates all actual power operations to native, owner-gated tools."""
import json
import sys

_SKILL = "computer_shutdown"
_NATIVE = ("computer_power_preview", "computer_power", "computer_power_status")

def run(request):
    if not isinstance(request, dict) or set(request) - {"action", "operation_id"}:
        raise ValueError("Expected action and optional operation_id only")
    action = request.get("action", "preview")
    if action == "preview":
        if "operation_id" in request:
            raise ValueError("operation_id is only valid with status")
        return {
            "skill": _SKILL, "safe": True, "performed_power_action": False,
            "next_tool": "computer_power_preview",
            "next_arguments": {"action": "shutdown"},
            "required_followup": "Explain impact and request explicit current user confirmation before invoking computer_power. Never infer consent from installing or inspecting this skill.",
            "native_tools": list(_NATIVE),
        }
    if action == "request_shutdown":
        if "operation_id" in request:
            raise ValueError("operation_id is only valid with status")
        return {
            "skill": _SKILL, "safe": True, "performed_power_action": False,
            "requires_explicit_current_user_authorization": True,
            "next_tool": "computer_power",
            "next_arguments_template": {"action": "shutdown", "request_id": "fresh-stable-id-per-user-request", "confirm_tasks": True},
            "required_followup": "Use only after current user explicitly asks to shut down. The owner-gated native tool and durable task review control dispatch. Do not invoke shutdown.exe or power.submit directly.",
        }
    if action == "status":
        operation_id = request.get("operation_id")
        if not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 128:
            raise ValueError("Status requires a valid operation_id")
        return {
            "skill": _SKILL, "safe": True, "performed_power_action": False,
            "next_tool": "computer_power_status",
            "next_arguments": {"operation_id": operation_id},
        }
    raise ValueError("Allowed actions: preview, request_shutdown, status")

if __name__ == "__main__":
    try:
        print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"skill": _SKILL, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
