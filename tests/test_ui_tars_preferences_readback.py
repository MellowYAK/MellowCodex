import asyncio
from hub import model_preferences as p
from hub.model_settings import ModelSettings
def test_browser_status_is_not_primary_model_loaded_status(monkeypatch):
 s=ModelSettings(browser_driver='ui_tars')
 async def fake():
  return dict(settings=s.model_dump(),model=s.model,effective=None,effective_source='model_not_loaded',reload_required=False,runtime_available=True,metadata={},browser_driver='ui_tars',browser_runtime={'available':True,'model':'ui-tars-local'})
 monkeypatch.setattr(p,'load_settings',lambda *args:s)
 monkeypatch.setattr(p,'status',fake)
 result=asyncio.run(p.perform(field='browser_driver'))
 assert result['saved']=='ui_tars' and result['browser_runtime']['available']
 assert result['effective_source']=='model_not_loaded'
