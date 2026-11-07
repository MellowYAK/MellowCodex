"""Read real ChatGPT feedback through the local Engine in an isolated store."""
import asyncio,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
async def main():
 from hub.config import ROOT,OLLAMA
 from hub.store import Store
 from hub.conversations import Conversations
 from hub.engine import Engine
 from hub.model_settings import ModelSettings,save_settings
 import httpx
 if ROOT!=Path('E:/AI/audits/chatgpt-memory-feedback-live-20261107'):raise RuntimeError('Expected isolated live-feedback root')
 async with httpx.AsyncClient(trust_env=False) as client:
  if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Another model resident')
 save_settings(ModelSettings(visual_guidance=False,keep_alive_minutes=1))
 original=json.loads((ROOT/'pending-review.json').read_text(encoding='utf-8'))
 store=Store(ROOT/'hub.sqlite3');chats=Conversations(store)
 task=chats.submit(original['chat_id'],'בדוק באמצעות כלי המשובים השמורים מה ChatGPT אימת לגבי צילום המסך שביקשתי. האם ביקשתי כל שולחן העבודה או רק את חלון Notepad? האם המשוב מוכיח שהפעולה בוצעה? אל תשלח שוב הודעה ואל תבצע פעולה במחשב.','inspect','feedback-continuity-live')
 started=time.monotonic()
 try:
  try:await asyncio.wait_for(Engine(store).run(task['id']),180)
  except TimeoutError:store.update(task['id'],state='paused',result='Acceptance timeout')
  final=store.get(task['id']);actions=store.actions(task['id'])
  used=any(a['tool']=='conversation_memory_reviews' and any(r['id']==original['id'] and r['response']['verdict']=='confirmed' for r in (a.get('result') or {}).get('items',[])) for a in actions)
  report={'task':final,'actions':actions,'elapsed':round(time.monotonic()-started,2),'real_feedback_read':used}
  (ROOT/'engine-continuity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'state':final['state'],'elapsed':report['elapsed'],'real_feedback_read':used,'answer':final['result']},ensure_ascii=False))
 finally:
  async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
   await client.post(OLLAMA+'/api/generate',json={'model':'qwen3.5:4b','keep_alive':0,'stream':False})
   print(json.dumps({'resident_models':(await client.get(OLLAMA+'/api/ps')).json()}))
asyncio.run(main())
