import asyncio
import pytest
from hub.tools import ToolRunner
from hub.store import Store
from hub.engine import Engine
from hub.errors import DesktopUnavailable

def test_lock_defers_without_sending_input(tmp_path,monkeypatch):
    monkeypatch.setattr('hub.tools.session_status',lambda:{'interactive':False,'locked':True})
    runner=ToolRunner()
    monkeypatch.setattr(runner.desktop,'focus',lambda *a:pytest.fail('input must not run'))
    task={'id':'locked-test','workspace':str(tmp_path),'mode':'desktop'}
    with pytest.raises(DesktopUnavailable):
        asyncio.run(runner.execute(task,'focus_window',{'hwnd':1}))
    result=asyncio.run(runner.execute(task,'write_file',{'path':'background.txt','content':'works while locked'}))
    assert (tmp_path/'background.txt').read_text()=='works while locked'

def test_deferred_action_is_durable_and_resumes(tmp_path,monkeypatch):
    async def scenario():
        store=Store(tmp_path/'state.sqlite3')
        task=store.create('Desktop test',str(tmp_path),'desktop','desktop-test')
        engine=Engine(store)
        monkeypatch.setattr('hub.tools.session_status',lambda:{'interactive':False})
        async def chat(*args):
            return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'focus_window','arguments':{'hwnd':1}}}]},{}
        engine.chat=chat
        await engine.run(task['id'])
        assert store.get(task['id'])['state']=='waiting_desktop'
        assert store.actions(task['id'])[0]['result']['input_sent'] is False
        assert not any(a['state']=='pending' for a in store.actions(task['id']))
        resumed=[]
        engine.enqueue=lambda task_id:resumed.append(task_id)
        monkeypatch.setattr('hub.engine.session_status',lambda:{'interactive':True})
        monitor=asyncio.create_task(engine.watch_desktop())
        await asyncio.sleep(3.2)
        monitor.cancel()
        await asyncio.gather(monitor,return_exceptions=True)
        assert resumed==[task['id']]
        assert store.get(task['id'])['state']=='queued'
    asyncio.run(scenario())

def test_browser_dom_survives_unavailable_screenshot(tmp_path):
    from hub.browser import Browser
    class Page:
        url='http://localhost/fixture'
        async def evaluate(self,*args):
            return {'url':self.url,'text':'Visible document text','elements':[{'ref':'e1'}],'width':1280,'height':800}
        async def screenshot(self,**kwargs):
            raise RuntimeError('Renderer unavailable while hidden')
    async def scenario():
        browser=Browser()
        async def connect():return Page()
        browser.connect=connect
        result=await browser.observe(tmp_path)
        assert result['text']=='Visible document text'
        assert result['screenshot_available'] is False
        assert 'path' not in result
        assert browser.observation['refs']=={'e1'}
    asyncio.run(scenario())

def test_remote_input_rejects_stale_frame():
 from hub.browser import Browser
 from hub.errors import ObservationError
 import asyncio,time
 async def run():
  b=Browser();page=type('Page',(),{'url':'https://example.test/'})()
  async def connect():return page
  b.connect=connect
  b.remote_frame={'id':'new','page':page,'url':page.url,'at':time.monotonic(),'width':800,'height':600}
  with pytest.raises(ObservationError):await b.remote_input({'frame_id':'old','action':'click','x':10,'y':10})
  with pytest.raises(ObservationError):await b.remote_input({'frame_id':'new','action':'click','x':900,'y':10})
 asyncio.run(run())
