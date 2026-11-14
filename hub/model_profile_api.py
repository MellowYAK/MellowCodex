"""Model policy endpoints: one shared source for native UI and authorized MCP."""
from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .config import OLLAMA, STATE
from .model_placement import (
    BUILTIN_PRESETS, GlobalPlacementConfig, PlacementProfile,
    load_global, save_global, load_profile_overrides, save_profile,
    resolve_profile,
)


class GlobalChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    settings: dict = Field(default_factory=dict)
    reset: bool = False


class ModelChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=300)
    settings: dict = Field(default_factory=dict)
    reset: bool = False
    clear_fields: list[str] = Field(default_factory=list)


def router(is_busy):
    routes = APIRouter(prefix="/profiles")

    def state(model=None):
        global_config = load_global(STATE)
        payload = {
            "global": global_config.model_dump(),
            "builtin_presets": BUILTIN_PRESETS,
            "request_quota": "unlimited" if global_config.request_limit is None
                             else global_config.request_limit,
            "quota_note": "No artificial total request limit; safe serial GPU access and real hardware constraints still apply.",
            "model_overrides": load_profile_overrides(STATE),
        }
        if model:
            effective, provenance = resolve_profile(STATE, model)
            payload.update(model=model, effective=effective.model_dump(),
                           provenance=provenance)
        return payload

    @routes.get("")
    async def status(model: str | None = None):
        return state(model)

    @routes.post("/global")
    async def change_global(body: GlobalChange):
        if is_busy():
            return {"accepted": False, "error": "Finish active tasks before changing model policy"}
        previous = load_global(STATE)
        if body.reset:
            replacement = GlobalPlacementConfig()
        else:
            merged = {**previous.model_dump(), **body.settings}
            if "defaults" in body.settings:
                merged["defaults"] = {**previous.defaults.model_dump(), **body.settings["defaults"]}
            if "presets" in body.settings:
                merged["presets"] = {**previous.presets, **body.settings["presets"]}
            replacement = GlobalPlacementConfig.model_validate(merged)
        save_global(STATE, replacement)
        return {"accepted": True, "applies": "next_model_load", **state()}

    @routes.post("/model")
    async def change_model(body: ModelChange):
        if is_busy():
            return {"accepted": False, "error": "Finish active tasks before changing model profile"}
        async with httpx.AsyncClient(timeout=7, trust_env=False) as c:
            tags = await c.get(OLLAMA + "/api/tags")
            tags.raise_for_status()
        if body.model not in {item.get("name") for item in tags.json().get("models", [])}:
            return {"accepted": False, "error": "Select an exact installed model name"}
        # An empty override inherits all global settings. Never copies a global
        # profile into model-specific storage.
        prior = {} if body.reset else load_profile_overrides(STATE).get(body.model, {})
        allowed = set(PlacementProfile.model_fields)
        if any(field not in allowed for field in body.clear_fields):
            return {"accepted": False, "error": "Unknown profile field"}
        for field in body.clear_fields:
            prior.pop(field, None)
        profile = PlacementProfile.model_validate({**prior, **body.settings})
        if body.reset:
            profile = PlacementProfile()
        save_profile(STATE, body.model, profile)
        return {"accepted": True, "applies": "next_model_load", **state(body.model)}

    return routes
