import asyncio
import time
from types import SimpleNamespace
import pytest
from hub.browser import Browser, CLICK_JS
from hub.errors import ObservationError

@pytest.mark.parametrize('fail_drag',[False,True])
def test_virtual_drag_releases_button_and_invalidates_frame(fail_drag):
 async def run():
  calls=[]
  class Session:
   async def send(self,method,args):
    calls.append((args['type'],args))
    if args['type']=='mouseMoved' and args['buttons'] and fail_drag:raise RuntimeError('renderer failed')
   async def detach(self):calls.append(('detach',{}))
  class Context:
   async def new_cdp_session(self,page):return Session()
  page=SimpleNamespace(url='https://example.test/',context=Context())
  browser=Browser()
  async def connect():return page
  browser.connect=connect
  browser.remote_frame={'id':'frame','page':page,'url':page.url,'at':time.monotonic(),'width':400,'height':300,'regions':{'start':{'x':10,'y':20,'width':20,'height':20},'end':{'x':100,'y':120,'width':20,'height':20}}}
  args={'frame_id':'frame','action':'drag','ref':'start','end_ref':'end'}
  if fail_drag:
   with pytest.raises(RuntimeError):await browser.remote_input(args)
  else:
   result=await browser.remote_input(args)
   assert result['input_sent'] and result['physical_pointer_used'] is False and result['verification_required']
  assert calls[-2][0]=='mouseReleased' and calls[-1][0]=='detach' and browser.remote_frame is None
  assert calls[0][1]['x']==20 and calls[0][1]['y']==30
  assert calls[-2][1]['x']==110 and calls[-2][1]['y']==130
  with pytest.raises(ObservationError):await browser.remote_input(args)
 asyncio.run(run())

def test_frame_normalizes_device_pixels_to_pointer_coordinates():
 import base64
 from io import BytesIO
 from PIL import Image
 async def run():
  raw=BytesIO();Image.new('RGB',(80,40)).save(raw,'JPEG')
  class Page:
   url='https://example.test/'
   async def screenshot(self,**kwargs):return raw.getvalue()
   async def title(self):return 'Test'
   async def evaluate(self,script,*args):
    if 'width:innerWidth' in script:return {'width':40,'height':20}
    if script.startswith('token =>'):return {'elements':[]}
    return []
  browser=Browser();page=Page()
  async def connect():return page
  browser.connect=connect
  result=await browser.frame()
  image=Image.open(BytesIO(base64.b64decode(result['image'].split(',')[1])))
  assert image.size==(result['width'],result['height'])==(40,20)
 asyncio.run(run())

def test_virtual_drag_rejects_outside_before_input():
 async def run():
  page=SimpleNamespace(url='https://example.test/')
  browser=Browser()
  async def connect():return page
  browser.connect=connect
  browser.remote_frame={'id':'frame','page':page,'url':page.url,'at':time.monotonic(),'width':400,'height':300}
  with pytest.raises(ObservationError,match='endpoint'):
   await browser.remote_input({'frame_id':'frame','action':'drag','x':10,'y':20,'end_x':900,'end_y':120})
  assert browser.remote_frame is not None
 asyncio.run(run())


@pytest.mark.parametrize('blocked',[True,False])
def test_dom_click_is_once_and_post_capture_failure_does_not_erase_input(blocked,tmp_path):
 async def run():
  called=[]
  class Target:
   async def count(self):return 1
   async def is_visible(self):return True
   async def evaluate(self,script):
    assert script==CLICK_JS
    called.append(1)
    return {'invoked':not blocked,'reason':'Overlay covers control'}
  page=SimpleNamespace(url='https://example.test/',locator=lambda _:Target())
  browser=Browser()
  browser.observation={'id':'fresh','at':time.monotonic(),'page':page,'url':page.url,'refs':['e1']}
  async def connect():return page
  async def observe(folder):raise RuntimeError('Renderer lost after input')
  browser.connect=connect;browser.observe=observe
  if blocked:
   with pytest.raises(ObservationError,match='Overlay'):await browser.act({'action':'click','observation_id':'fresh','ref':'e1'},tmp_path)
  else:
   result=await browser.act({'action':'click','observation_id':'fresh','ref':'e1'},tmp_path)
   assert result['input_sent'] and result['verified'] is False
   assert 'Renderer lost' in result['observation_error']
  assert called==[1] and browser.observation is None
 asyncio.run(run())
