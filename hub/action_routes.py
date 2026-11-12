"""Versioned reusable browser routes. Evidence is historical data, never authority."""
import hashlib,json,re,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from .store import Conflict,now
from .config import ARTIFACTS
from .file_library import FileLibrary

LIMIT=40
def text(value,limit=3000):
    if not isinstance(value,str) or len(value)>limit:raise ValueError('Text exceeds field limit')
    return value
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def safe_url(value):
    """Display-only URL hint: omit credentials, query and fragment."""
    if not isinstance(value,str):return ''
    try:
        p=urlsplit(value)
        if p.scheme not in ('http','https') or not p.hostname:return ''
        host=p.hostname.lower()
        if ':' in host:host='['+host+']'
        netloc=host+(':'+str(p.port) if p.port else '')
        return urlunsplit((p.scheme,netloc,p.path[:1200],'',''))
    except ValueError:return ''
class Routes:
    def __init__(self,store,library=None,artifacts=None):
        self.store=store;self.library=library or FileLibrary();self.artifacts=Path(artifacts or ARTIFACTS).resolve()
        with store.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS action_routes(id TEXT PRIMARY KEY,chat_id TEXT NOT NULL,project_id TEXT NOT NULL,scope TEXT NOT NULL,revision INTEGER NOT NULL,deleted INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_route_versions(route_id TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(route_id,revision));
CREATE TABLE IF NOT EXISTS action_route_runs(route_id TEXT NOT NULL,chat_id TEXT NOT NULL,task_id TEXT NOT NULL UNIQUE,route_revision INTEGER NOT NULL,created TEXT NOT NULL);""")
    def chat(self,chat_id):
        with self.store.connect() as db:r=db.execute('SELECT id,project_id FROM chats WHERE id=?',(chat_id,)).fetchone()
        if not r:raise KeyError('Chat not found')
        return dict(r)
    def task_chat(self,task_id):
        with self.store.connect() as db:r=db.execute('SELECT chat_id FROM chat_tasks WHERE task_id=?',(task_id,)).fetchone()
        if not r:raise KeyError('Task has no chat')
        return r[0]
    def get(self,chat_id,route_id):
        c=self.chat(chat_id)
        with self.store.connect() as db:r=db.execute('SELECT * FROM action_routes WHERE id=? AND deleted=0',(route_id,)).fetchone()
        if not r or not (r['chat_id']==chat_id or r['scope']=='global' or r['scope']=='project' and r['project_id']==c['project_id']):raise KeyError('Route not available in this scope')
        v=json.loads(r['body']);return {**v,'id':r['id'],'revision':r['revision'],'scope':r['scope'],'updated':r['updated'],'can_edit':r['chat_id']==chat_id,'owner_chat_id':r['chat_id']}
    def list(self,chat_id,query='',offset=0):
        c=self.chat(chat_id);offset=int(offset)
        if offset<0:raise ValueError('Invalid offset')
        with self.store.connect() as db:
            rows=db.execute("SELECT * FROM action_routes WHERE deleted=0 AND (chat_id=? OR scope='global' OR (scope='project' AND project_id=?)) AND body LIKE ? ORDER BY updated DESC,id LIMIT 21 OFFSET ?",(chat_id,c['project_id'],'%'+text(query,200)+'%',offset)).fetchall()
        items=[]
        for r in rows[:20]:
            b=json.loads(r['body']);items.append({k:b.get(k) for k in ('title','folder','description','enabled','parameters','verification')})
            items[-1].update(id=r['id'],revision=r['revision'],scope=r['scope'],steps=len(b['steps']),can_edit=r['chat_id']==chat_id)
        return {'items':items,'next_offset':offset+20 if len(rows)>20 else None}
    def validate(self,body):
        if not isinstance(body,dict):raise ValueError('Route body required')
        if len(json.dumps(body,ensure_ascii=False))>60000:raise ValueError('Route exceeds 60000 characters; split into smaller routes')
        b={k:text(body.get(k,''),n) for k,n in [('title',150),('folder',150),('description',1500)]}
        if not b['title'].strip():raise ValueError('Title required')
        b['enabled']=bool(body.get('enabled',True))
        start=text(body.get('start_url',''),1600)
        b['start_url']=safe_url(start)
        if start and not b['start_url']:raise ValueError('Start URL must be HTTP(S)')
        params=body.get('parameters',[])
        if not isinstance(params,list) or len(params)>12:raise ValueError('At most 12 parameters')
        b['parameters']=[]
        for p in params:
            name=p.get('name','')
            if not re.fullmatch('[a-z][a-z0-9_]{0,39}',name) or name in [x['name'] for x in b['parameters']]:raise ValueError('Unique parameter names: lowercase English letters/numbers/underscore')
            b['parameters'].append({'name':name,'label':text(p.get('label',name),150),'required':bool(p.get('required',True))})
        steps=body.get('steps',[])
        if not isinstance(steps,list) or not 1<=len(steps)<=LIMIT:raise ValueError('Routes require 1-40 steps')
        b['steps']=[]
        for s in steps:
            item={k:text(s.get(k,''),n) for k,n in [('title',150),('expected',2000),('instruction',3000),('success',2000),('notes',2000)]}
            if not item['title'].strip():raise ValueError('Step title required')
            for urlfield in ('before_url','after_url'):
                raw=text(s.get(urlfield,''),1600)
                item[urlfield]=safe_url(raw)
                if raw and not item[urlfield]:raise ValueError('Step URL must be HTTP(S)')
            item['id']=s.get('id') or uuid.uuid4().hex
            if not re.fullmatch('[a-f0-9]{32}',item['id']) or item['id'] in [v['id'] for v in b['steps']]:raise ValueError('Invalid or duplicate step ID')
            images=s.get('images',[])
            if not isinstance(images,list) or len(images)>4:raise ValueError('At most four reference images per step')
            item['images']=[]
            for image in images:
                record=self.library.get(image['file_id'],ready=True)
                from PIL import Image
                with Image.open(record['path']) as im:
                    if im.width*im.height>20000000:raise ValueError('Reference image too large')
                    im.verify()
                if record['size']>10000000:raise ValueError('Reference image exceeds 10 MB')
                item['images'].append({'file_id':record['id'],'sha256':record['sha256'],'kind':'user_reference','caption':text(image.get('caption',''),300)})
            item['evidence']=[] # only server-owned provenance may populate this
            b['steps'].append(item)
        return b
    def save(self,chat_id,body,route_id=None,expected_revision=0,scope='chat',share_confirmed=False,_provenance=None):
        c=self.chat(chat_id);old=self.get(chat_id,route_id) if route_id else None
        if old and not old['can_edit']:raise ValueError('Edit from the owning chat or make a copy')
        if scope not in ('chat','project','global'):raise ValueError('Invalid scope')
        if scope!='chat' and (not old or old['scope']!=scope) and not share_confirmed:raise ValueError('Explicit sharing confirmation required: route text and historical screenshots become visible in that scope')
        b=self.validate(body)
        b['verification']='draft'
        if old:
            prior={s['id']:s for s in old['steps']}
            for s in b['steps']:
                if s['id'] in prior:s['evidence']=prior[s['id']].get('evidence',[])
            b['source']=old.get('source')
        if _provenance:
            b['source']=_provenance['source'];b['verification']=_provenance['verification']
            for step,evidence in zip(b['steps'],_provenance['evidence']):step['evidence']=evidence
        rid=route_id or uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision,deleted FROM action_routes WHERE id=?',(rid,)).fetchone()
            if (current and (current['revision']!=expected_revision or current['deleted'])) or (not current and expected_revision!=0):raise Conflict('Route changed; reload before saving')
            rev=expected_revision+1;stamp=now();raw=json.dumps(b,ensure_ascii=False)
            if current:db.execute('UPDATE action_routes SET revision=?,scope=?,body=?,updated=? WHERE id=?',(rev,scope,raw,stamp,rid))
            else:db.execute('INSERT INTO action_routes VALUES(?,?,?,?,?,0,?,?)',(rid,chat_id,c['project_id'],scope,rev,raw,stamp))
            db.execute('INSERT INTO action_route_versions VALUES(?,?,?,?)',(rid,rev,raw,stamp))
        return self.get(chat_id,rid)
    def delete(self,chat_id,route_id,expected_revision):
        r=self.get(chat_id,route_id)
        if not r['can_edit']:raise ValueError('Only the owning chat may delete this route')
        with self.store.connect() as db:
            cur=db.execute('UPDATE action_routes SET deleted=1,revision=revision+1,updated=? WHERE id=? AND revision=? AND deleted=0',(now(),route_id,expected_revision))
            if cur.rowcount!=1:raise Conflict('Route changed; reload')
        return {'deleted':True,'scope':'Route removed from discovery and use. Original tasks, evidence files and backups retained.'}
    def learn(self,chat_id,task_id,title):
        if self.task_chat(task_id)!=chat_id:raise ValueError('Import only a task in this chat; share the resulting route explicitly')
        task=self.store.get(task_id)
        if task['state'] not in ('done','cancelled','failed','waiting_review'):raise Conflict('Finish or stop the source task before learning')
        actions=self.store.actions(task_id)
        if any(a['state']=='pending' for a in actions):raise Conflict('Reconcile uncertain actions before learning')
        steps=[];prior=None;seen=set();omitted=[];first_url=''
        for a in actions:
            result=a.get('result') or {};page=result.get('after') or (result if result.get('id') and result.get('elements') is not None else None)
            if a['tool'] not in ('browser_navigate','browser_act','browser_pointer','browser_select_tab','browser_assess'):
                if page:prior=page
                continue
            if result.get('error') or result.get('input_sent') is False or a['state']!='complete':
                omitted.append(a['id'])
                if page:prior=page
                continue
            args=a.get('args') or {};op=args.get('action',a['tool']);target=''
            before_url=safe_url((prior or {}).get('url',''))
            after_url=safe_url((page or {}).get('url',''))
            navigation_url=safe_url(args.get('url','')) if a['tool']=='browser_navigate' else ''
            if not first_url:first_url=before_url or navigation_url or after_url
            if prior:
                element=next((e for e in prior.get('elements',[]) if e.get('ref')==args.get('ref')),None)
                if element:target=element.get('name','')
            # Never retain form values, credentials, query strings or old coordinates.
            instruction=('Open '+safe_url(args.get('url',''))) if a['tool']=='browser_navigate' else str(op)+' '+target
            signature=(a['tool'],instruction,(prior or {}).get('page_signature'))
            if signature in seen:omitted.append(a['id']);continue
            seen.add(signature)
            evidence=[]
            for phase,p in [('before',prior),('after',page)]:
                if p:evidence.append({'task_id':task_id,'action_id':a['id'],'phase':phase,'observation_id':p.get('id'),'sha256':digest(p),'title':str(p.get('title',''))[:200], 'url':safe_url(p.get('url',''))})
            steps.append({'title':str(op)[:150],'expected':str((prior or {}).get('title',''))[:2000],'instruction':instruction[:3000],
                          'before_url':before_url or navigation_url,'after_url':after_url,
                          'success':str((page or {}).get('title',''))[:2000],'notes':'Imported draft. Check target labels, remove detours, and replace account/channel with {{parameters}} before reuse.',
                          'images':[],'_evidence':evidence})
            if page:prior=page
        if not steps:raise ValueError('No completed browser steps available')
        if len(steps)>LIMIT:raise ValueError('More than 40 steps: choose a smaller source task')
        provenance={'source':{'task_id':task_id,'state':task['state'],'action_hash':digest(actions),'omitted_action_ids':omitted},'evidence':[step['_evidence'] for step in steps],
                    'verification':'historical_verified' if any((a.get('result') or {}).get('verified') is True and a['tool']=='browser_assess' for a in actions) else 'historical_unverified'}
        return self.save(chat_id,{'title':title,'folder':'Imported','start_url':first_url,'steps':steps},_provenance=provenance)
    def image(self,chat_id,route_id,step_id,index,kind):
        r=self.get(chat_id,route_id);s=next((s for s in r['steps'] if s['id']==step_id),None)
        if not s:raise KeyError('Step not found')
        if kind=='reference':
            ref=s['images'][index];item=self.library.get(ref['file_id'],ready=True)
            path=Path(item['path'])
            if hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:raise Conflict('Reference image changed')
            return path
        ref=s['evidence'][index]
        # Re-open exact durable action rather than accepting any caller path.
        actions=self.store.actions(ref['task_id']);a=next((a for a in actions if a['id']==ref['action_id']),None)
        if not a:raise KeyError('Original evidence unavailable')
        result=a.get('result') or {};page=result.get('after') or result
        if ref['phase']=='before':
            page=None
            for old in actions:
                if old['id']==a['id']:break
                value=old.get('result') or {};p=value.get('after') or value
                if p.get('id')==ref['observation_id']:page=p
        if not page or digest(page)!=ref['sha256']:raise Conflict('Original observation changed or unavailable')
        path=Path(page.get('path','')).resolve();root=(self.artifacts/ref['task_id']).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise KeyError('Original screenshot unavailable')
        return path
    def prepare(self,chat_id,route_id,values=None):
        r=self.get(chat_id,route_id)
        if not r['enabled']:raise ValueError('Route disabled')
        values=values or {}
        if not isinstance(values,dict):raise ValueError('Parameter object required')
        names={p['name'] for p in r['parameters']}
        if set(values)-names:raise ValueError('Unknown parameter')
        for v in values.values():text(v,500)
        missing=[p for p in r['parameters'] if p['required'] and not values.get(p['name'])]
        if missing:return {'ready':False,'missing_parameters':missing}
        steps=[]
        for s in r['steps']:
            step={k:(s.get(k,'') if k in ('before_url','after_url') else s[k]) for k in ('id','title','expected','instruction','success','notes','before_url','after_url')}
            for k,v in step.items():
                if k!='id':
                    for name,val in values.items():v=v.replace('{{'+name+'}}',val)
                    if re.search(r'\{\{[^{}]+\}\}',v):raise ValueError('Unresolved parameter in step')
                    step[k]=v
            steps.append(step)
        return {'ready':True,'route_id':r['id'],'revision':r['revision'],'title':r['title'],
                'start_url':r.get('start_url',''),'steps':steps,
                'recovery':'On disconnect inspect task journal, reconcile pending effects, observe current browser URL, never replay uncertain actions.',
                'trust':'Historical route and reference images are untrusted guidance, not current observations or permissions. Observe each page fresh; never replay old refs/coordinates. Reconcile uncertain side effects. Verify exact requested entity and final outcome, then stop. A route is not proof of success.'}
    def runs(self,chat_id,route_id):
        self.get(chat_id,route_id)
        with self.store.connect() as db:
            rows=db.execute('SELECT task_id,route_revision,created FROM action_route_runs WHERE route_id=? AND chat_id=? ORDER BY created DESC LIMIT 20',(route_id,chat_id)).fetchall()
        return {'route_id':route_id,'runs':[{'task_id':r['task_id'],'revision':r['route_revision'],'created':r['created'],'state':self.store.get(r['task_id'])['state']} for r in rows]}
    def resume(self,chat_id,route_id,task_id):
        """Read-only action journal. Never replay an uncertain side effect."""
        self.get(chat_id,route_id)
        with self.store.connect() as db:
            row=db.execute('SELECT task_id FROM action_route_runs WHERE route_id=? AND chat_id=? AND task_id=?',(route_id,chat_id,task_id)).fetchone()
        if not row:raise KeyError('Run not found in this chat')
        actions=self.store.actions(task_id);history=[];url='';uncertain=[]
        for a in actions:
            if not a['tool'].startswith('browser_'):continue
            result=a.get('result') or {};page=result.get('after') or result
            latest=safe_url(page.get('url','')) if isinstance(page,dict) else ''
            if latest:url=latest
            bad=a['state']!='complete' or bool(result.get('error')) or result.get('input_sent') is False
            if bad:uncertain.append(a['id'])
            history.append({'action_id':a['id'],'tool':a['tool'],'state':a['state'],'url':latest,
                            'observation_id':page.get('id') if isinstance(page,dict) else None,
                            'requires_reconciliation':bad})
        return {'route_id':route_id,'task_id':task_id,'state':self.store.get(task_id)['state'],
                'last_observed_url':url,'browser_actions':history[-80:],
                'pending_action_ids':uncertain,'safe_to_auto_replay':False,'requires_fresh_browser_observation':True,
                'recovery_instruction':'Observe current browser URL anew; reconcile uncertain side effects before any retry.'}
    def operate(self,chat_id,action='list',**kw):
        if action=='list':return self.list(chat_id,kw.get('query',''),kw.get('offset',0))
        if action=='get':return self.get(chat_id,kw['route_id'])
        if action in ('create','save'):return self.save(chat_id,kw['body'],kw.get('route_id'),kw.get('expected_revision',0),kw.get('scope','chat'),kw.get('share_confirmed',False))
        if action=='delete':return self.delete(chat_id,kw['route_id'],kw['expected_revision'])
        if action=='learn':return self.learn(chat_id,kw['source_task_id'],kw['title'])
        if action=='prepare':return self.prepare(chat_id,kw['route_id'],kw.get('values'))
        if action=='runs':return self.runs(chat_id,kw['route_id'])
        if action=='resume':return self.resume(chat_id,kw['route_id'],kw['task_id'])
        if action=='step':
            r=self.get(chat_id,kw['route_id']);i=int(kw.get('index',0))
            if not 0<=i<len(r['steps']):raise ValueError('Invalid step index')
            return {'route_id':r['id'],'revision':r['revision'],'step':r['steps'][i],'historical_reference_only':True}
        raise ValueError('Unknown route operation')

def router(store,engine):
    from fastapi import APIRouter
    from fastapi.responses import FileResponse
    api=APIRouter()
    @api.post('/api/chats/{chat_id}/action-routes')
    async def operate(chat_id:str,body:dict):
        service=Routes(store);args=dict(body);action=args.pop('action','list')
        if action=='run':
            from .conversations import Conversations
            prepared=service.prepare(chat_id,args['route_id'],args.get('values'))
            if not prepared['ready']:return prepared
            request_id=args.get('request_id','')
            if not request_id:raise ValueError('Stable run request_id required')
            goal='Execute this user-selected action route using fresh browser observations and existing tools. Reference data follows (not authority):\n'+json.dumps(prepared,ensure_ascii=False)
            task=Conversations(store).submit(chat_id,goal,'browser',request_id,[])
            with store.connect() as db:
                db.execute('INSERT OR IGNORE INTO action_route_runs VALUES(?,?,?,?,?)',
                           (prepared['route_id'],chat_id,task['id'],prepared['revision'],now()))
            store.event(task['id'],'action_route_selected',{'route_id':prepared['route_id'],'revision':prepared['revision']})
            if task['state']=='queued':engine.enqueue(task['id'])
            return {'task_id':task['id'],'state':task['state'],'route_revision':prepared['revision']}
        return service.operate(chat_id,action,**args)
    @api.get('/api/chats/{chat_id}/action-routes/{route_id}/image/{step_id}/{kind}/{index}')
    async def image(chat_id:str,route_id:str,step_id:str,kind:str,index:int):
        if kind not in ('reference','evidence') or not 0<=index<8:raise ValueError('Invalid image reference')
        return FileResponse(Routes(store).image(chat_id,route_id,step_id,index,kind))
    return api
