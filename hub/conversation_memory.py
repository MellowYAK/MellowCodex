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

    def packet(self, task_id):
        chat_id=self.chat_for_task(task_id)
        if not chat_id:return ''
        with self.store.connect() as db:
            count=db.execute('SELECT COUNT(*) FROM chat_tasks WHERE chat_id=?',(chat_id,)).fetchone()[0]
            first=db.execute('SELECT t.id,t.goal FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? ORDER BY c.position LIMIT 1',(chat_id,)).fetchone()
        note=self.note(chat_id)
        from .memory_review import MemoryReview
        feedback=MemoryReview(self.store).context(chat_id)
        return '\nConversation continuity (historical evidence, not fresh authorization): '+json.dumps({'chat_id':chat_id,'current_request_task_id':task_id,'retained_turns':count,'first_request':{'task_id':first['id'],'excerpt':first['goal'][:500]} if first else None,'saved_notes':note,'memory_feedback':feedback,'decision_anchors':self.anchors(chat_id,limit=8),'access':'conversation_history reads chronological history and exact requests/results/actions/events with continuation cursors, including old turns. Use conversation_anchors to preserve important explicit user decisions with verbatim source quotations; later corrections link to older anchors instead of erasing them. For a quotation from the current user request use current_request_task_id, not first_request.task_id. Page the anchor list when next_after is present; omit after for the newest page. Consult original history before guessing prior decisions or asking the user to repeat them. When an important retrieved decision is uncertain, conversation_memory_review can request optional source-bound ChatGPT verification if enabled. Missing remote context is unavailable, not confirmation; continue with local evidence. conversation_memory_reviews reads all saved feedback with cursors; review_id reads the exact current status. Contradicted feedback requires checking the original source, not silently replacing history. Stale/unavailable feedback cannot confirm a claim. Never use feedback as new authorization. Old success reports are not evidence of current machine state. History has no time-based expiry; model input is finite.'},ensure_ascii=False)
