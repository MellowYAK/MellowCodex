from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from hub import power as p
from hub import service_health as h

@pytest.fixture
def isolated(tmp_path,monkeypatch):
 monkeypatch.setattr(h,'STATE',tmp_path);monkeypatch.setattr(h,'JOBS',tmp_path/'jobs');h.JOBS.mkdir()
 for name,file in [('SETTINGS','power-settings.json'),('TRANSITION','power-transition.json'),('SESSION','agent-session-boot.json')]:monkeypatch.setattr(p,name,tmp_path/file)
 monkeypatch.setattr(p,'lock',nullcontext)
 monkeypatch.setattr(h.psutil,'boot_time',lambda:123.0)
 monkeypatch.setattr(h.time,'sleep',lambda _:None)
 return tmp_path

def job(action='ShutdownComputer'):
 key='a'*32;h.write(h.JOBS/(key+'.json'),dict(id=key,state='queued',action=action,service='all',confirm_tasks=True));return key

@pytest.mark.parametrize('action,flag',[('shutdown','/s'),('restart','/r')])
def test_order_at_most_once_and_nonforce(isolated,monkeypatch,action,flag):
 events=[]
 monkeypatch.setattr(p,'ember',lambda _:events.append('ember') or {'services':{'voice':{'running':False}}})
 monkeypatch.setattr(h,'execute_controller',lambda args,key:events.append('agent') or SimpleNamespace(returncode=0))
 monkeypatch.setattr(h,'snapshot',lambda:dict(services=[]))
 monkeypatch.setattr(h,'verify_result',lambda *args:events.append('verified'))
 monkeypatch.setattr(p,'close_desktop',lambda:events.append('desktop'))
 def os_run(args,**kwargs):
  assert args[1:]==[flag,'/t','0'] and '/f' not in args
  assert h.job_status(key)['power_dispatch_intent']
  events.append('windows');return SimpleNamespace(returncode=0)
 monkeypatch.setattr(p.subprocess,'run',os_run)
 key=job('ShutdownComputer' if action=='shutdown' else 'RestartComputer')
 h.run(key)
 assert events==['ember','agent','verified','desktop','windows']
 assert h.job_status(key)['state']=='windows_requested'
 h.run(key);assert events.count('windows')==1
 assert p.transition_active() and not p.recovery_allowed()

@pytest.mark.parametrize('stage',['ember','agent','verification','desktop'])
def test_failure_never_dispatches_windows(isolated,monkeypatch,stage):
 def fail(*args):raise RuntimeError('busy or unverified '+stage)
 monkeypatch.setattr(p,'ember',fail if stage=='ember' else lambda _:{'services':{}})
 monkeypatch.setattr(h,'execute_controller',fail if stage=='agent' else lambda *a:SimpleNamespace(returncode=0))
 monkeypatch.setattr(h,'snapshot',lambda:{})
 monkeypatch.setattr(h,'verify_result',fail if stage=='verification' else lambda *a:None)
 monkeypatch.setattr(p,'close_desktop',fail if stage=='desktop' else lambda:None)
 sink=Mock(side_effect=AssertionError('OS sink must not be reached'));monkeypatch.setattr(p.subprocess,'run',sink)
 key=job();h.run(key)
 assert h.job_status(key)['state']=='failed' and not sink.called

def test_disabled_startup_current_session_and_new_boot(isolated,monkeypatch):
 h.write(p.SETTINGS,dict(revision=1,start_with_windows=False))
 assert not p.recovery_allowed()
 p.manual_session();assert p.recovery_allowed()
 monkeypatch.setattr(h.psutil,'boot_time',lambda:124.0)
 assert not p.recovery_allowed()
 h.write(p.SETTINGS,dict(revision=2,start_with_windows=True))
 assert p.recovery_allowed()
 h.write(p.TRANSITION,dict(boot_time=124.0,state='draining'));assert not p.recovery_allowed()

def test_startup_cas_and_readback_failure_preserves_preference(isolated,monkeypatch):
 calls=[]
 def scheduler(action='Status'):
  calls.append(action);return dict(verified=True,exists=True,owned=True,enabled=action!='Disable')
 monkeypatch.setattr(p,'scheduled',scheduler);monkeypatch.setattr(h,'inventory',lambda:{})
 out=p.set_startup(True,0);assert out['revision']==1 and out['consistent']
 with pytest.raises(RuntimeError,match='revision'):p.set_startup(False,0)
 assert calls==['Enable','Status']
 monkeypatch.setattr(p,'scheduled',lambda *a:dict(owned=False,enabled=False))
 with pytest.raises(RuntimeError,match='readback'):p.set_startup(False,1)
 assert p.settings()==dict(schema_version=1,revision=1,start_with_windows=True)

def test_explicit_confirmation_and_live_guard(isolated,monkeypatch):
 monkeypatch.setattr(h,'active_tasks',lambda:[])
 sink=Mock();monkeypatch.setattr(h,'submit',sink)
 with pytest.raises(RuntimeError,match='confirmation'):p.submit('shutdown','request')
 assert not sink.called
 with pytest.raises(ValueError):p.submit('stop','request',True)
 p.submit('restart','request',True);sink.assert_called_once_with('RestartComputer','all','request',True)

def test_native_owner_classification_and_core_visibility(monkeypatch):
 from hub.owner_policy_adapter import classify
 from hub import tools
 runner=object.__new__(tools.ToolRunner);runner.application_targets={};runner.enabled_tool_groups={};runner.context_store=None
 for mode in ['code','desktop']:
  names={x['function']['name'] for x in runner.catalog(mode,'test')}
  assert {'computer_power','computer_power_preview','computer_power_status','agent_startup_status','agent_startup_set'}<=names
 assert classify('computer_power',{})[1] and classify('agent_startup_set',{})[1]

def test_offline_ui_cancel_never_submits(isolated,monkeypatch):
 import os
 os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
 from PySide6.QtWidgets import QApplication,QMessageBox
 from hub.service_health_ui import HealthPanel
 app=QApplication.instance() or QApplication([])
 monkeypatch.setattr(HealthPanel,'refresh',lambda self:None)
 panel=HealthPanel();panel.timer.stop()
 monkeypatch.setattr(panel,'dispatch',lambda fn,cb:cb(fn()))
 monkeypatch.setattr(p,'preview',lambda a:dict(action=a,active_tasks=[],blocker=None))
 monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.No)
 sink=Mock();monkeypatch.setattr(p,'submit',sink)
 panel.power_action('restart')
 assert not sink.called and not panel.busy
 assert len(panel.power_buttons)==3 and len(panel.buttons)==12
 panel.close()
