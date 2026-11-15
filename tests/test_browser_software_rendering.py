"""An explicit local marker switches only Qt Chromium to software rendering."""
from hub import browser_view


def test_software_webengine_renderer_marker_is_opt_in(tmp_path, monkeypatch):
    monkeypatch.setattr(browser_view, "STATE", tmp_path)
    monkeypatch.setattr(browser_view, "CDP_PORT", 9324)
    monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)
    browser_view.configure_browser()
    assert "--disable-gpu" not in browser_view.os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
    assert browser_view.os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] == "127.0.0.1:9324"
    (tmp_path / "browser-software-rendering.enabled").write_text("user-authorized renderer isolation")
    browser_view.configure_browser()
    assert "--disable-gpu" in browser_view.os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
    assert "--disable-background-timer-throttling" in browser_view.os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
    assert browser_view.os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] == "127.0.0.1:9324"
