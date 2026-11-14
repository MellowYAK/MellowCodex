"""System status must not block the Hub event loop during gateway readiness."""
import asyncio
import time
from hub import app as hubapp

def test_status_chat_offloads_blocking_collector(monkeypatch):
    seen=[]
    class Chat:
        def submit(self,*args,**kwargs):
            time.sleep(0.10)
            seen.append(args[1])
            return {'id':'status-id','state':'done'}
    monkeypatch.setattr(hubapp,'conversations',lambda:Chat())
    monkeypatch.setattr(hubapp,'public_task',lambda item:item)
    async def exercise():
        body=hubapp.ChatMessage(text='Status',mode='inspect',
                                request_id='status-offload-20261113')
        pending=asyncio.create_task(hubapp.chat_message('a'*32,body))
        await asyncio.sleep(0.02)
        assert not pending.done(), 'Hub event loop blocked on health probe'
        result=await pending
        assert result['state']=='done'
    asyncio.run(exercise())
    assert seen==['Status']
