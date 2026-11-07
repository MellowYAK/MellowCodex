"""Real Engine recall beyond recent context against explicitly synthetic history."""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


async def main():
    from hub.config import ROOT, STATE, OLLAMA
    from hub.store import Store
    from hub.conversations import Conversations
    from hub.conversation_memory import ConversationMemory
    from hub.engine import Engine
    from hub.model_settings import ModelSettings, save_settings
    import httpx

    if not os.environ.get('LOCAL_AGENT_ROOT') or ROOT == Path('E:/AI'):
        raise RuntimeError('Isolated audit root required')
    async with httpx.AsyncClient(trust_env=False) as client:
        if (await client.get(OLLAMA + '/api/ps')).json().get('models'):
            raise RuntimeError('Another model is resident')
    save_settings(ModelSettings(visual_guidance=False, keep_alive_minutes=1))
    store = Store(STATE / 'hub.sqlite3')
    chats = Conversations(store)
    memory = ConversationMemory(store)
    folder = ROOT / 'fixture'
    folder.mkdir(parents=True, exist_ok=True)
    reuse = os.environ.get('LOCAL_AGENT_RECALL_SEED')
    if reuse:
        import sqlite3
        source = Path(reuse)
        if not source.is_relative_to(Path('E:/AI/audits')):
            raise RuntimeError('Only isolated audit seeds allowed')
        with sqlite3.connect(source) as src, sqlite3.connect(store.path) as dst:
            src.backup(dst)
        with store.connect() as db:
            chat = db.execute('SELECT chat_id FROM chat_tasks ORDER BY rowid LIMIT 1').fetchone()[0]
            source_ids = [r[0] for r in db.execute("SELECT source_task_id FROM conversation_anchors WHERE label IN ('קוד סביבת הקבלה','תיקון קוד סביבת הקבלה') ORDER BY rowid")]
    else:
        chat = chats.create(chats.project(str(folder))['id'])['id']
    if not reuse:source_ids = []
    initial_anchor = None
    for i in range(0 if reuse else 1000):
        goal = f'רישום רקע מספר {i}: אין שינוי בהחלטות הקודמות.'
        if i == 137:
            goal = 'החלטה: קוד סביבת הקבלה הוא תמר-6193.'
        elif i == 413:
            goal = 'תיקון: קוד סביבת הקבלה הוא הדס-9274 במקום הקוד הקודם.'
        elif 700 <= i < 724:
            goal = f'החלטה עצמאית: צבע קטגוריה {i} הוא כחול.'
        task = chats.submit(chat, goal, 'inspect', f'synthetic-{i}')
        store.update(task['id'], state='done', result='נרשם ביומן הבדיקה הסינתטי.')
        if i == 137:
            initial_anchor = memory.remember(chat, task['id'], goal, 'קוד סביבת הקבלה')['id']
            source_ids.append(task['id'])
        elif i == 413:
            memory.remember(chat, task['id'], goal, 'תיקון קוד סביבת הקבלה', initial_anchor)
            source_ids.append(task['id'])
        elif 700 <= i < 724:
            memory.remember(chat, task['id'], goal, f'צבע קטגוריה {i}')
    no_anchors=os.environ.get('LOCAL_AGENT_RECALL_NO_ANCHORS')=='1'
    if no_anchors:
        with store.connect() as db:db.execute('DELETE FROM conversation_anchors WHERE chat_id=?',(chat,))
    question=('מה המזהה הנוכחי של סביבת הקבלה, ואיזה מזהה החלפנו? בדוק בשיחה המקורית, בלי לנחש ובלי לבצע פעולה במחשב.' if no_anchors else
              'מה קוד סביבת הקבלה העדכני שבחרתי בשיחה ומה היה הקוד לפני התיקון? בדוק במקורות השיחה, אל תנחש ואל תבצע פעולה במחשב.')
    task = chats.submit(chat, question, 'inspect', 'recall-retest' if reuse else 'recall')
    packet = memory.packet(task['id'])
    assert 'הדס-9274' not in packet and 'תמר-6193' not in packet
    relevant=memory.relevant_anchors(chat,task['goal'])
    started = time.monotonic()
    try:
        try:
            await asyncio.wait_for(Engine(store).run(task['id']), 180)
        except TimeoutError:
            store.update(task['id'], state='paused', result='Acceptance timed out')
        final = store.get(task['id'])
        actions = store.actions(task['id'])
        retrieval_events=[e for e in store.events(task['id']) if e['kind']=='conversation_sources_retrieved']
        reads = [a for a in actions if a['tool'] in ('conversation_anchors', 'conversation_history') and a['state'] == 'complete']
        supplied=json.dumps(final.get('messages',[{}])[0].get('content',''),ensure_ascii=False)
        evidence = json.dumps([a.get('result') for a in reads], ensure_ascii=False)+supplied
        verified = all(code in final['result'] and code in evidence for code in ('הדס-9274', 'תמר-6193')) and all(s in evidence for s in source_ids) and bool(retrieval_events)
        report = {'retrieval_verified': verified, 'verified': None, 'independent_answer_review_required':True,
                  'synthetic_history_turns': 1000, 'synthetic_anchors': 0 if no_anchors else 26,
                  'real_engine_recall': True, 'target_absent_from_recent_packet': True,
                  'automatic_source_retrieval':relevant,
                  'retrieval_events':retrieval_events,
                  'elapsed': round(time.monotonic()-started, 2), 'source_ids': source_ids,
                  'task': final, 'actions': actions}
        (ROOT / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: report[k] for k in ('retrieval_verified', 'independent_answer_review_required', 'elapsed', 'target_absent_from_recent_packet')}, ensure_ascii=False))
        print(final['result'])
    finally:
        async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
            await client.post(OLLAMA + '/api/generate', json={'model': 'qwen3.5:4b', 'keep_alive': 0, 'stream': False})
            print(json.dumps({'resident_models': (await client.get(OLLAMA + '/api/ps')).json()}))


asyncio.run(main())
