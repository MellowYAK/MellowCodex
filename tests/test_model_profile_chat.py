import asyncio
import httpx
from hub import model_profile_chat as chat
from hub.model_placement import load_global, load_profile_overrides, resolve_profile


class Client:
    def __init__(self, **kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def get(self,url):
        return httpx.Response(200,request=httpx.Request("GET",url),
            json={"models":[{"name":"qwen3.5:4b"},
                             {"name":"hf.co/unsloth/Qwen3.5-9B-GGUF:Qwen3.5-9B-Q8_0.gguf"}]})


def test_chat_changes_only_named_model(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    monkeypatch.setattr(chat.httpx,"AsyncClient",Client)
    result=asyncio.run(chat.apply("הגדר למודל qwen3.5:4b 70% GPU"))
    assert result["accepted"] and result["scope"]=="model"
    assert load_profile_overrides(tmp_path)["qwen3.5:4b"]=={"mode":"percent","gpu_percent":70}
    assert resolve_profile(tmp_path,"other")[0].mode=="auto"


def test_global_change_inherited_by_future_model(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    result=asyncio.run(chat.apply("הגדר ברירת מחדל לכל המודלים CPU בלבד"))
    assert result["accepted"]
    assert resolve_profile(tmp_path,"future:8b")[0].mode=="cpu"


def test_choose_named_global_preset(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    result=asyncio.run(chat.apply("בחר פרופיל ביצועים גלובלי"))
    assert result["accepted"] and load_global(tmp_path).active_preset=="gpu_priority"


def test_ambiguous_model_does_not_mutate(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    monkeypatch.setattr(chat.httpx,"AsyncClient",Client)
    result=asyncio.run(chat.apply("set GPU to 70% on the model"))
    assert not result["accepted"]
    assert not load_profile_overrides(tmp_path)


def test_busy_rejects_writes(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    result=asyncio.run(chat.apply("קבע ברירת מחדל ל־CPU בלבד",busy=True))
    assert not result["accepted"]


def test_load_uses_verified_memory_control(monkeypatch,tmp_path):
    monkeypatch.setattr(chat,"STATE",tmp_path)
    monkeypatch.setattr(chat.httpx,"AsyncClient",Client)
    from hub import model_memory
    calls=[]
    async def control(action,model):
        calls.append((action,model))
        return {"verified":True,"memory":{"models":[{"name":model}]}}
    monkeypatch.setattr(model_memory,"control",control)
    result=asyncio.run(chat.apply("טען qwen3.5:4b עם 70% GPU"))
    assert result["accepted"] and result["loaded"]
    assert calls==[("switch","qwen3.5:4b")]
