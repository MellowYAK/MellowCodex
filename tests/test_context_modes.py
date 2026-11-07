import asyncio
import pytest
from test_context_integration import service
from hub.context.indexing import Indexing
from hub.context.api import dispatch, ContextRequest


def test_exact_requested_indexed_path_precedes_model_navigation():
    from types import SimpleNamespace
    from hub.context.exploration import seed_navigation
    calls=[];events=[]
    async def chat(*args,**kwargs):raise AssertionError('Exact source path needs no query invention')
    async def read(name,args):calls.append((name,args));return {'text':'value=1'}
    engine=SimpleNamespace(chat=chat,store=SimpleNamespace(event=lambda *args:events.append(args)))
    asyncio.run(seed_navigation(engine,{'id':'t','goal':'Read-only: inspect pkg/request.py validation'},read,
        {'navigation_tree':{'directories':{'pkg':['request.py','request.py.old','other.py']}}}))
    assert calls==[('context_expand',{'ref':'pkg/request.py','lines':60})]
    assert events[0][2]['explicit_paths']==['pkg/request.py']


def test_switch_preserves_baseline_and_routes_search_and_handles(tmp_path):
    svc,p,_=service(tmp_path);pid=p['id'];root=tmp_path/'project'
    (root/'large.py').write_text('# padding\n'*8000+'\ndef tail_feature(): return 1\n')
    svc.refresh(pid);svc.annotate(pid,'a.py',aliases=['apc_only'],origin='apc:fixture')
    baseline=svc.path.read_bytes()
    queue=Indexing(svc);queue.settings(pid,False,'fast');asyncio.run(queue.once())
    fast=queue.selected(pid)
    assert fast.path!=svc.path
    assert svc.path.read_bytes()==baseline
    assert not fast.search(pid,'apc_only')['results']
    hit=dispatch(svc,'search',ContextRequest(project_id=pid,query='tail_feature'))['results'][0]
    assert hit['matches'][0]['line']==8002
    assert hit['suggested_start']==7997
    assert 'tail_feature' in fast.expand(pid,hit['ref'],start=8000)['text']
    queue.settings(pid,False,'apc_baseline')
    assert queue.selected(pid).search(pid,'apc_only')['results']
    with pytest.raises(ValueError):dispatch(svc,'expand',ContextRequest(project_id=pid,ref=hit['ref']))


def test_paging_and_forward_reverse_dependencies(tmp_path):
    svc,p,_=service(tmp_path);pid=p['id'];root=tmp_path/'project'
    (root/'pkg').mkdir();(root/'pkg/a.py').write_text('from . import b\nfrom .b import value\n')
    (root/'pkg/b.py').write_text('value=2\n')
    for n in range(90):(root/f'file{n}.py').write_text('value=1\n')
    q=Indexing(svc);q.settings(pid,False,'fast');asyncio.run(q.once());fast=q.selected(pid)
    paths=[];capsules=[];offset=0
    while True:
        page=fast.overview(pid,offset,20);paths+=page['paths'];capsules+=page['capsules'];offset=page['next_offset']
        if offset is None:break
    assert len(paths)==len(set(paths))==93
    tree=page['navigation_tree']
    assert tree['listed_files']==93 and tree['omitted_files']==0
    assert tree['directories']['pkg']==['a.py','b.py']
    b=next(c for c in capsules if c['path']=='pkg/b.py')
    assert any(r['kind']=='imported_by' and r['path']=='pkg/a.py' for r in fast.related(pid,b['ref'])['related'])


def test_mode_change_cannot_displace_running_scan(tmp_path):
    svc,p,store=service(tmp_path);q=Indexing(svc);q.request(p['id'])
    with store.connect() as db:db.execute("UPDATE project_index_jobs SET state='running'")
    with pytest.raises(ValueError,match='running'):q.settings(p['id'],True,'fast')
    assert q.status(p['id'])['mode']=='apc_baseline'


def test_fast_startup_scripts_do_not_change_baseline_coverage(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'start.sh').write_text('python -m application\n')
    svc.refresh(p['id'])
    assert 'start.sh' not in svc.overview(p['id'])['paths']
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    fast=q.selected(p['id']);hit=fast.search(p['id'],'application')['results'][0]
    assert fast.expand(p['id'],hit['ref'])['text']=='python -m application'


def test_fast_bootstrap_reads_current_instructions(tmp_path):
    from types import SimpleNamespace
    from hub.context.runtime import prepare
    svc,p,store=service(tmp_path);root=tmp_path/'project'
    (root/'AGENTS.md').write_text('Preserve existing audio files.')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    task=store.create('explore',p['path'],'code','fast-bootstrap')
    class Runner:
        async def execute(self,task,name,args):
            return dispatch(svc,{'project_context':'overview'}.get(name,name.removeprefix('context_')),ContextRequest(project_id=p['id'],**args))
    messages=[{'role':'system','content':'base'},{'role':'user','content':'explore'}]
    async def chat(messages,tools):return {'content':'{"queries":[]}'},{}
    asyncio.run(prepare(SimpleNamespace(store=store,runner=Runner(),chat=chat),task,messages))
    assert [a['tool'] for a in store.actions(task['id'])]==['project_context','context_expand']
    assert 'Preserve existing audio files.' in messages[-1]['content']


def test_directed_bootstrap_retains_instructions_without_broad_navigation(tmp_path):
    from types import SimpleNamespace
    from hub.context.runtime import prepare
    svc,p,store=service(tmp_path);root=tmp_path/'project'
    (root/'AGENTS.md').write_text('Preserve existing audio files.')
    (root/'README.md').write_text('Unrelated project overview')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    task=store.create('CURRENT STEP: inspect a.py; overall: plan a feature',p['path'],'code','directed-bootstrap')
    store.event(task['id'],'chatgpt_action',{'action_id':'step1','request':'Read a.py lines 1-20 only'})
    class Runner:
        async def execute(self,task,name,args):
            return dispatch(svc,{'project_context':'overview'}.get(name,name.removeprefix('context_')),ContextRequest(project_id=p['id'],**args))
    async def chat(*args):raise AssertionError('Director steps must not invoke autonomous discovery')
    messages=[{'role':'system','content':'base'},{'role':'user','content':task['goal']}]
    asyncio.run(prepare(SimpleNamespace(store=store,runner=Runner(),chat=chat),task,messages))
    actions=store.actions(task['id'])
    assert [a['tool'] for a in actions]==['project_context','context_expand']
    assert actions[-1]['result']['path']=='AGENTS.md'
    assert 'Preserve existing audio files.' in messages[-1]['content']
    assert store.latest_event(task['id'],'source_navigation_delegated')
    assert 'CURRENT STEP only' in messages[0]['content']
    from hub.context.exploration import SOURCE_SYSTEM, DIRECTED_SOURCE_SYSTEM
    from hub.i18n import t
    assert DIRECTED_SOURCE_SYSTEM in messages[0]['content']
    assert SOURCE_SYSTEM not in messages[0]['content']
    assert t('context.fast_instruction') not in messages[0]['content']


def test_exploration_advances_only_repeated_reads_from_observed_refs():
    from hub.context.exploration import advance
    action={'tool':'context_search','args':{'query':'render'},'state':'complete',
            'result':{'results':[{'path':'src/render.py','ref':'fast/observed:hash'}]}}
    message={'tool_calls':[{'function':{'name':'context_search','arguments':{'query':'render'}}}]}
    assert advance(message,[action,action])[1]==[]  # baseline remains untouched
    bootstrap={'tool':'project_context','result':{'mode':'fast'}}
    changed,events=advance(message,[bootstrap,action,action])
    assert events and changed['tool_calls'][0]['function']=={'name':'context_expand','arguments':{'ref':'fast/observed:hash','lines':80}}
    assert message['tool_calls'][0]['function']['name']=='context_search'


def test_reworded_searches_advance_to_exact_observed_match():
    from hub.context.exploration import advance
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    for query in ('video','video generate'):
        actions.append({'tool':'context_search','args':{'query':query},'state':'complete',
                        'result':{'results':[{'path':'src/gateway.py','ref':'fast/source:hash','suggested_start':400}]}})
    changed,events=advance({'tool_calls':[{'function':{'name':'context_search','arguments':{'query':'generate clip'}}}]},actions)
    assert events and changed['tool_calls'][0]['function']['arguments']['start']==400


def test_mcp_mode_changes_share_http_and_persist(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hub.context.api import router
    from hub.context.tools import register_mcp
    svc,p,_=service(tmp_path);app=FastAPI();app.include_router(router(lambda:svc));client=TestClient(app);funcs={}
    class MCP:
        def tool(self,**kw):
            def register(fn):funcs[fn.__name__]=fn;return fn
            return register
    async def local(path,data=None,timeout=15):
        response=client.get(path) if data is None else client.post(path,json=data)
        assert response.status_code==200
        return response.json()
    register_mcp(MCP(),local,None,None)
    async def run():
        await funcs['project_index_settings'](p['id'],False,'fast')
        await funcs['context_refresh'](p['id'])
        assert (await funcs['project_index_status'](p['id']))['mode']=='fast'
        hit=(await funcs['context_search'](p['id'],'total'))['results'][0]
        assert hit['ref'].startswith('fast/')
        assert (await funcs['context_expand'](p['id'],path=hit['path']))['path']==hit['path']
        assert (await funcs['context_related'](p['id'],path=hit['path']))['symbols']
        await funcs['project_index_settings'](p['id'],False,'apc_baseline')
        assert client.get('/api/project-index/'+p['id']).json()['mode']=='apc_baseline'
    asyncio.run(run())


def test_large_text_is_streamed_searchable_to_tail_and_deduplicated(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'large.json').write_text(('shared_marker '+('x'*180)+'\n')*23000+'unique_tail_feature\n',encoding='utf8')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    hits=fast.search(p['id'],'shared_marker')['results']
    assert len(hits)==1
    tail=fast.search(p['id'],'unique_tail_feature')['results'][0]
    assert tail['matches'][0]['line']==23001
    page=fast.expand(p['id'],tail['ref'],start=23001)
    assert page['text']=='unique_tail_feature' and page['next_line'] is None
    with fast.db() as db:
        assert db.execute("SELECT extractor FROM files WHERE path='large.json'").fetchone()[0]=='streamed_text_v1'
        assert db.execute('SELECT count(*) FROM search').fetchone()[0]>50


def test_source_checkpoint_is_local_derived_evidence_not_execution():
    from types import SimpleNamespace
    from hub.context.exploration import checkpoint
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    for n in range(6):actions.append({'tool':'context_expand','result':{'path':f'{n}.py','ref':f'fast/{n}:hash','start':1,'end':1,'text':'def observed(): return 1'}})
    events=[];calls=[]
    class Store:
        def actions(self,tid):return actions
        def event(self,tid,kind,data):events.append((kind,data))
    async def chat(messages,tools):
        calls.append((messages,tools));return {'content':'Observed 0.py:1; runtime remains unverified.'},{}
    engine=SimpleNamespace(store=Store(),chat=chat);task={'id':'test','goal':'Read-only plan'}
    result=asyncio.run(checkpoint(engine,task))
    assert result['source_count']==6 and 'not runtime or independent verification' in result['basis']
    assert calls==[] and events[-1][0]=='source_checkpoint'
    assert 'def observed()' in result['text']
    assert asyncio.run(checkpoint(engine,task,result))==result and len(calls)==0


def test_fast_exact_path_read_still_verifies_hash(tmp_path):
    svc,p,_=service(tmp_path);q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    hit=fast.search(p['id'],'total')['results'][0]
    assert fast.expand(p['id'],hit['path'])['ref']==hit['ref']
    with pytest.raises(Exception):fast.expand(p['id'],'../outside.py')
    (tmp_path/'project'/hit['path']).write_text('changed')
    with pytest.raises(Exception):fast.expand(p['id'],hit['path'])


def test_source_review_rejects_invalid_verdict_and_skips_baseline():
    from types import SimpleNamespace
    from hub.context.exploration import review
    actions=[];events=[];calls=[]
    class Store:
        def actions(self,tid):return actions
        def event(self,tid,kind,data):events.append((kind,data))
        def latest_event(self,tid,kind):return None
    async def chat(messages,tools):
        calls.append(messages);return {'content':'I think it is fine'},{}
    engine=SimpleNamespace(store=Store(),chat=chat);task={'id':'test','goal':'read-only plan'}
    assert asyncio.run(review(engine,task,'draft')) is None and not calls
    actions.extend([{'tool':'project_context','result':{'mode':'fast','total_files':310,'coverage':{'symbol_count':1689}}},
                    {'tool':'context_expand','result':{'path':'api.py','ref':'fast/ref:hash','start':1,'end':1,'text':'def create(body: Generate): pass'}}])
    result=asyncio.run(review(engine,task,'The API accepts an arbitrary dictionary.'))
    assert result['verdict']=='needs_correction'
    assert result['actionable'] is False
    import json
    assert json.loads(calls[-1][1]['content'])['objective']=='read-only plan'
    assert json.loads(calls[-1][1]['content'])['measured_index']['total_files']==310
    assert json.loads(calls[-1][1]['content'])['measured_index']['coverage']['symbol_count']==1689
    assert 'not independent QA' in result['basis']
    assert events[-1][0]=='source_answer_review'
    before=len(calls)
    assert asyncio.run(review(engine,task,''))['basis']=='empty-response validation, not model review'
    assert len(calls)==before
    async def anchored_chat(messages,tools):
        return {'content':json.dumps({'verdict':'needs_correction','draft_quote':'arbitrary dictionary',
            'source_path':'api.py','source_start':1,'source_end':1})},{}
    engine.chat=anchored_chat
    anchored=asyncio.run(review(engine,task,'The API accepts an arbitrary dictionary.'))
    assert anchored['actionable'] is True
    assert anchored['source_quote']=='def create(body: Generate): pass'


@pytest.mark.parametrize('source_args',[{'ref':'fast/a:h'},{'path':'a.py'}])
def test_repeated_source_prefix_continues_at_delivered_cursor(source_args):
    from hub.context.exploration import advance
    action={'tool':'context_expand','state':'complete','args':{'ref':'fast/a:h','start':1,'lines':80},
            'result':{'ref':'fast/a:h','path':'a.py','start':1,'end':2,'text':'line one\nline two','next_line':3,'total_lines':200}}
    message={'tool_calls':[{'function':{'name':'context_expand','arguments':{**source_args,'start':1,'lines':150}}}]}
    result,events=advance(message,[{'tool':'project_context','result':{'mode':'fast'}},{**action,'id':'first'},{**action,'id':'second'}])
    assert events and result['tool_calls'][0]['function']['arguments']['start']==3


def test_continuation_merges_previous_pages_without_pagination_cycle():
    from hub.context.exploration import advance
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    for ident,start,end in [('a',1,2),('b',3,4),('c',1,2)]:
        actions.append({'id':ident,'tool':'context_expand','args':{'ref':'fast/a:h','start':start,'lines':2},'state':'complete',
                        'result':{'ref':'fast/a:h','path':'a.py','start':start,'end':end,'text':'a\nb','next_line':end+1,'total_lines':6}})
    result,_=advance({'tool_calls':[{'function':{'name':'context_expand','arguments':{'path':'a.py','start':1,'lines':6}}}]},actions)
    assert result['tool_calls'][0]['function']['arguments']['start']==5


def test_fast_search_prefers_all_terms_with_partial_fallback(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'specific.py').write_text('def distinctive_capability(): return 42')
    (root/'noise.py').write_text('def unrelated_capability(): return 0')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    assert [r['path'] for r in fast.search(p['id'],'def distinctive_capability')['results']]==['specific.py']
    assert fast.search(p['id'],'distinctive_capability missing_term')['results'][0]['path']=='specific.py'
    (root/'large.txt').write_text('first_marker\n'+('middle '*12000)+'\nlast_marker')
    (root/'small.txt').write_text('first_marker last_marker')
    fast.refresh(p['id'])
    assert {r['path'] for r in fast.search(p['id'],'first_marker last_marker')['results']}=={'large.txt','small.txt'}


def test_review_source_excerpt_does_not_cut_function_body_at_2200_chars():
    from hub.context.exploration import checkpoint_sources
    source=('# prefix\n'*400)+'return actual_behavior'
    actions=[{'tool':'project_context','result':{'mode':'fast'}},
             {'tool':'context_expand','result':{'path':'worker.py','ref':'fast/a:h','start':1,'end':401,'text':source}}]
    assert checkpoint_sources(actions)[0]['excerpt']==source


def test_fast_explicit_filename_beats_service_alias_mentions(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'gateway.py').write_text('def handle_request(): return 42')
    (root/'manage.py').write_text('service_gateway = "python gateway.py"')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    assert [r['path'] for r in fast.search(p['id'],'service_gateway gateway.py')['results']]==['gateway.py']


def test_fast_distinctive_symbol_finds_definition_not_translation(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'gateway.py').write_text('def create_image_video(): return 42')
    (root/'labels.json').write_text('{"text": "missing_service.py create_image_video"}')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    assert [r['path'] for r in fast.search(p['id'],'missing_service.py create_image_video')['results']]==['gateway.py']


def test_named_symbol_cursor_targets_definition_beyond_first_symbols(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    source='# create_requested_feature route_alias\n'+''.join(f'def unrelated_{i}(): return 0\n' for i in range(25))+'\ndef create_requested_feature(): return 42\n'
    (root/'gateway.py').write_text(source)
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    hit=fast.search(p['id'],'create_requested_feature route_alias')['results'][0]
    assert hit['matched_definitions'][0]['line']==28
    assert hit['suggested_start']==23


def test_repeated_broad_search_traces_read_implementation_before_noise():
    from hub.context.exploration import advance
    args={'query':'new feature'}
    result={'results':[{'ref':'fast/worker:h','path':'worker.py'},{'ref':'fast/noise:h','path':'unrelated.py'}]}
    actions=[{'tool':'project_context','result':{'mode':'fast'}},
             {'tool':'context_expand','args':{},'state':'complete','result':{'ref':'fast/worker:h'}},
             {'tool':'context_search','args':args,'state':'complete','result':result},
             {'tool':'context_search','args':args,'state':'complete','result':result}]
    message={'tool_calls':[{'function':{'name':'context_search','arguments':args}}]}
    out,events=advance(message,actions)
    assert out['tool_calls'][0]['function']=={'name':'context_related','arguments':{'ref':'fast/worker:h'}}
    assert events


def test_unknown_compound_symbol_finds_existing_component_not_generic_handler(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'image_video.py').write_text('def create():\n    """Local image video generation."""\n    return 42')
    (root/'diagnostics.py').write_text('# API endpoint handler\ndef report(): return 0')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    result=fast.search(p['id'],'generate_image_video API endpoint handler')
    assert [r['path'] for r in result['results']]==['image_video.py']
    assert 'matched_definitions' not in result['results'][0]


def test_fast_from_package_import_traces_module_before_package_marker(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'pkg').mkdir();(root/'pkg/__init__.py').write_text('VERSION=1')
    (root/'pkg/feature.py').write_text('def work(): return 42')
    (root/'pkg/worker.py').write_text('from . import feature\nfrom pkg import feature as f\n')
    svc.refresh(p['id']);baseline=svc.path.read_bytes()
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    related=fast.related(p['id'],'pkg/worker.py')['related']
    assert related[0]['path']=='pkg/feature.py'
    assert related[-1]['path']=='pkg/__init__.py'
    assert any(r['path']=='pkg/worker.py' and r['kind']=='imported_by' for r in fast.related(p['id'],'pkg/feature.py')['related'])
    assert svc.path.read_bytes()==baseline


def test_navigation_seed_uses_only_observed_sources_and_keeps_tests():
    from types import SimpleNamespace
    from hub.context.exploration import seed_navigation
    events=[];calls=[]
    async def chat(messages,tools):return {'content':'{"queries":["build scene"]}'},{}
    async def read(name,args):
        calls.append((name,args))
        if name=='context_search':return {'results':[{'path':'worker.py','ref':'fast/worker:h','suggested_start':30}]}
        if name=='context_related':return {'related':[{'path':'api.py','ref':'fast/api:h','kind':'imports'},{'path':'tests/test_worker.py','ref':'fast/test:h','kind':'imported_by'}]}
        return {'text':'observed'}
    engine=SimpleNamespace(chat=chat,store=SimpleNamespace(event=lambda *a:events.append(a)))
    asyncio.run(seed_navigation(engine,{'id':'t','goal':'Add a feature'},read))
    assert [a['ref'] for n,a in calls if n=='context_expand']==['fast/worker:h','fast/api:h','fast/test:h']
    assert calls[1][1]['start']==30
    assert events[0][1]=='source_navigation_plan'


def test_fast_concept_search_does_not_prefer_generic_project_prose(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'image_video.py').write_text('"""Text conditioned video generation."""\ndef create(): return 1')
    (root/'README.md').write_text('text-to-video feature implementation integration architecture')
    (root/'voice.py').write_text('"""Text and video conversion library."""\ndef speak(): return 1')
    (root/'test_video.py').write_text('# text video')
    (root/'install_video.py').write_text('# text video')
    (root/'image_video_worker.py').write_text('# video worker process\ndef generate(): return 1')
    (root/'voice_warm_worker.py').write_text('# text process worker process process\ndef warm(): return 1')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    result=fast.search(p['id'],'text-to-video feature implementation')['results']
    assert result[0]['path']=='image_video.py'
    assert 'voice.py' in {r['path'] for r in result}  # ranked, not silently excluded
    result=fast.search(p['id'],'text-to-video conversion library')['results']
    assert result[0]['path']=='image_video.py'  # extra vocabulary must not exclude a strong source lead
    result=fast.search(p['id'],'text-to-video worker process')['results']
    assert result[0]['path']=='image_video_worker.py'
    assert 'voice_warm_worker.py' in {r['path'] for r in result}


def test_fast_literal_decorator_does_not_confuse_tokens_with_exact_code(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'routes.py').write_text("@router.post('/append')\ndef append_item(): return 1")
    (root/'noise.py').write_text("# router post append\ndef post(): return []")
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    hits=fast.search(p['id'],"@router.post('/append')")['results']
    assert [r['path'] for r in hits]==['routes.py']
    assert fast.search(p['id'],"@router.post('/unknown')")['results']  # token fallback remains available


def test_navigation_seed_reserves_source_reads_for_later_concepts():
    from types import SimpleNamespace
    from hub.context.exploration import seed_navigation
    expanded=[]
    async def chat(messages,tools):return {'content':'{"queries":["worker","dependency","interface"]}'},{}
    async def read(name,args):
        if name=='context_search':
            return {'results':[{'path':args['query']+str(i)+'.py','ref':args['query']+str(i)} for i in range(2)]}
        if name=='context_related':
            return {'related':[{'path':'config.py','ref':'config'},{'path':'tests/test_worker.py','ref':'test'}]}
        expanded.append(args['ref']);return {'text':'actual source'}
    engine=SimpleNamespace(chat=chat,store=SimpleNamespace(event=lambda *a:None))
    asyncio.run(seed_navigation(engine,{'id':'t','goal':'feature plan'},read))
    assert 'dependency0' in expanded and 'interface0' in expanded
    assert len(expanded)==6


def test_navigation_planner_receives_observed_project_vocabulary():
    import json
    from types import SimpleNamespace
    from hub.context.exploration import seed_navigation
    async def chat(messages,tools):
        payload=json.loads(messages[-1]['content'])
        assert payload['objective']=='add requested capability'
        assert payload['observed_source_excerpts'][0]['text']=='Existing component: spectral_render.py'
        return {'content':'{"queries":[]}'},{}
    async def read(*args):raise AssertionError('No queries returned')
    engine=SimpleNamespace(chat=chat,store=SimpleNamespace(event=lambda *args:None))
    asyncio.run(seed_navigation(engine,{'id':'t','goal':'add requested capability'},read,
        {'observed_source_excerpts':[{'path':'README.md','text':'Existing component: spectral_render.py'}]}))


def test_read_only_synthesis_preserves_evidence_and_never_shortcuts_implementation():
    import json
    from hub.context.exploration import synthesis_request
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:h','start':1,'end':1,'text':'def known(): return 1'}} for i in range(6)]
    task={'goal':'Read-only: investigate the requested feature'}
    result=synthesis_request(task,actions,{'analysis_only':True})
    assert result['source_count']==6
    payload=json.loads(result['messages'][-1]['content'])
    assert payload['objective']==task['goal'] and len(payload['observed_source_excerpts'])==6
    # Stay in the focused investigation after tool calls rather than restoring
    # the unrelated desktop catalog or losing the search result just requested.
    actions.append({'tool':'context_search','args':{'query':'missing transformation'},'result':{'results':[{'path':'converter.py','suggested_start':42}]}})
    continued=synthesis_request(task,actions,{'analysis_only':True},6)
    navigation=json.loads(continued['messages'][-1]['content'])['recent_navigation_results']
    assert navigation[-1]['result']['results'][0]['path']=='converter.py'
    assert navigation[-1]['result']['results'][0]['suggested_start']==42
    corrected=synthesis_request(task,actions,{},6,feedback='Check the actual worker input contract')
    assert corrected is not None
    assert 'Check the actual worker input contract' in corrected['messages'][1]['content']
    assert synthesis_request(task,actions,{'analysis_only':False}) is not None
    assert synthesis_request({'goal':'Implement the feature'},actions,{'analysis_only':True}) is None
    assert synthesis_request({'goal':'Implement the feature'},actions,{},6,feedback='Review draft') is None


def test_synthesis_retains_director_corrections_without_replacing_objective():
    import json
    from hub.context.exploration import synthesis_request
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:h','start':1,'end':1,'text':'def known(): return 1'}} for i in range(6)]
    task={'goal':'Read-only: explain the existing input contract'}
    guidance=[{'revision':2,'text':'Check the worker before concluding the input is optional.','required_tools':['context_expand']}]
    result=synthesis_request(task,actions,{},director_guidance=guidance)
    packet=json.loads(result['messages'][-1]['content'])
    assert packet['director_guidance_to_verify']==guidance
    assert packet['overall_objective_scope_only']==task['goal']
    assert packet['current_step']==guidance[-1]['text']
    assert 'at most 600 words' not in result['messages'][-1]['content']
    assert result['tools']==[]
    assert 'tools' not in synthesis_request(task,actions,{})
    assert synthesis_request({'goal':'Implement a feature'},actions,{},director_guidance=guidance) is None
    assert packet['observed_source_excerpts']
    assert json.loads(synthesis_request(task,actions,{})['messages'][-1]['content'])['director_guidance_to_verify']==[]


def test_directed_synthesis_uses_requested_range_not_old_broad_sources():
    import json
    from hub.context.exploration import synthesis_request,DIRECTED_SOURCE_SYSTEM
    actions=[{'tool':'project_context','result':{'mode':'fast'}},{'tool':'context_expand','result':{'path':'worker.py','ref':'hash','start':1,'end':4,'text':'old\na\nb\nunrelated'}}]
    guidance=[{'text':'Return only the input names as JSON','required_sources':[{'path':'worker.py','start':2,'end':3}]}]
    result=synthesis_request({'goal':'Read-only: whole project plan'},actions,{},director_guidance=guidance)
    packet=json.loads(result['messages'][-1]['content'])
    assert result['messages'][0]['content'].startswith(DIRECTED_SOURCE_SYSTEM)
    assert packet['observed_source_excerpts'][0]['excerpt']=='2: a\n3: b'
    assert packet['current_step']==guidance[-1]['text']


def test_synthesis_ranks_relevant_measured_code_before_incidental_recent_pages():
    from hub.context.exploration import ranked_synthesis_sources
    sources=[{'path':'invoice_worker.py','measured_flow':{'facts':[{'kind':'call'}]}},
             {'path':'invoice.html','measured_flow':{'facts':[]}},
             {'path':'settings.py','measured_flow':{'facts':[{'kind':'call'}]}}]
    assert [x['path'] for x in ranked_synthesis_sources(sources,'Plan invoice generation')]==['invoice_worker.py','invoice.html','settings.py']


def test_focused_autonomous_question_keeps_measured_contract_without_broad_plan():
    import json
    from hub.context.exploration import synthesis_request
    actions=[{'tool':'project_context','result':{'mode':'fast'}},
        {'tool':'context_expand','result':{'path':'a.py','ref':'fast/a:hash','start':1,'end':1,
            'text':'value=1','measured_input_declarations':[{'class':'Example','fact':'observed'}]}}]
    result=synthesis_request({'goal':'Read-only: inspect a.py and return JSON'},actions,{})
    packet=json.loads(result['messages'][-1]['content'])
    assert packet['objective']=='Read-only: inspect a.py and return JSON'
    assert packet['observed_source_excerpts'][0]['measured_input_declarations'][0]['fact']=='observed'
    assert 'at most 600 words' not in result['messages'][-1]['content']
    assert 'director_guidance_to_verify' not in packet
    assert 'output_schema' not in result
    structured=synthesis_request({'goal':'Read-only: inspect a.py and return a JSON array'},actions,{})
    assert structured['tools']==[] and structured['output_schema']['type']=='array'
    actions[-1]['result'].pop('measured_input_declarations')
    assert 'output_schema' not in synthesis_request({'goal':'Read-only: inspect a.py and return a JSON array'},actions,{})


def test_directed_synthesis_assembles_chunks_of_requested_version_and_reports_gaps():
    import json
    from hub.context.exploration import synthesis_request
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    def add(digest,start,text):
        actions.append({'tool':'context_expand','result':{'path':'worker.py','ref':'fast/worker:'+digest,
            'start':start,'end':start+len(text.split('\n'))-1,'text':text}})
    old,new='a'*64,'b'*64
    add(old,1,'old1\nold2\nold3\nold4')
    add(new,1,'new1\nnew2');add(new,3,'new3\nnew4')
    requirement={'path':'worker.py','start':2,'end':4,'sha256':new}
    def packet():
        result=synthesis_request({'goal':'Read-only: inspect'},actions,{},director_guidance=[
            {'text':'Explain this exact version','required_sources':[requirement]}])
        return json.loads(result['messages'][-1]['content'])
    result=packet()
    assert result['observed_source_excerpts'][0]['excerpt']=='2: new2\n3: new3\n4: new4'
    assert result['observed_source_excerpts'][0]['sha256']==new
    assert result['missing_required_sources']==[]
    actions.pop()
    result=packet()
    assert result['observed_source_excerpts']==[]
    assert result['missing_required_sources']==[requirement]


def test_synthesis_numbers_actual_ranges_preserving_blank_lines_and_raw_evidence():
    import json
    from hub.context.exploration import synthesis_request,checkpoint_sources
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:h',
        'start':41,'end':43,'text':'first\n\nlast'}} for i in range(6)]
    packet=json.loads(synthesis_request({'goal':'Read-only: explain'},actions,{})['messages'][-1]['content'])
    assert all(s['excerpt']=='41: first\n42: \n43: last' for s in packet['observed_source_excerpts'])
    assert all(s['excerpt']=='first\n\nlast' for s in checkpoint_sources(actions))
    assert all(a['result']['text']=='first\n\nlast' for a in actions[1:])


def test_redundant_source_identity_must_match_and_cannot_bypass_stale_hash(tmp_path):
    from hub.i18n import CapabilityError
    svc,p,_=service(tmp_path)
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    hit=fast.search(p['id'],'a.py')['results'][0]
    result=dispatch(svc,'expand',ContextRequest(project_id=p['id'],ref=hit['ref'],path=hit['path']))
    assert result['path']==hit['path']
    with pytest.raises(ValueError,match='different files'):
        dispatch(svc,'expand',ContextRequest(project_id=p['id'],ref=hit['ref'],path='wrong.py'))
    (tmp_path/'project'/hit['path']).write_text('value=99')
    with pytest.raises(CapabilityError,match='changed'):
        dispatch(svc,'expand',ContextRequest(project_id=p['id'],ref=hit['ref'],path=hit['path']))


def test_source_draft_budgets_tool_schema_and_nested_json(monkeypatch):
    import json
    from hub.context.exploration import synthesis_request
    from hub.model_context import prepare_messages
    from hub.model_settings import ModelSettings
    settings=ModelSettings(context_tokens=8192,response_tokens=1024)
    monkeypatch.setattr('hub.model_settings.load_settings',lambda:settings)
    tree={'directories':{'src':[f'component_{i}.py' for i in range(1500)]},'listed_files':1500,'omitted_files':0}
    actions=[{'tool':'project_context','result':{'mode':'fast','navigation_tree':tree}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:h','start':1,'end':80,'text':('quoted="value"\\path\n'*120)}} for i in range(12)]
    catalog=[{'type':'function','function':{'name':'context_search','description':'source '*1000,'parameters':{'type':'object'}}}]
    result=synthesis_request({'goal':'Read-only: inspect'},actions,{},catalog=catalog)
    packet=json.loads(result['messages'][1]['content'])
    assert packet['omitted_source_ranges']>0 and packet['observed_source_excerpts']
    assert packet['indexed_filename_tree']['omitted_files']>0
    assert tree['listed_files']==1500 and len(tree['directories']['src'])==1500
    assert prepare_messages(result['messages'],catalog,settings.context_tokens,settings.response_tokens)


def test_draft_source_references_are_resolved_and_read_before_review(tmp_path):
    from types import SimpleNamespace
    from hub.context.runtime import prepare
    from hub.context.exploration import ground_named_sources
    svc,p,store=service(tmp_path);root=tmp_path/'project'
    (root/'AGENTS.md').write_text('Project rules')
    (root/'pkg').mkdir();(root/'pkg/helper_service.py').write_text('def work(): return 42')
    (root/'pane.js').write_text("fetch('/jobs')")
    (root/'pane.py').write_text('def required_input(asset): return asset')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    task=store.create('explore',p['path'],'code','named-reference')
    class Runner:
        async def execute(self,task,name,args):
            return dispatch(svc,{'project_context':'overview'}.get(name,name.removeprefix('context_')),ContextRequest(project_id=p['id'],**args))
    async def chat(messages,tools):return {'content':'{"queries":[]}'},{}
    engine=SimpleNamespace(store=store,runner=Runner(),chat=chat)
    messages=[{'role':'system','content':'base'},{'role':'user','content':'explore'}]
    asyncio.run(prepare(engine,task,messages))
    draft='Change helper_service.py and pane.js; unknown_service.py is only a proposed new module.'
    added=asyncio.run(ground_named_sources(engine,task,draft,messages))
    assert added==['pkg/helper_service.py','pane.js','pane.py']
    assert any('def work(): return 42' in m.get('content','') for m in messages)
    count=len(store.actions(task['id']))
    assert asyncio.run(ground_named_sources(engine,task,draft,messages))==[]
    assert len(store.actions(task['id']))==count
    assert not any(a['tool']=='context_expand' and 'unknown' in str(a['args']) for a in store.actions(task['id']))


def test_fast_companion_links_are_scoped_and_marked_as_heuristic(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'image-jobs.js').write_text("fetch('/image-jobs')")
    (root/'image_jobs.py').write_text('def create(): return 42')
    (root/'other').mkdir();(root/'other/image_jobs.py').write_text('unrelated=True')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once());fast=q.selected(p['id'])
    links=[h for h in fast.related(p['id'],'image-jobs.js')['related'] if h['kind']=='possible_companion']
    assert [(h['path'],h['confidence']) for h in links]==[('image_jobs.py','filename_heuristic')]


def test_repeated_search_stays_on_search_roots_not_recursive_dependencies():
    from hub.context.exploration import advance
    args={'query':'requested feature'}
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    for i in range(2):actions.append({'id':str(i),'tool':'context_search','args':args,'state':'complete','result':{'results':[{'ref':'fast/api:h','path':'api.py'},{'ref':'fast/worker:h','path':'worker.py'}]}})
    actions.extend([
        {'tool':'context_expand','args':{},'state':'complete','result':{'ref':'fast/api:h'}},
        {'tool':'context_related','args':{},'state':'complete','result':{'ref':'fast/api:h','related':[{'ref':'fast/config:h','path':'config.py'}]}},
        {'tool':'context_expand','args':{},'state':'complete','result':{'ref':'fast/config:h'}},
        {'tool':'context_related','args':{},'state':'complete','result':{'ref':'fast/config:h','related':[{'ref':'fast/noise:h','path':'unrelated.py'}]}}])
    message={'tool_calls':[{'function':{'name':'context_search','arguments':args}}]}
    result,_=advance(message,actions)
    assert result['tool_calls'][0]['function']=={'name':'context_expand','arguments':{'ref':'fast/worker:h','lines':80}}
    actions.append({'tool':'context_expand','args':{},'state':'complete','result':{'ref':'fast/api:h','path':'api.py','start':90,'end':100,'text':'def create(): pass','total_lines':150}})
    result,_=advance(message,actions)
    assert result['tool_calls'][0]['function']=={'name':'context_expand','arguments':{'ref':'fast/api:h','start':1,'lines':80}}


def test_source_revision_keeps_previous_draft_as_unverified_data():
    import json
    from hub.context.exploration import synthesis_request
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:h','start':1,'end':2,'text':'def run(): pass'}} for i in range(6)]
    task={'goal':'Read-only: investigate a feature'}
    revised=synthesis_request(task,actions,{},6,feedback='Verify the consumer inputs',previous_draft='Previous proposed strategy')
    packet=json.loads(revised['messages'][1]['content'])
    assert packet['previous_unverified_draft']=='Previous proposed strategy'
    assert packet['review_feedback_to_verify']=='Verify the consumer inputs'
    initial=synthesis_request(task,actions,{},previous_draft='stale draft')
    assert json.loads(initial['messages'][1]['content'])['previous_unverified_draft']==''


def test_component_navigation_uses_only_measured_paths_and_traces_each():
    from types import SimpleNamespace
    from hub.context.exploration import seed_navigation
    calls=[];events=[]
    async def chat(messages,tools):
        return {'content':'{"queries":[],"components":["src/producer.py","invented.py","src/consumer.py","src/producer.py"]}'},{}
    async def read(name,args):
        calls.append((name,args))
        if name=='context_related':return {'related':[]}
        return {'text':'def execute(): pass'}
    engine=SimpleNamespace(chat=chat,store=SimpleNamespace(event=lambda *a:events.append(a)))
    asyncio.run(seed_navigation(engine,{'id':'test','goal':'Read-only: plan conversion'},read,
        {'navigation_tree':{'directories':{'src':['producer.py','consumer.py']}}}))
    assert [a['ref'] for n,a in calls if n=='context_expand']==['src/producer.py','src/consumer.py']
    assert [a['ref'] for n,a in calls if n=='context_related']==['src/producer.py','src/consumer.py']
    assert len([e for e in events if e[1]=='source_component_inspected'])==2


def test_shared_fast_expand_exposes_contracts_without_changing_apc(tmp_path):
    svc,p,_=service(tmp_path);root=tmp_path/'project'
    (root/'request.py').write_text('class Request(BaseModel):\n    name: str\n')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    result=dispatch(svc,'expand',ContextRequest(project_id=p['id'],path='request.py'))
    assert result['measured_input_declarations'][0]['fields'][0]['field']=='name'
    assert result['measured_input_declarations'][0]['fields'][0]['required_in_this_declaration']
    assert q.selected(p['id']).database_name=='context-fast.sqlite3'


def test_directed_search_preserves_requested_operation():
    from hub.context.exploration import advance
    args={'query':'requested feature'}
    actions=[{'tool':'project_context','result':{'mode':'fast'}}]
    actions += [{'tool':'context_search','args':args,'state':'complete','result':{'results':[{'ref':'fast/api:h','path':'api.py'}]}} for _ in range(2)]
    message={'tool_calls':[{'function':{'name':'context_search','arguments':args}}]}
    autonomous,changes=advance(message,actions)
    assert changes and autonomous!=message
    directed,changes=advance(message,actions,directed=True)
    assert directed==message and changes==[]


def test_packet_preserves_source_over_unverified_draft_and_reports_omitted_ranges(monkeypatch):
    import json
    from hub.context.exploration import bounded_packet
    from hub.model_settings import ModelSettings
    monkeypatch.setattr('hub.model_settings.load_settings', lambda: ModelSettings(context_tokens=8192,response_tokens=1024))
    source={'path':'worker.py','start':10,'end':20,'excerpt':'actual source '*40}
    packet=json.loads(bounded_packet({'previous_unverified_draft':'unsupported assertion '*10000,'sources':[source]},'sources'))
    assert packet['sources']==[source]
    assert packet['previous_draft_omitted_for_budget'] is True
    oversized={'path':'other.py','start':1,'end':100,'excerpt':'long observed source '*10000}
    packet=json.loads(bounded_packet({'sources':[source,oversized]},'sources'))
    assert packet['sources']==[source]
    assert packet['omitted_source_locations']==[{'path':'other.py','start':1,'end':100}]
    assert packet['omitted_source_ranges']==1


def test_map_reports_measured_parser_coverage_without_claiming_all_files(tmp_path):
    svc,p,store=service(tmp_path)
    root=tmp_path/'project'
    (root/'broken.py').write_text('def broken(:')
    (root/'screen.js').write_text('function showPanel() {}')
    q=Indexing(svc);q.settings(p['id'],False,'fast');asyncio.run(q.once())
    fast=q.selected(p['id']);page=fast.overview(p['id'],0,1)
    coverage=page['coverage']
    assert coverage['syntax_error_count']==1
    assert coverage['syntax_error_paths']==['broken.py']
    assert sum(coverage['parser_counts'].values())==page['total_files']
    assert coverage['parser_counts']['text_v1']==1
    assert 'Other indexed languages are searchable text' in coverage['limitations']
    assert 'node_modules' in coverage['excluded_directory_names']
    assert fast.search(p['id'],'broken')['results']


def test_synthesis_keeps_measured_coverage_separate_from_omitted_tree():
    import json
    from hub.context.exploration import synthesis_request
    coverage={'parser_counts':{'python_ast_imports_v2':214,'text_v1':95},'symbol_count':1689}
    actions=[{'tool':'project_context','result':{'mode':'fast','total_files':310,'coverage':coverage,
        'navigation_tree':{'directories':{},'listed_files':0,'omitted_files':310}}}]
    actions += [{'tool':'context_expand','result':{'path':f'{i}.py','ref':f'fast/{i}:hash','start':1,'end':1,'text':'value = 1'}} for i in range(6)]
    packet=json.loads(synthesis_request({'goal':'Read-only: map project'},actions,{})['messages'][1]['content'])
    assert packet['measured_index']['total_files']==310
    assert packet['measured_index']['coverage']==coverage
    assert packet['indexed_filename_tree']['listed_files']==0
    assert len(packet['observed_source_excerpts'])==6
