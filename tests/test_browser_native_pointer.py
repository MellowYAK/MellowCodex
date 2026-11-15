"""Regression: embedded Qt browser virtual click must use native IPC, not CDP mouse."""
import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from hub.browser import Browser
from hub.errors import ObservationError


def test_native_virtual_click_uses_zero_distance_widget_event(monkeypatch):
    async def run():
        clicked = AsyncMock(side_effect=AssertionError("CDP mouse must not be used"))
        page = SimpleNamespace(url="https://example.test/", mouse=SimpleNamespace(click=clicked))
        browser = Browser()
        browser.target_id = "native-target"
        async def connect():
            return page
        browser.connect = connect
        browser.remote_frame = {
            "id": "frame", "page": page, "url": page.url,
            "at": time.monotonic(), "width": 400, "height": 300,
            "regions": {"link": {"x": 10, "y": 20, "width": 20, "height": 30}},
        }
        seen = {}
        class Process:
            async def communicate(self):
                return b'{"input_sent":true,"backend":"qt-widget-events"}', b""
        async def spawn(*argv, **options):
            seen["argv"] = argv
            return Process()
        monkeypatch.setattr("hub.browser.asyncio.create_subprocess_exec", spawn)
        result = await browser.remote_input({"frame_id": "frame", "action": "click", "ref": "link"})
        assert result["input_sent"] and result["physical_pointer_used"] is False
        assert seen["argv"][2:4] == ("hub.browser_ipc", "--virtual-drag")
        payload = json.loads(seen["argv"][4])
        assert payload == {"target_id": "native-target", "expected_url": page.url,
                           "x": 20, "y": 35, "end_x": 20, "end_y": 35, "button": "left"}
        clicked.assert_not_awaited()
        assert browser.remote_frame is None
    asyncio.run(run())


def test_native_click_without_target_fails_before_cdpevents():
    async def run():
        page = SimpleNamespace(url="https://example.test/")
        browser = Browser()
        async def connect():
            return page
        browser.connect = connect
        browser.remote_frame = {"id": "frame", "page": page, "url": page.url,
                                "at": time.monotonic(), "width": 300, "height": 200}
        with pytest.raises(ObservationError, match="Native browser target"):
            await browser.remote_input({"frame_id": "frame", "action": "click", "x": 20, "y": 30})
    asyncio.run(run())
