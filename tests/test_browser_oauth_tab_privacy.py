"""Never deliver OAuth authorization codes in tab inventory to the model."""
from hub.browser_evidence import display_url, display_title


def test_callback_oauth_credentials_are_removed_from_model_tab_inventory():
    url='http://127.0.0.1:8890/social/youtube/callback?code=SENSITIVE_AUTH_CODE&state=SENSITIVE_STATE&scope=youtube'
    title='127.0.0.1:8890/social/youtube/callback?code=SENSITIVE_AUTH_CODE&state=SENSITIVE_STATE'
    assert display_url(url)=='http://127.0.0.1:8890/social/youtube/callback'
    assert display_title(title)=='127.0.0.1:8890/social/youtube/callback'
    assert "SENSITIVE_AUTH_CODE" not in display_url(url)+display_title(title)
    assert "SENSITIVE_STATE" not in display_url(url)+display_title(title)


def test_ordinary_tab_titles_preserved_without_long_queries():
    assert display_title('Ember Video - media studio')=='Ember Video - media studio'
    assert display_url('https://example.com/news?page=2&secret=XYZ')=='https://example.com/news?page=2'


def test_browser_tab_tool_sources_use_sanitized_url_and_title():
    from pathlib import Path
    src=(Path(__file__).parents[1]/"hub"/"browser.py").read_text(encoding="utf-8")
    assert "'url':display_url(t['url'])" in src
    assert "'title':display_title(t['title'])" in src
