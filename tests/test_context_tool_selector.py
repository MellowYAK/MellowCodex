from hub.context_tool_selector import compact_tool_catalog

def tool(name):
    return {"type":"function","function":{"name":name,"description":"x"*200,
                                            "parameters":{"type":"object"}}}

def test_code_fallback_retains_source_and_write_tools():
    names=["project_context","context_search","context_expand","run_shell",
           "write_file","browser_navigate","app_open","unrelated_tool"]
    chosen,proof=compact_tool_catalog([tool(n) for n in names],"code")
    assert proof["reduced"]
    assert len(chosen)<len(names)
    assert {x["function"]["name"] for x in chosen}=={
        "project_context","context_search","context_expand","run_shell","write_file"}

def test_no_missing_essential_available():
    original=[tool("unknown_a"),tool("unknown_b")]
    selected,diag=compact_tool_catalog(original,"code")
    assert selected==original
    assert not diag["reduced"]
