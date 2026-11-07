import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.store import Store
from hub.engine import Engine
from hub.config import ARTIFACTS
async def main():
 store=Store(ARTIFACTS/'native-inspection-test.sqlite3');engine=Engine(store)
 import uuid
 task=store.create('בדוק בקריאה בלבד אילו לשוניות פתוחות כעת ביישום Google Chrome במחשב, ומהי הלשונית הפעילה. אל תפתח דפים ואל תשנה דבר. אין להסיק מצב של Chrome מהדפדפן המובנה.', 'E:/AI/repos/sandbox','desktop',uuid.uuid4().hex)
 await asyncio.wait_for(engine.run(task['id']),timeout=120)
 task=store.get(task['id']);actions=store.actions(task['id'])
 report={'state':task['state'],'tools':[a['tool'] for a in actions],'result':task['result'],'observed_tabs':[a['result'].get('tabs') for a in actions if a['tool']=='window_inspect' and a.get('result')]}
 (ARTIFACTS/'native-inspection-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)
 engine.runner.accessibility.executor.shutdown(wait=False)
asyncio.run(main())
