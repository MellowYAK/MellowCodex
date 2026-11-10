import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import asyncio
if sys.flags.isolated:
    class _IsolatedMark:
        @staticmethod
        def parametrize(*args, **kwargs):
            return lambda function: function
    class _IsolatedPytest:
        mark = _IsolatedMark()
    pytest = _IsolatedPytest()
else:
    import pytest
from types import SimpleNamespace
from hub.store import Store
from hub.conversations import Conversations
if not sys.flags.isolated:
    from hub.bridge_controller import BridgeController

@pytest.mark.parametrize('code_block',[False,True])
def test_busy_chat_preserves_request_until_admitted(tmp_path,code_block):
 async def run():
  store=Store(tmp_path/'db');conversations=Conversations(store)
  chat=conversations.create(conversations.project(str(tmp_path))['id'])
  busy=conversations.submit(chat['id'],'Existing work','desktop','existing')
  action='{"local_agent_action":{"id":"new-action","task":"Handle the new request"}}'
  reply={'fingerprint':'new-reply','id':'reply','user_id':'new','text':'Proposed action' if code_block else action,'code_blocks':[action] if code_block else []}
  class Bridge:
   async def read(self):return {'users':['old','new request'],'user_messages':[{'id':'old','text':'old','order':0},{'id':'new','text':'new request','order':1}]}
   async def reply(self):return reply
  queued=[];engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=True,continuous=True,phase='listening',chat_id=chat['id'],authorized_user_id='old',latest_user_id='old',seen_user_ids=['old'],max_steps=8,run_id='run')
  async def remote(*args,**kwargs):
   # Starting the task must not depend on remote messaging being available.
   assert len(queued)==1
  controller.notify_remote=remote
  await controller.tick();await controller.tick()
  assert not queued and 'new-reply' not in controller.state['seen']
  assert controller.state['pending_requests'][0]['id']=='new'
  assert 'new' not in controller.state.get('handled_request_ids',[])
  assert controller.state['dispatch_wait_reason']
  store.update(busy['id'],state='done')
  await controller.tick()
  assert len(queued)==1 and controller.state['phase']=='waiting_task'
  assert not controller.state['pending_requests'] and 'new-reply' in controller.state['seen']
  assert 'dispatch_wait_reason' not in controller.state
  await controller.tick()
  assert len(queued)==1
 asyncio.run(run())

def test_current_chatgpt_json_label_is_parsed_without_pre_tag():
 from hub.chatgpt_bridge import action_from_reply
 assert action_from_reply('JSON\n{"local_agent_action":{"id":"pdf","task":"Save article"}}')['id']=='pdf'
 assert action_from_reply('Quoted instructions: JSON\n{"local_agent_action":{"id":"pdf","task":"Save article"}}') is None

def test_failure_keeps_listener_and_next_request_runs_without_replay(tmp_path):
 async def run():
  store=Store(tmp_path/'db');p=Conversations(store).project(str(tmp_path));chat=Conversations(store).create(p['id'])
  old=Conversations(store).submit(chat['id'],'Close Explorer','desktop','old')
  uncertain=store.begin_action(old['id'],'desktop_action',{'action':'click'})
  store.update(old['id'],state='waiting_user',result='Invalid window handle')
  class Bridge:
   async def read(self):return {'users':['Close Explorer','Save PDF'],'user_messages':[{'id':'old','text':'Close Explorer','order':0},{'id':'new','text':'Save PDF','order':1}]}
   async def reply(self):return {'fingerprint':'pdf','id':'reply','user_id':'new','text':'{"local_agent_action":{"id":"pdf","task":"Save requested article PDF"}}'}
   async def send(self,text):
    assert 'Invalid window handle' in text
    assert 'inspect it before retrying' in text
    return {'sent':True}
  queued=[];engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=True,continuous=True,phase='waiting_task',task_id=old['id'],chat_id=chat['id'],authorized_user_id='old',latest_user_id='old',seen_user_ids=['old'],max_steps=8,run_id='run')
  await controller.tick()
  assert controller.state['enabled'] and controller.state['phase']=='waiting_reply'
  await controller.tick();await controller.tick()
  assert len(queued)==1 and 'Save PDF' in store.get(queued[0])['goal']
  assert store.actions(old['id'])[0]['id']==uncertain and store.actions(old['id'])[0]['state']=='pending'
  rows=controller.transcript.list(chat['id'])
  assert any('Invalid window handle' in m['text'] for m in rows)
  await engine.lock.acquire()
  store.update(queued[0],state='running')
  await controller.tick()
  engine.lock.release()
  assert any('התחלתי' in m['text'] for m in controller.transcript.list(chat['id']))
 asyncio.run(run())

def test_explorer_close_never_targets_desktop_or_shutdown(monkeypatch):
 from hub.applications import Applications
 calls=[]
 class Function:
  def __init__(self,fn):self.fn=fn
  def __call__(self,*args):return self.fn(*args)
 windows=[{'hwnd':1,'executable':'C:/Windows/explorer.exe','class_name':'Progman'}, {'hwnd':2,'executable':'C:/Windows/explorer.exe','class_name':'CabinetWClass'}]
 class Desktop:
  user=SimpleNamespace(GetAncestor=Function(lambda hwnd,kind:hwnd.value),PostMessageW=Function(lambda hwnd,*args:calls.append(hwnd) or True))
  def windows(self):return windows[:1] if calls else windows
 desktop=Desktop();app=Applications(desktop,None)
 monkeypatch.setattr("ctypes.WinDLL",lambda *a,**k:desktop.user)
 async def find(q):return {'windows':desktop.windows(),'installed':[{'executable':'C:/Windows/explorer.exe'}],'process_count':1}
 async def sleep(_):pass
 app.find=find;monkeypatch.setattr('hub.applications.asyncio.sleep',sleep);monkeypatch.setattr('hub.preferences.load_input_mode',lambda state:'quiet')
 result=asyncio.run(app.close('explorer.exe'))
 assert calls==[2] and result['closed_verified'] and result['process_count']==1

def test_cancelled_action_reconciles_only_after_runner_ends(tmp_path,monkeypatch):
 from hub import app as api
 from hub.store import Conflict
 s=Store(tmp_path/'recovery.db'); chats=Conversations(s); chat=chats.create(chats.project(str(tmp_path))['id'])
 t=chats.submit(chat['id'],'Inert synthetic work','code','first')
 action=s.begin_action(t['id'],'synthetic_no_effect',{'noop':True})
 s.update(t['id'],state='cancelled')
 monkeypatch.setattr(api,'store',s)
 monkeypatch.setattr(api,'engine',SimpleNamespace(jobs={t['id']:SimpleNamespace(done=lambda:False)}))
 body=api.Reconcile(action_id=action,expected_revision=s.get(t['id'])['revision'],observation='Synthetic task ended, with no external operation invoked.')
 with pytest.raises(Conflict,match='still active'):
  asyncio.run(api.reconcile(t['id'],body))
 assert s.actions(t['id'])[0]['state']=='pending'
 with pytest.raises(Conflict,match='Reconcile the uncertain'):
  chats.submit(chat['id'],'Inert follow-up','code','blocked')
 monkeypatch.setattr(api,'engine',SimpleNamespace(jobs={}))
 result=asyncio.run(api.reconcile(t['id'],body))
 assert result['state']=='cancelled'
 a=s.actions(t['id'])[0]
 assert a['state']=='complete' and a['result']['effect_verified'] is False
 assert a['result']['replay_permitted'] is False
 assert a['result']['status']=='reconciled_unknown'
 assert any(e['kind']=='action_reconciled' for e in s.events(t['id']))
 later=chats.submit(chat['id'],'Inert follow-up','code','after')
 assert later['state']=='queued' and later['id']!=t['id']
 assert s.get(t['id'])['state']=='cancelled'

import unittest
import tempfile
from unittest.mock import patch

import unittest

if sys.flags.isolated:
 class GuardCancelledPendingRecoveryTest(unittest.TestCase):
  def test_synthetic_cancelled_recovery_via_installed_hub_environment(self):
   # Guard remains independent. Execute the genuine behavioral pytest case
   # against the same immutable candidate with the existing installed Hub venv.
   import os, subprocess
   source=Path(__file__).resolve().parents[1]
   hub_python=Path(r"E:\AI\tools\hub-venv\Scripts\python.exe")
   self.assertTrue(hub_python.is_file(),"Installed Hub test interpreter missing")
   self.assertTrue((source/"hub"/"app.py").is_file())
   env=os.environ.copy()
   env["PYTHONDONTWRITEBYTECODE"]="1"
   env["PYTHONNOUSERSITE"]="1"
   result=subprocess.run([str(hub_python),"-m","pytest","tests/test_task_recovery.py",
            "-q","-k","cancelled_action_reconciles_only_after_runner_ends",
            "-p","no:cacheprovider"],cwd=str(source),env=env,
            capture_output=True,text=True,timeout=25,check=False)
   output=(result.stdout or "")+"\n"+(result.stderr or "")
   self.assertEqual(result.returncode,0,output[-3000:])
   self.assertIn("1 passed",output,"Behavioral pytest did not pass one case: "+output[-1500:])

import unittest

class NativeExistingExtensionCatalogTest(unittest.TestCase):
    def test_default_catalog_advertises_reuse_without_installer(self):
        import subprocess
        source=Path(__file__).resolve().parents[1]
        hub_python=Path(r"E:\AI\tools\hub-venv\Scripts\python.exe")
        self.assertTrue(hub_python.is_file())
        script="""from hub.tools import ToolRunner
from hub.model_protocol import normalize_message
for mode in ('code','desktop'):
    catalog=ToolRunner().catalog(mode,'inert-fresh-chat')
    names={x['function']['name'] for x in catalog}
    assert {'extensions_list','extension_run'} <= names,(mode,names)
    assert 'extension_register' not in names,mode
    normalized,changed=normalize_message({'role':'assistant','content':'{"name":"extensions_list","arguments":{}}'},catalog)
    assert changed and normalized['tool_calls'][0]['function']['name']=='extensions_list'
print('NATIVE_EXTENSIONS_CATALOG_PASS')
"""
        result=subprocess.run([str(hub_python),"-B","-c",script],cwd=str(source),capture_output=True,text=True,timeout=20,check=False)
        self.assertEqual(result.returncode,0,(result.stdout or '')+(result.stderr or ''))
        self.assertIn('NATIVE_EXTENSIONS_CATALOG_PASS',result.stdout or '')

class BrowserGuidanceCorrectionAcceptance(unittest.TestCase):
    def test_browser_guidance_existing_context_action_and_cancel_fence(self):
        import subprocess
        source=Path(__file__).resolve().parents[1]
        hub_python=Path(r"E:\AI\tools\hub-venv\Scripts\python.exe")
        script=r"""import tempfile
from pathlib import Path
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.development.guidance import Guidance
from hub.tools import ToolRunner
with tempfile.TemporaryDirectory() as d:
    store=Store(Path(d)/'guidance.sqlite3')
    conv=Conversations(store)
    chat=conv.create(conv.project(d)['id'])
    task=conv.submit(chat['id'],'Harmless project context only','browser','safe-original')
    store.update(task['id'],state='waiting_review')
    rev=store.get(task['id'])['revision']
    guidance=Guidance(store)
    epoch=guidance.begin(task['id'])
    status=guidance.status(task['id'])
    assert status['consumer_epoch']==epoch and status['guidance_revision']==0
    g=guidance.submit(task['id'],rev,0,epoch,'safe-browser-guide','Read only existing project context.',
       allowed_tools=['project_context'],context_read={'operation':'overview','offset':0,'limit':1})
    assert g['guidance_revision']==1
    call=guidance.next_context_call(task['id'],[])
    assert call['tool_calls'][0]['function']=={'name':'project_context','arguments':{'offset':0,'limit':1}}
    runner=ToolRunner();runner.context_store=store
    tools={x['function']['name'] for x in runner.catalog('browser',task['id'])}
    assert 'project_context' in tools and 'browser_navigate' not in tools
    store.update(task['id'],state='cancelled')
    try:
        guidance.submit(task['id'],store.get(task['id'])['revision'],1,epoch,'reject-after-cancel','Should not run',
             allowed_tools=['project_context'])
    except Conflict:pass
    else:raise AssertionError('Cancelled browser task accepted new guidance')
print('BROWSER_GUIDANCE_CONTEXT_AND_CANCEL_FENCE_PASS')
"""
        result=subprocess.run([str(hub_python),"-B","-c",script],cwd=str(source),
                              capture_output=True,text=True,timeout=25,check=False)
        self.assertEqual(result.returncode,0,(result.stdout or '')+(result.stderr or ''))
        self.assertIn('BROWSER_GUIDANCE_CONTEXT_AND_CANCEL_FENCE_PASS',result.stdout or '')

import unittest

class MCPNormalReviewAdapterTest(unittest.TestCase):
    def test_existing_review_route_and_declared_tool_schema(self):
        import subprocess
        source=Path(__file__).resolve().parents[1]
        python=Path(r"E:\AI\tools\hub-venv\Scripts\python.exe")
        script=r"""import asyncio
from hub import mcp_gateway as gateway
id='a'*32
seen=[]
async def local(path,data=None,timeout=15):
    seen.append((path,data))
    assert path=='/api/tasks/'+id+'/review'
    assert data=={'decision':'approve','expected_revision':9,
                  'reason':'Observed exactly one safe project_context read.',
                  'resume_handoff':False}
    return {'id':id,'revision':10,'state':'done'}
original=gateway.local
try:
    gateway.local=local
    result=asyncio.run(gateway.task_review(id,9,'Observed exactly one safe project_context read.'))
finally:
    gateway.local=original
assert result['state']=='done' and result['revision']==10 and len(seen)==1
declared={x.name:x.input_schema for x in asyncio.run(gateway.mcp.list_tools())}
assert 'task_review' in declared and {'task_id','expected_revision','reason'}<=set(declared['task_review']['properties'])
print('MCP_GENERAL_TASK_REVIEW_FORWARD_SCHEMA_PASS')
"""
        result=subprocess.run([str(python),"-B","-c",script],cwd=str(source),capture_output=True,text=True,timeout=25,check=False)
        self.assertEqual(result.returncode,0,(result.stdout or '')+(result.stderr or ''))
        self.assertIn('MCP_GENERAL_TASK_REVIEW_FORWARD_SCHEMA_PASS',result.stdout or '')

import unittest
class NormalDesktopInsideSelfDevelopTest(unittest.TestCase):
 def test_read_capture_and_shared_extensions_do_not_bypass_code_guard(self):
  import subprocess
  root=Path(__file__).resolve().parents[1]
  code=r"""import asyncio,tempfile
from pathlib import Path
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop
from hub.tools import ToolRunner
from hub.engine import Engine
async def main():
 with tempfile.TemporaryDirectory() as d:
  store=Store(Path(d)/'temporary.sqlite3')
  manager=SelfDevelop(store)
  chat=manager.start('Retain development lifecycle','selfdevelop-visual-read-engine-fixture-20261109','mcp')['chat_id']
  conv=Conversations(store)
  screenshot=conv.submit(chat,'Screenshot only, no input','desktop','normal-read-screenshot')
  names={t['function']['name'] for t in ToolRunner().catalog('desktop',screenshot['id'])}
  assert {'capture_screenshot','extensions_list','extension_run'}<=names,names
  assert 'extension_register' not in names
  engine=object.__new__(Engine)
  engine.store=store;engine.jobs={}
  async def no_op(task_id):pass
  engine.run=no_op
  engine.enqueue(screenshot['id'])
  await asyncio.sleep(.01)
  assert store.get(screenshot['id'])['state']=='queued'
  store.update(screenshot['id'],state='done')
  code=conv.submit(chat,'Existing code development still guarded','code','code-step')
  try:engine.enqueue(code['id'])
  except Conflict as e:assert 'guidance' in str(e).lower()
  else:raise AssertionError('code task bypassed guidance')
  try:conv.submit(chat,'No concurrency bypass','desktop','screen-concurrent')
  except Conflict:pass
  else:raise AssertionError('unreviewed code work bypassed')
asyncio.run(main())
print('NORMAL_DESKTOP_WITHIN_SELFDEVELOP_PASS')
"""
  r=subprocess.run([r"E:\AI\tools\hub-venv\Scripts\python.exe",'-B','-c',code],cwd=str(root),text=True,capture_output=True,timeout=25)
  self.assertEqual(r.returncode,0,(r.stdout or '')+(r.stderr or ''))
  self.assertIn('NORMAL_DESKTOP_WITHIN_SELFDEVELOP_PASS',r.stdout)

import unittest
class ChatModeLifeCycleAcceptance(unittest.TestCase):
 def test_persistent_transition_and_active_fences(self):
  import subprocess
  root=Path(__file__).resolve().parents[1]
  code=r"""import tempfile,asyncio
from pathlib import Path
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.development.selfdevelop import SelfDevelop
from hub import mcp_gateway
with tempfile.TemporaryDirectory() as d:
 s=Store(Path(d)/'fixture.sqlite3');dev=SelfDevelop(s)
 chat=dev.start('Persist this development objective','selfdevelop-mode-transition-fixture-20261109','mcp')['chat_id']
 c=Conversations(s);assert c.mode_status(chat)['mode']=='selfdevelop'
 task=c.submit(chat,'Capture once','desktop','shot-fixture')
 try:c.switch_mode(chat,'normal',0,'switch-1-20261109','inspection')
 except Conflict:pass
 else:raise AssertionError('Active task switch accepted')
 s.update(task['id'],state='done')
 a=c.switch_mode(chat,'normal',0,'switch-1-20261109','inspection')
 assert a['mode']=='normal' and a['revision']==1 and c.mode_for_task(task['id'])=='normal'
 assert c.switch_mode(chat,'normal',0,'switch-1-20261109','inspection')['revision']==1
 try:c.switch_mode(chat,'selfdevelop',0,'switch-2-20261109','resume')
 except Conflict:pass
 else:raise AssertionError('Stale revision accepted')
 b=c.switch_mode(chat,'selfdevelop',1,'switch-2-20261109','resume')
 assert b['mode']=='selfdevelop' and b['revision']==2 and b['objective']=='Persist this development objective'
 assert b['transitions']==2 and b['history_preserved']
 assert c.get(chat)['turns'][0]['id']==task['id']
 code=c.submit(chat,'Develop code','code','code-fixture')
 try:dev.guard(code['id'])
 except Conflict:pass
 else:raise AssertionError('Code director guard bypass')
 names={t.name for t in asyncio.run(mcp_gateway.mcp.list_tools())}
 assert 'chat_mode_status' in names and 'chat_mode_switch' in names
print('CHAT_MODE_LIFECYCLE_CAS_PASS')
"""
  p=subprocess.run([r"E:\AI\tools\hub-venv\Scripts\python.exe",'-B','-c',code],cwd=str(root),capture_output=True,text=True,timeout=30)
  self.assertEqual(p.returncode,0,(p.stdout or '')+(p.stderr or ''))
  self.assertIn('CHAT_MODE_LIFECYCLE_CAS_PASS',p.stdout)


import unittest

class OwnerDurationDesktopPinSmoke(unittest.TestCase):
    def test_reviewed_helper_pin_and_variable_expiry_tooltip(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"hub"/"desktop_app.py").read_text(encoding="utf-8")
        assert "6495e6b8b062d34847ac57bb05bdc4054ebe96fb8aa029a4a2456c158f6a76ec" in code
        assert "Chat override duration is owner-configurable (minutes, hours or days)." in code
        assert "Chat overrides last one hour." not in code

