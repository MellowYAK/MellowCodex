from hub.login_navigation import candidates,login_form

def element(name,type='Hyperlink',**fields):
    return {'name':name,'type':type,'enabled':True,**fields}

def test_login_discovery_prefers_observed_signin_and_excludes_browser_profile():
    state={'elements':[element('Microsoft Edge Profile, Please sign in','Button'),element('mail'),element('Menu','Button'),element('My account'),element('Continue',href='https://example.test/auth/login')]}
    found=candidates(state)
    assert found[0]['href']=='https://example.test/auth/login'
    assert [e['name'] for e in found]==['Continue','My account','Menu','mail']

def test_login_form_requires_fields_and_submit_not_homepage_or_addressbar():
    assert not login_form({'elements':[element('Address bar','Edit',value='https://example.test/login'),element('Login','Hyperlink')]})
    assert login_form({'elements':[element('Username','Edit'),element('Password','Edit',password=True),element('Sign in','Button')]})
    assert not login_form({'elements':[element('Search','Edit'),element('Sign in','Button')]})


def test_identifier_first_login_requires_observed_auth_route():
    controls=[element('מייל','Edit'),element('המשך','Button')]
    assert not login_form({'elements':controls})
    assert not login_form({'elements':controls+[element('Sign in',href='https://example.test/login')]})
    assert not login_form({'elements':controls+[element('Address bar','Edit',value='https://example.test/newsletter')]})
    assert login_form({'elements':controls+[element('Address and search bar','Edit',value='https://example.test/#/login')]})
    assert not login_form({'elements':[element('Email','Edit'),element('Continue','Button',enabled=False),element('Address bar','Edit',value='https://example.test/login')]})


def test_fragment_route_is_an_observed_login_clue():
    found=candidates({'elements':[element('Menu','Button'),element('mail',href='https://example.test/#/login')]})
    assert found[0]['name']=='mail' and found[0]['score']==100


def test_login_click_respects_physical_input_preference(monkeypatch,tmp_path):
    import asyncio
    from types import SimpleNamespace
    from hub.login_navigation import LoginNavigation
    control=element('Sign in','Button',ref='u1',bounds={'left':10,'top':20,'width':100,'height':40})
    async def inspect(hwnd):return {'id':'fresh-controls','elements':[control]}
    async def invoke(args):raise AssertionError('Physical mode must not invoke directly')
    sent=[]
    desktop=SimpleNamespace(stopped=False,focus=lambda hwnd:None,capture_target=lambda hwnd,folder:{'id':'fresh-image'},act=sent.append)
    runner=SimpleNamespace(desktop=desktop,accessibility=SimpleNamespace(inspect=inspect,act=invoke))
    monkeypatch.setattr('hub.preferences.load_input_mode',lambda state:'physical')
    asyncio.run(LoginNavigation(runner,{},tmp_path).click(42,{'id':'old'},control))
    assert sent==[{'action':'click','observation_id':'fresh-image','x':60,'y':40}]
