import pytest
from hub.conversations import Conversations
from hub.store import Store,Conflict
from hub.tools import ToolRunner

def test_binding_preserves_history_and_changes_next_workspace(tmp_path):
    old=tmp_path/'old';old.mkdir();new=tmp_path/'new';new.mkdir()
    store=Store(tmp_path/'state.sqlite3');c=Conversations(store)
    chat=c.create(c.project(str(old))['id'])
    task=c.submit(chat['id'],'inspect','desktop','first-request')
    with pytest.raises(Conflict):c.bind_project(chat['id'],str(new))
    result=c.bind_project(chat['id'],str(new),task['id'])
    assert result['effective']=='next_task'
    assert store.get(task['id'])['workspace']==str(old)
    store.update(task['id'],state='done',result='observed')
    following=c.submit(chat['id'],'continue','desktop','second-request')
    assert following['workspace']==str(new)
    assert len(c.get(chat['id'])['turns'])==2

def test_absolute_files_and_relative_scope(tmp_path):
    root=tmp_path/'project';root.mkdir()
    other=tmp_path/'outside.txt';other.write_text('sample')
    runner=ToolRunner()
    for mode in ('desktop','code'):
        assert runner.path({'workspace':str(root),'mode':mode},str(other))==other
    with pytest.raises(ValueError):runner.path({'workspace':str(root),'mode':'inspect'},str(other))
    with pytest.raises(ValueError):runner.path({'workspace':str(root),'mode':'desktop'},'../outside.txt')

def test_desktop_development_tools_are_discoverable():
    runner=ToolRunner();runner.enabled_tool_groups['task']={'development'}
    names={t['function']['name'] for t in runner.catalog('desktop','task')}
    assert {'project_bind','context_search','project_index','candidate_create','candidate_read','candidate_patch','candidate_test','candidate_diff'}<=names
    assert 'window_inspect' not in names
    runner.enabled_tool_groups['task'].add('desktop')
    assert 'window_inspect' in {t['function']['name'] for t in runner.catalog('desktop','task')}

def test_feedback_timeout_reconciles_without_resend(tmp_path):
 import asyncio
 from types import SimpleNamespace
 from hub.bridge_controller import BridgeController
 async def run():
  class Bridge:
   async def connect(self):return {'ready':True}
   async def read(self):return {'user_messages':[{'id':'receipt','text':'Observed result','order':2}]}
   async def send(self,*args,**kwargs):raise AssertionError('Must not resend')
  store=Store(tmp_path/'bridge.sqlite3');c=Conversations(store);chat=c.create(c.project(str(tmp_path))['id'])
  controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock()))
  controller.state.update(enabled=True,continuous=True,phase='sending_feedback',chat_id=chat['id'],pending_outbound_text='Observed result',outbound_baseline=[],outbound_key='feedback')
  await controller.tick()
  assert controller.state['phase']=='waiting_reply'
  assert controller.state['pending_outbound_text'] is None
 asyncio.run(run())

def test_large_file_paging_keeps_exact_text(tmp_path,monkeypatch):
 import asyncio
 import hub.tools as tools
 from hub.model_context import compact_result
 import json
 monkeypatch.setattr(tools,'ARTIFACTS',tmp_path/'artifacts')
 path=tmp_path/'source.txt';text='line source evidence\n'*400;path.write_text(text,encoding='utf-8')
 runner=ToolRunner();task={'id':'paging','workspace':str(tmp_path),'mode':'inspect'}
 async def run():
  chunks=[];offset=0
  while True:
   page=await runner.execute(task,'read_file',{'path':'source.txt','offset':offset})
   page=json.loads(compact_result(page,700))
   assert page['content']==text[offset:offset+len(page['content'])]
   chunks.append(page['content']);offset=page['next_offset']
   if offset is None:break
  assert ''.join(chunks)==text
 asyncio.run(run())

def test_candidate_continues_only_in_same_chat_and_workspace(tmp_path):
 from hub.development.service import Development
 source=tmp_path/'source';source.mkdir();(source/'a.py').write_text('value=1')
 store=Store(tmp_path/'db.sqlite3');c=Conversations(store);p=c.project(str(source));chat=c.create(p['id'])
 first=c.submit(chat['id'],'create','desktop','create-request');dev=Development(store,tmp_path/'candidates')
 candidate=dev.create(first)
 assert candidate['candidate_path']!=str(source)
 store.update(first['id'],state='done')
 second=c.submit(chat['id'],'continue','desktop','continue-request')
 assert dev.inspect(second,candidate['id'])['id']==candidate['id']
 other=c.create(p['id']);unrelated=c.submit(other['id'],'inspect','desktop','unrelated-request')
 with pytest.raises(ValueError):dev.inspect(unrelated,candidate['id'])


def test_candidate_inspection_manifest_is_bounded_for_model():
    import json
    from hub.model_context import compact_result
    value={'id':'candidate','candidate_path':'isolated/source','revision':0,'files':{f'file_{i}.py':'a'*64 for i in range(500)}}
    result=json.loads(compact_result(value,1500))
    assert len(json.dumps(result,ensure_ascii=False))<1800
    assert result['file_count']==500 and result['files_truncated']
    assert result['candidate_path']=='isolated/source'
    assert len(value['files'])==500
