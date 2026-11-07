"""Durable director guidance with revision and consumer-epoch fencing."""
import json
import uuid
from typing import Literal
from pathlib import PurePosixPath
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..store import Conflict, now
from .contracts import PatchProposal

class ContextRead(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation:Literal['brief','overview','search','related']
    query:str=Field(default='',max_length=500)
    path:str=Field(default='',max_length=700)
    ref:str=Field(default='',max_length=700)
    offset:int=Field(default=0,ge=0,le=10000)
    limit:int=Field(default=10,ge=1,le=40)

    def call(self):
        name={'brief':'project_brief','overview':'project_context','search':'context_search','related':'context_related'}[self.operation]
        fields={'brief':['query'],'overview':['offset','limit'],'search':['query','offset','limit'],'related':['path','ref']}[self.operation]
        return name,{key:getattr(self,key) for key in fields}

class SourceRequirement(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str=Field(min_length=1,max_length=1000)
    start:int=Field(ge=1)
    end:int=Field(ge=1)
    sha256:str=Field(default='',pattern=r'^([a-f0-9]{64})?$')

    @field_validator('path')
    @classmethod
    def relative_path(cls,value):
        value=value.replace('\\','/')
        if PurePosixPath(value).is_absolute() or ':' in value or '..' in PurePosixPath(value).parts:
            raise ValueError('Source requirements use project-relative paths')
        return str(PurePosixPath(value))

    @field_validator('end')
    @classmethod
    def ordered_range(cls,value,info):
        if value<info.data.get('start',1):raise ValueError('Source range ends before it starts')
        return value

def source_covered(requirement,actions,created):
    """Prove delivered text coverage from successful, version-consistent reads."""
    groups={}
    for action in actions:
        result=action.get('result')
        if action.get('state')!='complete' or action.get('created','')<created or not isinstance(result,dict):continue
        if result.get('error') or result.get('verified') is False or not result.get('text'):continue
        if str(result.get('path','')).replace('\\','/')!=requirement['path']:continue
        digest=result.get('sha256') or result.get('hash') or str(result.get('ref','')).rsplit(':',1)[-1]
        import re
        if not re.fullmatch('[a-f0-9]{64}',str(digest)):continue
        if requirement['sha256'] and digest!=requirement['sha256']:continue
        start,end=result.get('start'),result.get('end')
        if not isinstance(start,int) or not isinstance(end,int) or start<1 or end<start:continue
        # Metadata cannot stand in for source omitted by a transport compactor.
        if len(result['text'].split('\n'))<end-start+1:continue
        groups.setdefault(digest,[]).append((start,end))
    for ranges in groups.values():
        cursor=requirement['start']
        for start,end in sorted(ranges):
            if start>cursor:break
            cursor=max(cursor,end+1)
            if cursor>requirement['end']:return True
    return False

class Guidance:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS development_consumers(task_id TEXT PRIMARY KEY,epoch TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS development_guidance(task_id TEXT NOT NULL,revision INTEGER NOT NULL,request_id TEXT NOT NULL,text TEXT NOT NULL,epoch TEXT NOT NULL,consumed_epoch TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,PRIMARY KEY(task_id,revision),UNIQUE(task_id,request_id));
''')
            if 'required_tools' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN required_tools TEXT NOT NULL DEFAULT '[]'")
            if 'required_sources' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN required_sources TEXT NOT NULL DEFAULT '[]'")
            if 'allowed_tools' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN allowed_tools TEXT NOT NULL DEFAULT 'null'")

            if 'evidence_only' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN evidence_only INTEGER NOT NULL DEFAULT 0")

            if 'context_read' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN context_read TEXT NOT NULL DEFAULT 'null'")

            if 'exact_patch' not in {r[1] for r in db.execute('PRAGMA table_info(development_guidance)')}:
                db.execute("ALTER TABLE development_guidance ADD COLUMN exact_patch TEXT NOT NULL DEFAULT 'null'")

    def context_read(self,task_id):
        records=self.status(task_id)['guidance']
        return json.loads(records[-1]['context_read']) if records else None

    def next_context_call(self,task_id,actions):
        record=self.status(task_id)['guidance'][-1]
        request=json.loads(record['context_read'])
        if not request:return None
        name,args=ContextRead.model_validate(request).call()
        if any(a['tool']==name and a.get('args')==args and a['created']>=record['created'] for a in actions):return None
        return {'role':'assistant','content':'Retrieving the director-requested project context.',
                'tool_calls':[{'function':{'name':name,'arguments':args}}]}

    def exact_patch(self,task_id):
        records=self.status(task_id)['guidance']
        return json.loads(records[-1]['exact_patch']) if records else None

    def next_patch_call(self,task_id,actions):
        records=self.status(task_id)['guidance']
        if not records:return None
        record=records[-1];patch=json.loads(record['exact_patch'])
        if not patch:return None
        current=[a for a in actions if a.get('created','')>=record['created']]
        attempted=[a for a in current if a.get('tool')=='candidate_patch' and a.get('args')==patch]
        if not attempted:name,args='candidate_patch',patch
        elif attempted[-1]['state']=='complete' and not (attempted[-1].get('result') or {}).get('error'):
            name,args='candidate_diff',{'candidate_id':patch['candidate_id']}
            if any(a.get('tool')==name and a.get('args')==args for a in current):return None
        else:return None
        return {'role':'assistant','content':'Executing the exact director patch step without model rewriting.',
                'tool_calls':[{'function':{'name':name,'arguments':args}}]}

    def evidence_only(self,task_id):
        records=self.status(task_id)['guidance']
        return bool(records and records[-1]['evidence_only'])

    def allowed_tools(self,task_id):
        """A task's director constraints can narrow, never widen, its tool scope."""
        with self.store.connect() as db:
            values=[json.loads(r[0]) for r in db.execute('SELECT allowed_tools FROM development_guidance WHERE task_id=?',(task_id,))]
        scopes=[set(value) for value in values if value is not None]
        return set.intersection(*scopes) if scopes else None

    def begin(self,task_id):
        epoch=uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute('INSERT INTO development_consumers VALUES(?,?) ON CONFLICT(task_id) DO UPDATE SET epoch=excluded.epoch',(task_id,epoch))
        return epoch

    def status(self,task_id):
        task=self.store.get(task_id)
        with self.store.connect() as db:
            consumer=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            rows=db.execute('SELECT * FROM development_guidance WHERE task_id=? ORDER BY revision',(task_id,)).fetchall()
        return {'task_id':task_id,'task_revision':task['revision'],'task_state':task['state'],'human_request_original':task['goal'],'consumer_epoch':consumer['epoch'] if consumer else '', 'guidance_revision':len(rows),'guidance':[dict(r) for r in rows]}

    def submit(self,task_id,expected_task_revision,expected_revision,consumer_epoch,request_id,text,required_tools=None,required_sources=None,allowed_tools=None,evidence_only=False,exact_patch=None,context_read=None):
        if context_read is not None:
            context_read=ContextRead.model_validate(context_read).model_dump()
            if required_sources or required_tools or exact_patch or evidence_only:raise ValueError('Context retrieval is a separate bounded step')
            name,_=ContextRead.model_validate(context_read).call()
            if allowed_tools is not None and name not in allowed_tools:raise ValueError('Context retrieval selected tool is excluded by allowed_tools')
            allowed_tools=[name]
        if len(required_sources or [])>20:raise ValueError('Too many source requirements')
        required_sources=[SourceRequirement.model_validate(s).model_dump() for s in (required_sources or [])]
        if exact_patch is not None:
            exact_patch=PatchProposal.model_validate(exact_patch).model_dump()
            if evidence_only or required_sources or required_tools:raise ValueError('Exact patch is a separate bounded step')
            safe={'candidate_patch','candidate_diff'}
            if allowed_tools is not None and set(allowed_tools)!=safe:raise ValueError('Exact patch requires patch and diff tools only')
            allowed_tools=sorted(safe)
        if type(evidence_only) is not bool:raise ValueError('evidence_only must be boolean')
        if evidence_only:
            if not required_sources or required_tools:raise ValueError('Evidence-only steps require source ranges and no other required tools')
            safe={'project_context','context_refresh','context_expand'}
            if allowed_tools is not None and (not isinstance(allowed_tools,list) or any(not isinstance(n,str) for n in allowed_tools) or not set(allowed_tools)<=safe):raise ValueError('Evidence-only steps allow only source retrieval tools')
            allowed_tools=sorted(set(allowed_tools) if allowed_tools is not None else safe)
        required_tools=list(dict.fromkeys(required_tools or []))
        import re
        if allowed_tools is not None:
            if not isinstance(allowed_tools,list) or len(allowed_tools)>200 or any(not isinstance(n,str) or not re.fullmatch('[a-z][a-z0-9_]{0,79}',n) for n in allowed_tools):raise ValueError('Invalid allowed tool names')
            allowed_tools=sorted(set(allowed_tools))
        if len(required_tools)>20 or any(not re.fullmatch('[a-z][a-z0-9_]{0,79}',n) for n in required_tools):raise ValueError('Invalid required tool names')
        if not text.strip() or len(text)>8000 or not 1<=len(request_id)<=100:raise ValueError('Invalid guidance text or request identity')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not task:raise KeyError('Task not found')
            old=db.execute('SELECT * FROM development_guidance WHERE task_id=? AND request_id=?',(task_id,request_id)).fetchone()
            if old:
                if json.loads(old['context_read'])!=context_read or json.loads(old['exact_patch'])!=exact_patch or bool(old['evidence_only'])!=evidence_only or old['text']!=text or json.loads(old['required_tools'])!=required_tools or json.loads(old['required_sources'])!=required_sources or json.loads(old['allowed_tools'])!=allowed_tools:raise Conflict('Guidance request identity reused with different content')
                return dict(old)
            consumer=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            epoch=consumer['epoch'] if consumer else ''
            count,size=db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(text)),0) FROM development_guidance WHERE task_id=?',(task_id,)).fetchone()
            if task['mode']!='code' or task['state'] in ('done','cancelled'):raise Conflict('Task does not accept coding guidance')
            if task['revision']!=expected_task_revision or count!=expected_revision or epoch!=consumer_epoch:raise Conflict('Stale task, guidance revision or consumer epoch; read current guidance status')
            if size+len(text)>20000:raise Conflict('Mandatory guidance budget exceeded; split the task')
            scopes=[set(json.loads(r[0])) for r in db.execute("SELECT allowed_tools FROM development_guidance WHERE task_id=? AND allowed_tools!='null'",(task_id,))]
            if allowed_tools is not None:scopes.append(set(allowed_tools))
            if scopes:
                effective=set.intersection(*scopes)
                needed=set(required_tools)|({'context_expand'} if required_sources else set())|({'candidate_patch','candidate_diff'} if exact_patch else set())|({ContextRead.model_validate(context_read).call()[0]} if context_read else set())
                for prior in db.execute('SELECT required_tools,required_sources FROM development_guidance WHERE task_id=?',(task_id,)):
                    needed.update(json.loads(prior[0]))
                    if json.loads(prior[1]):needed.add('context_expand')
                if not needed<=effective:raise ValueError('Required evidence tools conflict with allowed tools')
            db.execute('INSERT INTO development_guidance(task_id,revision,request_id,text,epoch,created,required_tools,required_sources,allowed_tools,evidence_only,exact_patch,context_read) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(task_id,count+1,request_id,text,epoch,now(),json.dumps(required_tools),json.dumps(required_sources),json.dumps(allowed_tools),int(evidence_only),json.dumps(exact_patch),json.dumps(context_read)))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',(task_id,task['revision'],'guidance_received',json.dumps({'guidance_revision':count+1,'request_id':request_id,'consumer_epoch':epoch}),now()))
        return self.status(task_id)

    def consume(self,task_id,epoch):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT epoch FROM development_consumers WHERE task_id=?',(task_id,)).fetchone()
            if not current or current['epoch']!=epoch:raise Conflict('Coding consumer was replaced')
            rows=db.execute('SELECT * FROM development_guidance WHERE task_id=? ORDER BY revision',(task_id,)).fetchall()
            fresh=[r for r in rows if r['consumed_epoch']!=epoch]
            if fresh:
                db.execute('UPDATE development_guidance SET consumed_epoch=? WHERE task_id=?',(epoch,task_id))
                db.execute('INSERT INTO events(task_id,revision,kind,data,at) SELECT id,revision,?,?,? FROM tasks WHERE id=?',('guidance_in_packet',json.dumps({'consumer_epoch':epoch,'revisions':[r['revision'] for r in fresh],'meaning':'included in next model packet; not execution confirmation'}),now(),task_id))
        return [dict(r) for r in rows]

    def missing_evidence(self,task_id,actions):
        records=self.status(task_id)['guidance'];missing=[]
        for record in records:
            for source in json.loads(record['required_sources']):
                if not source_covered(source,actions,record['created']):
                    missing.append(f"source:{source['path']}:{source['start']}-{source['end']}")
            for name in json.loads(record['required_tools']):
                good=[a for a in actions if a['tool']==name and a['state']=='complete' and a['created']>=record['created'] and isinstance(a.get('result'),dict) and not a['result'].get('error') and a['result'].get('verified') is not False]
                if not good and name not in missing:missing.append(name)
        return missing

    def source_packet(self,task_id,actions):
        from ..source_feedback import source_feedback
        latest=self.status(task_id)['guidance'][-1]
        sources=json.loads(latest['required_sources'])
        selected=[a for a in actions if a.get('created','')>=latest['created']
                  and any(a.get('args',{}).get('path')==r['path'] for r in sources)]
        packet=source_feedback(selected)
        missing=self.missing_evidence(task_id,actions)
        return {**packet,'guidance_revision':latest['revision'],
                'requested_sources':sources,'missing_evidence':missing,
                'retrieval_complete':not missing and packet['complete_delivery'],
                'semantic_verified':False,'model_inference':False,
                'status':'awaiting_director_review'}

    def next_source_call(self,task_id,actions):
        """Dispatch exact required reads through the normal runner, once per chunk.

        Failed or stale reads remain missing evidence; never silently retry or
        replace them with a broad search. Normal runner path checks still apply.
        """
        for record in self.status(task_id)['guidance']:
            for source in json.loads(record['required_sources']):
                if source_covered(source,actions,record['created']):continue
                for start in range(source['start'],source['end']+1,200):
                    args={'path':source['path'],'start':start,'lines':min(200,source['end']-start+1)}
                    attempted=any(a.get('tool')=='context_expand' and a.get('args')==args and a.get('created','')>=record['created'] for a in actions)
                    if not attempted:
                        return {'role':'assistant','content':'Reading the required source range for director review.',
                                'tool_calls':[{'function':{'name':'context_expand','arguments':args}}]}
        return None
