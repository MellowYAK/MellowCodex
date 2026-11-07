import pytest
from hub.store import Store,Conflict
from hub.development.guidance import Guidance

def test_scope_persists_intersects_and_cannot_be_widened(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Read only',str(tmp_path),'code','scope')
    service=Guidance(store)
    args=dict(task_id=task['id'],expected_task_revision=task['revision'],expected_revision=0,consumer_epoch='',request_id='one',text='Read only',allowed_tools=['read_file','context_expand'])
    service.submit(**args);service.submit(**args)
    with pytest.raises(Conflict):service.submit(**{**args,'allowed_tools':['write_file']})
    service.submit(**{**args,'expected_revision':1,'request_id':'two','allowed_tools':['read_file','write_file']})
    service.begin(task['id'])
    assert Guidance(store).allowed_tools(task['id'])=={'read_file'}

def test_scope_rejects_impossible_evidence_requirement(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Read only',str(tmp_path),'code','scope')
    service=Guidance(store)
    with pytest.raises(ValueError):
        service.submit(task['id'],task['revision'],0,'','one','Read',allowed_tools=[],required_sources=[{'path':'a.py','start':1,'end':2}])
    assert service.allowed_tools(task['id']) is None

def test_play_scope_and_http_scope_preserve_empty_list():
    import json
    from hub.chatgpt_bridge import action_from_reply
    from hub.development.api import GuidanceRequest
    action={'id':'scope','task':'Answer only','mode':'code','allowed_tools':[]}
    assert action_from_reply(json.dumps({'local_agent_action':action}))['allowed_tools']==[]
    for bad in ['read_file',[42],['read-file']]:
        assert action_from_reply(json.dumps({'local_agent_action':{**action,'allowed_tools':bad}})) is None
    request=GuidanceRequest(task_id='a'*32,expected_task_revision=0,expected_revision=0,
                           consumer_epoch='',request_id='scope',text='Answer only',allowed_tools=[])
    assert request.model_dump()['allowed_tools']==[]

def test_scope_blocks_stale_mutating_calls_before_dispatch(tmp_path):
    import asyncio
    from hub.tools import ToolRunner
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Read only',str(tmp_path),'code','scope')
    Guidance(store).submit(task['id'],task['revision'],0,'','one','Read only',allowed_tools=['read_file'])
    runner=ToolRunner.__new__(ToolRunner);runner.context_store=store
    # No desktop/browser/terminal objects: denial must precede all side effects.
    for name,args in [('write_file',{'path':'bad.txt','content':'bad'}),('run_shell',{'command':'echo bad'}),('tools_enable',{'groups':['terminal']})]:
        result=asyncio.run(runner.execute(task,name,args))
        assert result['failure_kind']=='tool_scope_denied'
        assert result['effect_started'] is False
    assert not (tmp_path/'bad.txt').exists()

def test_guidance_fences_restarts_and_replays_without_duplicate_submission(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('original human objective',str(tmp_path),'code','guidance')
    service=Guidance(store);epoch=service.begin(task['id'])
    args=dict(task_id=task['id'],expected_task_revision=task['revision'],expected_revision=0,consumer_epoch=epoch,request_id='request1',text='Preserve tests; repair implementation.')
    status=service.submit(**args)
    assert status['guidance_revision']==1
    assert status['human_request_original']=='original human objective'
    service.submit(**args)
    assert service.status(task['id'])['guidance_revision']==1
    assert service.consume(task['id'],epoch)[0]['consumed_epoch']==''
    assert service.status(task['id'])['guidance'][0]['consumed_epoch']==epoch
    next_epoch=service.begin(task['id'])
    with pytest.raises(Conflict):service.consume(task['id'],epoch)
    with pytest.raises(Conflict):service.submit(**{**args,'expected_revision':1,'request_id':'request2'})
    assert service.consume(task['id'],next_epoch)[0]['text']==args['text']
    assert service.status(task['id'])['guidance'][0]['consumed_epoch']==next_epoch
    with pytest.raises(Conflict):service.submit(**{**args,'text':'different'})

def test_guidance_rejects_stale_task_and_retains_original_goal(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('שלום',str(tmp_path),'code','guidance2')
    service=Guidance(store)
    store.update(task['id'],state='running')
    with pytest.raises(Conflict):service.submit(task['id'],task['revision'],0,'','one','Change code')
    assert service.status(task['id'])['human_request_original']=='שלום'

def test_guidance_requires_observed_success_after_receipt(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('check diff',str(tmp_path),'code','evidence')
    service=Guidance(store)
    service.submit(task['id'],task['revision'],0,'','one','Inspect the diff',required_tools=['candidate_diff'])
    action={'tool':'candidate_diff','state':'complete','result':{},'created':'2000-01-01T00:00:00+00:00'}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['created']='2099-01-01T00:00:00+00:00'
    action['result']={'error':'failure'}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['result']={'verified':False}
    assert service.missing_evidence(task['id'],[action])==['candidate_diff']
    action['result']={'revision':1,'files':[]}
    assert service.missing_evidence(task['id'],[action])==[]

def test_required_source_coverage_is_versioned_and_requires_actual_text(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('read sources',str(tmp_path),'code','sources')
    service=Guidance(store)
    source={'path':'src/a.py','start':2,'end':5,'sha256':'a'*64}
    args=dict(task_id=task['id'],expected_task_revision=task['revision'],expected_revision=0,
              consumer_epoch='',request_id='sources',text='Inspect exact ranges',required_sources=[source])
    service.submit(**args)
    def action(start,end,digest='a',text=None):
        return {'tool':'context_expand','state':'complete','created':'2099',
                'result':{'path':'src/a.py','start':start,'end':end,'ref':'fast/id:'+digest*64,
                          'text':text if text is not None else '\n'.join('code' for _ in range(start,end+1))}}
    assert service.missing_evidence(task['id'],[action(2,3)])==['source:src/a.py:2-5']
    assert service.missing_evidence(task['id'],[action(2,3),action(4,5)])==[]
    assert service.missing_evidence(task['id'],[action(2,3),action(4,5,'b')])
    assert service.missing_evidence(task['id'],[action(2,5,text='omitted')])
    assert service.missing_evidence(task['id'],[action(2,5,text='a\nb\nc\n')])==[]
    assert service.missing_evidence(task['id'],[action(2,2),action(4,5)])
    service.submit(**args)  # identical replay remains idempotent
    with pytest.raises(Conflict):service.submit(**{**args,'required_sources':[{**source,'end':6}]})

@pytest.mark.parametrize('source',[
    {'path':'../secret','start':1,'end':2},
    {'path':'C:/secret','start':1,'end':2},
    {'path':'a.py','start':5,'end':2},
    {'path':'a.py','start':1,'end':2,'sha256':'not-a-hash'},
])
def test_invalid_source_requirement_rejected(tmp_path,source):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('read sources',str(tmp_path),'code','sources')
    service=Guidance(store)
    with pytest.raises(ValueError):service.submit(task['id'],task['revision'],0,'','x','Read',required_sources=[source])
    assert not service.status(task['id'])['guidance']

def test_direct_required_ranges_use_runner_chunks_without_retrying_failed_read(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('read sources',str(tmp_path),'code','ranges')
    service=Guidance(store)
    service.submit(task['id'],task['revision'],0,'','x','Read both ranges',required_sources=[
        {'path':'a.py','start':10,'end':214},{'path':'b.py','start':2,'end':3}])
    actions=[]
    for path,start,lines in [('a.py',10,200),('a.py',210,5),('b.py',2,2)]:
        call=service.next_source_call(task['id'],actions)['tool_calls'][0]['function']
        assert call=={'name':'context_expand','arguments':{'path':path,'start':start,'lines':lines}}
        actions.append({'tool':'context_expand','args':call['arguments'],'created':'2099','state':'complete','result':{'error':'missing'}})
    assert service.next_source_call(task['id'],actions) is None
    assert len(service.missing_evidence(task['id'],actions))==2


def test_evidence_only_preserves_source_and_reports_failed_reads(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('inspect',str(tmp_path),'code','raw')
    service=Guidance(store)
    source={'path':'a.py','start':1,'end':2}
    service.submit(task['id'],task['revision'],0,'','raw','Read source',required_sources=[source],evidence_only=True)
    assert service.evidence_only(task['id'])
    assert service.allowed_tools(task['id'])=={'project_context','context_refresh','context_expand'}
    a={'id':'a','created':'2099-01-01T00:00:00+00:00','tool':'context_expand','state':'complete',
       'args':{'path':'a.py'},'result':{'path':'a.py','start':1,'end':2,'sha256':'a'*64,'text':'x = 1\ny = 2'}}
    packet=service.source_packet(task['id'],[a])
    assert packet['retrieval_complete']
    assert packet['sources'][0]['text']==a['result']['text']
    assert packet['semantic_verified'] is False
    a['result']['error']='read failed'
    packet=service.source_packet(task['id'],[a])
    assert not packet['retrieval_complete'] and packet['missing_evidence']
    assert not packet['sources']


def test_exact_patch_play_and_guidance_preserve_code_and_reject_conflicting_scope(tmp_path):
    import json
    from hub.chatgpt_bridge import action_from_reply
    patch={'candidate_id':'a'*32,'expected_revision':0,'changes':[{'path':'x.py','base_hash':None,'content':'# שלום\nx = "literal"\n'}]}
    action={'id':'patch','task':'Apply exact code','mode':'code','exact_patch':patch}
    assert action_from_reply(json.dumps({'local_agent_action':action}))['exact_patch']==patch
    assert action_from_reply(json.dumps({'local_agent_action':{**action,'allowed_tools':['run_shell']}})) is None
    store=Store(tmp_path/'db.sqlite3');task=store.create('Implement',str(tmp_path),'code','exact')
    service=Guidance(store)
    args=(task['id'],task['revision'],0,'','patch','Apply exact code')
    service.submit(*args,exact_patch=patch);service.submit(*args,exact_patch=patch)
    assert service.status(task['id'])['guidance_revision']==1
    assert service.allowed_tools(task['id'])=={'candidate_patch','candidate_diff'}
    with pytest.raises(Conflict):service.submit(*args,exact_patch={**patch,'expected_revision':1})
    failed={'tool':'candidate_patch','args':patch,'created':'2099','state':'uncertain','result':{}}
    assert service.next_patch_call(task['id'],[failed]) is None

def test_context_read_is_bounded_replay_safe_and_play_validated(tmp_path):
    import json
    from hub.chatgpt_bridge import action_from_reply
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Map only',str(tmp_path),'code','context')
    guide=Guidance(store)
    read={'operation':'search','query':'render'}
    guide.submit(task['id'],task['revision'],0,'','ctx','Search',context_read=read,allowed_tools=['context_search','context_expand'])
    assert guide.allowed_tools(task['id'])=={'context_search'}
    call=guide.next_context_call(task['id'],[])
    fn=call['tool_calls'][0]['function']
    assert fn['name']=='context_search' and fn['arguments']['query']=='render'
    action={'tool':fn['name'],'args':fn['arguments'],'created':'9999','state':'complete'}
    assert guide.next_context_call(task['id'],[action]) is None
    envelope={'local_agent_action':{'id':'map-one','task':'Search project','mode':'code','context_read':read}}
    assert action_from_reply(json.dumps(envelope))['context_read']['operation']=='search'
    envelope['local_agent_action']['context_read']={'operation':'shell'}
    assert action_from_reply(json.dumps(envelope)) is None


def test_context_read_respects_explicit_tool_exclusion(tmp_path):
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Map only',str(tmp_path),'code','excluded')
    with pytest.raises(ValueError,match='excluded'):
        Guidance(store).submit(task['id'],task['revision'],0,'','ctx','Search',context_read={'operation':'search','query':'x'},allowed_tools=[])


def test_context_read_skips_autonomous_bootstrap(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from hub.context.runtime import prepare
    store=Store(tmp_path/'hub.sqlite3');task=store.create('Map',str(tmp_path),'code','no-bootstrap')
    Guidance(store).submit(task['id'],task['revision'],0,'','ctx','Brief',context_read={'operation':'brief'})
    asyncio.run(prepare(SimpleNamespace(store=store),task,[]))
    assert store.actions(task['id'])==[]
    assert store.latest_event(task['id'],'source_navigation_delegated')
