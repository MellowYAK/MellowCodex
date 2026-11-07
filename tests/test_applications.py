import pytest
from hub.applications import matching,Applications
import asyncio

def test_application_matching_is_generic():
 apps=[{'name':'Adobe Photoshop','executable':'C:/Apps/Photoshop.exe'},{'name':'Microsoft Edge','executable':'C:/Apps/msedge.exe'},{'name':'Google Chrome','executable':'C:/Apps/chrome.exe'}]
 for query,exe in [('Photoshop','Photoshop.exe'),('Edge','msedge.exe'),('Chrome','chrome.exe')]:
  assert len(matching(query,apps))==1
  assert matching(query,apps)[0]['executable'].endswith(exe)
 assert matching('Not installed',apps)==[]

def test_open_does_not_claim_success_when_session_locked(monkeypatch):
 class Desktop:
  def focus(self,*a):pytest.fail('must not focus locked desktop')
 app=Applications(Desktop(),None)
 async def find(q):return {'windows':[{'hwnd':123}],'installed':[]}
 app.find=find
 monkeypatch.setattr('hub.session.session_status',lambda:{'interactive':False})
 result=asyncio.run(app.open('Any application'))
 assert result['opened_verified'] is False


def test_native_browser_url_uses_identified_executable_and_verifies_address(monkeypatch):
 from types import SimpleNamespace
 window={'hwnd':12,'executable':'C:/Apps/chrome.exe','title':'Requested site - Google Chrome'}
 class Desktop:
  def windows(self):return [window]
 class Access:
  async def inspect(self,hwnd):return {'elements':[{'type':'Edit','value':'www.example.com/path'}]}
 app=Applications(Desktop(),Access())
 async def find(query):return {'windows':[],'installed':[{'executable':'C:/Apps/chrome.exe'}]}
 async def sleep(_):pass
 app.find=find;launched=[]
 monkeypatch.setattr('hub.session.session_status',lambda:{'interactive':True})
 monkeypatch.setattr('hub.applications.subprocess.Popen',lambda argv:launched.append(argv))
 monkeypatch.setattr('hub.applications.asyncio.sleep',sleep)
 result=asyncio.run(app.open('Chrome','https://www.example.com/path'))
 assert launched==[['C:/Apps/chrome.exe','https://www.example.com/path']]
 assert result['opened_verified'] and result['observed_url']=='www.example.com/path'


def test_reopening_same_native_url_reuses_existing_tab(monkeypatch):
 window={'hwnd':12,'executable':'C:/Apps/msedge.exe','title':'Page - Edge'}
 class Access:
  async def inspect(self,hwnd):return {'title':'Page - Edge','elements':[{'type':'Edit','value':'https://example.com/'}]}
 app=Applications(None,Access())
 async def find(q):return {'windows':[window],'installed':[{'executable':'C:/Apps/msedge.exe'}]}
 app.find=find
 monkeypatch.setattr('hub.session.session_status',lambda:{'interactive':True})
 monkeypatch.setattr('hub.applications.subprocess.Popen',lambda *a:pytest.fail('Must not create a duplicate tab'))
 result=asyncio.run(app.open('Edge','https://example.com/'))
 assert result['reused_existing'] and result['opened_verified']


def test_native_target_cannot_silently_navigate_embedded_browser(tmp_path):
 from hub.tools import ToolRunner
 from hub.errors import ObservationError
 runner=ToolRunner();runner.application_targets['native-task']='Google Chrome'
 with pytest.raises(ObservationError,match='different application'):
  asyncio.run(runner.execute({'id':'native-task','workspace':str(tmp_path),'mode':'desktop'},'browser_navigate',{'url':'https://example.com/'}))


def test_normal_close_keeps_unsaved_dialog_and_never_force_kills(monkeypatch):
 from types import SimpleNamespace
 calls=[]
 class Function:
  def __init__(self,callback):self.callback=callback
  def __call__(self,*args):return self.callback(*args)
 window={'hwnd':42,'executable':'C:/Apps/editor.exe','title':'Unsaved document'}
 user=SimpleNamespace(GetAncestor=Function(lambda hwnd,kind:42),PostMessageW=Function(lambda *args:calls.append(args) or True))
 class Desktop:
  def windows(self):return [window]
 monkeypatch.setattr('ctypes.WinDLL',lambda *a,**k:user)
 desktop=Desktop();desktop.user=user;app=Applications(desktop,None)
 async def find(q):return {'windows':[window],'installed':[{'executable':window['executable']}],'process_count':1}
 async def sleep(_):pass
 app.find=find
 monkeypatch.setattr('hub.preferences.load_input_mode',lambda state:'quiet')
 monkeypatch.setattr('hub.applications.asyncio.sleep',sleep)
 result=asyncio.run(app.close('Editor'))
 assert not result['closed_verified'] and result['windows']==[window]
 assert calls==[(42,0x0010,0,0)]


def test_unknown_process_title_prevents_verified_absence(monkeypatch):
 from hub import applications
 monkeypatch.setattr(applications,'installed_apps',lambda:[])
 monkeypatch.setattr(applications.psutil,'process_iter',lambda attrs:[])
 class Desktop:
  def windows(self):return [{'hwnd':99,'title':'Welcome - Example Editor','process':'','executable':''}]
 result=asyncio.run(Applications(Desktop(),None).find('Example Editor'))
 assert not result['absence_verified']
 assert result['unresolved_windows'][0]['hwnd']==99
