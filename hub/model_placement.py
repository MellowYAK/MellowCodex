"""Validated per-model CPU/GPU placement preferences and honest planning.

The GPU target describes an approximate share of weight layers. Ollama and
its backend own the final memory allocation; /api/ps is authoritative.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class PlacementProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["auto", "gpu", "cpu", "percent", "layers"] = "auto"
    gpu_percent: int = Field(default=70, ge=0, le=100)
    gpu_layers: int | None = Field(default=None, ge=0)
    context_mode: Literal["maximum", "manual"] = "maximum"
    context_tokens: int | None = Field(default=None, ge=1024)
    output_mode: Literal["maximum", "manual"] = "maximum"
    output_tokens: int | None = Field(default=None, ge=256)

    @model_validator(mode="after")
    def validate_custom(self):
        if self.mode == "layers" and self.gpu_layers is None:
            raise ValueError("gpu_layers required for layers mode")
        if self.context_mode == "manual" and self.context_tokens is None:
            raise ValueError("context_tokens required for manual context")
        if self.output_mode == "manual" and self.output_tokens is None:
            raise ValueError("output_tokens required for manual output")
        return self


def load_profiles(state_dir: Path) -> dict[str, PlacementProfile]:
    path = Path(state_dir) / "model-placement-profiles.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {name: resolve_profile(state_dir, name)[0]
                for name, value in raw.items() if isinstance(name, str) and name}
    except (OSError, ValueError, TypeError):
        return {}


def save_profile(state_dir: Path, model: str, profile: PlacementProfile):
    if not isinstance(model, str) or not model.strip() or len(model) > 300:
        raise ValueError("An installed model name is required")
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    profiles = load_profile_overrides(state_dir)
    changes = profile.model_dump(exclude_unset=True)
    if changes:
        profiles[model] = changes
    else:
        profiles.pop(model, None)
    path = state_dir / "model-placement-profiles.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(profiles,
                               ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return profile


def plan(profile: PlacementProfile, *, weight_bytes: int, free_vram_bytes: int,
         layer_count: int | None = None, vram_reserve_bytes: int = 1024**3) -> dict:
    """Return a requested layer budget, never an unmeasured memory assertion."""
    if weight_bytes <= 0 or free_vram_bytes < 0:
        raise ValueError("Model weight size and free VRAM must be measured")
    available = max(0, free_vram_bytes - max(vram_reserve_bytes, free_vram_bytes // 8))
    affordable_percent = min(100, available * 100 // weight_bytes)
    if profile.mode == "cpu":
        target = 0
    elif profile.mode == "gpu":
        target = 100
    elif profile.mode == "percent":
        target = profile.gpu_percent
    elif profile.mode == "layers":
        if not layer_count:
            raise ValueError("Layer metadata required for exact layer selection")
        target = min(100, (profile.gpu_layers or 0) * 100 // layer_count)
    else:
        target = affordable_percent
    safe_target = min(target, affordable_percent)
    if profile.mode == "gpu" and safe_target < 100:
        raise ValueError("GPU-only requested but available GPU memory is insufficient")
    layers = None
    if layer_count is not None:
        if layer_count <= 0:
            raise ValueError("Invalid layer count")
        layers = (layer_count * safe_target) // 100
        if profile.mode == "layers":
            layers = min(profile.gpu_layers or 0, layers)
    return dict(mode=profile.mode, requested_gpu_weight_percent=target,
                planned_gpu_weight_percent=safe_target,
                num_gpu=layers,
                weight_bytes=weight_bytes, free_vram_bytes=free_vram_bytes,
                estimated_only=True,
                note="GPU % is a weight-layer target, not actual VRAM %. Verify /api/ps after loading.")


# Machine-level defaults + selectable presets. An override stores only fields
# explicitly edited for one model, never a snapshot of its inherited defaults.
BUILTIN_PRESETS = {
    "automatic": {},
    "gpu_priority": {"mode": "percent", "gpu_percent": 90},
    "cpu_only": {"mode": "cpu"},
    "memory_saver": {"mode": "auto"},
    "maximum_quality": {"mode": "auto", "context_mode": "maximum", "output_mode": "maximum"},
}


class GlobalPlacementConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_preset: str = Field(default="automatic", min_length=1, max_length=64)
    defaults: PlacementProfile = Field(default_factory=PlacementProfile)
    presets: dict[str, dict] = Field(default_factory=dict)
    # None means no artificial per-user quota; scheduler and hardware remain bounded.
    request_limit: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_presets(self):
        if len(self.presets) > 50:
            raise ValueError("Too many named presets")
        for name, changes in self.presets.items():
            if not name or len(name) > 64 or name in BUILTIN_PRESETS:
                raise ValueError("Invalid or reserved preset name")
            if not isinstance(changes, dict):
                raise ValueError("Preset fields must be an object")
            PlacementProfile.model_validate({**self.defaults.model_dump(), **changes})
            if set(changes) - set(PlacementProfile.model_fields):
                raise ValueError("Unknown preset field")
        if self.active_preset not in BUILTIN_PRESETS and self.active_preset not in self.presets:
            raise ValueError("Selected preset does not exist")
        return self


def load_global(state_dir: Path) -> GlobalPlacementConfig:
    try:
        return GlobalPlacementConfig.model_validate_json(
            (Path(state_dir) / "model-global-policy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return GlobalPlacementConfig()


def save_global(state_dir: Path, config: GlobalPlacementConfig) -> GlobalPlacementConfig:
    # Validate before touching persistent state.
    config = GlobalPlacementConfig.model_validate(config)
    folder = Path(state_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "model-global-policy.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    temp.replace(path)
    return config


def load_profile_overrides(state_dir: Path) -> dict[str, dict]:
    path = Path(state_dir) / "model-placement-profiles.json"
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            return {}
        result = {}
        for name, value in source.items():
            if isinstance(name, str) and name and isinstance(value, dict):
                result[name] = PlacementProfile.model_validate(value).model_dump(exclude_unset=True)
        return result
    except (OSError, TypeError, ValueError):
        return {}


def resolve_profile(state_dir: Path, model: str) -> tuple[PlacementProfile, dict]:
    global_policy = load_global(state_dir)
    values = global_policy.defaults.model_dump()
    origins = dict.fromkeys(values, "global_default")
    preset = BUILTIN_PRESETS.get(global_policy.active_preset)
    if preset is None:
        preset = global_policy.presets[global_policy.active_preset]
    for key, value in preset.items():
        values[key] = value
        origins[key] = "global_preset:" + global_policy.active_preset
    override = load_profile_overrides(state_dir).get(model, {})
    for key, value in override.items():
        values[key] = value
        origins[key] = "model_override"
    return PlacementProfile.model_validate(values), {
        "active_global_preset": global_policy.active_preset,
        "field_sources": origins,
        "overrides": override,
        "request_limit": global_policy.request_limit,
    }


def recommend_context(*, native_context: int | None, model_info: dict,
                      model_bytes: int, free_ram_bytes: int | None,
                      free_vram_bytes: int | None, fallback_context: int) -> dict:
    """Plan the highest estimated usable context from *current* free memory.

    This is preflight only. Native architecture limit is a hard upper bound;
    actual /api/ps and a real inference are needed before claiming activation.
    The conservative fallback KV estimate is labeled, never called measured.
    """
    if native_context is not None and native_context < 1024:
        raise ValueError("Invalid native context length")
    if not isinstance(model_info, dict) or model_bytes < 0:
        raise ValueError("Invalid model metadata")
    info = {str(key).lower(): value for key, value in model_info.items()}
    def field(suffix):
        return next((int(v) for k, v in info.items()
                     if k.endswith(suffix) and isinstance(v, (int, float)) and v > 0), None)
    layers = field(".block_count")
    kv_heads = field(".attention.head_count_kv")
    key_dim = field(".attention.key_length")
    value_dim = field(".attention.value_length")
    # FP16 is the conservative default until actual KV-cache data is available.
    estimated = bool(layers and kv_heads and key_dim and value_dim)
    kv_per_token = 2 * layers * kv_heads * (key_dim + value_dim) if estimated else 128 * 1024
    native_max = native_context if native_context is not None else fallback_context
    if free_ram_bytes is None and free_vram_bytes is None:
        return {'planned_context':min(native_max,fallback_context),
                'native_context':native_context,
                'basis':'unverified_memory_using_existing_runtime_value',
                'kv_bytes_per_token_estimate':kv_per_token,
                'verified':False}
    ram = max(0,free_ram_bytes or 0)
    vram = max(0,free_vram_bytes or 0)
    # Reserve Windows/application RAM, graphics memory for kernel/prompt, and
    # the model itself; unavailable/missing hardware metrics do not imply infinity.
    ram_headroom = max(0,ram - max(2 * 1024**3,ram // 5))
    vram_headroom = max(0,vram - max(1024**3,vram // 6))
    kv_budget = max(0,ram_headroom + vram_headroom - model_bytes - 512*1024**2)
    possible = kv_budget // max(1,kv_per_token)
    if possible < 1024:
        return {'planned_context':min(native_max, max(1024, min(fallback_context,2048))),
                'native_context':native_context,'basis':'low_memory_fallback_oom_risk',
                'kv_bytes_per_token_estimate':kv_per_token,'verified':False}
    planned = min(native_max,max(1024, (possible // 1024) * 1024))
    return {'planned_context':planned,'native_context':native_context,
            'basis':'derived_from_available_memory_and_estimated_fp16_kv',
            'kv_bytes_per_token_estimate':kv_per_token,'verified':False,
            'memory_budget_bytes':kv_budget}
