import asyncio
from contextlib import asynccontextmanager
import hmac
import json
from pathlib import Path
import secrets
import shutil
import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import __version__
from .config import ROOT, STATE, ARTIFACTS, MODEL, OLLAMA, PORT
from .engine import Engine
from .store import Store, Conflict
from .hotkey import EmergencyHotkey
from .browser import Browser
from .session_transfer import Pairing,validate_transfer
from .session import session_status
pairing=Pairing()
mobile_pairing=Pairing()

token_file=STATE/'hub.key'
if not token_file.exists():
    token_file.write_text(secrets.token_urlsafe(32),encoding='utf-8')
TOKEN=token_file.read_text(encoding='utf-8').strip()
store=Store(STATE/'hub.sqlite3')
engine=Engine(store)
from .model_catalog import service_for as model_catalog_for,router as model_catalog_router
model_catalog_service=model_catalog_for(store)

@asynccontextmanager
async def lifespan(app):
    owner=(STATE/'runner.lock').open('a+b')
    if os.name=='nt':
        import msvcrt
        owner.seek(0)
        if owner.read(1)==b'':
            owner.write(b'0')
            owner.flush()
        owner.seek(0)
        msvcrt.locking(owner.fileno(),msvcrt.LK_NBLCK,1)
    loop=asyncio.get_running_loop()
    hotkey=EmergencyHotkey(lambda: asyncio.run_coroutine_threadsafe(engine.stop_all(),loop))
    hotkey.start()
    app.state.hotkey=hotkey
    monitor=asyncio.create_task(engine.watch_desktop())
    from .schedules import watch_schedules
    schedule_monitor=asyncio.create_task(watch_schedules(engine))
    from .context.indexing import Indexing
    index_monitor=asyncio.create_task(Indexing(project_context_service()).watch())
    from .bridge_controller import BridgeController
    app.state.bridge=BridgeController(engine);engine.on_stop=app.state.bridge.stop
    bridge_monitor=asyncio.create_task(app.state.bridge.watch())
    from .relay import supervise
    relay_monitor=asyncio.create_task(supervise()) if (STATE/'relay.json').exists() else None
    from .shutdown import Shutdown
    objective_monitor=None
    try:
        model_catalog_service.recover()
        store.recover()
        from .conversations import migrate_legacy
        migrate_legacy(store)
        for task in store.list():
            if task['state']=='queued':
                engine.enqueue(task['id'])
        from .development.selfdevelop import SelfDevelop
        objective_monitor=asyncio.create_task(SelfDevelop(store).watch_objectives(development_service))
        app.state.shutdown=Shutdown(engine,model_catalog_service,
            [monitor,schedule_monitor,index_monitor,bridge_monitor,objective_monitor])
        yield
    finally:
        if objective_monitor:
            objective_monitor.cancel()
            await asyncio.gather(objective_monitor,return_exceptions=True)
        await model_catalog_service.close()
        index_monitor.cancel();await asyncio.gather(index_monitor,return_exceptions=True)
        if relay_monitor:
            relay_monitor.cancel();await asyncio.gather(relay_monitor,return_exceptions=True)
        bridge_monitor.cancel()
        await asyncio.gather(bridge_monitor,return_exceptions=True)
        await engine.runner.chatgpt.browser.disconnect()
        schedule_monitor.cancel()
        await asyncio.gather(schedule_monitor,return_exceptions=True)
        monitor.cancel()
        await asyncio.gather(monitor,return_exceptions=True)
        hotkey.close()
        # A service shutdown preserves idle listening; the user's Stop button does not.
        engine.on_stop=None
        await engine.stop_all(pause_schedules=False)
        await engine.runner.browser.disconnect()
        owner.close()

app=FastAPI(title='Local Agent Hub',version=__version__,lifespan=lifespan,docs_url=None,redoc_url=None)

@app.get('/api/owner-permissions/status')
async def owner_permission_status(chat_id: str = ''):
    # STATUS ONLY. MCP/agent/Guard have no permission-write API.
    from .owner_policy import BrokerReadOnly, public_status
    from .owner_broker import owner_status, owner_snapshot
    status = public_status(owner_snapshot(chat_id), chat_id)
    return {**status, 'broker': owner_status()}


@app.post('/api/lifecycle/shutdown')
async def shutdown_agent(body:dict | None=None):
    from .service_health import submit,active_tasks
    body=body or {}
    if not body.get('confirm_tasks'):
        raise HTTPException(409, {'reason':'Confirm whole-agent task impact in Health and Services first','active_tasks':active_tasks()})
    try:
        return await asyncio.to_thread(submit,'Stop','all',body.get('request_id',''),True)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))

@app.get('/api/lifecycle/status')
async def shutdown_status():
    return app.state.shutdown.status

@app.get('/api/lifecycle/labels')
async def shutdown_labels():
    from .i18n import t
    return {key:t('lifecycle.'+key,'he') for key in ('shutdown','stopping')}
STATIC=Path(__file__).parent/'static'
from .context.api import router as context_router
def project_context_service():
    from .context import ProjectContext
    from .conversations import Conversations
    return ProjectContext(STATE,Conversations(store))
app.include_router(context_router(project_context_service))
from .development.api import router as development_router
def development_service():
    from .development.service import Development
    from .config import ROOT
    return Development(store,ROOT/'candidates')
app.include_router(development_router(development_service))
app.include_router(model_catalog_router(lambda:model_catalog_service))
from .guardian.jobs import router as upgrade_router
app.include_router(upgrade_router(ROOT))
from .skill_shops import router as skill_shops_router, action_router as skill_shops_action_router
app.include_router(skill_shops_action_router())
app.include_router(skill_shops_router())
ALLOWED_HOSTS={f'127.0.0.1:{PORT}',f'localhost:{PORT}','testserver'}
ALLOWED_ORIGINS={f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}
ALLOWED_HOSTS.add(f'100.78.233.10:{PORT}')
ALLOWED_ORIGINS.add(f'http://100.78.233.10:{PORT}')

@app.middleware('http')
async def local_only(request: Request, call_next):
    if request.headers.get('host') not in ALLOWED_HOSTS:
        return JSONResponse({'detail':'Invalid local host'},status_code=403)
    if request.url.path.startswith('/api/'):
        key=request.headers.get('x-hub-key') or request.cookies.get('hub_session','')
        if not hmac.compare_digest(key,TOKEN):
            return JSONResponse({'detail':'Open the local application first'},status_code=401)
        if request.method not in ('GET','HEAD'):
            origin=request.headers.get('origin')
            if not request.headers.get('x-hub-key') and origin not in ALLOWED_ORIGINS:
                return JSONResponse({'detail':'Same-origin request required'},status_code=403)
    lifecycle=getattr(app.state,'shutdown',None)
    if lifecycle and lifecycle.status['state']!='idle' and request.method not in ('GET','HEAD') and not request.url.path.startswith('/api/lifecycle/'):
        return JSONResponse({'detail':'Agent shutdown in progress; new work is disabled'},status_code=503)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'"
    return response

@app.exception_handler(Conflict)
async def conflict_handler(request, exc):
    return JSONResponse({'detail':str(exc)},status_code=409)

@app.exception_handler(KeyError)
async def missing_handler(request, exc):
    return JSONResponse({'detail':'Not found'},status_code=404)

@app.exception_handler(ValueError)
async def invalid_handler(request, exc):
    return JSONResponse({'detail':str(exc)},status_code=400)

@app.get('/')
async def index(request:Request):
    local=request.client and request.client.host in ('127.0.0.1','::1','testclient')
    if not local and not hmac.compare_digest(request.cookies.get('hub_session',''),TOKEN):
        return HTMLResponse('<html dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><h2>Local Agent</h2><p>פתח את קישור החיבור האישי שקיבלת כדי להתחבר לסוכן.</p></html>',status_code=401)
    response=FileResponse(STATIC/'index.html')
    response.set_cookie('hub_session',TOKEN,httponly=True,samesite='strict')
    return response

@app.post('/api/mobile/pair')
async def pair_mobile():
    import time
    result=mobile_pairing.issue()
    mobile_pairing.codes[result['code']]=time.monotonic()+1800
    return {'url':f'http://100.78.233.10:{PORT}/connect?code='+result['code'],'expires_seconds':1800}

@app.get('/connect')
async def connect_mobile(code:str):
    mobile_pairing.consume(code)
    response=RedirectResponse('/',status_code=303)
    response.set_cookie('hub_session',TOKEN,httponly=True,samesite='strict',max_age=86400*7)
    return response

@app.get('/static/{name}')
async def static_file(name: str):
    if name not in ('app.js','app.css','context.js','development.js','models.js','richtext.js','continuity.js','shell.js','product.css','delegation.js','owner-permissions.js'):
        raise HTTPException(404)
    return FileResponse(STATIC/name)

@app.get('/api/capabilities')
async def capabilities():
    from .model_settings import load_settings
    selected_model=load_settings(STATE).model
    model_status={'online':False,'available':False,'name':selected_model}
    async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
        try:
            response=await client.get(OLLAMA+'/api/tags')
            response.raise_for_status()
            model_status.update(online=True,available=any(m['name']==selected_model for m in response.json().get('models',[])))
        except Exception as exc:
            model_status['error']=str(exc)
    return {'model':model_status,'root':str(ROOT),'free_gb':round(shutil.disk_usage(ROOT).free/1024**3,1),'desktop':{'driver':'Windows SendInput + MSS + Windows-MCP accessibility','physical_input_requires_unlocked_session':True,'background_accessibility':True,'session':session_status(),'game_support':'experimental; not benchmarked','emergency_hotkey':'Ctrl+Alt+F12','hotkey_registered':getattr(getattr(app.state,'hotkey',None),'registered',False)},'browser':await Browser.status(),'checkpoint_backend':'Microsoft Agent Framework FileCheckpointStorage','stopped':engine.runner.desktop.stopped}

@app.post('/api/browser/pair')
async def pair_browser():
    return pairing.issue()

class ExtensionOperation(BaseModel):
    action: Literal['status','install','enable','disable','uninstall']='status'
    extension_id: str|None=Field(default=None,max_length=200)
    path: str|None=Field(default=None,max_length=2000)

@app.get('/api/browser/extensions')
async def browser_extensions_status():
    return await Browser.extensions()

@app.post('/api/browser/extensions')
async def browser_extensions_operation(body:ExtensionOperation):
    return await Browser.extensions(**body.model_dump())

@app.post('/bridge/import')
async def import_chrome_session(request:Request):
    raw=await request.body()
    if len(raw)>2_000_000:raise HTTPException(413,'Transfer exceeds size limit')
    try:data=json.loads(raw)
    except Exception:raise ValueError('Invalid transfer format')
    transfer=validate_transfer(data)
    if engine.lock.locked():raise Conflict('Pause the running task before importing a session')
    async with engine.lock:
        pairing.consume(data.get('code',''))
        try:return await engine.runner.browser.import_session(transfer)
        except Exception:
            # Keep browser errors from echoing credentials or complete script payloads.
            raise HTTPException(502,'Session transfer did not finish. Inspect the built-in browser and retry with a new pairing code.')

class Criterion(BaseModel):
    path: str = Field(min_length=1,max_length=1000)
    contains: str | None = None

class NewTask(BaseModel):
    goal: str = Field(min_length=1,max_length=20000)
    workspace: str = str(ROOT/'repos'/'sandbox')
    mode: Literal['inspect','code','desktop','browser']='desktop'
    idempotency_key: str = Field(min_length=8,max_length=200)
    criteria: list[Criterion] = Field(default_factory=list,max_length=30)

def public_task(task):
    from .task_answer import task_answer
    return {**{k:v for k,v in task.items() if k not in ('messages','idem')},'answer':task_answer(task)}

@app.post('/api/tasks',status_code=201)
async def create_task(body: NewTask):
    workspace=Path(body.workspace).resolve()
    if not workspace.is_dir():
        raise ValueError('Workspace must be an existing folder')
    criteria=[c.model_dump(exclude_none=True) for c in body.criteria]
    for criterion in criteria:
        engine.runner.path({'workspace':str(workspace)},criterion['path'])
    task=store.create(body.goal,str(workspace),body.mode,body.idempotency_key,criteria)
    if task['state']=='queued':
        engine.enqueue(task['id'])
    return public_task(task)

@app.get('/api/tasks')
async def list_tasks():
    return [public_task(t) for t in store.list()]

@app.get('/api/activity')
async def activity():
    from .task_status import task_status
    with store.connect() as db:
        rows=db.execute("SELECT t.id,ct.chat_id,t.goal FROM tasks t LEFT JOIN chat_tasks ct ON ct.task_id=t.id ORDER BY CASE WHEN t.state IN ('queued','running','verifying','waiting_desktop') THEN 0 ELSE 1 END,t.updated DESC LIMIT 8").fetchall()
    items=[]
    for row in rows:
        status=task_status(store,row['id'])
        status.pop('diagnostics',None)
        items.append(dict(status,chat_id=row['chat_id'],goal=row['goal']))
    return {'items':items}

@app.get('/api/tasks/{task_id}')
async def get_task(task_id: str):
    return public_task(store.get(task_id))

@app.get('/api/tasks/{task_id}/events')
async def events(task_id: str,after: int=0):
    store.get(task_id)
    return store.events(task_id,after)

@app.get('/api/tasks/{task_id}/source/{action_id}')
async def recorded_task_source(task_id:str,action_id:str):
    from .source_feedback import recorded_source
    store.get(task_id)
    return recorded_source(store.actions(task_id),action_id)

@app.get('/api/tasks/{task_id}/review')
async def review_bundle(task_id: str):
    task=store.get(task_id)
    return {'task':public_task(task),'actions':store.actions(task_id),'checks':engine.verify(task),'artifacts':[p.name for p in (ARTIFACTS/task_id).glob('*') if p.is_file()]}

class Control(BaseModel):
    command: Literal['pause','resume','cancel']
    expected_revision: int
    resume_handoff: bool = False

@app.post('/api/tasks/{task_id}/control')
async def control(task_id: str,body: Control):
    bridge=app.state.bridge
    if body.resume_handoff:
        if body.command!='resume' or bridge.state.get('task_id')!=task_id or not bridge.state.get('chat_id'):
            raise Conflict('Only the saved handoff task can resume in its linked conversation')
        if bridge.state.get('pending_outbound_text'):
            raise Conflict('Resolve the pending outbound message before resuming its handoff')
    task=await engine.control(task_id,body.command,body.expected_revision)
    if body.resume_handoff:
        # Explicitly resume the existing job and conversation, never issue another request.
        bridge.state.update(enabled=True,phase='waiting_task',connection='reconnecting',error='')
        if not bridge.state.get('objective'):bridge.state['objective']=task['goal']
        bridge.save()
    return public_task(task)

class Review(BaseModel):
    decision: Literal['approve','request_changes','reject']
    expected_revision: int
    reason: str = Field(min_length=1,max_length=10000)
    resume_handoff: bool = False

@app.post('/api/tasks/{task_id}/review')
async def review(task_id: str,body: Review):
    task=store.get(task_id)
    bridge=app.state.bridge
    if body.resume_handoff and (body.decision!='request_changes' or bridge.state.get('task_id')!=task_id or bridge.state.get('pending_outbound_text')):
        raise Conflict('Only the saved handoff task without a pending send can retry in its linked conversation')
    if task['revision']!=body.expected_revision or task['state'] not in (('waiting_review','waiting_user') if body.decision=='request_changes' else ('waiting_review',)):
        raise Conflict('Task is not awaiting this revision of review')
    if body.decision=='request_changes' and any(a['state']=='pending' for a in store.actions(task_id)):
        raise Conflict('Reconcile uncertain actions before resuming this task')
    checks=engine.verify(task)
    if body.decision=='approve' and any(not c['passed'] for c in checks):
        raise Conflict('Acceptance criteria still fail')
    baseline=store.latest_event(task_id,'verification')
    if body.decision=='approve':
        if not baseline or baseline['data'].get('checks')!=checks or baseline['data'].get('evidence')!=engine.evidence(task):
            raise Conflict('Evidence changed since verification. Request a new check before approval.')
    if body.decision=='approve':
        from .development.selfdevelop import SelfDevelop
        objective=SelfDevelop(store)
        if objective.has_objective_run(task_id):
            # Validate and atomically commit the exact artifact review.
            # A binding failure cannot leave a partially approved task.
            return public_task(objective.commit_objective_review(
                task_id,body.expected_revision,body.reason,development_service()))
    state={'approve':'done','request_changes':'queued','reject':'failed'}[body.decision]
    messages=task['messages']
    if body.decision=='request_changes':
        messages.append({'role':'user','content':body.reason})
    updated=store.update(task_id,expected=body.expected_revision,kind='review',state=state,messages=messages,result=body.reason if state=='failed' else task['result'])
    store.event(task_id,'review_decision',body.model_dump())
    if state=='queued':
        if body.resume_handoff:
            bridge.state.update(enabled=True,phase='waiting_task',connection='reconnecting',error='')
            if not bridge.state.get('objective'):bridge.state['objective']=task['goal']
            bridge.save()
        engine.enqueue(task_id)
    return public_task(updated)

class Reconcile(BaseModel):
    action_id: str
    expected_revision: int
    observation: str = Field(min_length=10,max_length=5000)

@app.post('/api/tasks/{task_id}/reconcile')
async def reconcile(task_id: str,body: Reconcile):
    task=store.get(task_id)
    if task['revision']!=body.expected_revision or task['state'] not in ('paused','waiting_user','failed','cancelled'):
        raise Conflict('Task must be stopped at the current revision')
    job=engine.jobs.get(task_id)
    if job is not None and not job.done():
        raise Conflict('Task executor still active; cannot reconcile uncertain action')
    action=next((a for a in store.actions(task_id) if a['id']==body.action_id and a['state']=='pending'),None)
    if not action:
        raise ValueError('No matching uncertain action')
    store.end_action(body.action_id,{'user_reconciled':body.observation,
                                    'effect_verified':False,'replay_permitted':False,
                                    'status':'reconciled_unknown'})
    store.event(task_id,'action_reconciled',{'action_id':body.action_id,
                'prior_state':task['state'],'effect_verified':False,
                'observation':body.observation})
    messages=task['messages']+[{'role':'user','content':'Interrupted action '+action['tool']+' was checked by the user: '+body.observation+'. Inspect current state before continuing.'}]
    return public_task(store.update(task_id,expected=body.expected_revision,messages=messages,kind='reconciled'))

@app.post('/api/stop')
async def stop():
    await engine.stop_all()
    return {'stopped':True}

class MemoryRequest(BaseModel):
    action: Literal['load','unload','unload_all','switch']
    model: str | None = None

@app.get('/api/model/memory')
async def model_memory_status():
    from .model_memory import status
    return await status()

@app.post('/api/model/memory')
async def model_memory_control(body:MemoryRequest):
    from .model_memory import control
    if body.action in ('unload','unload_all'):
        await engine.stop_all(pause_schedules=False)
    elif engine.lock.locked() or any(t['state'] in ('queued','running','verifying') for t in store.list()):
        raise Conflict('Finish or stop active tasks before changing model memory')
    async with engine.lock:
        return await control(body.action,body.model)

@app.post('/api/model/unload')
async def unload():
    return await model_memory_control(MemoryRequest(action='unload'))

@app.get('/api/tasks/{task_id}/artifacts/{name}')
async def artifact(task_id: str,name: str):
    store.get(task_id)
    root=(ARTIFACTS/task_id).resolve()
    path=(root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path,media_type='image/png' if path.suffix=='.png' else 'text/plain')

# Chat API: histories remain on the computer and are shared by desktop and mobile.
from .conversations import Conversations

def conversations():return Conversations(store)

@app.get('/api/chats')
async def chats_index():return conversations().inventory()

class ProjectInput(BaseModel):
    path:str
    name:str|None=None

@app.post('/api/projects')
async def project_add(body:ProjectInput):
    from .context.indexing import Indexing
    return Indexing(project_context_service()).register(body.path,body.name)['project']

class ChatInput(BaseModel):
    project_id:str
    conversation_key:str|None=None

@app.post('/api/chats/{chat_id}/project')
async def chat_bind_project(chat_id:str,body:ProjectInput):
    return conversations().bind_project(chat_id,body.path)

@app.post('/api/chats')
async def chat_add(body:ChatInput):return conversations().create(body.project_id,conversation_key=body.conversation_key)

@app.get('/api/chats/{chat_id}')
async def chat_get(chat_id:str):
    result=conversations().get(chat_id)
    result['turns']=[public_task(t) for t in result['turns']]
    return result

@app.get('/api/chats/{chat_id}/history')
async def conversation_history(chat_id:str,after:int=-1,limit:int=10,query:str='',task_id:str|None=None,field:str='result',offset:int=0,chars:int=3000):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).history(chat_id,after,limit,query,task_id,field,offset,chars)

@app.get('/api/chats/{chat_id}/turns')
async def conversation_turn_page(chat_id:str,before:int|None=None,limit:int=30):
    return conversations().page(chat_id,before,limit)

class ConversationAnchorInput(BaseModel):
    source_task_id:str
    quote:str=Field(min_length=1,max_length=1200)
    label:str=Field(min_length=1,max_length=160)
    supersedes:str|None=None

@app.get('/api/chats/{chat_id}/anchors')
async def conversation_anchors_get(chat_id:str,after:int|None=None,limit:int=12):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).anchors(chat_id,after,limit)

@app.post('/api/chats/{chat_id}/anchors')
async def conversation_anchors_save(chat_id:str,body:ConversationAnchorInput):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).remember(chat_id,**body.model_dump())

class ContinuityInput(BaseModel):
    text:str=Field(max_length=6000)
    expected_revision:int=Field(ge=0)
    source:Literal['user','director']='user'

@app.get('/api/chats/{chat_id}/continuity')
async def continuity_get(chat_id:str):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).note(chat_id)

@app.post('/api/chats/{chat_id}/continuity')
async def continuity_save(chat_id:str,body:ContinuityInput):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).save_note(chat_id,body.text,body.expected_revision,body.source)

class MemoryReviewSettingsInput(BaseModel):
    enabled: bool|None=None
    transport: Literal['auto','browser','mcp']|None=None

class MemoryReviewInput(BaseModel):
    source_task_id: str
    claim: str=Field(min_length=1,max_length=1000)
    evidence_quote: str=Field(min_length=1,max_length=2400)
    field: Literal['goal','result']='result'
    offset: int=Field(default=0,ge=0)
    chars: int=Field(default=1800,ge=1,le=2400)

class MemoryReviewResponseInput(BaseModel):
    verdict: Literal['confirmed','contradicted','unavailable']
    context_available: bool
    evidence: str=Field(min_length=1,max_length=2400)
    transport: Literal['browser','mcp']='mcp'

@app.get('/api/chats/{chat_id}/memory-review/settings')
async def memory_review_settings_get(chat_id:str):
    from .memory_review import MemoryReview
    return MemoryReview(store).settings(chat_id)

@app.get('/api/chats/{chat_id}/memory-reviews')
async def memory_review_history(chat_id:str,after:int|None=None,limit:int=10):
    from .memory_review import MemoryReview
    return MemoryReview(store).history(chat_id,after,limit)

@app.post('/api/chats/{chat_id}/memory-review/settings')
async def memory_review_settings_save(chat_id:str,body:MemoryReviewSettingsInput):
    from .memory_review import MemoryReview
    return MemoryReview(store).settings(chat_id,**body.model_dump())

@app.post('/api/chats/{chat_id}/memory-review')
async def memory_review_create(chat_id:str,body:MemoryReviewInput):
    from .memory_review import MemoryReview
    return MemoryReview(store).request(chat_id,**body.model_dump())

@app.get('/api/chats/{chat_id}/memory-review/{review_id}')
async def memory_review_get(chat_id:str,review_id:str):
    from .memory_review import MemoryReview
    return MemoryReview(store).get(chat_id,review_id)

@app.post('/api/chats/{chat_id}/memory-review/{review_id}')
async def memory_review_respond(chat_id:str,review_id:str,body:MemoryReviewResponseInput):
    from .memory_review import MemoryReview
    return MemoryReview(store).respond(chat_id,review_id,**body.model_dump())

@app.get('/api/chats/{chat_id}/progress')
async def chat_progress(chat_id:str):
    chat=conversations().get(chat_id)
    active=next((t for t in reversed(chat['turns']) if t['state'] in ('queued','running','verifying','waiting_desktop')),None)
    if not active:return {'active':False}
    entries=[store.latest_event(active['id'],kind) for kind in ('model_start','tool_start','tool_result')]
    latest=max((e for e in entries if e),key=lambda e:e['seq'],default=None)
    name=(latest or {}).get('data',{}).get('name')
    labels={'find_login':'מחפש כניסה בקישורים ובתפריטים ובודק את הטופס','chatgpt_ask':'ממתין לבדיקה חזותית מ־ChatGPT','capture_screenshot':'מצלם ושומר את המסך','window_inspect':'קורא את פקדי החלון','window_act':'מפעיל פקד בחלון','desktop_action':'מבצע פעולת עכבר או מקלדת','app_open':'פותח ובודק את היישום','app_close':'סוגר ובודק את היישום'}
    text=labels.get(name,'מבצע פעולה') if latest and latest['kind']=='tool_start' else 'המודל מחשב את הצעד הבא'
    return {'active':True,'task_id':active['id'],'state':active['state'],'text':text,'since':latest['at'] if latest else active['updated']}

@app.get('/api/tasks/{task_id}/diagnostics')
async def task_diagnostics(task_id:str):
    from .task_status import task_status
    return task_status(store,task_id)

@app.get('/api/tasks/{task_id}/action-log')
async def task_action_log(task_id:str):
    from .action_log import action_log
    return action_log(store,task_id)

@app.get('/api/remote/status')
async def remote_status():
    from .remote_config import load,PUBLIC
    from . import mcp_auth
    try:status=json.loads((STATE/'relay-status.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):status={'state':'disabled'}
    return {'enabled':bool(load().get('enabled')),'url':PUBLIC+'/mcp','status':status,'pending':mcp_auth.pending()}

class RemoteApproval(BaseModel):
    request_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    allow:bool

@app.post('/api/remote/approve')
async def remote_approve(body:RemoteApproval):
    from . import mcp_auth
    try:mcp_auth.approve(body.request_id,body.allow)
    except mcp_auth.TokenError:raise HTTPException(410,'Connection request expired or already handled')
    return {'approved':body.allow}

@app.post('/api/remote/revoke')
async def remote_revoke():
    from . import mcp_auth
    with mcp_auth.db() as conn:conn.execute("DELETE FROM records WHERE kind='grant'")
    return {'revoked':True}

class ChatEdit(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    pinned:bool=False
    archived:bool=False

@app.post('/api/chats/{chat_id}/edit')
async def chat_edit(chat_id:str,body:ChatEdit):
    result=conversations().update(chat_id,body.title,body.pinned,body.archived)
    result['turns']=[public_task(t) for t in result['turns']]
    return result


class ChatModeChange(BaseModel):
    mode:Literal['selfdevelop','normal']
    expected_revision:int=Field(ge=0)
    request_id:str=Field(min_length=8,max_length=100)
    reason:str=Field(min_length=1,max_length=2000)

@app.get('/api/chats/{chat_id}/mode')
async def chat_mode_status(chat_id:str):
    return conversations().mode_status(chat_id)

@app.post('/api/chats/{chat_id}/mode')
async def chat_mode_switch(chat_id:str,body:ChatModeChange):
    return conversations().switch_mode(chat_id,**body.model_dump())

def require_active_selfdevelop(chat_id):
    if conversations().mode_status(chat_id)['mode']!='selfdevelop':
        raise HTTPException(409,'Chat is in normal mode: switch back before a SelfDevelop development command')

class ChatMessage(BaseModel):
    text:str=Field(min_length=1,max_length=30000)
    mode:Literal['code','inspect','desktop','browser']='desktop'
    request_id:str=Field(min_length=8,max_length=200)
    attachments:list[dict]=Field(default_factory=list,max_length=5)
    user_message:str|None=Field(default=None,max_length=8000)
    source:Literal['local','mcp']='local'

from .development.guidance import SourceRequirement

class SourceMessage(BaseModel):
    text:str=Field(min_length=1,max_length=8000)
    request_id:str=Field(min_length=8,max_length=100)
    sources:list[SourceRequirement]=Field(min_length=1,max_length=20)

class SelfDevelopStart(BaseModel):
    objective:str=Field(min_length=1,max_length=8000)
    conversation_key:str=Field(min_length=8,max_length=512)
    transport:Literal['mcp','play']='mcp'

class SelfDevelopStep(BaseModel):
    request_id:str=Field(min_length=8,max_length=100)
    instruction:str=Field(min_length=1,max_length=8000)
    allowed_tools:list[str]=Field(min_length=1,max_length=20)
    required_tools:list[str]=Field(default_factory=list,max_length=20)
    required_sources:list[SourceRequirement]=Field(default_factory=list,max_length=20)
    evidence_only:bool=False
    exact_patch:dict|None=None
    context_read:dict|None=None

class SelfDevelopCommand(BaseModel):
    request_id:str=Field(min_length=8,max_length=100)
    instruction:str=Field(min_length=1,max_length=8000)
    command:str=Field(min_length=1,max_length=20000)
    shell:Literal['powershell','cmd']='powershell'
    timeout:int=Field(default=60,ge=1,le=180)

@app.post('/api/selfdevelop/{chat_id}/command')
async def selfdevelop_command(chat_id:str,body:SelfDevelopCommand):
    require_active_selfdevelop(chat_id)
    from .development.commands import dispatch
    task=dispatch(store,chat_id,**body.model_dump())
    if task['state']=='queued':engine.enqueue(task['id'])
    return public_task(task)

class SelfDevelopCorrection(BaseModel):
    task_id:str=Field(pattern='^[a-f0-9]{32}$')
    expected_revision:int=Field(ge=0)
    request_id:str=Field(min_length=8,max_length=100)
    reason:str=Field(min_length=1,max_length=8000)
    command:str=Field(min_length=1,max_length=20000)
    shell:Literal['powershell','cmd']='powershell'
    timeout:int=Field(default=60,ge=1,le=180)

@app.post('/api/selfdevelop/{chat_id}/command/correct')
async def selfdevelop_command_correct(chat_id:str,body:SelfDevelopCorrection):
    require_active_selfdevelop(chat_id)
    from .development.commands import correct
    task=correct(store,chat_id,**body.model_dump())
    if task['state']=='queued':engine.enqueue(task['id'])
    return public_task(task)

@app.post('/api/selfdevelop/start')
async def selfdevelop_start(body:SelfDevelopStart):
    from .development.selfdevelop import SelfDevelop
    return SelfDevelop(store).start(**body.model_dump())

@app.get('/api/selfdevelop/{chat_id}')
async def selfdevelop_status(chat_id:str):
    from .development.selfdevelop import SelfDevelop
    status=SelfDevelop(store).status(chat_id)
    lifecycle=conversations().mode_status(chat_id)
    status['mode']=lifecycle['mode']
    status['mode_revision']=lifecycle['revision']
    status['history_preserved']=True
    if lifecycle['mode']=='normal':
        status['next_action']='SelfDevelop is preserved but suspended. Use chat_mode_switch after review of all active work.'
    return status

@app.post('/api/selfdevelop/{chat_id}/step')
async def selfdevelop_step(chat_id:str,body:SelfDevelopStep):
    require_active_selfdevelop(chat_id)
    from .development.selfdevelop import SelfDevelop
    task=SelfDevelop(store).step(chat_id,**body.model_dump())
    if task['state']=='queued':engine.enqueue(task['id'])
    return public_task(task)

@app.post('/api/chats/{chat_id}/sources')
async def chat_sources(chat_id:str,body:SourceMessage):
    """Install exact director instructions before making the task runnable."""
    from .development.guidance import Guidance
    task=conversations().submit(chat_id,body.text,'code',body.request_id)
    guide=Guidance(store)
    status=guide.status(task['id'])
    guide.submit(task['id'],task['revision'],status['guidance_revision'],status['consumer_epoch'],
                 body.request_id,body.text,required_sources=[s.model_dump() for s in body.sources],evidence_only=True)
    if task['state']=='queued':engine.enqueue(task['id'])
    return public_task(task)

@app.post('/api/chats/{chat_id}/messages')
async def chat_message(chat_id:str,body:ChatMessage):
    from .model_settings import parse_model_command
    if parse_model_command(body.text) is not None:
        from .model_preferences import perform
        outcome=await perform(text=body.text,busy=any(not job.done() for job in engine.jobs.values()))
        return {'handled_model_command':True,'model_command':outcome}
    task=conversations().submit(chat_id,body.text,body.mode,body.request_id,body.attachments,presentation={'text':body.user_message or body.text,'source':body.source})
    if task['state']=='queued':engine.enqueue(task['id'])
    return public_task(task)

@app.get('/api/folders')
async def folders(path:str='E:/'):
    folder=Path(path).resolve()
    if not folder.is_dir():raise ValueError('Folder not found')
    items=[]
    for child in folder.iterdir():
        try:
            if child.is_dir():items.append({'name':child.name,'path':str(child)})
        except OSError:pass
    return {'path':str(folder),'parent':str(folder.parent),'folders':sorted(items,key=lambda x:x['name'].lower())[:500]}

class BrowserCommand(BaseModel):
    action:Literal['observe','navigate','click','fill','back','forward']
    url:str=''
    observation_id:str=''
    ref:str=''
    text:str=''

@app.post('/api/browser/control')
async def browser_control(body:BrowserCommand):
    if engine.lock.locked():raise Conflict('The agent is using the computer; wait or stop the task first')
    async with engine.lock:
        folder=ARTIFACTS/'browser-manual'
        if body.action=='observe':return await engine.runner.browser.observe(folder)
        if body.action=='navigate':return await engine.runner.browser.navigate(body.url,folder)
        return await engine.runner.browser.act(body.model_dump(),folder)

@app.get('/api/browser/image/{name}')
async def browser_image(name:str):
    folder=(ARTIFACTS/'browser-manual').resolve();path=(folder/name).resolve()
    if path.parent!=folder or path.suffix!='.png' or not path.is_file():raise HTTPException(404)
    return FileResponse(path)

def file_library():
    from .file_library import FileLibrary
    return FileLibrary(STATE,ROOT/'files')

@app.post('/api/files/upload')
async def upload_file(request:Request,name:str):
    from .file_library import MAX_UPLOAD
    if int(request.headers.get('content-length','0'))>MAX_UPLOAD:raise HTTPException(413,'File exceeds 100 MB')
    library=file_library();item=library.reserve(name,'chat upload',request.headers.get('content-type',''))
    count=0
    try:
        with Path(item['path']).open('wb') as output:
            async for chunk in request.stream():
                count+=len(chunk)
                if count>MAX_UPLOAD:raise HTTPException(413,'File exceeds 100 MB')
                output.write(chunk)
        return await asyncio.to_thread(library.finish,item['id'])
    except BaseException:
        library.fail(item['id'],'Upload interrupted or exceeded size limit')
        Path(item['path']).unlink(missing_ok=True)
        raise

@app.get('/api/files')
async def library_files():return {'files':file_library().list()}

@app.get('/api/files/{file_id}/content')
async def library_content(file_id:str):
    item=file_library().get(file_id,ready=True)
    return FileResponse(item['path'],filename=item['name'],media_type=item['mime'])

class BrowserUpload(BaseModel):
    file_id:str
    observation_id:str
    ref:str

@app.post('/api/browser/upload')
async def browser_upload_file(body:BrowserUpload):
    if engine.lock.locked():raise Conflict('The agent is using the browser')
    item=file_library().get(body.file_id,ready=True)
    async with engine.lock:
        return await engine.runner.browser.upload(body.observation_id,body.ref,item['path'])

@app.get('/api/projects/{project_id}/files')
async def project_files(project_id:str,path:str='.'):
    project=next((p for p in conversations().inventory()['projects'] if p['id']==project_id),None)
    if not project:raise KeyError('Project not found')
    root=Path(project['path']).resolve();target=(root/path).resolve()
    if not target.is_relative_to(root):raise ValueError('Path outside project')
    if target.is_dir():
        entries=[]
        for f in target.iterdir():
            try:entries.append({'name':f.name,'path':str(f.relative_to(root)),'directory':f.is_dir()})
            except OSError:pass
        return {'path':str(target.relative_to(root)),'parent':str(target.parent.relative_to(root)) if target!=root else '.', 'entries':sorted(entries,key=lambda e:(not e['directory'],e['name'].lower()))[:500]}
    if target.stat().st_size>500000:raise ValueError('Preview limited to 500 KB')
    data=target.read_bytes()
    if b'\x00' in data:raise ValueError('Binary file; text preview unavailable')
    return {'path':str(target.relative_to(root)),'content':data.decode('utf-8',errors='replace')}

@app.get('/api/projects/{project_id}/git')
async def project_git(project_id:str):
    project=next((p for p in conversations().inventory()['projects'] if p['id']==project_id),None)
    if not project:raise KeyError('Project not found')
    import subprocess
    def run():
        result={}
        for key,args in [('status',['status','--short']),('diff',['diff','--no-ext-diff','--no-textconv','--stat']),('patch',['diff','--no-ext-diff','--no-textconv','--'])]:
            p=subprocess.run(['git','-C',project['path'],*args],capture_output=True,timeout=15,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result[key]=(p.stdout+p.stderr)[:100000]
        return result
    return await asyncio.to_thread(run)

class CommandInput(BaseModel):
    project_id:str
    command:str=Field(min_length=1,max_length=10000)

@app.post('/api/terminal')
async def terminal(body:CommandInput):
    project=next((p for p in conversations().inventory()['projects'] if p['id']==body.project_id),None)
    if not project:raise KeyError('Project not found')
    if engine.lock.locked():raise Conflict('Wait for the current task or stop it first')
    async with engine.lock:
        # Explicit user-entered command, executed by the same bounded product tool.
        engine.runner.desktop.stopped=False
        return await engine.runner.execute({'id':'manual-terminal','workspace':project['path'],'mode':'code'},'run_shell',{'command':body.command,'timeout':60})

class ProjectNotes(BaseModel):
    notes:str=Field(max_length=12000)

@app.get('/api/projects/{project_id}/notes')
async def project_notes_get(project_id:str):
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS project_notes(project_id TEXT PRIMARY KEY,notes TEXT NOT NULL)')
        row=db.execute('SELECT notes FROM project_notes WHERE project_id=?',(project_id,)).fetchone()
    return {'notes':row[0] if row else ''}

@app.post('/api/projects/{project_id}/notes')
async def project_notes_save(project_id:str,body:ProjectNotes):
    if not any(p['id']==project_id for p in conversations().inventory()['projects']):raise KeyError('Project not found')
    await project_notes_get(project_id)
    with store.connect() as db:db.execute('INSERT OR REPLACE INTO project_notes VALUES(?,?)',(project_id,body.notes))
    return {'saved':True}

class WorktreeInput(BaseModel):
    project_id:str

@app.post('/api/worktrees')
async def create_worktree(body:WorktreeInput):
    from .development.git import worktree
    project=next((p for p in conversations().inventory()['projects'] if p['id']==body.project_id),None)
    if not project:raise KeyError('Project not found')
    result=await asyncio.to_thread(worktree,project['path'],ROOT/'worktrees')
    return conversations().project(result['path'],project['name']+' · '+Path(result['path']).name[:12])


from .schedules import Schedules
class ScheduleInput(BaseModel):
    project_id:str
    prompt:str=Field(min_length=1,max_length=10000)
    mode:Literal['inspect','code','browser','desktop']='inspect'
    interval_minutes:int=Field(ge=1,le=43200)

@app.get('/api/schedules')
async def schedule_list():return Schedules(store).list()

@app.post('/api/schedules')
async def schedule_create(body:ScheduleInput):return Schedules(store).create(body.project_id,body.prompt,body.mode,body.interval_minutes)

class ScheduleToggle(BaseModel):
    enabled:bool

@app.post('/api/schedules/{schedule_id}')
async def schedule_enable(schedule_id:str,body:ScheduleToggle):
    Schedules(store).enable(schedule_id,body.enabled)
    return {'enabled':body.enabled}


class GPTConnect(BaseModel):
    tab_id:str|None=None
    create:bool=False

@app.post('/api/chatgpt/connect')
async def gpt_connect(body:GPTConnect):
    if any(not job.done() for job in engine.jobs.values()):raise Conflict('Wait for the agent to finish or stop it first')
    async with engine.lock:
        result=await engine.runner.chatgpt.connect(body.tab_id,body.create)
        # A probe does not resolve an uncertain send or restart listening.
        from datetime import datetime,timezone
        app.state.bridge.state['last_connection_check']={**result,'checked_at':datetime.now(timezone.utc).isoformat()}
        app.state.bridge.save()
        return result

@app.get('/api/chatgpt/status')
async def gpt_status():return app.state.bridge.state

@app.get('/api/chatgpt/play-protocol')
async def get_play_protocol():
    from .play_protocol import protocol
    return protocol()

@app.get('/api/ai-connectors')
async def ai_connectors():
    from .ai_connectors import catalog
    return catalog()

from .delegation_api import router as delegation_router
app.include_router(delegation_router(store,engine))

class ChatConnectionInput(BaseModel):
    transport:Literal['play','mcp']|None=None
    favorite:bool|None=None
    url:str|None=None

@app.get('/api/chatgpt/favorites')
async def chatgpt_favorites():return {'items':app.state.bridge.transcript.favorites()}

@app.get('/api/chats/{chat_id}/connection')
async def chat_connection(chat_id:str):return app.state.bridge.transcript.connection(chat_id)

@app.post('/api/chats/{chat_id}/connection')
async def chat_connection_save(chat_id:str,body:ChatConnectionInput):
    bridge=app.state.bridge
    async with engine.lock:
        if (body.url is not None or body.transport is not None) and bridge.state.get('chat_id')==chat_id:
            if bridge.state.get('enabled') or bridge.state.get('pending_outbound_text'):
                raise Conflict('Stop the active handoff and reconcile any uncertain send before changing its connection')
            # Reset only after validation/save succeeds; the next selection must reopen the saved URL.
            result=bridge.transcript.configure(chat_id,**body.model_dump())
            bridge.state['chat_id']=None;bridge.save()
            return result
        return bridge.transcript.configure(chat_id,**body.model_dump())

class InputPreference(BaseModel):
    mode:Literal['auto','quiet','physical']

from .model_settings import ModelSettings,load_settings,save_settings,PRESETS

class ModelPreferenceCommand(BaseModel):
    action:Literal['get','set','reset']='get'
    field:str|None=None
    value:str|int|float|bool|None=None
    scope:str='default'
    text:str|None=None
    apply_now:bool=False

@app.get('/api/settings/model/control')
async def model_preferences_get():
    from .model_preferences import status
    return await status()

@app.post('/api/settings/model/control')
async def model_preferences_control(body:ModelPreferenceCommand):
    from .model_preferences import perform
    return await perform(action=body.action,field=body.field,value=body.value,scope=body.scope,
                         text=body.text,apply_now=body.apply_now,
                         busy=any(not job.done() for job in engine.jobs.values()))


@app.get('/api/settings/model')
async def get_model_settings():
    models=[];runtime=[];error=None
    async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
        try:
            tags,ps=await asyncio.gather(client.get(OLLAMA+'/api/tags'),client.get(OLLAMA+'/api/ps'))
            tags.raise_for_status();ps.raise_for_status()
            models=[{'name':m['name'],'size_gb':round(m.get('size',0)/1024**3,2)} for m in tags.json().get('models',[])]
            runtime=[{'name':m['name'],'vram_gb':round(m.get('size_vram',0)/1024**3,2),'context_length':m.get('context_length')} for m in ps.json().get('models',[])]
        except Exception:error='לא ניתן להתחבר למנוע המקומי. ההגדרות השמורות עדיין זמינות.'
    metrics=[]
    for task in store.list()[:10]:
        metrics.extend(e['data']['metrics'] for e in store.events(task['id']) if e['kind']=='model' and e['data'].get('metrics'))
    recent=metrics[-20:]
    return {'settings':load_settings(STATE).model_dump(),'presets':PRESETS,'models':models,'runtime':runtime,'error':error,'recent_inference_seconds':[round(m['total_duration']/1e9,2) for m in recent if m.get('total_duration')],'busy':any(not job.done() for job in engine.jobs.values())}

@app.post('/api/settings/model')
async def set_model_settings(body:ModelSettings):
    if any(not job.done() for job in engine.jobs.values()):raise Conflict('עצור או המתן לסיום המשימה לפני שינוי הגדרות המודל')
    async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
        try:
            response=await client.get(OLLAMA+'/api/tags');response.raise_for_status()
        except httpx.HTTPError:raise HTTPException(503,'המנוע המקומי לא זמין; ההגדרות הקודמות נשמרו')
    if body.model not in {m['name'] for m in response.json().get('models',[])}:raise ValueError('בחר מודל שמותקן במחשב')
    if body.coding_model and body.coding_model not in {m['name'] for m in response.json().get('models',[])}:raise ValueError('מודל התכנות צריך להיות מותקן במחשב')
    save_settings(body,STATE)
    return {'settings':body.model_dump(),'applies':'next_request'}

@app.get('/api/settings/input-mode')
async def get_input_mode():
    from .preferences import load_input_mode
    return {'mode':load_input_mode(STATE)}

@app.post('/api/settings/input-mode')
async def set_input_mode(body:InputPreference):
    from .preferences import save_input_mode
    if any(not job.done() for job in engine.jobs.values()):raise Conflict('Stop or finish the current task before changing input mode')
    save_input_mode(STATE,body.mode)
    return {'mode':body.mode}

class MCPObservation(BaseModel):
    project_id:str
    request_id:str
    operation:str
    phase:Literal['started','completed','failed']
    payload:dict

class MCPConversationMessage(BaseModel):
    project_id:str
    conversation_key:str
    message_id:str
    text:str
    speaker:Literal['user','chatgpt']

@app.post('/api/mcp/conversation-message')
async def mcp_conversation_message(body:MCPConversationMessage):
    if not body.message_id.strip() or not body.text.strip():raise ValueError('Message ID and text are required')
    chat=conversations().create(body.project_id,title=body.text[:80],conversation_key=body.conversation_key)
    transcript=app.state.bridge.transcript
    transcript.configure(chat['id'],transport='mcp')
    transcript.append(chat['id'],body.speaker,'user_to_chatgpt' if body.speaker=='user' else 'chatgpt_to_agent',body.text,key='mcp-message:'+body.message_id)
    return {'chat_id':chat['id'],'recorded':True,'continue_in_this_chat':True}

@app.post('/api/chats/{chat_id}/mcp-observation')
async def mcp_observation(chat_id:str,body:MCPObservation):
    from .mcp_observation import record_observation
    return record_observation(conversations(),app.state.bridge.transcript,chat_id,body.model_dump())

@app.get('/api/chats/{chat_id}/correspondence')
async def correspondence(chat_id:str,after:float=0):
    from datetime import datetime
    messages=app.state.bridge.transcript.list(chat_id,after)
    # Ordinary agent turns and bridge exchanges share the same saved chat timeline.
    if messages:
        chat=conversations().get(chat_id)
        for task in chat['turns']:
            events=store.events(task['id'])
            is_handoff=any(e['kind']=='chatgpt_action' for e in events)
            created=datetime.fromisoformat(task['created']).timestamp()
            if not is_handoff and created>after:
                files=[f for e in events if e['kind']=='attachments' for f in e['data'].get('files',[])]
                messages.append({'id':'task-user-'+task['id'],'speaker':'user','direction':'user_to_agent','text':task['goal'],'created':created,'files':files,'status':'received'})
            if task.get('result'):
                updated=datetime.fromisoformat(task.get('updated',task['created'])).timestamp()
                if updated>after:messages.append({'id':'task-answer-'+task['id'],'speaker':'local_agent','direction':'agent_to_user','text':task['result'],'created':updated,'files':[],'status':task['state']})
    return {'messages':sorted(messages,key=lambda m:m['created'])}

@app.get('/api/chatgpt/presentation')
async def get_presentation():
    from .preferences import load_presentation
    return {'mode':load_presentation(STATE)}

class GPTContext(BaseModel):
    chat_id:str

class GPTDraft(BaseModel):
    chat_id:str
    action:Literal['list','archive','restore']
    draft_id:str|None=None

@app.post('/api/chatgpt/drafts')
async def chatgpt_drafts(body:GPTDraft):
    from .chatgpt_drafts import manage
    if any(not job.done() for job in engine.jobs.values()):raise Conflict('Wait for the active task')
    async with engine.lock:return await manage(app.state.bridge,body.chat_id,body.action,body.draft_id)

@app.post('/api/chatgpt/context')
async def select_chatgpt_context(body:GPTContext):
    if any(not job.done() for job in engine.jobs.values()):raise Conflict('Finish or stop the current task before switching conversations')
    async with engine.lock:
        connection=app.state.bridge.transcript.connection(body.chat_id)
        if connection['transport']=='mcp':
            return {**connection,'listening':False,'requires':'Use this chat_id in the authenticated MCP conversation; no browser opened'}
        chat=await app.state.bridge.select_context(body.chat_id)
        return {'chat_id':chat['id'],'url':engine.runner.chatgpt.bound_url,'listening':app.state.bridge.state.get('enabled',False)}

class GPTPresentation(BaseModel):
    mode:Literal['background','split']

@app.post('/api/chatgpt/presentation')
async def set_presentation(body:GPTPresentation):
    import sys
    from .preferences import save_presentation
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--presentation',body.mode,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
    out,err=await asyncio.wait_for(process.communicate(),8)
    if process.returncode:raise HTTPException(503,'The desktop window is unavailable; open Local Agent and try again')
    result=json.loads(out)
    save_presentation(STATE,body.mode)
    return result

class GPTQuestion(BaseModel):
    question:str=Field(min_length=1,max_length=20000)
    file_ids:list[str]=Field(default_factory=list,max_length=5)
    chat_id:str|None=None
    project_id:str|None=None

@app.post('/api/chatgpt/ask')
async def gpt_ask(body:GPTQuestion):
    state=app.state.bridge.state
    if any(not job.done() for job in engine.jobs.values()) or (state.get('enabled') and not (state.get('continuous') and state.get('phase')=='listening')):raise Conflict('Another task is using the connected session')
    paths=[file_library().get(i,ready=True)['path'] for i in body.file_ids]
    async with engine.lock:
        chat=await app.state.bridge.select_context(body.chat_id,body.project_id)
        app.state.bridge.transcript.append(chat['id'],'user','user_to_agent',body.question)
        try:answer=await engine.runner.chatgpt.ask(body.question,file_paths=paths)
        except Exception as exc:
            detail=type(exc).__name__+': '+str(exc)
            app.state.bridge.transcript.append(chat['id'],'local_agent','agent_to_user',detail,status='needs_review')
            raise HTTPException(409,detail) from exc
        return {**answer,'chat_id':chat['id']}

class GPTObjective(BaseModel):
    project_id:str
    objective:str=Field(min_length=1,max_length=12000)
    max_steps:int=Field(default=8,ge=1,le=20)

@app.post('/api/chatgpt/start')
async def gpt_start(body:GPTObjective):return await app.state.bridge.enable(body.project_id,body.objective,body.max_steps)

class GPTListen(BaseModel):
    project_id:str
    max_steps:int=Field(default=8,ge=1,le=20)
    chat_id:str|None=None

@app.post('/api/chatgpt/listen')
async def gpt_listen(body:GPTListen):return await app.state.bridge.listen(body.project_id,body.max_steps,chat_id=body.chat_id)

@app.post('/api/chatgpt/new-conversation')
async def gpt_new_conversation(body:GPTListen):
    controller=app.state.bridge
    if body.chat_id:raise ValueError('New conversation creates a separate local chat; do not supply chat_id')
    if controller.state.get('enabled') or controller.state.get('phase')=='opening_conversation' or controller.state.get('pending_outbound_text') or any(not job.done() for job in engine.jobs.values()):
        raise Conflict('Finish or stop the current handoff and reconcile uncertain sends first')
    async with engine.lock:
        # Validate project before opening a tab. Keep failed setup visible in this same local chat.
        chat=conversations().create(body.project_id,'ChatGPT · PLAY')
        controller.state.update(phase='opening_conversation',play_setup_chat_id=chat['id'],error='')
        controller.save()
        try:
            await asyncio.wait_for(controller.select_context(chat['id']),45)
            return await controller.listen(body.project_id,body.max_steps,chat_id=chat['id'],already_locked=True)
        except Exception as exc:
            detail=str(exc) or 'Browser setup timed out. Inspect the newly opened ChatGPT tab and complete login if required; no automatic retry was made.'
            if controller.state.get('phase')!='send_uncertain':controller.state.update(enabled=False,phase='connection_attention',error=detail)
            controller.save()
            controller.transcript.append(chat['id'],'local_agent','agent_status','PLAY setup requires attention: '+detail,status='needs_review')
            raise HTTPException(409,detail+' Local chat: '+chat['id']) from exc

@app.post('/api/chatgpt/stop')
async def gpt_stop():
    app.state.bridge.stop()
    task_id=app.state.bridge.state.get('task_id')
    if task_id:
        task=store.get(task_id)
        if task['state'] in ('queued','running','verifying','waiting_desktop'):
            await engine.control(task_id,'pause',task['revision'])
    return app.state.bridge.state


@app.get('/api/browser/frame')
async def browser_frame():
    from .browser_access import interactive_access
    async with interactive_access(engine,app.state.bridge,observation_only=True):return await engine.runner.browser.frame()

class BrowserInput(BaseModel):
    frame_id:str
    ref:str=''
    end_ref:str=''
    action:Literal['click','move','drag','text','key','scroll']
    x:float=0
    y:float=0
    end_x:float=0
    end_y:float=0
    button:Literal['left','right','middle']='left'
    text:str=Field(default='',max_length=2000)
    key:str=Field(default='',max_length=50)
    amount:int=0

@app.post('/api/browser/input')
async def browser_input(body:BrowserInput):
    from .browser_access import interactive_access
    async with interactive_access(engine,app.state.bridge):return await engine.runner.browser.remote_input(body.model_dump())

@app.get('/api/browser/tabs')
async def browser_tabs_view():
    from .browser_access import interactive_access
    async with interactive_access(engine,app.state.bridge):return await engine.runner.browser.tabs()

@app.post('/api/browser/focus')
async def focus_native_browser():
    import sys
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--focus-browser',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
    await asyncio.wait_for(process.communicate(),5)
    if process.returncode:raise HTTPException(503,'Open the Local Agent desktop window first')
    return {'focused':True}

class BrowserTab(BaseModel):
    tab_id:str

@app.post('/api/browser/select')
async def browser_select_view(body:BrowserTab):
    from .browser_access import interactive_access
    async with interactive_access(engine,app.state.bridge):
        await engine.runner.browser.select_tab(body.tab_id)
        await engine.runner.browser.show_selected()
        return {'selected':body.tab_id}


from .screenshot_settings import ScreenshotSettings
@app.get('/api/settings/screenshots')
async def screenshot_settings_get():
    from .screenshot_settings import load
    return load().model_dump()

@app.post('/api/settings/screenshots')
async def screenshot_settings_set(body:ScreenshotSettings):
    from .screenshot_settings import save
    return save(body)

from .browser_selections import router as browser_selections_router
app.include_router(browser_selections_router())


# Native rescue and MCP share the same durable service manager.
@app.get('/api/service-health')
async def service_health_snapshot(compact:bool=False):
    from .service_health import snapshot,compact_status
    data=await asyncio.to_thread(snapshot)
    return compact_status(data) if compact else data

class ServiceHealthAction(BaseModel):
    action: str
    service: str = 'mcp'
    request_id: str
    confirm_tasks: bool = False

@app.post('/api/service-health/action')
async def service_health_action(body: ServiceHealthAction):
    from .service_health import submit
    try:
        return await asyncio.to_thread(submit,body.action,body.service,body.request_id,body.confirm_tasks)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))

@app.get('/api/service-health/action/{action_id}')
async def service_health_action_result(action_id:str):
    from .service_health import job_status
    try:return job_status(action_id)
    except ValueError as exc:raise HTTPException(404,str(exc))

@app.post('/api/service-health/connection/challenge')
async def service_health_challenge():
    from .service_health import challenge
    return challenge()

class HealthConnectionAck(BaseModel):
    nonce: str

@app.post('/api/service-health/connection/ack')
async def service_health_ack(body:HealthConnectionAck):
    from .service_health import acknowledge
    try:return acknowledge(body.nonce)
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.post('/api/service-health/quiesce')
async def service_health_quiesce():
    return app.state.shutdown.start(keep_desktop=True)


@app.get('/api/chats/{chat_id}/context-memory')
async def context_memory_status(chat_id:str,task_id:str|None=None):
    from .conversation_memory import ConversationMemory
    from .model_settings import load_settings
    memory=ConversationMemory(store)
    with store.connect() as db:
        memory._exists(db,chat_id)
        if task_id is None:
            row=db.execute('SELECT task_id FROM chat_tasks WHERE chat_id=? ORDER BY position DESC LIMIT 1',(chat_id,)).fetchone()
            task_id=row[0] if row else None
    result=memory.context_diagnostics(chat_id,task_id) if task_id else {'chat_id':chat_id,'task_id':None,'packet':None,'checkpoint':None,'history_loaded':False}
    settings=load_settings()
    result['settings']={k:getattr(settings,k) for k in ('context_management','working_input_tokens','context_tokens','response_tokens')}
    result['scope']='chat';result['rollback']='Set context_management to legacy through model settings; durable evidence is retained.'
    return result

@app.get('/api/chats/{chat_id}/context-evidence')
async def context_memory_evidence(chat_id:str,task_id:str,message_index:int,sha256:str,offset:int=0,chars:int=3000):
    from .conversation_memory import ConversationMemory
    try:return ConversationMemory(store).context_evidence(chat_id,task_id,message_index,sha256,offset,chars)
    except KeyError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))


@app.get('/api/chats/{chat_id}/context-pins')
async def context_memory_pins(chat_id:str,offset:int=0):
    from .conversation_memory import ConversationMemory
    return ConversationMemory(store).pinned_memory(chat_id,offset)

@app.post('/api/chats/{chat_id}/context-pins')
async def context_memory_pin(chat_id:str,body:dict):
    from .conversation_memory import ConversationMemory
    try:return ConversationMemory(store).pin_memory(chat_id,body['anchor_id'],body['scope'],body['pinned'],body['expected_revision'])
    except KeyError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))

@app.post('/api/service-health/connector-observation')
async def service_health_connector_observation(body:dict):
    from . import service_health as health
    try:
        return health.diagnostics.observe(health,body.get('connector'),body.get('outcome'),body.get('checked_at'))
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.get('/api/power/preview/{action}')
async def computer_power_preview(action:str):
    from .power import preview
    try:return await asyncio.to_thread(preview,action)
    except ValueError as exc:raise HTTPException(400,str(exc))

class ComputerPowerRequest(BaseModel):
    action:str
    request_id:str
    confirm_tasks:bool=False

@app.post('/api/power/action')
async def computer_power_action(body:ComputerPowerRequest):
    from .power import submit
    try:return await asyncio.to_thread(submit,body.action,body.request_id,body.confirm_tasks)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@app.get('/api/power/startup')
async def agent_startup_status():
    from .power import startup_status
    return await asyncio.to_thread(startup_status)

class AgentStartupRequest(BaseModel):
    enabled:bool
    expected_revision:int

@app.post('/api/power/startup')
async def agent_startup_set(body:AgentStartupRequest):
    from .power import set_startup
    try:return await asyncio.to_thread(set_startup,body.enabled,body.expected_revision)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

class TaskLifecycleRequest(BaseModel):
    chat_id:str
    expected_revision:int
    action:Literal['resume','cancel','delete']
    confirm:bool=False

@app.get('/api/tasks/{task_id}/delete-preview')
async def task_delete_preview(task_id:str,chat_id:str):
    from .task_lifecycle import preview
    return preview(store,engine,chat_id,task_id)

@app.post('/api/tasks/{task_id}/lifecycle')
async def task_lifecycle_action(task_id:str,body:TaskLifecycleRequest):
    from .task_lifecycle import bound,remove
    bound(store,body.chat_id,task_id)
    if body.action=='delete':
        return remove(store,engine,body.chat_id,task_id,body.expected_revision,body.confirm)
    return public_task(await engine.control(task_id,body.action,body.expected_revision))
