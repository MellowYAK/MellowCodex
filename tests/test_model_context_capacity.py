"""Native context and machine-memory limits, not arbitrary 16K ceilings."""
from hub.model_placement import recommend_context


def test_context_can_exceed_legacy_16k_32k_caps():
    metadata={"qwen.block_count":32,"qwen.attention.head_count_kv":4,
              "qwen.attention.key_length":128,"qwen.attention.value_length":128}
    result=recommend_context(native_context=262144,model_info=metadata,
        model_bytes=5*1024**3,free_ram_bytes=36*1024**3,
        free_vram_bytes=10*1024**3,fallback_context=16384)
    assert result["planned_context"] > 32768
    assert result["planned_context"] <= result["native_context"]
    assert result["verified"] is False


def test_context_never_exceeds_model_native():
    result=recommend_context(native_context=32768,model_info={},
        model_bytes=1024,free_ram_bytes=40*1024**3,
        free_vram_bytes=12*1024**3,fallback_context=4096)
    assert result["planned_context"] == 32768


def test_context_uncertain_memory_does_not_assume_infinity():
    result=recommend_context(native_context=262144,model_info={},
        model_bytes=5*1024**3,free_ram_bytes=None,
        free_vram_bytes=None,fallback_context=16384)
    assert result["planned_context"]==16384
    assert result["basis"]=="unverified_memory_using_existing_runtime_value"


def test_incomplete_metadata_is_labeled_unverified():
    result=recommend_context(native_context=262144,model_info={"x.block_count":24},
        model_bytes=6*1024**3,free_ram_bytes=12*1024**3,
        free_vram_bytes=2*1024**3,fallback_context=16384)
    assert result["verified"] is False
    assert result["kv_bytes_per_token_estimate"]==128*1024


def test_low_memory_never_promises_full_native_context():
    result=recommend_context(native_context=262144,model_info={},
        model_bytes=10*1024**3,free_ram_bytes=1024**3,
        free_vram_bytes=0,fallback_context=16384)
    assert result["planned_context"] <= 2048
    assert result["basis"]=="low_memory_fallback_oom_risk"
