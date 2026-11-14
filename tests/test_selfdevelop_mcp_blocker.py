"""SelfDevelop preflight blocker is visible through MCP rather than a transport error."""
import asyncio
import json
import pytest
from hub import mcp_gateway as gateway


class FakeResponse:
    status_code = 409
    is_success = False

    def __init__(self, detail):
        self.detail = detail
        self.text = str(detail)

    def json(self):
        return {'detail': self.detail}


class FakeClient:
    def __init__(self, detail):
        self.detail = detail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, *args, **kwargs):
        return FakeResponse(self.detail)


def test_selfdevelop_blocker_structured(monkeypatch, tmp_path):
    (tmp_path/'hub.key').write_text('local-test-key', encoding='utf-8')
    monkeypatch.setattr(gateway, 'STATE', tmp_path)
    detail = {'code':'selfdevelop_blocked', 'blocking_task_id':'a'*32,
              'state':'waiting_review', 'revision':7,
              'reason':'Prior SelfDevelop task is not terminal',
              'required_action':'selfdevelop_review with the current revision'}
    monkeypatch.setattr(gateway.httpx, 'AsyncClient',
                        lambda **kwargs: FakeClient(json.dumps(detail)))
    result=asyncio.run(gateway.local('/api/selfdevelop/'+'b'*32+'/step',
                                     {'request_id':'smoke'}))
    assert result['code']=='selfdevelop_blocked'
    assert result['state']=='waiting_review' and result['status_code']==409
    assert result['blocking_task_id']==detail['blocking_task_id']
    assert result['revision']==7
    assert result['required_action']==detail['required_action']


def test_unrelated_conflict_still_raises(monkeypatch, tmp_path):
    (tmp_path/'hub.key').write_text('local-test-key', encoding='utf-8')
    monkeypatch.setattr(gateway,'STATE',tmp_path)
    monkeypatch.setattr(gateway.httpx,'AsyncClient',
                        lambda **kwargs: FakeClient('Other state conflict'))
    with pytest.raises(gateway.LocalStateConflict):
        asyncio.run(gateway.local('/api/development/control-plane/activate',
                                  {'request_id':'smoke'}))
