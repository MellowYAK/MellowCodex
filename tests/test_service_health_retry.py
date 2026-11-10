
from types import SimpleNamespace
from unittest.mock import Mock
from hub import service_health as h

def setup(monkeypatch,tmp_path):
 monkeypatch.setattr(h,'STATE',tmp_path);monkeypatch.setattr(h,'JOBS',tmp_path)
 monkeypatch.setattr(h.time,'sleep',lambda _:None)
 monkeypatch.setattr(h,'active_tasks',lambda:[])
 monkeypatch.setattr(h,'execute_controller',lambda *_:SimpleNamespace(returncode=0))
 job='a'*32;h.write(tmp_path/(job+'.json'),dict(id=job,action='Start',service='mcp',state='queued'))
 return job

def test_transient_unknown_rechecked_without_service_replay(monkeypatch,tmp_path):
 job=setup(monkeypatch,tmp_path)
 probe=Mock(side_effect=[{'sample':1},{'sample':2}])
 check=Mock(side_effect=[RuntimeError('unknown'),None])
 controller=Mock(return_value=SimpleNamespace(returncode=0))
 monkeypatch.setattr(h,'snapshot',probe);monkeypatch.setattr(h,'verify_result',check);monkeypatch.setattr(h,'execute_controller',controller)
 h.run(job);record=h.job_status(job)
 assert record['state']=='completed' and record['verification_attempt']==2
 assert controller.call_count==1

def test_persistent_unknown_fails_and_retains_evidence(monkeypatch,tmp_path):
 job=setup(monkeypatch,tmp_path)
 monkeypatch.setattr(h,'snapshot',lambda:{'state':'unknown'})
 check=Mock(side_effect=RuntimeError('ownership unknown'));monkeypatch.setattr(h,'verify_result',check)
 h.run(job);record=h.job_status(job)
 assert record['state']=='failed' and record['result']=={'state':'unknown'}
 assert check.call_count==3
