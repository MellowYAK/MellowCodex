import asyncio
import httpx
import pytest
from hub import model_providers as providers
from hub.model_catalog import ModelCatalog
from hub.store import Store


def test_metadata_filters_shards_and_projection_without_loading(monkeypatch):
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200,json={'sha':'revision','cardData':{'license':'apache-2.0'},'siblings':[
            {'rfilename':'model.Q4_K_M.gguf','lfs':{'size':123,'sha256':'abc'}},
            {'rfilename':'model-00001-of-00002.gguf'}, {'rfilename':'mmproj.gguf'},
            {'rfilename':'nested/model.gguf'}, {'rfilename':'script.py'}]})
    client=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(providers.details('owner/repo'))
    assert len(result['files'])==4
    assert [f['name'] for f in result['files'] if f['install_supported']]==['model.Q4_K_M.gguf']
    assert result['files'][0]['bytes']==123
    assert result['remote_code_allowed'] is False
    assert len(calls)==1 and 'huggingface.co/api/models/owner/repo' in calls[0]


def test_hf_provenance_survives_restart_and_direct_alias_rejected(tmp_path,monkeypatch):
    async def details(repo):return {'gated':False,'private':False,'revision':'v1','license':'mit','source_url':'https://huggingface.co/o/r','files':[{'name':'m.gguf','install_supported':True,'ollama_name':'hf.co/o/r:m.gguf'}]}
    monkeypatch.setattr(providers,'details',details)
    async def run():
        service=ModelCatalog(Store(tmp_path/'db'))
        with pytest.raises(ValueError,match='Hugging Face installer'):service.submit('hf.co/o/r:m.gguf','raw')
        job=await service.install_hf('o/r','m.gguf','approved')
        await service.cancel(job['id'])
        persisted=ModelCatalog(Store(tmp_path/'db')).jobs()[0]
        assert persisted['provenance']['revision']=='v1'
        assert persisted['provenance']['revision_pinned'] is False
        assert (await service.install_hf('o/r','m.gguf','approved'))['id']==job['id']
    asyncio.run(run())


def test_metadata_revision_change_never_claims_verified_install(tmp_path,monkeypatch):
    revisions=iter(['v1','v2'])
    async def details(repo):return {'gated':False,'private':False,'revision':next(revisions),'license':'mit','source_url':'https://huggingface.co/o/r','files':[{'name':'m.gguf','install_supported':True,'ollama_name':'hf.co/o/r:m.gguf'}]}
    monkeypatch.setattr(providers,'details',details)
    def handler(request):
        if request.url.path=='/api/pull':return httpx.Response(200,text='{"status":"success"}\n')
        return httpx.Response(200,json={'models':[{'name':'hf.co/o/r:m.gguf','digest':'actual'}]})
    client=httpx.AsyncClient
    monkeypatch.setattr('hub.model_catalog.httpx.AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    async def run():
        service=ModelCatalog(Store(tmp_path/'db'))
        await service.install_hf('o/r','m.gguf','change')
        await asyncio.gather(*service.active.values())
        assert service.jobs()[0]['state']=='failed'
        assert 'revision changed' in service.jobs()[0]['progress']['error']
    asyncio.run(run())
