"""Deterministic project intelligence. APC provenance: docs/apc-reuse-manifest.json.

Only metadata contracts are ported. Python AST + SQLite FTS5 replace APC's
regex extraction and full-JSON candidate scan. Never executes project code.
"""
import ast
import hashlib
import json
import os
import re
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from ..i18n import CapabilityError, t

EXCLUDED={'.git','.venv','venv','node_modules','__pycache__','.pytest_cache','models',
          'state','backups','credentials','secrets','uploads','downloads','artifacts',
          'output','dist','build','vendor','data','.tools'}
EXTENSIONS={'.py','.js','.ts','.tsx','.jsx','.php','.html','.css','.json','.md','.toml','.yaml','.yml','.ps1','.sql','.txt'}
MAX_FILE=1_000_000
MAX_FILES=15000

def digest(data):return hashlib.sha256(data).hexdigest()
def identity(*parts):return digest('\0'.join(parts).encode())[:32]
def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text)).casefold() if unicodedata.category(c)!='Mn')

def allowed(rel):
    p=Path(rel)
    return not (any(part.lower() in EXCLUDED for part in p.parts)
                or p.name.startswith('.env') or p.name.lower() in {'config.php','hub.key'}
                or re.search(r'(?:credential|secret|private.?key|token)',p.name,re.I)
                or p.suffix.lower() not in EXTENSIONS)

def safe_path(root,rel):
    win=PureWindowsPath(rel)
    if not rel or win.is_absolute() or win.drive or ':' in rel or '\x00' in rel:
        raise CapabilityError('context.invalid_path')
    root=Path(root).resolve();p=(root/rel).resolve()
    if not p.is_relative_to(root) or not allowed(rel):raise CapabilityError('context.invalid_path')
    # Refuse links even when their current target happens to stay within root.
    cur=root
    for part in Path(rel).parts:
        if part in ('..','') or part.rstrip('. ')!=part or PureWindowsPath(part).is_reserved():raise CapabilityError('context.invalid_path')
        cur=cur/part
        if cur.is_symlink() or (hasattr(cur,'is_junction') and cur.is_junction()):raise CapabilityError('context.invalid_path')
    return p

def extract(rel,text):
    symbols=[];imports=[]
    if rel.endswith('.py'):
        try:tree=ast.parse(text)
        except SyntaxError:return symbols,imports,'syntax_error'
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                symbols.append({'name':n.name,'kind':type(n).__name__,'line':n.lineno,'end_line':n.end_lineno})
            elif isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):imports.append('.'*n.level+(n.module or ''))
        return symbols,imports,'python_ast_v1'
    return symbols,imports,'text_v1'

class ProjectContext:
    def __init__(self,state,conversations):
        self.state=Path(state);self.state.mkdir(parents=True,exist_ok=True)
        self.path=self.state/'context.sqlite3';self.conversations=conversations
        with self.db() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS snapshots(project TEXT PRIMARY KEY,revision INTEGER NOT NULL,updated REAL NOT NULL,counts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,project TEXT NOT NULL,path TEXT NOT NULL,hash TEXT NOT NULL,size INTEGER NOT NULL,mtime INTEGER NOT NULL,extractor TEXT NOT NULL,symbols TEXT NOT NULL,imports TEXT NOT NULL,UNIQUE(project,path));
CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(file_id UNINDEXED,project UNINDEXED,path,body,metadata,tokenize='unicode61 remove_diacritics 2');
''')
        # Authoritative annotations live in the existing backed-up task database.
        with self.conversations.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS context_annotations(project TEXT NOT NULL,path TEXT NOT NULL,origin TEXT NOT NULL,payload TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(project,path,origin))''')
            db.execute('''CREATE TABLE IF NOT EXISTS context_import_reports(project TEXT NOT NULL,source TEXT NOT NULL,source_sha256 TEXT NOT NULL,report TEXT NOT NULL,updated REAL NOT NULL,PRIMARY KEY(project,source))''')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:yield db
        finally:db.close()

    def project(self,project_id):
        with self.conversations.store.connect() as db:
            row=db.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
        if not row:raise CapabilityError('context.missing')
        return dict(row)

    def annotations(self,project_id,path=None):
        with self.conversations.store.connect() as db:
            rows=db.execute('SELECT * FROM context_annotations WHERE project=?'+(' AND path=?' if path else ''),(project_id,path) if path else (project_id,)).fetchall()
        return [dict(r)|{'payload':json.loads(r['payload'])} for r in rows]

    def refresh(self,project_id):
        p=self.project(project_id);root=Path(p['path']).resolve()
        if not root.is_dir():raise CapabilityError('context.invalid_path')
        with self.db() as db:
            old={r['path']:dict(r) for r in db.execute('SELECT * FROM files WHERE project=?',(project_id,))}
            seen=set();changed=[];skipped=0;unchanged=0
            from .inventory import walk
            deadline=time.monotonic()+30;read_bytes=0
            for rel in walk(root,EXCLUDED,deadline):
                if not allowed(rel):continue
                if len(seen)>=MAX_FILES:raise CapabilityError('context.limit')
                try:
                    path=safe_path(root,rel);stat=path.stat()
                    if stat.st_size>MAX_FILE:skipped+=1;continue
                    read_bytes+=stat.st_size
                    if read_bytes>100_000_000 or time.monotonic()>deadline:raise ValueError('Index read budget exceeded; previous index preserved')
                    prior=old.get(rel)
                    raw=path.read_bytes()
                    if prior and prior['mtime']==stat.st_mtime_ns and prior['size']==stat.st_size and prior['extractor']==('python_ast_v1' if rel.endswith('.py') else 'text_v1') and digest(raw)==prior['hash']:
                        seen.add(rel);unchanged+=1;continue
                    text=raw.decode('utf-8-sig');h=digest(raw)
                except OSError:
                    raise
                except (UnicodeError,CapabilityError):skipped+=1;continue
                seen.add(rel)
                syms,imports,extractor=extract(rel,text);fid=identity(project_id,rel)
                metadata=json.dumps([a['payload'] for a in self.annotations(project_id,rel)],ensure_ascii=False)
                db.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)',(fid,project_id,rel,h,len(raw),stat.st_mtime_ns,extractor,json.dumps(syms),json.dumps(imports)))
                db.execute('DELETE FROM search WHERE file_id=?',(fid,))
                db.execute('INSERT INTO search VALUES(?,?,?,?,?)',(fid,project_id,norm(rel),norm(text[:64000]),norm(metadata)))
                changed.append(rel)
            deleted=set(old)-seen
            for rel in deleted:
                db.execute('DELETE FROM files WHERE id=?',(old[rel]['id'],));db.execute('DELETE FROM search WHERE file_id=?',(old[rel]['id'],))
            last=db.execute('SELECT revision FROM snapshots WHERE project=?',(project_id,)).fetchone()
            revision=(last[0] if last else 0)+(1 if changed or deleted or not last else 0)
            counts={'indexed':db.execute('SELECT count(*) FROM files WHERE project=?',(project_id,)).fetchone()[0],'changed':len(changed),'deleted':len(deleted),'unchanged':unchanged,'skipped':skipped}
            db.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?)',(project_id,revision,time.time(),json.dumps(counts)))
        result={'project_id':project_id,'revision':revision,**counts}
        from .indexing import Indexing
        Indexing(self).record_refresh(project_id,result)
        return result

    def overview(self,project_id):
        p=self.project(project_id)
        with self.db() as db:
            snap=db.execute('SELECT * FROM snapshots WHERE project=?',(project_id,)).fetchone()
            paths=[r[0] for r in db.execute('SELECT path FROM files WHERE project=? ORDER BY path LIMIT 80',(project_id,))]
        annotations=[];budget=6000;required=[];omitted=0
        for item in self.annotations(project_id):
            constraints=item['payload'].get('must_not_break',[])
            if constraints:required.append({'path':item['path'],'origin':item['origin'],'revision':item['revision'],'must_not_break':constraints})
        if len(json.dumps(required,ensure_ascii=False))>12000:raise CapabilityError('context.limit')
        for item in self.annotations(project_id):
            size=len(json.dumps(item,ensure_ascii=False))
            if size>budget:
                omitted+=1;continue
            annotations.append(item);budget-=size
        return {'project':p,'index':dict(snap) if snap else None,'paths':paths,'annotations':annotations,'required_constraints':required,'omitted_annotations':omitted,'source_policy':t('context.source_data'),'inference_required':False}

    def handle(self,row):return row['id']+':'+row['hash']

    def search(self,project_id,query,limit=10,offset=0):
        self.project(project_id)
        if not query.strip() or len(query)>500 or not 1<=limit<=40 or not 0<=offset<=10000:raise CapabilityError('context.invalid')
        terms=re.findall(r'\w+',norm(query),re.U)[:16]
        if not terms:return {'results':[]}
        expr=' OR '.join('"'+term+'"' for term in terms)
        with self.db() as db:
            rows=db.execute('''SELECT f.*,bm25(search,0,0,5,1,8) score,snippet(search,3,'[',']',' â€¦ ',32) excerpt FROM search JOIN files f ON f.id=search.file_id WHERE search MATCH ? AND search.project=? ORDER BY score LIMIT ? OFFSET ?''',(expr,project_id,limit+1,offset)).fetchall()
        results=[]
        for r in rows[:limit]:
            notes=self.annotations(project_id,r['path']);meta=norm(json.dumps(notes,ensure_ascii=False))
            reasons=[]
            if any(term in norm(r['path']) for term in terms):reasons.append('path')
            if any(term in meta for term in terms):reasons.append('annotation')
            if not reasons:reasons.append('source')
            results.append({'ref':self.handle(r),'path':r['path'],'hash':r['hash'],'excerpt':r['excerpt'][:1200],'match_reasons':reasons,'symbols':json.loads(r['symbols'])[:15]})
        with self.db() as db:snapshot=db.execute('SELECT revision,updated,counts FROM snapshots WHERE project=?',(project_id,)).fetchone()
        return {'results':results,'next_offset':offset+limit if len(rows)>limit else None,'project_id':project_id,
                'snapshot':dict(snapshot) if snapshot else None,'freshness':'indexed snapshot; exact content hash is rechecked by context_expand before use'}

    def row(self,project_id,ref):
        self.project(project_id)
        parts=ref.split(':')
        if len(parts)!=2:raise CapabilityError('context.invalid')
        with self.db() as db:row=db.execute('SELECT * FROM files WHERE project=? AND id=?',(project_id,parts[0])).fetchone()
        if not row:raise CapabilityError('context.missing')
        if parts[1]!=row['hash']:raise CapabilityError('context.stale')
        return dict(row)

    def expand(self,project_id,ref,start=1,lines=80):
        if start<1 or not 1<=lines<=200:raise CapabilityError('context.invalid')
        row=self.row(project_id,ref);p=self.project(project_id);path=safe_path(p['path'],row['path'])
        if not path.is_file():raise CapabilityError('context.stale')
        if path.stat().st_size>MAX_FILE:raise CapabilityError('context.limit')
        raw=path.read_bytes()
        if digest(raw)!=row['hash']:raise CapabilityError('context.stale')
        all_lines=raw.decode('utf-8-sig').splitlines();selected=[];length=0
        for line in all_lines[start-1:start-1+lines]:
            if length+len(line)>12000:break
            selected.append(line);length+=len(line)+1
        if not selected and start<=len(all_lines):raise CapabilityError('context.limit')
        return {'ref':ref,'path':row['path'],'start':start,'end':start+len(selected)-1,'text':'\n'.join(selected),'next_line':start+len(selected) if start+len(selected)<=len(all_lines) else None,'total_lines':len(all_lines)}

    def related(self,project_id,ref):
        row=self.row(project_id,ref);imports=json.loads(row['imports']);stem=Path(row['path']).stem
        with self.db() as db:files=db.execute('SELECT * FROM files WHERE project=? ORDER BY path',(project_id,)).fetchall()
        related=[]
        for f in files:
            if f['id']==row['id']:continue
            module=f['path'].removesuffix('.py').replace('/','.')
            if any(i.strip('.')==module or module.endswith('.'+i.strip('.')) for i in imports if i.strip('.')):
                related.append({'ref':self.handle(f),'path':f['path'],'kind':'imports','confidence':'heuristic_module_resolution'})
            elif Path(f['path']).stem=='test_'+stem:
                related.append({'ref':self.handle(f),'path':f['path'],'kind':'tested_by','confidence':'filename_heuristic'})
        return {'ref':ref,'symbols':json.loads(row['symbols'])[:100],'imports':imports[:80],'related':related[:40]}

    def annotate(self,project_id,path,aliases=None,tags=None,notes='',must_not_break=None,origin='user'):
        p=self.project(project_id);safe_path(p['path'],path)
        payload={'aliases':aliases or [],'tags':tags or [],'notes':notes,'must_not_break':must_not_break or []}
        if len(json.dumps(payload,ensure_ascii=False))>12000:raise CapabilityError('context.limit')
        for k in ('aliases','tags','must_not_break'):
            if not isinstance(payload[k],list) or len(payload[k])>40 or any(not isinstance(v,str) or len(v)>500 for v in payload[k]):raise CapabilityError('context.invalid')
        if not isinstance(notes,str):raise CapabilityError('context.invalid')
        with self.conversations.store.connect() as db:
            old=db.execute('SELECT revision FROM context_annotations WHERE project=? AND path=? AND origin=?',(project_id,path,origin)).fetchone()
            revision=(old[0] if old else 0)+1
            db.execute('INSERT OR REPLACE INTO context_annotations VALUES(?,?,?,?,?)',(project_id,path,origin,json.dumps(payload,ensure_ascii=False),revision))
        with self.db() as db:
            row=db.execute('SELECT id FROM files WHERE project=? AND path=?',(project_id,path)).fetchone()
            if row:db.execute('UPDATE search SET metadata=? WHERE file_id=?',(norm(json.dumps([a['payload'] for a in self.annotations(project_id,path)],ensure_ascii=False)),row[0]))
        return {'path':path,'revision':revision,'origin':origin,'saved':True}

    def import_apc(self,project_id,path):
        p=self.project(project_id);source=safe_path(p['path'],path)
        if source.stat().st_size>MAX_FILE:raise CapabilityError('context.limit')
        raw=json.loads(source.read_text(encoding='utf-8-sig'))
        if isinstance(raw,dict) and raw.get('schema') not in (None,'apc.project_map_search_index.v1'):
            raise ValueError('Unsupported APC index schema')
        docs=raw.get('documents',raw.get('docs',[])) if isinstance(raw,dict) else raw
        if not isinstance(docs,list) or len(docs)>2000:raise CapabilityError('context.invalid')
        from .apc import document
        imported=skipped=0;reports=[];seen=set()
        for doc in docs:
            try:
                rel,content_hash,payload,provenance=document(doc)
                key=str(doc.get('doc_id',rel))
                if key in seen:raise ValueError('Duplicate document identity; conflicting entry skipped')
                seen.add(key)
                target=safe_path(p['path'],rel)
                if not target.is_file():raise CapabilityError('context.missing')
                if target.stat().st_size>MAX_FILE:raise CapabilityError('context.limit')
                measured=digest(target.read_bytes())
                if content_hash and content_hash!=measured:raise ValueError('Stale file content hash')
                origin='apc:'+identity(path,key)
                current=[a for a in self.annotations(project_id,rel) if a['origin']==origin]
                if not current or current[0]['payload']!=payload:self.annotate(project_id,rel,origin=origin,**payload)
                imported+=1
                reports.append({'doc_id':key,'status':'imported','path':rel,'origin':origin,'measured_file_sha256':measured,**provenance})
            except (CapabilityError,OSError,TypeError,AttributeError,ValueError) as exc:
                skipped+=1;reports.append({'doc_id':doc.get('doc_id') if isinstance(doc,dict) else None,'status':'skipped','reason':str(exc)})
        report={'schema':'mellow.apc-import-report.v1','imported':imported,'skipped':skipped,'source_preserved':True,'documents':reports}
        with self.conversations.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO context_import_reports VALUES(?,?,?,?,?)',(project_id,path,digest(source.read_bytes()),json.dumps(report,ensure_ascii=False),time.time()))
        return report

    def recovery(self,project_id):
        result=self.overview(project_id)
        with self.conversations.store.connect() as db:
            note=db.execute('SELECT notes FROM project_notes WHERE project_id=?',(project_id,)).fetchone()
            rows=db.execute('SELECT t.id,t.goal,t.state,t.result,t.revision FROM tasks t JOIN chat_tasks ct ON ct.task_id=t.id JOIN chats c ON c.id=ct.chat_id WHERE c.project_id=? ORDER BY t.created DESC LIMIT 8',(project_id,)).fetchall()
        result['saved_instructions']=note[0][:8000] if note else ''
        result['recent_tasks']=[dict(r)|{'goal':r['goal'][:1500],'result':(r['result'] or '')[:2000]} for r in rows]
        result['uncertain_actions']=[{'task_id':r['id'],'action_id':a['id'],'tool':a['tool'],'state':a['state']} for r in rows for a in self.conversations.store.actions(r['id']) if a['state']=='pending'][:40]
        result['replayed']=False
        return result
