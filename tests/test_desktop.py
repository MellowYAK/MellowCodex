import time
from types import SimpleNamespace
import pytest
from hub.desktop import Desktop

class FakeUser:
    def GetForegroundWindow(self):
        return 123
    def GetCursorPos(self,ptr):
        ptr._obj.x=500
        ptr._obj.y=500
    def SetCursorPos(self,x,y):
        self.cursor=(x,y)

def test_locked_foreground_uses_window_capture_without_input(monkeypatch, tmp_path):
    desktop=Desktop();desktop.user=FakeUser();desktop.target_hwnd=123
    monkeypatch.setattr('hub.desktop.session_status',lambda:{'interactive':False,'locked':True})
    calls=[]
    desktop._capture_window=lambda path,hwnd:(calls.append(hwnd) or {'left':0,'top':0,'width':100,'height':80})
    result=desktop.capture_target(123,tmp_path)
    assert calls==[123]
    assert result['backend']=='target-window-printwindow'
    assert result['input_ready'] is False
    assert desktop.observation is None

def test_failed_foreground_capture_tries_target_window(monkeypatch,tmp_path):
    import mss,win32gui
    desktop=Desktop();desktop.user=FakeUser();desktop.target_hwnd=123
    monkeypatch.setattr('hub.desktop.session_status',lambda:{'interactive':True})
    monkeypatch.setattr(win32gui,'GetWindowRect',lambda hwnd:(0,0,100,80))
    def unavailable():raise RuntimeError('GDI unavailable')
    monkeypatch.setattr(mss,'MSS',unavailable)
    desktop._capture_window=lambda path,hwnd:{'left':0,'top':0,'width':100,'height':80}
    result=desktop.capture_target(123,tmp_path)
    assert result['backend']=='target-window-printwindow'
    assert result['screen_capture_error']=='GDI unavailable'
    assert not result['input_ready']

@pytest.fixture
def desktop():
    d=Desktop()
    d.user=FakeUser()
    d._owned_by=lambda hwnd,target:False
    d.observation={'id':'fresh','hwnd':123,'captured':time.monotonic(),'left':0,'top':0,'width':1920,'height':1080}
    d.sent=[]
    d._send=lambda kind,**args:d.sent.append((kind,args))
    return d

def test_stale_observation_blocks_input(desktop):
    desktop.observation['captured']-=60
    with pytest.raises(ValueError):
        desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})
    assert not desktop.sent

def test_changed_foreground_blocks_input(desktop):
    desktop.observation['hwnd']=999
    with pytest.raises(ValueError):
        desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})

def test_wrong_target_blocks_input_even_if_foreground_stable(desktop):
    desktop.target_hwnd=999
    with pytest.raises(ValueError):
        desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})
    assert not desktop.sent

def test_observation_consumed_and_click_releases(desktop):
    desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})
    assert [s[1]['flags'] for s in desktop.sent]==[2,4]
    with pytest.raises(ValueError):
        desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})

def test_outside_coordinates_rejected(desktop):
    with pytest.raises(ValueError):
        desktop.act({'observation_id':'fresh','action':'click','x':2000,'y':100})
    assert not desktop.sent

def test_unicode_surrogates_have_matching_keyup(desktop):
    desktop.act({'observation_id':'fresh','action':'type','text':'שלום🙂'})
    assert len(desktop.sent)==12
    assert [s[1]['flags'] for s in desktop.sent]==[4,6]*6

def test_emergency_stop_blocks_input(desktop):
    desktop.stopped=True
    with pytest.raises(RuntimeError):
        desktop.act({'observation_id':'fresh','action':'click','x':100,'y':100})
    assert not desktop.sent

def test_multiline_unicode_uses_real_enter_and_keeps_surrogates(desktop,monkeypatch):
    delays=[];monkeypatch.setattr('hub.desktop.time.sleep',delays.append)
    desktop.act({'observation_id':'fresh','action':'type','text':'א\r\n🙂'})
    assert desktop.sent[2][1]=={'vk':13}
    assert desktop.sent[3][1]=={'vk':13,'flags':2}
    assert len(delays)==3
    assert [event[1].get('scan') for event in desktop.sent[-4:]]==[0xD83D,0xD83D,0xDE42,0xDE42]
