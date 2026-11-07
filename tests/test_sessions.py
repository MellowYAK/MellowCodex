import pytest
from hub.session_transfer import validate_transfer,Pairing

def test_pairing_one_time_and_expiry():
    pairing=Pairing();code=pairing.issue()['code'];pairing.consume(code)
    with pytest.raises(ValueError):pairing.consume(code)
    code=pairing.issue()['code'];pairing.codes[code]=0
    with pytest.raises(ValueError):pairing.consume(code)

def test_cross_site_cookies_rejected():
    with pytest.raises(ValueError):validate_transfer({'url':'https://example.com','cookies':[{'name':'x','value':'secret','domain':'other.example'}]})

def test_http_only_and_storage_preserved_without_logging():
    result=validate_transfer({'url':'https://app.example.com','cookies':[{'name':'session','value':'synthetic','domain':'.example.com','httpOnly':True,'secure':True,'sameSite':'no_restriction','session':True}],'localStorage':{'a':'b'}})
    assert result['cookies'][0]['httpOnly'] and result['cookies'][0]['sameSite']=='None'
    assert 'expires' not in result['cookies'][0]
    assert result['localStorage']=={'a':'b'}

def test_partitioned_cookies_explicitly_skipped():
    result=validate_transfer({'url':'https://example.com','cookies':[{'name':'x','value':'synthetic','domain':'example.com','partitionKey':{'topLevelSite':'https://example.com'}}]})
    assert result['skipped_partitioned']==1 and result['cookies']==[]

def test_browser_tools_available_in_full_mode():
    from hub.tools import ToolRunner
    names={tool['function']['name'] for tool in ToolRunner().catalog('desktop')}
    assert {'browser_navigate','browser_act','desktop_action','run_shell'}<=names
