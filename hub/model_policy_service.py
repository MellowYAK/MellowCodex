"""Shared global model preset configuration for UI and MCP."""
import json
from pydantic import ValidationError
from .config import STATE
from .model_placement import BUILTIN_PRESETS, GlobalPlacementConfig, load_global, save_global


async def perform(action="get", value=None, busy=False):
    if action not in ("get", "set", "reset"):
        return {"handled": True, "accepted": False, "error": "Expected get/set/reset"}
    if action == "get":
        return {"handled": True, "accepted": True,
                "global_policy": load_global(STATE).model_dump(),
                "available_presets": list(BUILTIN_PRESETS), "scope": "global"}
    if busy:
        return {"handled": True, "accepted": False,
                "error": "A task is active; global settings unchanged"}
    try:
        raw = json.loads(value) if isinstance(value, str) else value
        if action == "reset":
            policy = GlobalPlacementConfig()
        elif isinstance(raw, dict):
            current = load_global(STATE).model_dump()
            policy = GlobalPlacementConfig.model_validate({**current, **raw})
        else:
            return {"handled": True, "accepted": False,
                    "error": "Supply a global policy object"}
        save_global(STATE, policy)
        saved = load_global(STATE)
        return {"handled": True, "accepted": True, "scope": "global",
                "saved": saved.model_dump(), "applies": "next_model_load",
                "available_presets": list(BUILTIN_PRESETS),
                "note": "No artificial request quota; actual hardware and concurrency limits remain."}
    except (ValueError, TypeError, ValidationError) as exc:
        return {"handled": True, "accepted": False, "error": str(exc)[:400]}
