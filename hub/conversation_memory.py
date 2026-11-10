"""Chronological conversation evidence; no expiry, embeddings or inferred facts.

SQLite remains authoritative. Pages are bounded, never the retained history.
Saved continuity notes are explicit user/director statements with revisions.
"""
import json
import hashlib
import uuid
import re
from .store import Conflict, now


class ConversationMemory:
    def __init__(self, store):
        self.store=store
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS conversation_notes(
                chat_id TEXT NOT NULL, revision INTEGER NOT NULL, text TEXT NOT NULL,
                source TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(chat_id,revision))''')
            db.execute('''CREATE TABLE IF NOT EXISTS conversation_anchors(
                id TEXT PRIMARY KEY,chat_id TEXT NOT NULL,source_task_id TEXT NOT NULL,
                quote TEXT NOT NULL,source_hash TEXT NOT NULL,label TEXT NOT NULL,
                supersedes TEXT,created TEXT NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS conversation_anchors_chat ON conversation_anchors(chat_id,created)')
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='conversation_request_search'").fetchone():
                db.execute('CREATE VIRTUAL TABLE conversation_request_search USING fts5(goal)')
                db.execute('INSERT INTO conversation_request_search(rowid,goal) SELECT rowid,goal FROM tasks')
                db.execute('CREATE TRIGGER request_search_insert AFTER INSERT ON tasks BEGIN INSERT INTO conversation_request_search(rowid,goal) VALUES(new.rowid,new.goal); END')
                db.execute('CREATE TRIGGER request_search_delete AFTER DELETE ON tasks BEGIN DELETE FROM conversation_request_search WHERE rowid=old.rowid; END')
                db.execute('CREATE TRIGGER request_search_update AFTER UPDATE OF goal ON tasks BEGIN DELETE FROM conversation_request_search WHERE rowid=old.rowid; INSERT INTO conversation_request_search(rowid,goal) VALUES(new.rowid,new.goal); END')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='conversation_anchor_search'").fetchone():
                db.execute('CREATE VIRTUAL TABLE conversation_anchor_search USING fts5(quote,label)')
                db.execute('INSERT INTO conversation_anchor_search(rowid,quote,label) SELECT rowid,quote,label FROM conversation_anchors')
                db.execute('CREATE TRIGGER anchor_search_insert AFTER INSERT ON conversation_anchors BEGIN INSERT INTO conversation_anchor_search(rowid,quote,label) VALUES(new.rowid,new.quote,new.label); END')
                db.execute('CREATE TRIGGER anchor_search_delete AFTER DELETE ON conversation_anchors BEGIN DELETE FROM conversation_anchor_search WHERE rowid=old.rowid; END')
                db.execute('CREATE TRIGGER anchor_search_update AFTER UPDATE ON conversation_anchors BEGIN DELETE FROM conversation_anchor_search WHERE rowid=old.rowid; INSERT INTO conversation_anchor_search(rowid,quote,label) VALUES(new.rowid,new.quote,new.label); END')

    def relevant_anchors(self,chat_id,query,limit=6):
        """Indexed lexical candidates, not inferred facts; include linked corrections."""
        if not 1<=limit<=12:raise ValueError('Invalid relevant anchor limit')
        terms=list(dict.fromkeys(t.lower() for t in re.findall(r'[^\W_]+',query,flags=re.UNICODE) if len(t)>1))[:32]
        if not terms:return {'items':[],'evidence_only':True}
        match=' OR '.join('"'+t+'"' for t in terms)
        with self.store.connect() as db:
            self._exists(db,chat_id)
            seeds=[r[0] for r in db.execute('''SELECT a.id FROM conversation_anchor_search f
                JOIN conversation_anchors a ON a.rowid=f.rowid WHERE conversation_anchor_search MATCH ? AND a.chat_id=?
                ORDER BY rank,a.rowid DESC LIMIT ?''',(match,chat_id,limit))]
            # Follow both directions so a correction whose text omits the old
            # subject is not lost. Bound model input, never stored history.
            ids=list(seeds);index=0
            while index<len(ids) and len(ids)<24:
                ident=ids[index];index+=1
                for r in db.execute('''SELECT id FROM conversation_anchors WHERE chat_id=? AND
                    (supersedes=? OR id=(SELECT supersedes FROM conversation_anchors WHERE id=? AND chat_id=?))''',(chat_id,ident,ident,chat_id)):
                    if r[0] not in ids:ids.append(r[0])
                    if len(ids)>=24:break
            items=[]
            for ident in ids:
                row=db.execute('''SELECT a.*,t.goal,EXISTS(SELECT 1 FROM conversation_anchors n WHERE n.supersedes=a.id) superseded
                    FROM conversation_anchors a JOIN tasks t ON t.id=a.source_task_id WHERE a.id=? AND a.chat_id=?''',(ident,chat_id)).fetchone()
                item=dict(row);goal=item.pop('goal')
                item['source_changed']=hashlib.sha256(goal.encode()).hexdigest()!=item['source_hash']
                items.append(item)
        omitted=[]
        while len(json.dumps(items,ensure_ascii=False))>7000 and len(items)>1:
            omitted.insert(0,items.pop()['id'])
        return {'items':items,'omitted_anchor_ids':omitted,'evidence_only':True,'selection':'lexical candidates and linked corrections',
                'chain_may_continue':len(ids)>=24,'note':'Candidate relevance is not verified truth. Use original quotations and supersession links; changed sources require rereading. Full history and all anchors remain paged.'}

    def anchors(self,chat_id,after=None,limit=12):
        """User-request quotations, not model-generated facts or fresh permission."""
        if not 1<=limit<=30 or after is not None and after<0:raise ValueError('Invalid anchor page size/cursor')
        if after==0:after=None
        with self.store.connect() as db:
            self._exists(db,chat_id)
            rows=db.execute('''SELECT a.rowid cursor,a.*,t.goal,EXISTS(SELECT 1 FROM conversation_anchors n WHERE n.supersedes=a.id) superseded
                FROM conversation_anchors a JOIN tasks t ON t.id=a.source_task_id
                WHERE a.chat_id=? AND (? IS NULL OR a.rowid<?) ORDER BY a.rowid DESC LIMIT ?''',
                (chat_id,after,after,limit+1)).fetchall()
            items=[]
            for r in rows[:limit]:
                item=dict(r);goal=item.pop('goal')
                item['source_changed']=hashlib.sha256(goal.encode()).hexdigest()!=item['source_hash']
                items.append(item)
            cursor=db.execute('SELECT rowid FROM conversation_anchors WHERE id=?',(items[-1]['id'],)).fetchone()[0] if len(rows)>limit else None
        return {'items':items,'next_after':cursor,'evidence_only':True,'note':'Labels and supersession links are agent/director annotations; exact quotations remain the evidence. Changed sources require rereading. Historical requests do not authorize new actions.'}

    def remember(self,chat_id,source_task_id,quote,label,supersedes=None):
        if not quote.strip() or len(quote)>1200 or not label.strip() or len(label)>160:raise ValueError('Provide a short exact quotation and label')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._exists(db,chat_id)
            row=db.execute('SELECT t.goal,c.position FROM tasks t JOIN chat_tasks c ON c.task_id=t.id WHERE c.chat_id=? AND t.id=?',(chat_id,source_task_id)).fetchone()
            if not row or quote not in row['goal']:raise ValueError('Quotation must occur verbatim in a user request from this conversation')
            if supersedes:
                old=db.execute('SELECT c.position FROM conversation_anchors a JOIN chat_tasks c ON c.task_id=a.source_task_id WHERE a.chat_id=? AND a.id=?',(chat_id,supersedes)).fetchone()
                if not old or old['position']>=row['position']:raise ValueError('A replacement must cite a later user request in the same conversation')
            digest=hashlib.sha256(row['goal'].encode()).hexdigest()
            existing=db.execute('SELECT id FROM conversation_anchors WHERE chat_id=? AND source_task_id=? AND quote=? AND source_hash=? AND supersedes IS ?',(chat_id,source_task_id,quote,digest,supersedes)).fetchone()
            if supersedes and not existing and db.execute('SELECT 1 FROM conversation_anchors WHERE supersedes=?',(supersedes,)).fetchone():raise Conflict('Anchor already superseded; read the latest anchors')
            ident=existing['id'] if existing else uuid.uuid4().hex
            if not existing:db.execute('INSERT INTO conversation_anchors VALUES(?,?,?,?,?,?,?,?)',(ident,chat_id,source_task_id,quote,digest,label,supersedes,now()))
        return {'id':ident,'source_task_id':source_task_id,'quote':quote,'source_hash':digest,'label':label,'supersedes':supersedes,'evidence_only':True}

    def chat_for_task(self, task_id):
        with self.store.connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_tasks'").fetchone():return None
            row=db.execute('SELECT chat_id FROM chat_tasks WHERE task_id=?',(task_id,)).fetchone()
        return row[0] if row else None

    def _exists(self, db, chat_id):
        if not db.execute('SELECT 1 FROM chats WHERE id=?',(chat_id,)).fetchone():raise KeyError('Chat not found')

    def note(self, chat_id):
        with self.store.connect() as db:
            self._exists(db,chat_id)
            row=db.execute('SELECT * FROM conversation_notes WHERE chat_id=? ORDER BY revision DESC LIMIT 1',(chat_id,)).fetchone()
        return dict(row) if row else {'chat_id':chat_id,'revision':0,'text':'','source':'none'}

    def save_note(self, chat_id, text, expected_revision, source='user'):
        if source not in ('user','director'):raise ValueError('Notes must identify user or director provenance')
        if len(text)>6000:raise ValueError('Continuity notes exceed 6000 characters; history remains independently available')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._exists(db,chat_id)
            revision=db.execute('SELECT COALESCE(MAX(revision),0) FROM conversation_notes WHERE chat_id=?',(chat_id,)).fetchone()[0]
            if revision!=expected_revision:raise Conflict('Continuity note changed; read the current revision before saving')
            db.execute('INSERT INTO conversation_notes VALUES(?,?,?,?,?)',(chat_id,revision+1,text,source,now()))
        return self.note(chat_id)

    def history(self, chat_id, after=-1, limit=10, query='', task_id=None, field='result', offset=0, chars=3000):
        if after < -1 or not 1<=limit<=20 or offset<0 or not 1<=chars<=6000 or len(query)>500:raise ValueError('Invalid history page bounds')
        if field not in ('goal','result','actions','events'):raise ValueError('Unknown history field')
        with self.store.connect() as db:
            self._exists(db,chat_id)
            total=db.execute('SELECT COUNT(*) FROM chat_tasks WHERE chat_id=?',(chat_id,)).fetchone()[0]
            if task_id:
                row=db.execute('SELECT t.* FROM tasks t JOIN chat_tasks c ON c.task_id=t.id WHERE c.chat_id=? AND t.id=?',(chat_id,task_id)).fetchone()
                if not row:raise KeyError('Task does not belong to this conversation')
                if field in ('goal','result'):text=row[field]
                else:text=json.dumps(self.store.actions(task_id) if field=='actions' else self.store.events(task_id),ensure_ascii=False)
                end=min(offset+chars,len(text))
                return {'chat_id':chat_id,'task_id':task_id,'field':field,'text':text[offset:end],'offset':offset,'next_offset':end if end<len(text) else None,'total_characters':len(text),'evidence_only':True}
            terms=list(dict.fromkeys(t.lower() for t in re.findall(r'[^\W_]+',query,flags=re.UNICODE) if len(t)>1))[:32]
            match=' OR '.join('"'+t+'"' for t in terms) or '""'
            rows=db.execute('''SELECT c.position,t.id,t.created,t.state,substr(t.goal,1,500) goal,substr(t.result,1,500) result,length(t.goal) goal_characters,length(t.result) result_characters,
                CASE WHEN ?='' OR instr(lower(t.goal),lower(?))>0 OR instr(lower(t.result),lower(?))>0 THEN 'literal' ELSE 'token_candidate' END match_kind FROM chat_tasks c
                JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND c.position>?
                AND (?='' OR instr(lower(t.goal),lower(?))>0 OR instr(lower(t.result),lower(?))>0
                    OR t.rowid IN (SELECT rowid FROM conversation_request_search WHERE conversation_request_search MATCH ?))
                ORDER BY c.position LIMIT ?''',(query,query,query,chat_id,after,query,query,query,match,limit+1)).fetchall()
            fallback=bool(query and not rows)
            if fallback:
                # A translated/paraphrased query can miss literal Hebrew text.
                # Return a clearly labelled chronological page, not invented hits.
                rows=db.execute('''SELECT c.position,t.id,t.created,t.state,substr(t.goal,1,500) goal,substr(t.result,1,500) result,length(t.goal) goal_characters,length(t.result) result_characters
                    FROM chat_tasks c JOIN tasks t ON t.id=c.task_id
                    WHERE c.chat_id=? AND c.position>? ORDER BY c.position LIMIT ?''',(chat_id,after,limit+1)).fetchall()
        turns=[]
        for row in rows[:limit]:
            turn=dict(row)
            turn['source_roles']={'goal':'original_user_request','result':'historical_assistant_report_not_independent_verification'}
            turns.append(turn)
        candidates=any(turn.get('match_kind')=='token_candidate' for turn in turns)
        if candidates:
            return {'chat_id':chat_id,'total_turns':total,'turns':turns,'next_after':turns[-1]['position'] if len(rows)>limit else None,
                    'notes':self.note(chat_id),'evidence_only':True,'chronological_fallback':False,'search_mode':'literal_and_token_candidates',
                    'search_note':'Some records match individual query words, not the exact phrase. They are candidates, not verified answers. The goal field is the ORIGINAL USER REQUEST, not assistant prose. Read its text and later user corrections; result is an assistant report, not independent proof. Answer in the language of the current user request. Continue with the SAME query and next_after.',
                    'detail_tool':'conversation_history with task_id, field goal/result/actions/events and next_offset reads original full evidence'}
        return {'chat_id':chat_id,'total_turns':total,'turns':turns,'next_after':turns[-1]['position'] if len(rows)>limit else None,'notes':self.note(chat_id),'evidence_only':True,'chronological_fallback':fallback,'search_note':'No literal matches. These are chronological turns, NOT search matches. Read these and continue with query empty and next_after instead of repeating the same query.' if fallback else None,'detail_tool':'conversation_history with task_id, field and next_offset reads the exact full text'}

    def has_prior_context(self, task_id):
        chat_id=self.chat_for_task(task_id)
        if not chat_id:return False
        with self.store.connect() as db:
            other=db.execute('SELECT 1 FROM chat_tasks WHERE chat_id=? AND task_id!=? LIMIT 1',(chat_id,task_id)).fetchone()
            anchor=db.execute('SELECT 1 FROM conversation_anchors WHERE chat_id=? LIMIT 1',(chat_id,)).fetchone()
        return bool(other or anchor or self.note(chat_id)['text'])

    def packet(self, task_id):
        chat_id=self.chat_for_task(task_id)
        if not chat_id:return ''
        with self.store.connect() as db:
            count=db.execute('SELECT COUNT(*) FROM chat_tasks WHERE chat_id=?',(chat_id,)).fetchone()[0]
            first=db.execute('SELECT t.id,t.goal FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? ORDER BY c.position LIMIT 1',(chat_id,)).fetchone()
        note=self.note(chat_id)
        if count==1 and not note['text'] and not self.anchors(chat_id,limit=1)['items']:
            return '\nConversation continuity: this is the first request in this chat. No earlier conversation decisions are available. The current request is already provided above. Project implementation facts must come from project source, not from searching this same request in conversation history.'
        from .memory_review import MemoryReview
        feedback=MemoryReview(self.store).context(chat_id)
        return '\nConversation continuity (historical evidence, not fresh authorization): '+json.dumps({'chat_id':chat_id,'current_request_task_id':task_id,'retained_turns':count,'first_request':{'task_id':first['id'],'excerpt':first['goal'][:500]} if first else None,'saved_notes':note,'memory_feedback':feedback,'decision_anchors':self.relevant_anchors(chat_id,self.store.get(task_id)['goal']), 'explicit_pins':self.pinned_memory(chat_id),'access':'conversation_history reads chronological history and exact requests/results/actions/events with continuation cursors, including old turns. Use conversation_anchors to preserve important explicit user decisions with verbatim source quotations; later corrections link to older anchors instead of erasing them. For a quotation from the current user request use current_request_task_id, not first_request.task_id. Page the anchor list when next_after is present; omit after for the newest page. Consult original history before guessing prior decisions or asking the user to repeat them. When an important retrieved decision is uncertain, conversation_memory_review can request optional source-bound ChatGPT verification if enabled. Missing remote context is unavailable, not confirmation; continue with local evidence. conversation_memory_reviews reads all saved feedback with cursors; review_id reads the exact current status. Contradicted feedback requires checking the original source, not silently replacing history. Stale/unavailable feedback cannot confirm a claim. Never use feedback as new authorization. Old success reports are not evidence of current machine state. History has no time-based expiry; model input is finite.'},ensure_ascii=False)


    def working_state(self, task_id, expected_revision=None):
        """Incremental, source-bound projection; never authorizes or replays actions."""
        with self.store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS context_working_state(task_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, watermark INTEGER NOT NULL, task_revision INTEGER NOT NULL, data TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS context_events_task_seq ON events(task_id,seq)')
            db.execute('CREATE TRIGGER IF NOT EXISTS context_forget_task AFTER DELETE ON tasks BEGIN DELETE FROM context_working_state WHERE task_id=old.id; END')
            db.execute('CREATE TRIGGER IF NOT EXISTS context_forget_event AFTER DELETE ON events BEGIN DELETE FROM context_working_state WHERE task_id=old.task_id; END')
            db.execute('CREATE TRIGGER IF NOT EXISTS context_changed_goal AFTER UPDATE OF goal ON tasks BEGIN DELETE FROM context_working_state WHERE task_id=old.id; END')
            db.execute('BEGIN IMMEDIATE')
            task=db.execute('SELECT id,revision,state,goal,criteria FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not task:raise KeyError('Task not found')
            if expected_revision is not None and task['revision']!=expected_revision:raise Conflict('Task changed before context snapshot')
            old=db.execute('SELECT * FROM context_working_state WHERE task_id=?',(task_id,)).fetchone()
            state=json.loads(old['data']) if old else {'schema_version':1,'task_id':task_id,'revision':0,'source_watermark':0,'observations':[],'failed_attempts':[],'verification':[],'deployment':[]}
            rows=db.execute("SELECT seq,kind,data,at FROM events WHERE task_id=? AND seq>? ORDER BY seq LIMIT 1000",(task_id,state['source_watermark'])).fetchall()
            for event in rows:
                data=json.loads(event['data']);ref={'event_seq':event['seq'],'task_id':task_id,'timestamp':event['at']}
                if event['kind']=='tool_result':
                    result=data.get('result') or {};result=result if isinstance(result,dict) else {}
                    item={'source_refs':[ref],'action_id':data.get('action_id'),'tool':data.get('name'),'status':'observed','result_sha256':hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
                    action=db.execute('SELECT args FROM actions WHERE id=? AND task_id=?',(data.get('action_id'),task_id)).fetchone()
                    item['action_signature']=hashlib.sha256((str(data.get('name'))+(action[0] if action else '')).encode()).hexdigest()
                    if result.get('error'):
                        item.update(status='failed',error_excerpt=str(result['error'])[:300]);state['failed_attempts']=(state['failed_attempts']+[item])[-12:]
                    state['observations']=(state['observations']+[item])[-16:]
                    if data.get('name') in ('candidate_stage_release','upgrade_activate','upgrade_status'):
                        item=dict(item,reported_state=result.get('state'),verified=False);state['deployment']=(state['deployment']+[item])[-4:]
                elif event['kind']=='verification':
                    state['verification']=(state['verification']+[{'source_refs':[ref],'status':'recorded_check','scope':data.get('scope'),'not_deployment_proof':True}])[-4:]
                state['source_watermark']=event['seq']
            state.update(task_revision=task['revision'],lifecycle=task['state'],objective={'text':task['goal'],'source_refs':[{'task_id':task_id,'field':'goal','sha256':hashlib.sha256(task['goal'].encode()).hexdigest()}]},acceptance_criteria=json.loads(task['criteria']),next_step=None)
            state['pending_operations']=[dict(r) for r in db.execute("SELECT id,tool,state FROM actions WHERE task_id=? AND state!='complete' ORDER BY rowid DESC LIMIT 20",(task_id,))]
            state['degraded']='projection_catching_up' if len(rows)==1000 else None
            state['revision']+=1
            db.execute('INSERT INTO context_working_state VALUES(?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET revision=excluded.revision,watermark=excluded.watermark,task_revision=excluded.task_revision,data=excluded.data',(task_id,state['revision'],state['source_watermark'],task['revision'],json.dumps(state,ensure_ascii=False)))
        return state

    def context_evidence(self, chat_id, task_id, message_index, sha256, offset=0, chars=3000):
        """Expand an exact packet reference only inside its original conversation."""
        if self.chat_for_task(task_id)!=chat_id:raise KeyError('Evidence outside this conversation')
        if offset<0 or not 1<=chars<=6000 or message_index<0:raise ValueError('Invalid evidence page')
        messages=self.store.get(task_id)['messages']
        if message_index>=len(messages):raise ValueError('Source no longer available')
        text=messages[message_index].get('content','')
        if hashlib.sha256(text.encode()).hexdigest()!=sha256:raise Conflict('Evidence changed; obtain a fresh reference')
        return {'task_id':task_id,'message_index':message_index,'sha256':sha256,'text':text[offset:offset+chars],'offset':offset,'next_offset':offset+chars if offset+chars<len(text) else None,'evidence_only':True}

    def context_diagnostics(self, chat_id, task_id):
        if self.chat_for_task(task_id)!=chat_id:raise KeyError('Task outside this conversation')
        with self.store.connect() as db:
            row=db.execute("SELECT data FROM events WHERE task_id=? AND kind='model' ORDER BY seq DESC LIMIT 1",(task_id,)).fetchone()
            projection=db.execute("SELECT 1 FROM sqlite_master WHERE name='context_working_state'").fetchone()
            state=db.execute('SELECT revision,watermark,task_revision FROM context_working_state WHERE task_id=?',(task_id,)).fetchone() if projection else None
        metrics=json.loads(row[0]).get('metrics',{}) if row else {}
        return {'task_id':task_id,'chat_id':chat_id,'packet':metrics.get('packet'),'last_actual_input':metrics.get('prompt_eval_count'),'last_actual_output':metrics.get('eval_count'),'checkpoint':dict(state) if state else None,'history_loaded':False}


    def _pin_schema(self, db):
        db.execute('CREATE TABLE IF NOT EXISTS context_memory_pins(anchor_id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, project_id TEXT, scope TEXT NOT NULL, revision INTEGER NOT NULL, pinned INTEGER NOT NULL)')
        db.execute('CREATE TRIGGER IF NOT EXISTS context_forget_anchor AFTER DELETE ON conversation_anchors BEGIN DELETE FROM context_memory_pins WHERE anchor_id=old.id; END')
        db.execute('CREATE TRIGGER IF NOT EXISTS context_forget_anchor_source AFTER DELETE ON tasks BEGIN DELETE FROM context_memory_pins WHERE anchor_id IN (SELECT id FROM conversation_anchors WHERE source_task_id=old.id); END')

    def pin_memory(self, chat_id, anchor_id, scope, pinned, expected_revision):
        if scope not in ('chat','project') or not isinstance(pinned,bool):raise ValueError('Invalid memory pin')
        with self.store.connect() as db:
            self._pin_schema(db);db.execute('BEGIN IMMEDIATE')
            chat=db.execute('SELECT project_id FROM chats WHERE id=?',(chat_id,)).fetchone()
            anchor=db.execute('SELECT a.*,t.goal FROM conversation_anchors a JOIN tasks t ON t.id=a.source_task_id WHERE a.id=? AND a.chat_id=?',(anchor_id,chat_id)).fetchone()
            if not chat or not anchor:raise KeyError('Anchor outside this conversation')
            if hashlib.sha256(anchor['goal'].encode()).hexdigest()!=anchor['source_hash']:raise Conflict('Anchor source changed')
            old=db.execute('SELECT revision FROM context_memory_pins WHERE anchor_id=?',(anchor_id,)).fetchone()
            revision=old[0] if old else 0
            if revision!=expected_revision:raise Conflict('Memory pin changed; read current revision')
            if scope=='project' and not chat['project_id']:raise ValueError('Chat has no project')
            db.execute('INSERT INTO context_memory_pins VALUES(?,?,?,?,?,?) ON CONFLICT(anchor_id) DO UPDATE SET scope=excluded.scope,project_id=excluded.project_id,revision=excluded.revision,pinned=excluded.pinned',(anchor_id,chat_id,chat['project_id'],scope,revision+1,int(pinned)))
        return {'anchor_id':anchor_id,'scope':scope,'pinned':pinned,'revision':revision+1}

    def pinned_memory(self, chat_id, offset=0):
        if not isinstance(offset,int) or offset<0:raise ValueError("Invalid memory page")
        with self.store.connect() as db:
            self._pin_schema(db);self._exists(db,chat_id)
            project=db.execute('SELECT project_id FROM chats WHERE id=?',(chat_id,)).fetchone()[0]
            rows=db.execute("""SELECT p.*,a.quote,a.label,a.source_task_id,a.source_hash,t.goal FROM context_memory_pins p
                JOIN conversation_anchors a ON a.id=p.anchor_id JOIN tasks t ON t.id=a.source_task_id
                WHERE p.pinned=1 AND ((p.scope='chat' AND p.chat_id=?) OR (p.scope='project' AND p.project_id=?))
                AND NOT EXISTS(SELECT 1 FROM conversation_anchors newer WHERE newer.supersedes=a.id)
                ORDER BY p.revision DESC,p.anchor_id LIMIT 13 OFFSET ?""",(chat_id,project,offset)).fetchall()
            pin_records=[dict(r) for r in db.execute('SELECT anchor_id,scope,revision,pinned FROM context_memory_pins WHERE chat_id=? ORDER BY anchor_id LIMIT 100 OFFSET ?',(chat_id,offset))]
        items=[]
        for row in rows[:12]:
            if hashlib.sha256(row['goal'].encode()).hexdigest()!=row['source_hash']:continue
            items.append({k:row[k] for k in ('anchor_id','scope','revision','quote','label','source_task_id','source_hash','chat_id')})
        return {'items':items,'pin_records':pin_records,'next_offset':offset+12 if len(rows)>12 else None,'more_available':len(rows)>12,'evidence_only':True,'sharing':'project entries were explicitly promoted; chat entries remain private'}
