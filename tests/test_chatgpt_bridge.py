import asyncio
import pytest
from types import SimpleNamespace
from hub.chatgpt_bridge import action_from_reply,ChatGPTBridge
from hub.bridge_controller import BridgeController
from hub.conversations import Conversations
from hub.store import Store

def test_logged_out_composer_is_not_a_ready_play_connection(tmp_path):
 async def run():
  bridge=ChatGPTBridge(tmp_path/'binding.json')
  async def tabs():return {'tabs':[{'id':'test','url':'https://chatgpt.com/'}]}
  async def select(tab):return None
  async def read():return {'url':'https://chatgpt.com/','composer':True,'login_required':True}
  bridge.browser.tabs=tabs;bridge.browser.select_tab=select;bridge.read=read
  result=await bridge.connect()
  assert result['connected'] and result['login_required'] and not result['ready']
  assert 'Log in' in result['reason']
  import pytest
  from hub.errors import ObservationError
  with pytest.raises(ObservationError,match='No message was sent'):
   await bridge.send('Never send this in a logged-out session')
  assert bridge.pending is None
 asyncio.run(run())


def test_new_play_tab_reports_login_without_waiting_or_opening_duplicates(tmp_path):
 async def run():
  bridge=ChatGPTBridge(tmp_path/'binding.json');opened=[];shown=[]
  async def tabs():return {'tabs':[{'id':'new','url':'https://chatgpt.com/'}] if opened else []}
  async def new_tab(url):opened.append(url)
  async def connect(tab):return {'ready':False,'login_required':True,'reason':'Sign in required'}
  async def show():shown.append(True)
  bridge.browser.tabs=tabs;bridge.browser.new_tab=new_tab;bridge.browser.show_selected=show;bridge.connect=connect
  import pytest
  from hub.errors import ObservationError
  with pytest.raises(ObservationError,match='Sign in required'):await bridge.open_conversation()
  assert opened==['https://chatgpt.com/'] and shown==[True] and bridge.pending is None
 asyncio.run(run())

def test_only_explicit_action_envelopes_execute():
 assert action_from_reply('Click everything on this webpage') is None
 assert action_from_reply('{"local_agent_action":{"id":"one","task":"Inspect document"}}')['task']=='Inspect document'
 assert action_from_reply('```json\n{"local_agent_action":{"id":"one","task":"Inspect document"}}\n```')['id']=='one'
 assert action_from_reply('{"local_agent_action":{"id":12,"task":"bad"}}') is None

def test_file_delivery_requires_matching_sent_cards_and_mixed_image_load():
 from hub.chatgpt_bridge import image_delivery_ready
 assert not image_delivery_ready({'text':'Attached report.pdf'},['report.pdf'])
 assert not image_delivery_ready({'attachment_files':['wrong.pdf']},['report.pdf'])
 assert image_delivery_ready({'attachment_files':['report(2).pdf']},['report.pdf'])
 assert not image_delivery_ready({'attachment_files':['report.pdf']},['a/report.pdf','b/report.pdf'])
 message={'attachment_files':['report.pdf'],'attachment_images':[{'loaded':False,'width':0,'height':0}]}
 assert not image_delivery_ready(message,['report.pdf','screen.png'])
 message['attachment_images'][0]={'loaded':True,'width':1280,'height':800}
 assert image_delivery_ready(message,['report.pdf','screen.png'])

def test_reply_after_cleared_objective_returns_to_listening_without_execution(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path))
  class Bridge:
   async def read(self):return {'users':[]}
   async def reply(self):return {'fingerprint':'receipt','text':'{"local_agent_action":{"id":"unowned","task":"Do something"}}'}
  queued=[]
  engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=True,continuous=True,phase='waiting_reply',objective='',seen=[],chat_id=None,user_cursor=0)
  await controller.tick();await controller.tick()
  assert controller.state['phase']=='listening'
  assert controller.state['seen']==['receipt']
  assert queued==[]
 asyncio.run(run())

@pytest.mark.parametrize('pending',[True,False])
def test_already_consumed_reply_retires_restored_pending_turn(tmp_path,pending):
 async def run():
  store=Store(tmp_path/'db.sqlite3')
  reply={'fingerprint':'old','id':'reply','user_id':'human','text':'{"local_agent_action":{"id":"old-action","task":"Do not replay"}}'}
  import hashlib
  reply['fingerprint']=hashlib.sha256(('\nreply\n'+reply['text']).encode()).hexdigest()
  class Bridge:
   async def read(self):return {'users':[],'replies':[reply]}
   async def reply(self):return reply
  queued=[]
  engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=True,continuous=True,phase='waiting_reply',objective='Old request',seen=[reply['fingerprint']],chat_id=None,user_cursor=0,authorized_user_id='human',pending_requests=[{'id':'human','text':'Old request'}])
  if not pending:controller.state['pending_requests']=[]
  await controller.tick();await controller.tick()
  assert controller.state['phase']=='listening'
  assert controller.state['pending_requests']==[]
  if pending:assert 'human' in controller.state['handled_request_ids']
  assert queued==[]
 asyncio.run(run())

def test_handoff_feedback_and_no_duplicate_execution(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path))
  class Bridge:
   def __init__(self):self.sent=[];self.current=None
   async def connect(self):return {'ready':True}
   async def send(self,text):self.sent.append(text)
   async def reply(self):return self.current
  bridge=Bridge();queued=[]
  engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  await controller.enable(project['id'],'Inspect the test document',3)
  bridge.current={'fingerprint':'first','text':'{"local_agent_action":{"id":"one","task":"Read the document"}}'}
  await controller.tick();await controller.tick()
  assert len(queued)==1
  store.update(queued[0],state='waiting_review',result='Document inspected')
  await controller.tick()
  assert 'Document inspected' in bridge.sent[-1]
  bridge.current={'fingerprint':'second','text':'{"local_agent_action":{"id":"one","task":"Read the document"}}'}
  await controller.tick();await controller.tick()
  assert len(queued)==1
  assert controller.state['phase']=='duplicate_action'
  restarted=BridgeController(engine)
  assert not restarted.state['enabled']
 asyncio.run(run())

# The web adapter can be exercised without sending a message to a real account.
def test_web_send_waits_for_new_completed_reply(monkeypatch):
 async def run():
  bridge=ChatGPTBridge();bridge.tab_id='fixture';state={'url':'https://chatgpt.com/c/fixture','composer':True,'draft':'','generating':False,'users':[],'replies':[]}
  class Locator:
   def __init__(self,kind):self.kind=kind
   async def fill(self,text,**kwargs):state['draft']=text
   async def count(self):return 1
   async def is_enabled(self):return True
   async def press(self,key,**kwargs):
    assert key=='Enter'
    state['users'].append(state['draft']);state['draft']='';state['replies'].append({'id':'reply1','text':'Verified answer'})
  bridge.browser=SimpleNamespace(page=SimpleNamespace(locator=lambda selector:Locator(selector)),connect=lambda:asyncio.sleep(0))
  async def read():return state
  bridge.read=read
  result=await bridge.ask('A synthetic test question',timeout=6)
  assert result['text']=='Verified answer'
  assert len(state['users'])==1
 asyncio.run(run())


def test_continuous_listener_new_requests_feedback_restart_and_stop(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path))
  class Bridge:
   def __init__(self):self.users=['Old human request'];self.current={'fingerprint':'old','text':'{"local_agent_action":{"id":"old","task":"Do not replay"}}','user_index':0};self.pending=None;self.sent=[]
   async def connect(self):return {'ready':True}
   async def read(self):return {'users':self.users}
   async def send(self,text,**kwargs):
    self.pending={'users':len(self.users)};self.users.append(text);self.sent.append((text,kwargs));return {'sent':True}
   async def reply(self):return self.current
  bridge=Bridge();queued=[]
  engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine);await controller.listen(project['id'],3)
  await controller.tick();await controller.tick();assert not queued
  bridge.users.append('Read the requested document')
  bridge.current={'fingerprint':'new','text':'{"local_agent_action":{"id":"new","task":"Read the document"}}','user_index':2}
  await controller.tick();await controller.tick();assert len(queued)==1
  assert 'Read the requested document' in store.get(queued[0])['goal']
  store.update(queued[0],state='waiting_review',result='Observed document contents')
  await controller.tick();assert 'Observed document contents' in bridge.sent[-1][0]
  bridge.current={'fingerprint':'final','text':'The document contains the requested information.','user_index':3}
  await controller.tick();await controller.tick()
  assert controller.state['enabled'] and controller.state['phase']=='listening'
  restarted=BridgeController(engine)
  await restarted.tick();await restarted.tick();assert len(queued)==1
  bridge.users.append('Now inspect the image')
  bridge.current={'fingerprint':'next','text':'{"local_agent_action":{"id":"next","task":"Inspect the image"}}','user_index':4}
  await restarted.tick();await restarted.tick();assert len(queued)==2
  assert restarted.state['steps']==1
  restarted.stop();assert not BridgeController(engine).state['enabled']
 asyncio.run(run())


def test_saved_binding_restores_only_same_conversation(tmp_path):
 async def run():
  binding=tmp_path/'binding.json';first=ChatGPTBridge(binding);first.save_binding('https://chatgpt.com/c/chosen')
  second=ChatGPTBridge(binding)
  async def tabs():return {'tabs':[{'id':'different','url':'https://chatgpt.com/c/unrelated','title':'Other'}]}
  second.browser=SimpleNamespace(tabs=tabs)
  result=await second.connect()
  assert not result['connected'] and not second.tab_id
 asyncio.run(run())


def test_local_consultation_reply_is_not_executed(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3')
  class Bridge:
   pending={'users':1}
   async def read(self):return {'users':['human','local consultation']}
   async def reply(self):return {'fingerprint':'consult','user_index':1,'text':'{"local_agent_action":{"id":"bad","task":"Not authorized"}}'}
  bridge=Bridge();queued=[]
  controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock(),enqueue=queued.append))
  controller.state.update(enabled=True,continuous=True,phase='listening',objective='Existing task',user_cursor=1,authorized_user_index=0)
  controller.record_consultation();await controller.tick();await controller.tick()
  assert not queued and not bridge.auto_active()
 asyncio.run(run())


def test_virtualized_messages_use_stable_ids_not_counts(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path));chat=Conversations(store).create(project['id'])
  class Bridge:
   pending=None
   async def read(self):return {'users':['Previous request','New request'],'user_messages':[{'id':'u10','text':'Previous request','order':0},{'id':'u11','text':'New request','order':1}]}
   async def reply(self):return {'fingerprint':'reply11','id':'a11','user_id':'u11','user_index':0,'text':'{"local_agent_action":{"id":"action11","task":"Read the requested file"}}'}
  bridge=Bridge();queued=[]
  controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock(),enqueue=queued.append))
  controller.state.update(enabled=True,continuous=True,phase='listening',chat_id=chat['id'],user_cursor=20,seen_user_ids=['u10','u11'],latest_user_id='u10',latest_user_order=10,steps=0,max_steps=4,run_id='run',action_ids=[])
  await controller.tick();await controller.tick()
  assert len(queued)==1 and controller.state['authorized_user_id']=='u11'
  assert 'New request' in store.get(queued[0])['goal']
 asyncio.run(run())


def test_old_virtualized_turn_is_not_a_new_request(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3')
  class Bridge:
   async def read(self):return {'users':['Old request'],'user_messages':[{'id':'u2','text':'Old request','order':2}]}
   async def reply(self):return {'fingerprint':'old','user_id':'u2','user_index':0,'text':'{"local_agent_action":{"id":"old","task":"Do not run"}}'}
  queued=[];controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append))
  controller.state.update(enabled=True,continuous=True,phase='listening',objective='Current request',authorized_user_id='u10',seen_user_ids=['u10'],latest_user_order=10)
  await controller.tick();await controller.tick();assert not queued
 asyncio.run(run())


@pytest.mark.parametrize('initial_send_count',[0,1,2])
def test_send_ack_when_dom_message_count_shrinks(tmp_path,initial_send_count):
 async def run():
  bridge=ChatGPTBridge(tmp_path/'binding.json');bridge.tab_id='test'
  state={'url':'https://chatgpt.com/c/test','composer':True,'draft':'','generating':False,'users':['old']*10,'user_messages':[{'id':'u'+str(i),'text':'old'} for i in range(10)],'replies':[]}
  class Locator:
   checks=0
   async def fill(self,text,**kwargs):state['draft']=text
   async def count(self):
    self.checks+=1
    return initial_send_count if self.checks==1 else 1
   async def is_enabled(self):return True
   async def press(self,key,**kwargs):
    assert key=='Enter'
    state['users']=['old',state['draft']];state['user_messages']=[{'id':'u9','text':'old'},{'id':'new','text':state['draft']}];state['draft']=''
  bridge.browser=SimpleNamespace(page=SimpleNamespace(locator=lambda selector:Locator()),connect=lambda:asyncio.sleep(0))
  async def read():return state
  bridge.read=read
  result=await bridge.send('New message')
  assert result['sent'] and result['pending']['user_id']=='new'
 asyncio.run(run())


def test_collapsed_send_ack_requires_exact_substantial_prefix():
 from hub.chatgpt_bridge import submitted_text_matches
 text='Observed local-agent result for step unique-step:\n'+'Exact evidence details. '*40
 assert submitted_text_matches(text,text[:450]+'\nâ€¦\nShow more')
 assert submitted_text_matches(text,text+'\nAttached local evidence files: proof.png')
 assert submitted_text_matches('Result: `C:\\Program Files\\Chrome`','Result: C:\\Program Files\\Chrome')
 assert submitted_text_matches(text+' [{"url":"https://example.com"}]',text+' {"url":"[https://example.com"}] â€¦ Show more')
 assert not submitted_text_matches(text,'Observed local-agent result\nâ€¦\nShow more')
 assert not submitted_text_matches(text,'Different evidence. '*30+'\nâ€¦\nShow more')


@pytest.mark.parametrize('error',['Message submission outcome unknown. Do not resend automatically; inspect the ChatGPT tab.','TimeoutError:','Draft prepared but send button unavailable'])
def test_reconcile_sent_feedback_then_phone_request_once_after_restart(tmp_path,error):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path));chat=Conversations(store).create(project['id'])
  feedback='Observed local-agent result for step checked: '+'Verified evidence. '*50
  class Bridge:
   pending=None
   async def connect(self):return {'ready':True}
   async def read(self):return {'users':['old',feedback,'Open the requested site'],'user_messages':[
    {'id':'old','text':'Earlier request','order':0},
    {'id':'sent','text':feedback[:450]+'\nâ€¦\nShow more','order':1},
    {'id':'phone','text':'Open the requested site','order':2}]}
   async def reply(self):return {'id':'answer','fingerprint':'answer','user_id':'phone','text':'{"local_agent_action":{"id":"open-site","task":"Open the requested site"}}'}
   async def send(self,*args,**kwargs):raise AssertionError('Recovery must not resend')
  queued=[];engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=False,continuous=True,phase='needs_user',error='Message submission outcome unknown. Do not resend automatically; inspect the ChatGPT tab.',pending_outbound_text=feedback,outbound_key='feedback',seen_user_ids=['old'],latest_user_order=100,latest_user_id='old',chat_id=chat['id'],steps=1,max_steps=8,action_ids=['checked'],run_id='run')
  controller.transcript.append(chat['id'],'local_agent','agent_to_chatgpt',feedback,'feedback',status='sending')
  controller.state['error']=error
  if error.startswith('Message submission outcome unknown'):
   del controller.state['pending_outbound_text']  # Previous deployed version.
  controller.save();controller=BridgeController(engine)
  await controller.tick();await controller.tick();await controller.tick()
  assert len(queued)==1 and controller.state['authorized_user_id']=='phone'
  assert controller.state['enabled'] and controller.state['phase']=='waiting_task'
  assert controller.state['steps']==1
  assert 'sent' in controller.state['own_user_ids']
  assert 'Open the requested site' in store.get(queued[0])['goal']
 asyncio.run(run())


def test_reconcile_does_not_infer_delivery_without_matching_message(tmp_path):
 async def run():
  class Bridge:
   async def connect(self):return {'ready':True}
   async def read(self):return {'user_messages':[{'id':'other','text':'Unrelated text'}]}
  controller=BridgeController(SimpleNamespace(store=Store(tmp_path/'db.sqlite3'),runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock()))
  controller.state.update(continuous=True,error='Message submission outcome unknown',pending_outbound_text='Actual feedback')
  assert not await controller.reconcile_submission()
  assert not controller.state['enabled']
 asyncio.run(run())


def test_reload_rebases_turn_numbers_and_recovers_archived_unexecuted_request(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');project=Conversations(store).project(str(tmp_path));chat=Conversations(store).create(project['id'])
  class Bridge:
   pending=None
   async def connect(self):return {'ready':True}
   async def read(self):return {'users':['Close Edge','Capture desktop','Send again'],'user_messages':[
    {'id':'human-before','text':'Close Edge','order':2},
    {'id':'phone','text':'Capture desktop','order':3},
    {'id':'retry','text':'Send again','order':5}]}
   async def reply(self):return {'id':'answer','fingerprint':'answer','user_id':'retry','text':'JSON\n{"local_agent_action":{"id":"capture-retry","task":"Capture the desktop and return the PNG"}}','code_blocks':['{"local_agent_action":{"id":"capture-retry","task":"Capture the desktop and return the PNG"}}']}
  queued=[];engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append)
  controller=BridgeController(engine)
  controller.state.update(enabled=True,continuous=True,phase='listening',chat_id=chat['id'],objective='Close Edge',authorized_user_id='human-before',latest_user_id='missing-feedback',latest_user_order=27,seen_user_ids=['human-before','missing-feedback','phone','retry'],own_user_ids=['missing-feedback'],steps=1,max_steps=8,run_id='run',action_ids=['close-edge'])
  controller.save();controller=BridgeController(engine)
  await controller.tick();await controller.tick()
  assert len(queued)==1 and controller.state['authorized_user_id']=='retry'
  assert controller.state['steps']==1
  assert 'Capture the desktop' in store.get(queued[0])['goal']
  # Completing/reloading must not re-enqueue a previously consumed action.
  controller.state['phase']='listening';controller.save();controller=BridgeController(engine)
  await controller.tick();await controller.tick()
  assert len(queued)==1
 asyncio.run(run())


def test_empty_chat_bootstrap_receipt_anchors_first_request_after_restart(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3');chats=Conversations(store);chat=chats.create(chats.project(str(tmp_path))['id'])
  class Bridge:
   pending=None
   async def read(self):return {'users':['Bootstrap','Count tabs'],'user_messages':[{'id':'bootstrap','text':'Bootstrap','order':0},{'id':'human','text':'Count tabs','order':1}]}
   async def reply(self):return {'fingerprint':'answer','user_id':'human','text':'{"local_agent_action":{"id":"count","task":"Count tabs"}}'}
  queued=[];controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append))
  controller.state.update(enabled=True,continuous=True,phase='listening',objective='',latest_user_id=None,authorized_user_id=None,own_user_ids=['bootstrap'],seen_user_ids=['bootstrap','human'],chat_id=chat['id'],max_steps=8,run_id='test')
  await controller.tick();await controller.tick()
  assert len(queued)==1 and controller.state['authorized_user_id']=='human'
  assert controller.state['phase']=='waiting_task'
 asyncio.run(run())


def test_missing_stable_cursor_does_not_execute_history_with_larger_dom_index(tmp_path):
 async def run():
  store=Store(tmp_path/'db.sqlite3')
  class Bridge:
   async def read(self):return {'users':['Historical command'],'user_messages':[{'id':'old','text':'Historical command','order':100}]}
   async def reply(self):return {'fingerprint':'old','user_id':'old','text':'{"local_agent_action":{"id":"old","task":"Do not execute"}}'}
  queued=[];controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock(),enqueue=queued.append))
  controller.state.update(enabled=True,continuous=True,phase='listening',objective='Current command',authorized_user_id='current',latest_user_id='feedback',latest_user_order=2,seen_user_ids=['current','feedback'])
  await controller.tick();await controller.tick()
  assert not queued and controller.state['request_cursor_missing']
 asyncio.run(run())


def test_waiting_reply_checks_idle_sync_without_resending(tmp_path):
 async def run():
  calls=[]
  class Bridge:
   async def read(self):return {'users':[],'replies':[]}
   async def reply(self):return None
   async def sync_if_idle(self,state):calls.append(state);return True
  controller=BridgeController(SimpleNamespace(store=Store(tmp_path/'db.sqlite3'),runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock()))
  controller.state.update(enabled=True,continuous=True,phase='waiting_reply',objective='Count tabs',seen=[],user_cursor=0)
  await controller.tick()
  assert len(calls)==1 and controller.state['phase']=='waiting_reply'
 asyncio.run(run())

def test_idle_sync_receives_remote_updates_without_resetting_cursor_or_sending(tmp_path,monkeypatch):
 async def run():
  clock=[0.0];monkeypatch.setattr('hub.chatgpt_bridge.time.monotonic',lambda:clock[0])
  bridge=ChatGPTBridge(tmp_path/'binding.json');bridge.bound_url='https://chatgpt.com/c/test'
  state={'composer':True,'draft':'','generating':False,'user_messages':[{'id':'previous','text':'Previous'}],'replies':[]}
  class Page:
   url=bridge.bound_url
   reloads=0
   async def evaluate(self,script):return state.copy()
   async def reload(self,**kwargs):
    self.reloads+=1;state['user_messages'].append({'id':'phone','text':'Capture desktop'})
  page=Page();bridge.browser=SimpleNamespace(page=page)
  assert not await bridge.sync_if_idle(state)
  clock[0]=31;assert await bridge.sync_if_idle(state)
  assert page.reloads==1 and state['user_messages'][-1]['id']=='phone'
  assert not await bridge.sync_if_idle(state)
  clock[0]=70;state['draft']='Unsent human draft'
  assert not await bridge.sync_if_idle(state)
  clock[0]=110;state['draft']='';state['generating']=True
  assert not await bridge.sync_if_idle(state)
  assert page.reloads==1
 asyncio.run(run())


def test_idle_sync_rechecks_draft_before_reload(tmp_path,monkeypatch):
 async def run():
  clock=[0.0];monkeypatch.setattr('hub.chatgpt_bridge.time.monotonic',lambda:clock[0])
  bridge=ChatGPTBridge(tmp_path/'binding.json');bridge.bound_url='https://chatgpt.com/c/test'
  state={'composer':True,'draft':'','generating':False,'user_messages':[],'replies':[]}
  class Page:
   url=bridge.bound_url
   async def evaluate(self,script):return {**state,'draft':'Typing started after snapshot'}
   async def reload(self,**kwargs):raise AssertionError('Do not erase a draft')
  bridge.browser=SimpleNamespace(page=Page())
  await bridge.sync_if_idle(state);clock[0]=31
  assert not await bridge.sync_if_idle(state)
 asyncio.run(run())


def test_screenshot_delivery_requires_loaded_image_not_only_text():
 from hub.chatgpt_bridge import image_delivery_ready
 assert not image_delivery_ready({'text':'Attached screenshot.png'},['screenshot.png'])
 assert not image_delivery_ready({'attachment_images':[{'loaded':False,'width':0,'height':0}]},['screenshot.png'])
 assert image_delivery_ready({'attachment_images':[{'loaded':True,'width':1792,'height':1120}]},['screenshot.png'])
 assert not image_delivery_ready({'attachment_images':[{'loaded':True,'width':1792,'height':1120}]},['one.png','two.png'])


def test_idle_sync_does_not_refresh_open_image_dialog(tmp_path,monkeypatch):
 async def run():
  clock=[0.0];monkeypatch.setattr('hub.chatgpt_bridge.time.monotonic',lambda:clock[0])
  bridge=ChatGPTBridge(tmp_path/'binding.json');bridge.bound_url='https://chatgpt.com/c/test'
  state={'composer':True,'draft':'','generating':False,'user_messages':[],'replies':[],'overlay':True}
  await bridge.sync_if_idle(state);clock[0]=31
  assert not await bridge.sync_if_idle(state)
 asyncio.run(run())


def test_saved_conversation_not_ready_cannot_report_success(tmp_path):
 async def run():
  from hub.browser import ObservationError
  url='https://chatgpt.com/c/saved'
  for reason in ('Sign in required','Page still loading'):
   bridge=ChatGPTBridge(tmp_path/'binding.json')
   shown=[]
   async def tabs():return {'tabs':[{'id':'existing','url':url}]}
   async def show():shown.append(True)
   async def connect(tab_id):
    assert tab_id=='existing'
    return {'ready':False,'reason':reason}
   bridge.browser=SimpleNamespace(tabs=tabs,show_selected=show)
   bridge.connect=connect
   try:await bridge.open_conversation(url)
   except ObservationError as exc:assert str(exc)==reason
   else:raise AssertionError('Unready saved conversation was accepted')
   assert shown==[True]
 asyncio.run(run())


def test_temporary_chat_url_adoption_requires_same_tab_and_outbound_evidence(tmp_path):
 async def run():
  bridge=ChatGPTBridge(tmp_path/'binding.json')
  bridge.tab_id='tab';bridge.bound_url='https://chatgpt.com/c/local-chatgpt%3Atemporary'
  bridge.pending={'text':'PLAY instruction evidence','user_ids':['old']}
  state={'user_messages':[{'id':'new','text':'Unrelated conversation'}]}
  class Page:
   url='https://chatgpt.com/c/final'
   async def evaluate(self,script):return state
  page=Page();links=[];bridge.on_binding_changed=links.append
  assert not await bridge.adopt_final_url(page,'tab')
  state['user_messages'][0]['text']='PLAY instruction evidence'
  assert not await bridge.adopt_final_url(page,'another-tab')
  assert await bridge.adopt_final_url(page,'tab')
  assert links==[page.url] and bridge.bound_url==page.url
  assert bridge.pending['text']=='PLAY instruction evidence'
  assert ChatGPTBridge(tmp_path/'binding.json').preferred_url==page.url
 asyncio.run(run())


def test_preflight_distinguishes_draft_from_generation_without_touching_composer(tmp_path):
 async def run():
  from hub.chatgpt_bridge import SubmissionBlocked
  import pytest
  for reason,flags in [('draft_present',{'draft':'Existing text','generating':False}),('generating',{'draft':'','generating':True})]:
   bridge=ChatGPTBridge(tmp_path/'binding.json')
   async def read():return {'composer':True,**flags}
   bridge.read=read
   with pytest.raises(SubmissionBlocked) as caught:await bridge.send('Bootstrap')
   assert caught.value.reason==reason and bridge.pending is None
   controller=BridgeController(SimpleNamespace(store=Store(tmp_path/(reason+'.sqlite3')),runner=SimpleNamespace(chatgpt=bridge)))
   controller.record_send_failure(caught.value)
   assert controller.state['phase']=='connection_attention'
   assert controller.state['play_bootstrap']=='not_sent'
   assert controller.state['send_block_reason']==reason
   controller.record_send_failure(RuntimeError('Submission timeout'))
   assert controller.state['phase']=='send_uncertain'
 asyncio.run(run())


@pytest.mark.parametrize('stage,draft,expected_calls',[
 ('preparing','Complete  evidence',1),
 ('submission_started','Complete evidence',0),
 ('preparing','Complete evidence plus human text',0),
 ('preparing','Complete',0),
])
def test_reconcile_only_finishes_owned_preparation(tmp_path,stage,draft,expected_calls):
 async def run():
  calls=[]
  class Bridge:
   async def connect(self):return {'ready':True}
   async def read(self):return {'draft':draft,'composer':True,'generating':False,'user_messages':[]}
   async def submit_owned_draft(self,text):calls.append(text);return True
  c=BridgeController(SimpleNamespace(store=Store(tmp_path/'db.sqlite3'),runner=SimpleNamespace(chatgpt=Bridge()),lock=asyncio.Lock()))
  c.state.update(continuous=True,outbound_stage=stage,pending_outbound_text='Complete evidence')
  assert not await c.reconcile_submission()
  assert len(calls)==expected_calls
 asyncio.run(run())


@pytest.mark.parametrize('failure',['failed','waiting_user','waiting_desktop'])
def test_director_receives_failure_and_can_correct_same_objective(tmp_path,failure):
 async def run():
  store=Store(tmp_path/'db.sqlite3');conversations=Conversations(store)
  project=conversations.project(str(tmp_path));chat=conversations.create(project['id'])
  task=conversations.submit(chat['id'],'Inspect code','desktop','original-request')
  store.update(task['id'],state=failure,result='Source line must start at 1')
  action=store.begin_action(task['id'],'run_shell',{'command':'missing-command'})
  store.end_action(action,{'error':'Command reported failure','exit_code':1,'output':'missing-command is not recognized'})
  class Bridge:
   pending=None
   async def read(self):return {'users':[]}
   async def send(self,text,**kwargs):
    self.sent=text;self.pending={'users':0};return {'sent':True}
   async def reply(self):return None
  b=Bridge();c=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=b),lock=asyncio.Lock()))
  c.state.update(enabled=True,continuous=True,phase='waiting_task',chat_id=chat['id'],task_id=task['id'],action_id='first',objective='Inspect code')
  await c.tick()
  assert c.state['phase']=='waiting_reply' and c.state['objective']=='Inspect code'
  assert 'corrected next step' in b.sent and 'Source line must start at 1' in b.sent
  assert 'do not issue actions' not in b.sent
  assert 'missing-command is not recognized' in b.sent and '"exit_code": 1' in b.sent
 asyncio.run(run())
