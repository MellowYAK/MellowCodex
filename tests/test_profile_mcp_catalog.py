"""Regression: the new shared profile service is advertised in the MCP catalog.

Importing the isolated candidate gateway does not connect to a remote provider.
"""
import asyncio


def test_global_and_per_model_tools_are_mcp_registered():
    from hub.mcp_gateway import mcp
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert {
        "model_profiles_status",
        "model_profiles_global_set",
        "model_profiles_model_set",
        "model_settings_status",
        "model_settings_command",
        "model_memory_control",
    }.issubset(names)


def test_no_duplicate_profile_tools():
    from hub.mcp_gateway import mcp
    names=[tool.name for tool in asyncio.run(mcp.list_tools())]
    assert names.count("model_profiles_status")==1
    assert names.count("model_profiles_global_set")==1
    assert names.count("model_profiles_model_set")==1
