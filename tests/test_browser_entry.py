from hub.browser_entry import discover,repeated_history
from hub.navigation import require_observed_navigation
from hub.errors import ObservationError
import pytest
def test_entry_from_registered_readme_only(tmp_path):
    (tmp_path/'README.md').write_text('Studio http://127.0.0.1:4567/\nManager http://localhost:4568/\nSecret http://u:p@localhost:9999/\nToken http://localhost:9998/?token=private\nExternal https://example.com/\nAPI http://localhost:4567/api\n',encoding='utf-8')
    p={'id':'p','name':'Sample Studio','path':str(tmp_path)}
    result=discover([p],'sample studio')
    assert [x['url'] for x in result['entries']]==['http://127.0.0.1:4567/','http://localhost:4568/']
    assert result['health_verified'] is False
    assert result['entries'][0]['line']==1
    assert not discover([p,p],'Sample Studio')['entries']
    assert not discover([p],'unknown')['entries']
def test_entry_is_navigation_evidence_not_permission_to_guess():
    rows=[{'tool':'browser_tabs','result':{'tabs':[{'url':'about:blank'}]}},
          {'tool':'agent_environment','result':{'browser_entry':{'entries':[{'url':'http://localhost:4567/'}]}}}]
    require_observed_navigation('Open Sample Studio','http://localhost:4567/',rows)
    with pytest.raises(ObservationError):require_observed_navigation('Open Sample Studio','http://localhost:4567/login',rows)
def test_history_guard_preserves_pagination_and_changed_results():
    a={'tool':'conversation_history','args':{'query':'x'},'result':{'turns':[],'next_after':5}}
    assert repeated_history('conversation_history',a['args'],[a,a])
    assert not repeated_history('conversation_history',{'query':'x','after':5},[a,a])
    assert not repeated_history('conversation_history',a['args'],[a,{**a,'result':{'turns':[1]}}])
