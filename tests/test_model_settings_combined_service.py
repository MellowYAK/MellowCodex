import asyncio
from hub import model_preferences as service
from hub.model_settings import ModelSettings
from test_model_preferences_chat import FakeClient

def test_set_both_runs_without_exception(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service.httpx,'AsyncClient',FakeClient)
    service.save_settings(ModelSettings(model='local-test'),tmp_path)
    result=asyncio.run(service.perform(text='הגדר את שניהם ל־16000'))
    assert result.get('accepted') is True, result
