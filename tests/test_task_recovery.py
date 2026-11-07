import asyncio
import pytest
from types import SimpleNamespace
from hub.store import Store
from hub.conversations import Conversations
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
