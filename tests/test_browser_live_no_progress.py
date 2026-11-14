import pytest
@pytest.mark.parametrize('name',['browser_tabs','agent_startup_status'])
def test_live_alternating_read_loop_is_bounded(name):
 from hub.browser_workflow import repeated_browser_reads
 read={'tool':name,'args':{},'state':'complete','result':{'state':'same'}}
 other={'tool':'browser_tabs' if name!='browser_tabs' else 'agent_startup_status','args':{},'state':'complete','result':{}}
 assert repeated_browser_reads(name,{},[read,other,read,other,read])
 changed=dict(read,result={'state':'new'})
 assert not repeated_browser_reads(name,{},[read,read,changed])
 navigation={'tool':'browser_navigate','state':'complete','result':{'id':'new'}}
 assert not repeated_browser_reads(name,{},[read,read,read,navigation])

def test_failed_navigation_is_bounded_but_new_url_remains_available():
 from hub.browser_workflow import repeated_browser_reads
 a={'tool':'browser_navigate','args':{'url':'http://localhost:8890/'},'state':'failed','result':{'error':'ERR_CONNECTION_REFUSED','exception_type':'Error'}}
 assert repeated_browser_reads('browser_navigate',a['args'],[a,a,a])
 assert not repeated_browser_reads('browser_navigate',{'url':'http://localhost:8891/'},[a,a,a])
