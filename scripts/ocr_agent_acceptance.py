import asyncio,json,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.store import Store
from hub.engine import Engine
from hub.config import ARTIFACTS
async def main():
 print('Initializing actual agent engine',flush=True)
 store=Store(ARTIFACTS/'ocr-agent-acceptance.sqlite3');engine=Engine(store)
 task=store.create(sys.argv[1] if len(sys.argv)>1 else 'קרא את התמונה visual-document-test.jpg בתיקיית העבודה באמצעות image_ocr. החזר בעברית את סוג המסמך ותמלול סעיפים 16 ו-17 בלבד. אל תנחש מילים לא ברורות. אל תפנה ל-ChatGPT: המשוב כבוי. ציין את הכלים שבהם השתמשת ואת מגבלות הבדיקה.', 'E:/AI/repos/sandbox',('desktop' if len(sys.argv)>1 else 'inspect'),uuid.uuid4().hex)
 print('Task '+task['id'],flush=True);start=time.monotonic()
 try:await asyncio.wait_for(engine.run(task['id']),timeout=180)
 except TimeoutError:
  store.update(task['id'],state='failed',result='Acceptance deadline exceeded; no successful result verified.')
 finally:
  report={'task':store.get(task['id']),'actions':store.actions(task['id']),'seconds':round(time.monotonic()-start,2)}
  (ARTIFACTS/(task['id']+'-acceptance.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
  print(json.dumps({'state':report['task']['state'],'result':report['task']['result'],'tools':[a['tool'] for a in report['actions']],'seconds':report['seconds']},ensure_ascii=True),flush=True)
  engine.runner.accessibility.executor.shutdown(wait=False)
asyncio.run(main())
