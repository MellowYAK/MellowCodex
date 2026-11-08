"""Acceptance for optional hash-fenced focused worker edits (not a model fixture)."""
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from hub.development import worker


def packet(text, writable=True):
    return {
        "model": "qwen2.5-coder:7b",
        "allowed_paths": ["guard.py"],
        "sources": {
            "guard.py": {
                "text": text,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "writable": writable,
            }
        },
    }


def focused(p, find, replace):
    return {"changes": [{
        "path": "guard.py",
        "base_hash": p["sources"]["guard.py"]["sha256"],
        "find": find,
        "replace": replace,
    }]}


def test_unique_fenced_edit_preserves_guards_docstring_and_crlf():
    source='"""Keep this docstring."""\r\n\r\ndef validate(x):\r\n    if not isinstance(x, str):\r\n        raise ValueError("bad")\r\n    return x.strip()\r\n'
    p=packet(source)
    actual=worker.materialize_patch(p, focused(p, "    return x.strip()", "    return x.strip().upper()"))
    changed=actual["changes"][0]
    assert changed["path"] == "guard.py"
    assert changed["content"] == source.replace("    return x.strip()", "    return x.strip().upper()")
    assert 'if not isinstance(x, str)' in changed["content"]
    assert changed["content"].startswith('"""Keep this docstring."""\r\n')
    assert "\r\n" in changed["content"]


@pytest.mark.parametrize("bad_find,bad_replace", [
    ("not present", "replacement"),
    ("same", "different"),
])
def test_missing_or_nonunique_match_rejected(bad_find, bad_replace):
    source="same\nsame\n"
    p=packet(source)
    with pytest.raises(ValueError):
        worker.materialize_patch(p, focused(p, bad_find, bad_replace))


def test_stale_hash_rejected_before_edit():
    p=packet("value=1\n")
    proposal=focused(p,"value=1","value=2")
    proposal["changes"][0]["base_hash"]="0"*64
    with pytest.raises(ValueError, match="hash|stale|mismatch|conflict"):
        worker.materialize_patch(p,proposal)


def test_unchanged_and_readonly_rejected():
    p=packet("value=1\n")
    with pytest.raises(ValueError):
        worker.materialize_patch(p,focused(p,"value=1","value=1"))
    p["sources"]["guard.py"]["writable"]=False
    with pytest.raises(ValueError):
        worker.materialize_patch(p,focused(p,"value=1","value=2"))


def test_legacy_full_content_remains_supported():
    p=packet("value=1\n")
    result=worker.materialize_patch(p,{"changes":[{"path":"guard.py","content":"value=2\n"}]})
    assert result["changes"] == [{"path":"guard.py","content":"value=2\n"}]


def test_worker_propose_returns_materialized_full_content(monkeypatch):
    p=packet("value=1\n")
    edit=focused(p,"value=1","value=2")
    settings=SimpleNamespace(context_tokens=32768,response_tokens=4096,request_timeout_seconds=20,keep_alive_minutes=1,temperature=0,inference_enabled=True)
    monkeypatch.setattr(worker,"load_settings",lambda: settings)
    monkeypatch.setattr(worker,"token_estimate",lambda _: 100)
    class DummyLease:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
    class DummyResources:
        def inference(self,*args): return DummyLease()
    monkeypatch.setattr(worker,"Resources",DummyResources)
    class Response:
        def __init__(self,data): self.data=data
        def raise_for_status(self): pass
        def json(self): return self.data
    class FakeClient:
        def __init__(self,*args,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,*args,**kwargs):
            return Response({"models":[{"name":p["model"]}]})
        async def post(self,*args,**kwargs):
            return Response({"message":{"content":json.dumps(edit)}})
    monkeypatch.setattr(worker.httpx,"AsyncClient",FakeClient)
    actual=asyncio.run(worker.propose(p))
    assert actual["proposal"]["changes"] == [{"path":"guard.py","content":"value=2\n"}]
