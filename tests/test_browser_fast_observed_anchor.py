"""A dynamic page may change unrelated text; a stable observed anchor is still safe."""
import asyncio
import time
from pathlib import Path
from types import SimpleNamespace
import pytest
from hub.browser import Browser, FAST_OBSERVED_ANCHOR_JS
from hub.errors import ObservationError


def _fixture(age=110, href="https://example.test/news", name="מבזקים"):
    page=SimpleNamespace(url="https://example.test/", context=SimpleNamespace(pages=[]))
    browser=Browser()
    browser.observation={
        "id":"obs","url":page.url,"at":time.monotonic()-age,"page":page,
        "refs":{"e1"},"elements":[{"ref":"e1","tag":"a","enabled":True,"href":href,"name":name}],
        "document_generation":1711111111111.5,
        "semantic_signature":"old-page-hash","coherent":False}
    async def connect():return page
    browser.connect=connect
    return browser,page


def test_dynamic_news_click_revalidates_anchor_without_full_page_signature(tmp_path):
    async def run():
        b,p=_fixture()
        calls=[]
        class Anchor:
            async def count(self):return 1
            async def is_visible(self):return True
            async def evaluate(self,script):calls.append("click");return {"invoked":True}
        anchor=Anchor()
        def locator(selector):
            assert "obs-e1" in selector
            return anchor
        p.locator=locator
        async def evaluate(script,params=None):
            assert script==FAST_OBSERVED_ANCHOR_JS
            assert params["href"]=="https://example.test/news"
            assert params["name"]=="מבזקים"
            calls.append("validated")
            return {"valid":True}
        p.evaluate=evaluate
        async def transition_state(page):return {"url":page.url,"ready":"complete"}
        b.transition_state=transition_state
        async def settle_transition(page,before,pages_before):return {"state":"observed_transition","kind":"navigation"}
        b.settle_transition=settle_transition
        async def observe(folder):return {"id":"new","url":"https://example.test/news","elements":[]}
        b.observe=observe
        async def strict_signature(page):raise AssertionError("Should not rescan mutable news text")
        b.semantic_signature=strict_signature
        result=await b.act({"action":"click","ref":"e1","observation_id":"obs"},tmp_path)
        assert result["input_sent"] is True
        assert result["after"]["url"]=="https://example.test/news"
        assert calls==["validated","click"]
    asyncio.run(run())


def test_changed_anchor_never_clicked(tmp_path):
    async def run():
        b,p=_fixture()
        clicked=[]
        p.locator=lambda x: (_ for _ in ()).throw(AssertionError("No locator on changed link"))
        async def evaluate(js,params=None):return {"valid":False,"reason":"Observed link identity changed"}
        p.evaluate=evaluate
        async def observe(folder):return {"id":"new","elements":[]}
        b.observe=observe
        result=await b.act({"action":"click","ref":"e1","observation_id":"obs"},tmp_path)
        assert result["input_sent"] is False
        assert result["error_code"]=="target_changed"
    asyncio.run(run())


def test_aged_form_input_still_rejected_without_dispatch(tmp_path):
    async def run():
        b,p=_fixture(age=110)
        b.observation["elements"]=[{"ref":"e1","tag":"input","enabled":True,"name":"Search"}]
        async def observe(folder):return {"id":"new","elements":[]}
        b.observe=observe
        p.locator=lambda x: (_ for _ in ()).throw(AssertionError("No input"))
        result=await b.act({"action":"fill","ref":"e1","observation_id":"obs","text":"unsafe"},tmp_path)
        assert result["input_sent"] is False
        assert result["error_code"]=="stale_observation"
    asyncio.run(run())


def test_very_old_anchor_still_rejected(tmp_path):
    async def run():
        b,p=_fixture(age=181)
        async def observe(folder):return {"id":"new","elements":[]}
        b.observe=observe
        result=await b.act({"action":"click","ref":"e1","observation_id":"obs"},tmp_path)
        assert result["input_sent"] is False
        assert result["error_code"]=="stale_observation"
    asyncio.run(run())
