import asyncio
import httpx
import pytest
from hub import model_memory as mm
from hub.model_settings import ModelSettings

@pytest.fixture
def memory(monkeypatch,tmp_path):
    monkeypatch.setattr('hub.resources.STATE',tmp_path)
    state={'settings':ModelSettings(model='old'),'loaded':{'old:latest'},'calls':[],'fail':False}
    monkeypatch.setattr(mm,'load_settings',lambda:state['settings'])
    monkeypatch.setattr(mm,'save_settings',lambda s:state.update(settings=s))
    def handler(request):
        if request.url.path=='/api/ps':return httpx.Response(200,json={'models':[{'name':n,'size_vram':100} for n in state['loaded']]})
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':n} for n in ['old:latest','new:latest']]})
        import json
        body=json.loads(request.content);state['calls'].append(body)
        if state['fail'] and body['keep_alive']:return httpx.Response(500,text='out of memory')
        name=body['model'] if ':' in body['model'] else body['model']+':latest'
        if body['keep_alive']:state['loaded'].add(name)
        else:state['loaded'].discard(name)
        return httpx.Response(200,json={})
    client=httpx.AsyncClient
    monkeypatch.setattr(mm.httpx,'AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    return state

def test_switch_loads_and_persists(memory):
    result=asyncio.run(mm.control('switch','new:latest'))
    assert result['verified'] and result['memory']['selected_model']=='new:latest'
    assert memory['loaded']=={'new:latest'}
    assert [c['keep_alive'] for c in memory['calls']]==[0,1800]

def test_failed_switch_preserves_selection(memory):
    memory['fail']=True
    with pytest.raises(httpx.HTTPStatusError):asyncio.run(mm.control('switch','new:latest'))
    assert memory['settings'].model=='old'

def test_missing_model_never_mutates(memory):
    with pytest.raises(ValueError):asyncio.run(mm.control('switch','missing'))
    assert not memory['calls'] and memory['loaded']=={'old:latest'}

def test_unload_all_and_reload(memory):
    memory['loaded'].add('new:latest')
    assert asyncio.run(mm.control('unload_all'))['verified']
    assert not memory['loaded']
    assert asyncio.run(mm.control('load'))['verified']
    assert memory['loaded']=={'old:latest'}


def test_unload_disables_inference_until_load(memory):
    assert asyncio.run(mm.control('unload'))['verified']
    assert not memory['settings'].inference_enabled
    asyncio.run(mm.status())
    assert not memory['settings'].inference_enabled
    assert asyncio.run(mm.control('load'))['verified']
    assert memory['settings'].inference_enabled
