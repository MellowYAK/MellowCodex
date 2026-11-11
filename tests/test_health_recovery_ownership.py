from types import SimpleNamespace
from unittest.mock import patch,Mock
import pytest
from hub import service_health as h

def test_missing_accepting_pid_retries_observation_only():
 probe=Mock(side_effect=[(True,set()),(True,{10})])
 with patch.object(h,'active_tasks',return_value=[]),patch.object(h,'config',return_value={}),patch.object(h,'inventory',return_value={'gateway':[{'pid':10,'owned':True}]}),patch.object(h,'port_identity',probe),patch.object(h.time,'sleep'):
  assert h.preflight('Stop','gateway')['accepted']
 assert probe.call_count==2

def test_foreign_accepting_pid_never_retried_or_adopted():
 probe=Mock(return_value=(True,{99}))
 with patch.object(h,'active_tasks',return_value=[]),patch.object(h,'config',return_value={}),patch.object(h,'inventory',return_value={'gateway':[{'pid':10,'owned':True}]}),patch.object(h,'port_identity',probe):
  with pytest.raises(RuntimeError,match='ownership'):h.preflight('Stop','gateway')
 assert probe.call_count==1

def test_guard_restart_requires_its_stopped_dependencies():
 result={'services':[dict(id='guard',owned=True,mcp_api_verified=True),dict(id='guard_gateway',owned=True,http_status=200),dict(id='relay',owned=False,process_exists=False)]}
 with pytest.raises(RuntimeError,match='relay'):h.verify_result('Restart','guard',result)
 result['services'][2].update(owned=True,process_exists=True)
 h.verify_result('Restart','guard',result)
