import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
import pytest
from hub.engine import Engine
from hub.store import Store
from hub.development.guidance import Guidance
from hub.model_settings import ModelSettings

@pytest.mark.parametrize('when',['inference','pending_action'])
@pytest.mark.parametrize('repeat',range(3))
def test_correction_fences_old_plan_same_task(tmp_path,monkeypatch,when,repeat):
 monkeypatch.setattr('hub.model_settings.load_settings',lambda:ModelSettings())
 store=Store(tmp_path/'hub.sqlite3')
 task=store.create('Original browser objective',str(tmp_path),'browser','correction')
 engine=Engine(store);calls=[];sent=[]
 def correct():
  service=Guidance(store);status=service.status(task['id'])
  service.submit(task['id'],status['task_revision'],status['guidance_revision'],status['consumer_epoch'],'correction-1','CURRENT CORRECTION: preserve existing records')
 async def chat(*args,**kwargs):
  calls.append(1)
  if len(calls)>1:
   assert 'CURRENT CORRECTION' in str(args[0])
   store.update(task['id'],state='paused')
   return {'role':'assistant','content':'Stopped test after observing correction'},{}
  if when=='inference':correct()
  call={'function':{'name':'browser_act','arguments':{'action':'click','observation_id':'observed','ref':'e1'}}}
  return {'role':'assistant','tool_calls':[call,call]},{}
 async def execute(*args,**kwargs):
  sent.append(1)
  if when=='pending_action':correct()
  return {'input_sent':True,'dispatch_state':'observed_transition'}
 engine.chat=chat;engine.runner.execute=execute
 asyncio.run(engine.run(task['id']))
 assert len(sent)==(1 if when=='pending_action' else 0)
 assert store.get(task['id'])['goal']==task['goal']
 assert store.latest_event(task['id'],'guidance_dispatch_fence')
 assert len(calls)==2

def test_model_timeout_retains_preflight_without_secret(tmp_path,monkeypatch):
 settings=ModelSettings(context_management='legacy')
 monkeypatch.setattr('hub.model_settings.load_settings',lambda:settings)
 @asynccontextmanager
 async def lease(*args,**kwargs):yield
 monkeypatch.setattr('hub.resources.Resources.inference',lease)
 class Client:
  def __init__(self,**kwargs):pass
  async def __aenter__(self):return self
  async def __aexit__(self,*args):pass
  async def post(self,*args,**kwargs):raise httpx.ReadTimeout('SECRET_TOKEN')
 monkeypatch.setattr('hub.engine.httpx.AsyncClient',Client)
 store=Store(tmp_path/'hub.sqlite3');task=store.create('test',str(tmp_path),'browser','timeout')
 engine=Engine(store)
 with pytest.raises(httpx.ReadTimeout):
  asyncio.run(engine.chat([{'role':'system','content':'Rules'},{'role':'user','content':'Test'}],[],task_id=task['id']))
 preflight=store.latest_event(task['id'],'model_packet_preflight')['data']
 failure=store.latest_event(task['id'],'model_dispatch_failure')['data']
 assert failure['exception_type']=='ReadTimeout' and failure['packet_sha256']==preflight['sha256']
 assert 'SECRET_TOKEN' not in str(store.events(task['id']))

@pytest.mark.parametrize('stop',['paused','cancelled','truncated'])
def test_browser_stop_and_truncated_output_never_dispatch(tmp_path,monkeypatch,stop):
 monkeypatch.setattr('hub.model_settings.load_settings',lambda:ModelSettings())
 store=Store(tmp_path/'hub.sqlite3');task=store.create('Browser objective',str(tmp_path),'browser','stop')
 engine=Engine(store);sent=[]
 async def chat(*args,**kwargs):
  if stop!='truncated':store.update(task['id'],state=stop)
  return {'role':'assistant','tool_calls':[{'function':{'name':'browser_act','arguments':{'action':'click','observation_id':'old','ref':'e1'}}}]},({'done_reason':'length','packet':{'response_tokens':256}} if stop=='truncated' else {})
 async def execute(*args,**kwargs):sent.append(1);return {}
 engine.chat=chat;engine.runner.execute=execute
 asyncio.run(engine.run(task['id']))
 assert not sent
 assert store.get(task['id'])['state']==('waiting_review' if stop=='truncated' else stop)
