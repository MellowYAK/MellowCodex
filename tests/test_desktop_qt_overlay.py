"""Qt UI runtime is opt-in and path-pinned; Hub runtime remains unchanged."""
from pathlib import Path
import sys
import pytest
from hub.qt_runtime import activate_desktop_runtime


def test_qt_override_disabled_by_default(tmp_path):
    before=sys.path[:]
    assert activate_desktop_runtime(tmp_path,tmp_path/"state") is None
    assert sys.path==before


def test_qt_override_loads_only_pinned_root_when_enabled(tmp_path):
    state=tmp_path/"state"
    state.mkdir()
    (state/"desktop-qt-stable6113.enabled").write_text("enabled")
    root=tmp_path/"tools"/"qt-stable-6113"/"site-packages"
    for name in ["PySide6/__init__.py","PySide6/Qt6Core.dll",
                 "PySide6/Qt6WebEngineCore.dll","shiboken6/__init__.py"]:
        file=root/name
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(b"test-only placeholder")
    original=sys.path[:]
    try:
        selected=activate_desktop_runtime(tmp_path,state)
        assert selected==str(root.resolve())
        assert sys.path[0]==selected
        assert activate_desktop_runtime(tmp_path,state)==selected
        assert sys.path.count(selected)==1
    finally:sys.path[:]=original


def test_incomplete_qt_overlay_refuses_activation(tmp_path):
    state=tmp_path/"state";state.mkdir()
    (state/"desktop-qt-stable6113.enabled").write_text("anything")
    with pytest.raises(RuntimeError,match="incomplete"):
        activate_desktop_runtime(tmp_path,state)
