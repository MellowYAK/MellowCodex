"""Real local-model recall from an old turn outside the recent context window."""
import asyncio,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from hub.config import ROOT,STATE,OLLAMA
    if not os.environ.get('LOCAL_AGENT_ROOT') or ROOT==Path('E:/AI'):raise RuntimeError('Audit root required')
    from hub.store import Store
    from hub.conversations import Conversations
    from hub.engine import Engine
    from hub.model_settings import ModelSettings,save_settings
    import httpx
    async with httpx.AsyncClient(trust_env=False) as client:
        if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Another model is resident')
    save_settings(ModelSettings(visual_guidance=False,keep_alive_minutes=1))
    store=Store(STATE/'hub.sqlite3');chats=Conversations(store)
    folder=ROOT/'fixture';folder.mkdir(parents=True,exist_ok=True)
    chat=chats.create(chats.project(str(folder))['id'])
    for i in range(22):
        goal='Archive note '+str(i)
        if i==3:goal='החלטת משתמש: שם סביבת הבדיקות הוא ארז-7319. אל תשנה את השם הזה.'
        task=chats.submit(chat['id'],goal,'inspect',str(i));store.update(task['id'],state='done',result='Recorded historical note')
    task=chats.submit(chat['id'],'מה שם סביבת הבדיקות שבחרתי קודם בשיחה? בדוק את ההיסטוריה והחזר את השם המדויק, בלי לנחש.','inspect','recall')
    started=time.monotonic()
    try:
        try:await asyncio.wait_for(Engine(store).run(task['id']),180)
        except TimeoutError:store.update(task['id'],state='paused',result='Acceptance timed out')
        final=store.get(task['id']);actions=store.actions(task['id'])
        evidence={'task':final,'actions':actions,'elapsed_seconds':round(time.monotonic()-started,2),'verified':bool('ארז-7319' in final['result'] and any(a['tool']=='conversation_history' for a in actions))}
        (ROOT/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in evidence.items() if k not in ('task','actions')},ensure_ascii=False));print(final['result'])
    finally:
        async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
            await client.post(OLLAMA+'/api/generate',json={'model':'qwen3.5:4b','keep_alive':0,'stream':False})
            print(json.dumps({'resident_models':(await client.get(OLLAMA+'/api/ps')).json()}))

asyncio.run(main())
