import asyncio
import pytest
from types import SimpleNamespace
from hub.store import Store
from hub.conversations import Conversations
from hub.bridge_transcript import BridgeTranscript
from hub.chatgpt_drafts import manage


@pytest.mark.parametrize('background_fill',[False,True])
def test_draft_archive_restore_is_reversible_and_never_sends(tmp_path,background_fill):
 async def run():
  store=Store(tmp_path/'db.sqlite3');chats=Conversations(store)
  chat=chats.create(chats.project(str(tmp_path))['id'])['id']
  state={'url':'https://chatgpt.com/','composer':True,'generating':False,'draft':'Human text\nשלום'}
  async def read():return state.copy()
  keys=[]
  async def fill(value,**kwargs):
   if value or not background_fill:state['draft']=value
  async def press(key,**kwargs):
   keys.append(key)
   if key=='Backspace':state['draft']=''
  bridge=SimpleNamespace(read=read,browser=SimpleNamespace(page=SimpleNamespace(locator=lambda _:SimpleNamespace(fill=fill,press=press))))
  controller=SimpleNamespace(state={},engine=SimpleNamespace(store=store),transcript=BridgeTranscript(store),bridge=bridge)
  result=await manage(controller,chat,'archive')
  assert result['verified'] and not result['sent'] and state['draft']==''
  assert keys==(['ControlOrMeta+A','Backspace'] if background_fill else [])
  listing=await manage(controller,chat,'list')
  assert len(listing['items'])==1 and 'text' not in listing['items'][0]
  restored=await manage(controller,chat,'restore',result['draft_id'])
  assert restored['verified'] and state['draft']=='Human text\nשלום'
  import pytest
  with pytest.raises(ValueError,match='Existing draft'):await manage(controller,chat,'restore',result['draft_id'])
  assert len((await manage(controller,chat,'list'))['items'])==1
 asyncio.run(run())
