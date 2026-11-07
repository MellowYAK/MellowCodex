import asyncio
import pytest
from hub.browser import Browser
from hub.errors import ObservationError


def test_recovery_budget_does_not_reload_forever():
 async def run():
  browser=Browser()
  async def targets():return [{'id':'tab','url':'https://example.test/'}]
  browser.targets=targets
  import time
  browser.recoveries['tab']=[time.monotonic(),time.monotonic()]
  with pytest.raises(ObservationError,match='two recovery attempts'):
   await browser.recover_target('tab','Target crashed')
 asyncio.run(run())


def test_closed_tab_is_not_replaced_or_replayed():
 async def run():
  browser=Browser()
  async def targets():return []
  browser.targets=targets
  with pytest.raises(ObservationError,match='closed'):
   await browser.recover_target('gone','Target crashed')
  assert not browser.recoveries
 asyncio.run(run())


@pytest.mark.parametrize('native',[False,True])
def test_recovery_reloads_same_target_and_invalidates_observation(monkeypatch,native):
 async def run():
  import json
  browser=Browser();browser.observation={'id':'stale'}
  native_calls=[]
  if native:
   import time
   browser.recoveries['same']=[time.monotonic()]
  class Process:
   async def communicate(self):return b'{"requested":true}',b''
  async def spawn(*args,**kwargs):native_calls.append(args);return Process()
  monkeypatch.setattr('hub.browser.asyncio.create_subprocess_exec',spawn)
  sent=[];urls=[]
  class Socket:
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   async def send(self,data):sent.append(json.loads(data))
   async def recv(self):return json.dumps({'id':sent[-1]['id'],'result':{'result':{'value':True}}})
  def connect(url,**kw):urls.append(url);return Socket()
  async def targets():return [{'id':'same','url':'https://example.test/article'}]
  async def disconnect():browser.page=None
  async def sleep(_):pass
  browser.targets=targets;browser.disconnect=disconnect
  monkeypatch.setattr('websockets.connect',connect);monkeypatch.setattr('hub.browser.asyncio.sleep',sleep)
  await browser.recover_target('same','Target crashed')
  assert urls==['ws://127.0.0.1:9223/devtools/page/same']
  assert sent[0]==({'id':1,'method':'Runtime.enable'} if native else {'id':1,'method':'Page.reload','params':{'ignoreCache':False}})
  assert bool(native_calls)==native
  if native:assert native_calls[0][-3:]==('--reload-target','same','https://example.test/article')
  assert len(sent)==2 and sent[1]['method']=='Runtime.evaluate'
  assert browser.observation is None and browser.target_id=='same'
  assert browser.last_recovery['action']=='reload_same_tab'
 asyncio.run(run())


def test_tab_switch_does_not_evaluate_crashed_current_page():
 async def run():
  from types import SimpleNamespace
  browser=Browser();browser.page=object()
  healthy=SimpleNamespace(url='https://example.test/',is_closed=lambda:False)
  browser.connection=SimpleNamespace(contexts=[SimpleNamespace(pages=[healthy])])
  connections=[]
  async def connect(ready=True):
   connections.append(ready)
   if ready:assert browser.page is healthy;return healthy
  async def target_for(page):assert page is healthy;return 'healthy'
  async def targets():return [{'id':'healthy','url':healthy.url,'title':'Healthy'}]
  browser.connect=connect;browser.target_for=target_for;browser.targets=targets
  assert await browser.select_tab('healthy') is healthy
  assert connections==[False,True]
  assert browser.target_id=='healthy'
 asyncio.run(run())


def test_hidden_selected_page_gets_nonzero_viewport(tmp_path,monkeypatch):
 async def run():
  import json
  from types import SimpleNamespace
  (tmp_path/'browser-endpoint.json').write_text(json.dumps({'url':'http://127.0.0.1:9223','pid':123,'instance':'instance'}))
  monkeypatch.setattr('hub.browser.STATE',tmp_path)
  monkeypatch.setattr('hub.browser.psutil.pid_exists',lambda pid:True)
  sizes=[]
  class Page:
   url='https://example.test/'
   def is_closed(self):return False
   def set_default_timeout(self,n):pass
   async def evaluate(self,script):return {'width':0,'height':0}
   async def set_viewport_size(self,size):sizes.append(size)
  browser=Browser();page=Page();browser.page=page;browser.instance='instance'
  browser.connection=SimpleNamespace(is_connected=lambda:True,contexts=[SimpleNamespace(pages=[page])])
  async def target_for(p):assert p is page;return 'selected'
  browser.target_for=target_for
  prepared=[]
  async def prepare(target):prepared.append(target)
  browser.prepare_hidden_target=prepare
  assert await browser.connect() is page
  assert sizes==[{'width':1280,'height':800}]
  assert prepared==['selected']
 asyncio.run(run())
