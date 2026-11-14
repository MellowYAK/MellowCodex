"""Translate global/per-model preferences into effective Ollama runtime options.

Automatic limits are constrained by the model and currently available memory;
manual overrides never silently mutate global preferences. Unmeasured backend
memory placement must not be reported as a verified allocation.
"""
from __future__ import annotations

from .config import OLLAMA, STATE
from .model_placement import resolve_profile
from .model_memory import _load_options, matches


async def effective_inference(client, settings):
    model = settings.model
    profile, origin = resolve_profile(STATE, model)
    try:
        response = await client.get(OLLAMA + "/api/ps")
        response.raise_for_status()
        resident = next((m for m in response.json().get("models", [])
                         if matches(m.get("name", ""), model)), None)
    except Exception:
        resident = None
    if resident and isinstance(resident.get("context_length"), int) and resident["context_length"] >= 1024:
        ctx = resident["context_length"]
        options = {"num_ctx": ctx}
        placement = {"mode": profile.mode, "source": "ollama:/api/ps",
                     "loaded_size_vram": resident.get("size_vram"),
                     "loaded_size": resident.get("size"),
                     "allocation_verified": True}
    else:
        response = await client.get(OLLAMA + "/api/tags")
        response.raise_for_status()
        options, placement = await _load_options(
            client, model, settings, response.json().get("models", []))
        ctx = int(options["num_ctx"])
    if profile.output_mode == "manual":
        requested = int(profile.output_tokens)
        if requested > ctx - 256:
            raise ValueError("Manual output token budget exceeds loaded model's available context")
        output_ceiling = requested
    else:
        output_ceiling = max(256, ctx - 256)
    actual = settings.model_copy(update={
        "context_tokens": ctx,
        "response_tokens": output_ceiling,
        "context_management": "bounded" if profile.context_mode == "maximum" else settings.context_management,
    })
    return actual, {k:v for k,v in options.items() if k != "num_ctx"}, {
        "profile_origin": origin, "placement": placement,
        "context_tokens": ctx, "output_ceiling": output_ceiling,
        "reserved_input_and_output_share_context": True,
    }
