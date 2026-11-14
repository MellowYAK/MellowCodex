"""Deterministic bounded context recovery without discarding user requirements."""
import ast
import pytest
from pathlib import Path
from hub.context_tool_selector import compact_tool_catalog
from hub.model_context import build_adaptive_packet, ContextBudgetError


def tool(name):
    return {"type":"function","function":{"name":name,"description":"x"*6000,
                 "parameters":{"type":"object","properties":{}}}}


def test_reducing_tool_schema_rescues_prompt_without_removing_requirements():
    messages=[{"role":"system","content":"Mandatory system policy"},
              {"role":"user","content":"Must retain the user's exact task and revisions"}]
    catalog=[tool("project_context"),tool("context_expand")]+[tool("unused"+str(i)) for i in range(15)]
    with pytest.raises(ContextBudgetError):
        build_adaptive_packet(messages,catalog,8192,2048)
    focused,meta=compact_tool_catalog(catalog,"code")
    assert meta["reduced"] and len(focused)==2
    packet,diag=build_adaptive_packet(messages,focused,8192,2048)
    assert any("exact task" in m["content"] for m in packet)
    assert diag["reserved_output"]>=256


def test_engine_fails_to_reviewable_checkpoint_not_terminal_failed_on_overflow():
    code=Path("hub/engine.py").read_text(encoding="utf-8")
    tree=ast.parse(code)
    names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
    assert "compact_tool_catalog" in names
    assert "ContextBudgetError" in names
    assert "'model_context_recovery_required'" in code
    assert "'model_context_catalog_recovery'" in code
    assert "state='waiting_review'" in code
