from pathlib import Path

import pytest
from hub.model_placement import PlacementProfile, load_profiles, save_profile, plan


def test_persistent_independent_profiles(tmp_path):
    save_profile(tmp_path, "qwen3.5:4b", PlacementProfile(mode="cpu"))
    save_profile(tmp_path, "qwen3.5:9b-q8", PlacementProfile(mode="percent", gpu_percent=70))
    profiles = load_profiles(tmp_path)
    assert profiles["qwen3.5:4b"].mode == "cpu"
    assert profiles["qwen3.5:9b-q8"].gpu_percent == 70


def test_automatic_reserves_vram_and_never_exaggerates():
    p = plan(PlacementProfile(), weight_bytes=10_000_000_000,
             free_vram_bytes=8_000_000_000, layer_count=40,
             vram_reserve_bytes=1_000_000_000)
    assert p["num_gpu"] <= 28
    assert p["estimated_only"]
    assert "not actual VRAM" in p["note"]


def test_cpu_and_gpu_only():
    cpu = plan(PlacementProfile(mode="cpu"), weight_bytes=2_000,
               free_vram_bytes=0, layer_count=20, vram_reserve_bytes=0)
    assert cpu["num_gpu"] == 0
    with pytest.raises(ValueError, match="insufficient"):
        plan(PlacementProfile(mode="gpu"), weight_bytes=10_000,
             free_vram_bytes=1_000, layer_count=20, vram_reserve_bytes=0)


def test_manual_requires_required_fields():
    with pytest.raises(ValueError):
        PlacementProfile(mode="layers")
    with pytest.raises(ValueError):
        PlacementProfile(context_mode="manual")


def test_percent_profile_respects_available_space():
    p = plan(PlacementProfile(mode="percent", gpu_percent=70), weight_bytes=10_000,
             free_vram_bytes=5_000, layer_count=40, vram_reserve_bytes=0)
    assert p["planned_gpu_weight_percent"] <= 50
    assert p["num_gpu"] <= 20
