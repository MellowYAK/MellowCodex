"""Real Engine source-bound decisions, corrections and recall after context rollover."""
import asyncio,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
async def main():
 from hub.config import ROOT,STATE,OLLAMA
 from hub.store import Store
 from hub.conversations import Conversations
 from hub.conversation_memory import ConversationMemory
 from hub.engine import Engine
 from hub.model_settings import ModelSettings,save_settings
 import httpx
 if not os.environ.get('LOCAL_AGENT_ROOT') or ROOT==Path('E:/AI'):raise RuntimeError('Isolated audit root required')
 async with httpx.AsyncClient(trust_env=False) as client:
  if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Another model is resident')
 save_settings(ModelSettings(visual_guidance=False,keep_alive_minutes=1))
 store=Store(STATE/'hub.sqlite3');chats=Conversations(store);folder=ROOT/'fixture';folder.mkdir(parents=True,exist_ok=True)
 chat=chats.create(chats.project(str(folder))['id'])['id'];runs=[]
 async def run(goal,idem):
  task=chats.submit(chat,goal,'code',idem);started=time.monotonic()
  try:await asyncio.wait_for(Engine(store).run(task['id']),180)
  except TimeoutError:store.update(task['id'],state='paused',result='Acceptance timed out')
  item={'task':store.get(task['id']),'actions':store.actions(task['id']),'elapsed':round(time.monotonic()-started,2)};runs.append(item)
  return item
 try:
  await run('החלטה לשיחה: שם סביבת הבדיקות הוא ארז-7319. שמור את ההחלטה עם ציטוט המקור באמצעות כלי זיכרון ההחלטות, כדי שלא תאבד בהמשך. אין לבצע פעולות אחרות.','remember-first')
  for i in range(20):
   task=chats.submit(chat,'פניית רקע מספר '+str(i),'inspect','filler-'+str(i));store.update(task['id'],state='done',result='Recorded')
  await run('תיקון להחלטה הקודמת: שם סביבת הבדיקות הוא ברוש-8426 במקום השם הקודם. שמור את התיקון עם ציטוט מקור וקישור להחלטה המוחלפת. אין לבצע פעולות אחרות.','remember-correction')
  for i in range(20):
   task=chats.submit(chat,'פניית רקע נוספת מספר '+str(i),'inspect','more-'+str(i));store.update(task['id'],state='done',result='Recorded')
  last=await run('מה שם סביבת הבדיקות העדכני שבחרתי בשיחה ומה היה השם לפני התיקון? ענה לפי מקורות שמורים, בלי לנחש.','recall')
  anchors=ConversationMemory(Store(store.path)).anchors(chat)
  verified=bool('ברוש-8426' in last['task']['result'] and 'ארז-7319' in last['task']['result'] and any(a['supersedes'] for a in anchors['items']) and all(any(a['tool']=='conversation_anchors' and a['state']=='complete' and not (a.get('result') or {}).get('error') for a in run['actions']) for run in runs[:2]))
  (ROOT/'acceptance.json').write_text(json.dumps({'verified':verified,'chat':chat,'runs':runs,'anchors':anchors},ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'verified':verified,'elapsed':[r['elapsed'] for r in runs],'anchors':len(anchors['items']),'answer':last['task']['result']},ensure_ascii=False))
 finally:
  async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
   await client.post(OLLAMA+'/api/generate',json={'model':'qwen3.5:4b','keep_alive':0,'stream':False})
   print(json.dumps({'resident_models':(await client.get(OLLAMA+'/api/ps')).json()}))
asyncio.run(main())
