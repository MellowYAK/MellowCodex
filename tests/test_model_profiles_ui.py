"""Checks that the model-profile UI is wired to the shared HTTP API."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_profile_ui_has_global_and_model_scopes():
    source=Path("hub/static/models.js").read_text(encoding="utf-8")
    for required in ("profiles/global", "profiles/model", "globalPreset", "modelSelect",
                     "modelMode", "modelContext", "modelOutput", "profileSection"):
        assert required in source
    assert "GPU 5.77GB" not in source


def test_profile_js_syntax_if_node_is_available():
    node=shutil.which("node")
    if not node:
        pytest.skip("Node.js not on Windows PATH; static check only")
    result=subprocess.run([node,"--check","hub/static/models.js"],
                          capture_output=True,text=True,timeout=15)
    assert result.returncode==0, result.stderr[:1500]


def test_mcp_profile_tools_registered_in_catalog_module():
    source=Path("hub/model_catalog.py").read_text(encoding="utf-8")
    assert "async def model_profiles_status(" in source
    assert "async def model_profiles_global_set(" in source
    assert "async def model_profiles_model_set(" in source
