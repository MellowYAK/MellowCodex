"""Public health readiness must use the light Hub identity, not large OpenAPI."""
import asyncio
from types import SimpleNamespace
import httpx
from fastapi import HTTPException
from hub import mcp_gateway

def test_hub_probe_checks_lightweight_root_identity(monkeypatch):
    paths=[]
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url):
            paths.append(url)
            return SimpleNamespace(is_success=True,
                text='<html><title>MellowCodex</title><button id="chatgpt-bridge"></button></html>',
                json=lambda: (_ for _ in ()).throw(ValueError('HTML')))
    monkeypatch.setattr(mcp_gateway.httpx,'AsyncClient',lambda **kwargs:Client())
    assert asyncio.run(mcp_gateway._hub_ready()) is True
    assert paths==['http://127.0.0.1:'+str(mcp_gateway.PORT)+'/']

def test_unrelated_server_root_never_counts_as_hub(monkeypatch):
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url):
            return SimpleNamespace(is_success=True,text='<html>Other service</html>',json=lambda:{})
    monkeypatch.setattr(mcp_gateway.httpx,'AsyncClient',lambda **kwargs:Client())
    assert asyncio.run(mcp_gateway._hub_ready()) is False

def test_connection_error_still_fails_and_gateway_retains_503(monkeypatch):
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url):raise httpx.ConnectError('Hub unavailable')
    monkeypatch.setattr(mcp_gateway.httpx,'AsyncClient',lambda **kwargs:Client())
    assert asyncio.run(mcp_gateway._hub_ready()) is False
    try:asyncio.run(mcp_gateway.health())
    except HTTPException as exc:assert exc.status_code==503
    else:assert False,'A real outage must not return healthy'
