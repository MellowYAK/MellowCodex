"""The fast skill routes preserve exact owner gates and avoid model loops."""
import asyncio
import pytest
from fastapi import HTTPException
from hub import skill_shops
from hub.skill_shops_lifecycle import digest


def route(name):
    return next(x.endpoint for x in skill_shops.action_router().routes if getattr(x,'name',None)==name)


def test_fast_install_preserves_preview_and_immutable_commit(monkeypatch):
    monkeypatch.setattr(skill_shops,'_require_chat',lambda c:None)
    calls=[]
    class Fake:
        def preview(self,a,s,c):
            calls.append(('preview',a,s,c))
            return {'digest':'a'*64}
        async def commit(self,a,s,d,c):
            calls.append(('commit',a,s,d,c))
            return {'status':'installed','executed':True,'functional_test_passed':True}
    monkeypatch.setattr(skill_shops,'_marketplace',Fake())
    r=asyncio.run(route('fast_install')(skill_shops.ShopFastInstallRequest(slug='test_skill',chat_id='c'*32)))
    assert r['status']=='installed' and r['single_call'] is True
    assert calls[1][3]=='a'*64


def test_fast_run_refuses_unapproved_and_unknown_chat(monkeypatch):
    from hub import skill_shops_lifecycle
    class Fake:
        def _installed(self,n):return {'name':n,'version':'v','source_sha256':'sha'}
    monkeypatch.setattr(skill_shops,'_marketplace',Fake())
    monkeypatch.setattr(skill_shops,'_require_chat',lambda c:None)
    monkeypatch.setattr(skill_shops_lifecycle,'protected_authorize',lambda plan:{'allowed':False,'reason':'no_owner'})
    req=skill_shops.ShopFastRunRequest(name='computer_shutdown',chat_id='c'*32,arguments={'action':'preview'})
    r=asyncio.run(route('fast_run')(req))
    assert r['executed'] is False and r['status']=='needs_owner'
    def reject(c):raise HTTPException(404,'Chat not found')
    monkeypatch.setattr(skill_shops,'_require_chat',reject)
    with pytest.raises(HTTPException) as e:asyncio.run(route('fast_run')(req))
    assert e.value.status_code==404


def test_fast_run_uses_verified_existing_extension_after_owner(monkeypatch):
    from hub import skill_shops_lifecycle,extensions
    class Fake:
        def _installed(self,n):return {'name':n,'version':'v','source_sha256':'sha'}
    monkeypatch.setattr(skill_shops,'_marketplace',Fake())
    monkeypatch.setattr(skill_shops,'_require_chat',lambda c:None)
    monkeypatch.setattr(skill_shops_lifecycle,'protected_authorize',
                        lambda plan:{'allowed':True,'server_identity_verified':True,
                                     'approved_action_digest':digest(plan)})
    observed=[]
    async def run(self,t,n,a):
        observed.append((n,a))
        return {'exit_code':0,'stdout':'{}','stderr':'','version':'v'}
    monkeypatch.setattr(extensions.Extensions,'run',run)
    r=asyncio.run(route('fast_run')(skill_shops.ShopFastRunRequest(name='computer_shutdown',
         chat_id='c'*32,arguments={'action':'preview'})))
    assert r['status']=='executed' and r['duration_ms']>=0
    assert observed==[('computer_shutdown',{'action':'preview'})]
