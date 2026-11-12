
from types import SimpleNamespace
from unittest.mock import patch
import json
import pytest
from hub import service_health as h

def test_foreign_accepting_pid_rejected_before_mutation():
 with patch.object(h,'active_tasks',return_value=[]),patch.object(h,'config',return_value={}),patch.object(h,'inventory',return_value={'gateway':[{'pid':10,'owned':True}]}),patch.object(h,'port_identity',return_value=(True,{99})):
  with pytest.raises(RuntimeError,match='ownership'):h.preflight('Stop','gateway')

def test_all_requires_confirmation_and_busy_single_service_refused():
 with pytest.raises(RuntimeError,match='confirmation'):h.preflight('Stop','all')
 with patch.object(h,'active_tasks',return_value=[{'id':'busy'}]):
  with pytest.raises(RuntimeError,match='Active tasks'):h.preflight('Restart','hub')

def test_connection_nonce_expiry_and_replay(tmp_path):
 with patch.object(h,'STATE',tmp_path):
  n=h.challenge()['nonce'];assert h.acknowledge(n)['verified']
  with pytest.raises(ValueError):h.acknowledge(n)
  h.write(tmp_path/'mcp-health-challenge.json',{'nonce':'old','created_at':0})
  with pytest.raises(ValueError):h.acknowledge('old')

def test_worker_pid_reuse_is_not_live():
 proc=SimpleNamespace(create_time=lambda:999,cmdline=lambda:['python','-m','hub.service_health','--run','x'])
 with patch.object(h.psutil,'Process',return_value=proc):
  assert not h.worker_alive({'worker_pid':5,'worker_created_at':100,'id':'x'})

def test_live_network_not_inferred_from_open_port(tmp_path):
 def response(url):
  return (200,{'models':[]}) if '/api/ps' in url else (200,{})
 with patch.object(h,'STATE',tmp_path),patch.object(h,'config',return_value={}),patch.object(h,'inventory',return_value={}),patch.object(h,'port_identity',return_value=(True,set())),patch.object(h,'api',side_effect=response),patch.object(h,'guard_status',return_value={'state':'unknown'}),patch.object(h,'relay_status',return_value={'state':'unknown','reason':'no receipt'}),patch.object(h,'network',return_value={'state':'unknown'}),patch.object(h,'active_tasks',return_value=[]),patch.object(h,'ps',return_value=SimpleNamespace(stdout='{"State":3}')):
  data=h.snapshot()
  assert data['remote']['state']=='unknown'
  assert next(x for x in data['services'] if x['id']=='gateway')['state']=='unknown'
  assert next(x for x in data['services'] if x['id']=='model')['state']=='idle'

def test_unicode_ui_and_no_server_dependency():
 from pathlib import Path
 p=Path(h.__file__).with_name('service_health_ui.py')
 source=p.read_text(encoding='utf8')
 assert sum('\u0590'<=x<='\u05ff' for x in source)>500
 assert 'from . import service_health as health' in source
