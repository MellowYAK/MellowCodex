from types import SimpleNamespace
from unittest.mock import Mock
import time
import pytest
from hub import service_health as h
from hub import health_diagnostics as d

@pytest.fixture
def isolated(tmp_path,monkeypatch):
 monkeypatch.setattr(h,'STATE',tmp_path);monkeypatch.setattr(h,'JOBS',tmp_path/'jobs')
 monkeypatch.setattr(h,'_snapshot_cache',None)
 return tmp_path

def test_connectors_independent_stale_not_disconnected_and_ordering(isolated):
 now=time.time()
 d.observe(h,'mellowcodex','success',now)
 d.observe(h,'guard','oauth_token_invalid_grant',now)
 assert d.connector(h,'mellowcodex')['status']=='operational'
 assert d.connector(h,'guard')['status']=='reauthentication_required'
 d.observe(h,'guard','success',now-10)
 assert d.connector(h,'guard')['status']=='reauthentication_required'
 c=d.connector(h,'mellowcodex',now+121)
 assert c['status']=='stale' and c['last_success_at']==now

def test_transport_invalidation_retains_last_success(isolated):
 now=time.time();d.observe(h,'mellowcodex','success',now)
 h.write(isolated/'connector-invalidated-mellowcodex.json',{'checked_at':now+1})
 c=d.connector(h,'mellowcodex',now+2)
 assert c['status']=='stale' and c['last_success_at']==now

def test_guard_coverage_not_api_failure_and_model_disabled(isolated):
 h.write(isolated/'model-settings.json',{'inference_enabled':False})
 now=time.time()
 data=dict(checked_at=now,manual_stop=False,agent_manual_stop=False,network={'state':'available'},guard_supervisor={'healthy':False,'started_pids':[]},
 services=[dict(id='guard',state='warning',reason='coverage',checked_at=now,mcp_api_verified=True),dict(id='model',state='idle',loaded=False,reason='unloaded',checked_at=now)])
 out=d.enrich(h,data)
 assert out['services'][0]['status']=='operational'
 assert out['services'][0]['dimensions']['supervisor']['healthy'] is False
 assert out['services'][1]['status']=='intentionally_stopped'

def test_repair_plan_respects_stops_unknown_ownership_and_network():
 rows=[dict(id='gateway',state='available',status='operational'),dict(id='guard',state='stopped',status='intentionally_stopped'),dict(id='relay',state='stopped',status='failed'),dict(id='hub',state='unknown',port_open=True)]
 steps=d.plan({'services':rows,'network':{'ssh_reachable':False}},'all')
 assert not any(x['outcome']=='repair' for x in steps)
 assert steps[0]['outcome']=='unchanged'
 assert steps[1]['reason']=='Owner stop marker preserved'

def test_reset_preserves_data_stop_markers_and_uncertain_actions(isolated,monkeypatch):
 h.JOBS.mkdir();job='a'*32
 h.write(h.JOBS/(job+'.json'),dict(id=job,state='running',created_at=0))
 for name in ['hub.sqlite3','hub.key','mcp-manual-stop','agent-manual-stop','health-snapshot.json']:
  (isolated/name).write_text('preserve')
 monkeypatch.setattr(h,'worker_alive',lambda _:False)
 result=d.reset(h,'b'*32)
 assert result['changed_operation_ids']==[job]
 assert h.job_status(job)['state']=='interrupted'
 assert not (isolated/'health-snapshot.json').exists()
 assert all((isolated/n).read_text()=='preserve' for n in ['hub.sqlite3','hub.key','mcp-manual-stop','agent-manual-stop'])

def test_reconnect_never_restarts_transport(isolated,monkeypatch):
 h.JOBS.mkdir();job='b'*32
 h.write(h.JOBS/(job+'.json'),dict(id=job,action='Reconnect',service='guard',state='queued'))
 monkeypatch.setattr(h.time,'sleep',lambda _:None);monkeypatch.setattr(h,'snapshot',lambda:{'services':[]})
 execute=Mock();monkeypatch.setattr(h,'execute_controller',execute)
 h.run(job)
 assert not execute.called
 assert h.job_status(job)['reconnect']['connector']=='guard'
 assert h.job_status(job)['outcome']=='requires_user_action'

def test_repair_network_failure_has_no_restart_loop(isolated,monkeypatch):
 h.JOBS.mkdir();job='c'*32
 h.write(h.JOBS/(job+'.json'),dict(id=job,action='Repair',service='mcp',state='queued'))
 monkeypatch.setattr(h.time,'sleep',lambda _:None)
 monkeypatch.setattr(h,'snapshot',lambda:{'services':[dict(id='gateway',state='available',status='operational'),dict(id='relay',state='stopped',status='failed')],'network':{'ssh_reachable':False}})
 execute=Mock();monkeypatch.setattr(h,'execute_controller',execute)
 h.run(job)
 assert not execute.called and h.job_status(job)['outcome']=='requires_user_action'

def test_offline_ui_per_service_actions_and_old_response_rejected(monkeypatch):
 import os
 os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
 from PySide6.QtWidgets import QApplication
 from hub.service_health_ui import HealthPanel
 app=QApplication.instance() or QApplication([])
 monkeypatch.setattr(HealthPanel,'refresh',lambda self:None)
 panel=HealthPanel();panel.timer.stop()
 data=dict(checked_at=time.time(),services=[dict(id='broker',name='OwnerBroker',description='owner',state='unknown',status='unverified',reason='not checked',checked_at=time.time())],network={'reason':'offline'},connectors={'guard':dict(status='unverified')},overall_status='unverified',manual_stop=False)
 panel.render(data)
 assert panel.table.columnCount()==7 and panel.table.cellWidget(0,6)
 assert all(not b.isEnabled() for b,k,a in panel.row_buttons if a!='Check')
 newer=panel.rendered_at;panel.render({**data,'checked_at':newer-10})
 assert panel.rendered_at==newer
 assert len(panel.buttons)==12
 panel.close()
