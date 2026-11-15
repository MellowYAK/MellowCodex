"""Qt's blank-frame fallback must not disable local web-app JavaScript."""
from PySide6.QtCore import QUrl
from hub.browser_view import should_enable_compatibility


def test_local_spa_never_auto_disables_javascript_after_white_frame():
    for url in ("http://127.0.0.1:8890/", "http://localhost:8890/", "http://[::1]:8890/", "https://localhost:8443/app"):
        assert should_enable_compatibility(QUrl(url),True,False,2) is False
        assert should_enable_compatibility(QUrl(url),True,False,99) is False


def test_remote_site_blank_render_recovery_is_unchanged():
    u=QUrl("https://www.ynet.co.il/news/category/184")
    assert should_enable_compatibility(u,True,False,1) is False
    assert should_enable_compatibility(u,True,False,2) is True
    assert should_enable_compatibility(u,False,False,3) is False
    assert should_enable_compatibility(u,True,True,3) is False
    assert should_enable_compatibility(QUrl("about:blank"),True,False,2) is False
