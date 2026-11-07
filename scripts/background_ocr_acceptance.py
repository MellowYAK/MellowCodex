import asyncio,json,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.store import Store
from hub.engine import Engine
from hub.config import ARTIFACTS
async def main():
 print('Initializing actual agent engine',flush=True)
 store=Store(ARTIFACTS/'background-ocr-acceptance.sqlite3');engine=Engine(store)
 from hub.errors import DesktopUnavailable
 execute=engine.runner.execute
 async def guarded(task,name,args):
  if name in ('observe_screen','capture_screenshot','focus_window','desktop_action'):
   raise DesktopUnavailable('Acceptance fixture: physical desktop unavailable; file operations remain available')
  if name=='chatgpt_ask':raise AssertionError('ChatGPT feedback forbidden in this acceptance')
  return await execute(task,name,args)
 engine.runner.execute=guarded
 chat=engine.chat
 seeded=False
 async def first_desktop_then_real(messages,catalog):
  nonlocal seeded
  if not seeded:
   seeded=True
   return {'role':'assistant','content':'Acceptance fixture: first desktop observation','tool_calls':[{'function':{'name':'observe_screen','arguments':{}}}]},{}
  return await chat(messages,catalog)
 engine.chat=first_desktop_then_real
 task=store.create('נסה קודם לצפות בשולחן העבודה. אם אינו זמין, המשך בכל זאת לקרוא את התמונה visual-document-test.jpg בתיקיית העבודה באמצעות image_ocr. החזר בעברית את סוג המסמך ותמלול סעיפים 16 ו-17 בלבד. אל תנחש מילים לא ברורות. אל תפנה ל-ChatGPT: המשוב כבוי. ציין את הכלים שבהם השתמשת ואת מגבלות הבדיקה.', 'E:/AI/repos/sandbox','desktop',uuid.uuid4().hex)
 print('Task '+task['id'],flush=True);start=time.monotonic()
 try:await asyncio.wait_for(engine.run(task['id']),timeout=180)
 finally:
  report={'task':store.get(task['id']),'actions':store.actions(task['id']),'seconds':round(time.monotonic()-start,2)}
  (ARTIFACTS/'background-ocr-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
  print(json.dumps({'state':report['task']['state'],'result':report['task']['result'],'tools':[a['tool'] for a in report['actions']],'seconds':report['seconds']},ensure_ascii=True),flush=True)
  engine.runner.accessibility.executor.shutdown(wait=False)
asyncio.run(main())

