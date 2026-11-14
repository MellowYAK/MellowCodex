"""Global defaults, named presets and per-model overrides must not leak."""
import json
import pytest
from hub.model_placement import (
    PlacementProfile, GlobalPlacementConfig, load_global, save_global,
    load_profiles, load_profile_overrides, save_profile, resolve_profile,
)


def test_new_model_inherits_global_default_no_arbitrary_quota(tmp_path):
    cfg = GlobalPlacementConfig(defaults=PlacementProfile(mode="cpu"))
    save_global(tmp_path, cfg)
    profile, info = resolve_profile(tmp_path, "future-model:70b")
    assert profile.mode == "cpu"
    assert profile.context_mode == "maximum"
    assert profile.output_mode == "maximum"
    assert info["request_limit"] is None
    assert info["field_sources"]["mode"] == "global_default"


def test_selectable_preset_applies_to_unknown_new_model(tmp_path):
    save_global(tmp_path, GlobalPlacementConfig(active_preset="gpu_priority"))
    model, why = resolve_profile(tmp_path, "model-not-yet-installed")
    assert model.mode == "percent" and model.gpu_percent == 90
    assert why["field_sources"]["gpu_percent"] == "global_preset:gpu_priority"


def test_model_override_only_explicit_fields_and_global_stays_stable(tmp_path):
    save_global(tmp_path, GlobalPlacementConfig(
        active_preset="gpu_priority",
        defaults=PlacementProfile(output_mode="manual", output_tokens=9000)))
    save_profile(tmp_path, "qwen3.5:9b", PlacementProfile(mode="cpu"))
    overrides = load_profile_overrides(tmp_path)
    assert overrides["qwen3.5:9b"] == {"mode":"cpu"}
    first, provenance = resolve_profile(tmp_path, "qwen3.5:9b")
    second, _ = resolve_profile(tmp_path, "qwen3.5:4b")
    assert first.mode == "cpu" and first.output_tokens == 9000
    assert provenance["field_sources"]["mode"] == "model_override"
    assert provenance["field_sources"]["output_tokens"] == "global_default"
    assert second.mode == "percent" and second.gpu_percent == 90
    assert load_global(tmp_path).active_preset == "gpu_priority"


def test_named_preset_selected_then_restored(tmp_path):
    cfg = GlobalPlacementConfig(
        active_preset="development",
        presets={"development":{"mode":"percent","gpu_percent":70}})
    save_global(tmp_path,cfg)
    profile,_ = resolve_profile(tmp_path,"brand-new")
    assert (profile.mode,profile.gpu_percent)==("percent",70)
    cfg.active_preset="automatic"
    save_global(tmp_path,cfg)
    profile,_=resolve_profile(tmp_path,"brand-new")
    assert profile.mode=="auto"


def test_invalid_preset_rejected_without_overwriting_file(tmp_path):
    save_global(tmp_path,GlobalPlacementConfig())
    original=(tmp_path/"model-global-policy.json").read_bytes()
    with pytest.raises(ValueError):
        GlobalPlacementConfig(active_preset="does-not-exist")
    with pytest.raises(ValueError):
        GlobalPlacementConfig(presets={"automatic":{"mode":"cpu"}})
    assert (tmp_path/"model-global-policy.json").read_bytes()==original


def test_legacy_full_profile_and_new_partial_profiles(tmp_path):
    file=tmp_path/"model-placement-profiles.json"
    file.write_text(json.dumps({"old":{"mode":"cpu","context_mode":"manual","context_tokens":8192}}))
    assert load_profiles(tmp_path)["old"].context_tokens==8192
    save_profile(tmp_path,"new",PlacementProfile(gpu_percent=85,mode="percent"))
    assert load_profile_overrides(tmp_path)["new"]=={"gpu_percent":85,"mode":"percent"}
