"""Runtime inference respects inherited model profile instead of global hard caps."""
import asyncio
import httpx
import pytest
from hub.model_settings import ModelSettings
from hub import inference_profiles as ip
from hub.model_placement import GlobalPlacementConfig, save_global, save_profile, PlacementProfile


class Client:
    def __init__(self, loaded=True):
        self.loaded=loaded
        self.calls=[]
    async def get(self, url):
        self.calls.append(("GET",url))
        if url.endswith("/api/ps"):
            return httpx.Response(200,request=httpx.Request("GET",url),json={"models":[{"name":"qwen3.5:4b",
                "context_length":32768,"size":5_000_000_000,"size_vram":3_000_000_000}]} if self.loaded else {"models":[]})
        if url.endswith("/api/tags"):
            return httpx.Response(200,json={"models":[{"name":"qwen3.5:4b","size":4_000_000_000}]})
        raise AssertionError(url)


def test_global_max_respects_loaded_context_and_adaptive_output(monkeypatch,tmp_path):
    monkeypatch.setattr(ip,"STATE",tmp_path)
    save_global(tmp_path,GlobalPlacementConfig())
    settings=ModelSettings(model="qwen3.5:4b",context_tokens=16384,
                           response_tokens=1024,context_management="shadow")
    actual,options,metadata=asyncio.run(ip.effective_inference(Client(),settings))
    assert actual.context_tokens==32768
    assert actual.response_tokens==32768-256
    assert actual.context_management=="bounded"
    assert options=={}
    assert metadata["placement"]["allocation_verified"]
    assert settings.context_tokens==16384


def test_model_specific_output_override_only_one_model(monkeypatch,tmp_path):
    monkeypatch.setattr(ip,"STATE",tmp_path)
    save_profile(tmp_path,"qwen3.5:4b",PlacementProfile(output_mode="manual",output_tokens=7000))
    settings=ModelSettings(model="qwen3.5:4b")
    actual,_,meta=asyncio.run(ip.effective_inference(Client(),settings))
    assert actual.response_tokens==7000
    assert meta["profile_origin"]["field_sources"]["output_tokens"]=="model_override"


def test_model_override_above_context_rejected(monkeypatch,tmp_path):
    monkeypatch.setattr(ip,"STATE",tmp_path)
    save_profile(tmp_path,"qwen3.5:4b",PlacementProfile(output_mode="manual",output_tokens=40000))
    with pytest.raises(ValueError,match="exceeds"):
        asyncio.run(ip.effective_inference(Client(),ModelSettings(model="qwen3.5:4b")))
