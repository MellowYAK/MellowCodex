"""Qt compatibility fallback must not break a different site's SPA.

Re-enable JavaScript on cross-host navigation without replaying navigation or
reloading the page; retain readable mode within the original failing host.
"""
from types import SimpleNamespace

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings

from hub.browser_view import BrowserView, should_restore_javascript


class Sink:
    def __init__(self):
        self.calls = []

    def setAttribute(self, *args):
        self.calls.append(("attribute", args))

    def setText(self, value):
        self.calls.append(("text", value))

    def setVisible(self, value):
        self.calls.append(("visible", value))


def make_case(*, current=True):
    settings, address, button, status = Sink(), Sink(), Sink(), Sink()
    page = SimpleNamespace(settings=lambda: settings)
    view = SimpleNamespace(
        compatibility_mode=True,
        compatibility_host="www.walla.co.il",
        blank_cycles=3,
        page=lambda: page,
    )
    other = object()
    ui = SimpleNamespace(
        current=lambda: view if current else other,
        address=address,
        full_site_button=button,
        status=status,
    )
    return ui, view, settings, address, button, status


def test_cross_host_walla_mail_restores_javascript_without_reloading():
    ui, view, settings, address, button, status = make_case()
    BrowserView.url_changed(ui, view, QUrl("https://friends.walla.co.il/#/login"))
    assert not view.compatibility_mode
    assert view.compatibility_host is None
    assert view.blank_cycles == 0
    assert settings.calls == [(
        "attribute",
        (QWebEngineSettings.WebAttribute.JavascriptEnabled, True),
    )]
    assert ("visible", False) in button.calls
    assert address.calls[-1] == ("text", "https://friends.walla.co.il/#/login")
    assert status.calls
    # No view.setUrl or page reload method exists in these fakes: triggering
    # either would raise instead of silently replaying an external action.


def test_same_host_readable_fallback_is_retained():
    ui, view, settings, address, button, status = make_case()
    BrowserView.url_changed(ui, view, QUrl("https://www.walla.co.il/next"))
    assert view.compatibility_mode
    assert view.compatibility_host == "www.walla.co.il"
    assert view.blank_cycles == 0
    assert settings.calls == []
    assert button.calls == []


def test_hidden_tab_restores_javascript_but_does_not_change_visible_ui():
    ui, view, settings, address, button, status = make_case(current=False)
    BrowserView.url_changed(ui, view, QUrl("https://friends.walla.co.il/#/login"))
    assert not view.compatibility_mode
    assert settings.calls
    assert address.calls == []
    assert button.calls == []
    assert status.calls == []


def test_cross_host_helper_rejects_non_web_navigation():
    assert should_restore_javascript("www.walla.co.il", QUrl("https://friends.walla.co.il/#/login"))
    assert should_restore_javascript("www.walla.co.il", QUrl("http://localhost:3000/"))
    assert not should_restore_javascript("www.walla.co.il", QUrl("https://www.walla.co.il/another"))
    assert not should_restore_javascript("www.walla.co.il", QUrl("file:///C:/data.html"))
    assert not should_restore_javascript("www.walla.co.il", QUrl("about:blank"))
    assert not should_restore_javascript(None, QUrl("https://friends.walla.co.il/"))


def test_helper_is_case_insensitive_and_requires_real_hostname_change():
    assert not should_restore_javascript("WWW.WALLA.CO.IL", QUrl("https://www.walla.co.il/"))
    assert should_restore_javascript("WWW.WALLA.CO.IL", QUrl("https://FRIENDS.WALLA.CO.IL/"))
