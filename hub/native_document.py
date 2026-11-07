"""Verified new-tab text workflow for UIA-compatible editors."""
import asyncio
from .errors import ObservationError
from .session import session_status

async def create_document(runner, hwnd, control_name, text, folder):
    if not text or len(text)>4000:raise ValueError('Text must contain 1–4000 characters')
    if not session_status().get('interactive'):
        raise ObservationError('This editor workflow requires interactive text input; no tab or text was changed. File and OCR tasks remain available.')
    before=await runner.accessibility.inspect(hwnd)
    if control_name in ('+','New Tab','New tab'):
        candidates=[e['name'] for e in before['elements'] if e['type']=='Button' and e.get('enabled') and e['name'].casefold() in ('add new tab','new tab')]
        if len(candidates)==1:control_name=candidates[0]
    result=await runner.accessibility.act({'observation_id':before['id'],'control_name':control_name,'action':'invoke'})
    after=result['after_accessibility']
    for _ in range(15):
        if after.get('tab_count')==before.get('tab_count',0)+1:break
        await asyncio.sleep(.2)
        after=await runner.accessibility.inspect(hwnd)
    if after.get('tab_count')!=before.get('tab_count',0)+1:
        raise ObservationError('New tab was not verified; no text was entered. Inspect before retrying.')
    editors=[e for e in after.get('elements',[]) if e['type']=='Document' and e.get('enabled') and e.get('value')=='']
    if len(editors)!=1:raise ObservationError('A unique blank document was not verified; no text was entered.')
    runner.desktop.focus(hwnd)
    # Set focus on the observed editor, not on a guessed point or old tab.
    def focus_editor():
        snapshot=runner.accessibility.snapshot
        if not snapshot or snapshot['id']!=after['id']:raise ObservationError('Editor observation expired')
        snapshot['refs'][editors[0]['ref']].set_focus()
    await asyncio.get_running_loop().run_in_executor(runner.accessibility.executor,focus_editor)
    shot=await asyncio.to_thread(runner.desktop.capture_target,hwnd,folder)
    runner.desktop.act({'observation_id':shot['id'],'action':'type','text':text})
    await asyncio.sleep(.25)
    verification=await runner.accessibility.inspect(hwnd)
    values=[e.get('value') for e in verification['elements'] if e['type']=='Document']
    normalize=lambda value:(value or '').replace('\r\n','\n').replace('\r','\n').rstrip('\n')
    verified=any(normalize(value)==normalize(text) for value in values)
    screenshot=await asyncio.to_thread(runner.desktop.capture_target,hwnd,folder)
    return {'text_verified':verified,'created_new_tab':True,'original_tab_count':before['tab_count'],
            'tab_count':verification['tab_count'],'selected_tab':verification.get('selected_tab'),
            'after':screenshot,'note':'Text compared with fresh UIA document content. Do not retype on mismatch; inspect the created tab.'}
