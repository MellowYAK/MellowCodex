"""Reversible, local-only preservation of browser composer text."""
import time
import uuid
from .chatgpt_bridge import COMPOSER


async def manage(controller,chat_id,action,draft_id=None):
    controller.transcript.connection(chat_id)
    if controller.state.get('enabled') or controller.state.get('pending_outbound_text'):
        raise ValueError('Stop listening and reconcile pending delivery first')
    store=controller.engine.store
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS saved_chatgpt_drafts(id TEXT PRIMARY KEY,chat_id TEXT,url TEXT,text TEXT,created REAL)')
        if action=='list':
            return {'items':[dict(r) for r in db.execute('SELECT id,url,created,length(text) characters FROM saved_chatgpt_drafts WHERE chat_id=? ORDER BY created DESC',(chat_id,))]}
        row=db.execute('SELECT * FROM saved_chatgpt_drafts WHERE id=? AND chat_id=?',(draft_id,chat_id)).fetchone() if action=='restore' else None
    if action not in ('archive','restore'):raise ValueError('Unknown draft action')
    if action=='restore' and row is None:raise ValueError('Saved draft not found in this chat')
    bridge=controller.bridge
    state=await bridge.read()
    if not state.get('composer') or state.get('generating') or state.get('login_required'):
        raise ValueError('Composer is unavailable or still generating')
    original=state.get('draft','')
    if action=='restore':
        if original.strip():raise ValueError('Existing draft preserved; archive it first')
        if state['url']!=row['url']:raise ValueError('Open the original draft URL before restoring')
        replacement=row['text']
    else:
        if not original.strip():return {'changed':False,'reason':'No draft'}
        draft_id=uuid.uuid4().hex;replacement=''
        with store.connect() as db:
            db.execute('INSERT INTO saved_chatgpt_drafts VALUES(?,?,?,?,?)',(draft_id,chat_id,state['url'],original,time.time()))
    fresh=await bridge.read()
    if fresh['url']!=state['url'] or fresh.get('draft','')!=original or fresh.get('generating'):
        raise ValueError('Composer changed; saved copy retained, browser not modified')
    await bridge.browser.page.locator(COMPOSER).fill(replacement,timeout=8000)
    after=await bridge.read()
    # Qt's background contenteditable can select text without applying fill('').
    # Retry only the observed unchanged draft, never different/new user text.
    if action=='archive' and after['url']==state['url'] and after.get('draft','')==original and not after.get('generating'):
        editor=bridge.browser.page.locator(COMPOSER)
        await editor.press('ControlOrMeta+A',timeout=8000)
        await editor.press('Backspace',timeout=8000)
        after=await bridge.read()
    verified=after['url']==state['url'] and after.get('draft','').strip()==replacement.strip()
    return {'draft_id':draft_id,'action':action,'verified':verified,'saved_copy_retained':True,'sent':False}
