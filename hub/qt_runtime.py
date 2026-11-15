"""Opt-in desktop-only Qt 6.11.3 runtime; never mutates Hub Python packages."""
import sys
from pathlib import Path


def activate_desktop_runtime(root, state):
    """Prepend one pinned, project-owned Qt runtime before PySide6 imports.

    The marker is a toggle, not a path: no input or web content can select
    arbitrary code to import. Other Hub processes retain their own Qt version.
    """
    if not (Path(state) / "desktop-qt-stable6113.enabled").is_file():
        return None
    location=Path(root) / "tools" / "qt-stable-6113" / "site-packages"
    required=("PySide6/__init__.py","PySide6/Qt6Core.dll",
              "PySide6/Qt6WebEngineCore.dll","shiboken6/__init__.py")
    if any(not (location / name).is_file() for name in required):
        raise RuntimeError("Pinned Qt 6.11.3 desktop runtime is incomplete; remove the desktop-qt-stable6113.enabled marker to revert.")
    path=str(location.resolve())
    if path not in sys.path:
        sys.path.insert(0,path)
    return path
