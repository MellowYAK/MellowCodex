"""Independent Gateway health probe: real failures remain failures, not false green."""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
from fastapi import HTTPException

from hub import mcp_gateway


def test_hub_ready_retries_once_and_ignores_environment_proxy(monkeypatch):
    seen=[]
    class FakeClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url):
            seen.append(url)
            if len(seen)==1:raise httpx.ReadTimeout('temporary overload')
            return SimpleNamespace(is_success=True,json=lambda:{'info':{'title':'Local Agent Hub'}})
    def factory(**kwargs):
        assert kwargs['trust_env'] is False
        assert kwargs['timeout'].read==4.0
        return FakeClient()
    monkeypatch.setattr(mcp_gateway.httpx,'AsyncClient',factory)
    assert asyncio.run(mcp_gateway._hub_ready()) is True
    assert len(seen)==2


def test_gateway_health_stays_503_when_hub_is_not_ready(monkeypatch):
    async def not_ready():return False
    monkeypatch.setattr(mcp_gateway,'_hub_ready',not_ready)
    with pytest.raises(HTTPException) as error:
        asyncio.run(mcp_gateway.health())
    assert error.value.status_code==503


def test_hub_readiness_rejects_wrong_or_unavailable_application(monkeypatch):
    class FakeClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url):
            return SimpleNamespace(is_success=True,json=lambda:{'info':{'title':'Not our Hub'}})
    monkeypatch.setattr(mcp_gateway.httpx,'AsyncClient',lambda **kwargs:FakeClient())
    assert asyncio.run(mcp_gateway._hub_ready()) is False
