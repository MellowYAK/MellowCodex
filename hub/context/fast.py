"""Source-first exploration; separate cache from the APC-derived baseline.

Reuses safe inventory/hash readers, not APC annotations or inferred graph data.
"""
import ast
import json
import re
from collections import Counter
from pathlib import PurePosixPath
from .service import ProjectContext, allowed, EXTENSIONS, EXCLUDED, norm, file_digest, extract


class FastContext(ProjectContext):
    database_name = 'context-fast.sqlite3'
    body_limit = None
    prefer_all_terms = True
    python_extractor = 'python_ast_imports_v2'
    allowed = staticmethod(lambda rel: allowed(rel,EXTENSIONS|{'.sh','.bat','.cmd','.ini'}))

    @staticmethod
    def extract(rel,text):
        symbols,imports,kind=extract(rel,text)
        if kind!='python_ast_v1':return symbols,imports,kind
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.ImportFrom):
                prefix='.'*node.level+(node.module+'.' if node.module else '')
                imports.extend(prefix+a.name for a in node.names if a.name!='*')
        return symbols,list(dict.fromkeys(imports)),'python_ast_imports_v2'

    @staticmethod
    def role(path):
        p=PurePosixPath(path)
        if path in ('AGENTS.md','README.md','docs/ARCHITECTURE.md'):return 'project_instructions'
        if p.name in ('pyproject.toml','package.json','requirements.txt','Cargo.toml','go.mod'):return 'dependency_manifest'
        if p.stem in ('main','app','server','gateway','router','routes','index','cli','manage','panel'):return 'possible_entrypoint'
        if p.name.startswith('test_') or 'tests' in p.parts:return 'possible_test'
        if p.suffix in ('.py','.js','.ts','.tsx','.jsx','.php','.html','.css','.ps1','.sh','.bat','.cmd'):return 'source'
        return 'supporting_file'

    def annotations(self, project_id, path=None):
        # User constraints remain authoritative in both modes. APC enrichment does not.
        return [a for a in super().annotations(project_id, path) if a['origin']=='user']

    def import_apc(self, *args, **kwargs):
        raise ValueError('APC import requires apc_baseline mode; fast source index is independent')

    def handle(self, row):
        return 'fast/' + super().handle(row)

    def row(self, project_id, ref):
        if not ref.startswith('fast/'):
            # Exact indexed relative paths are easier to use than opaque hashes.
            # Expansion still checks the indexed hash against the live file.
            self.project(project_id)
            with self.db() as db:
                row=db.execute('SELECT * FROM files WHERE project=? AND path=?',(project_id,ref)).fetchone()
            if row:return dict(row)
            raise ValueError('Index mode changed: obtain a fresh reference from context_search')
        return super().row(project_id, ref[5:])

    def expand(self,project_id,ref,start=1,lines=80):
        row=self.row(project_id,ref)
        result=super().expand(project_id,self.handle(row),start,lines)
        from .contracts import source_contracts,source_flow
        result['measured_input_declarations']=source_contracts(result['path'],result['text'],result['start'],symbols=json.loads(row['symbols']))
        result['measured_flow']=source_flow(result['path'],result['text'],result['start'],symbols=json.loads(row['symbols']))
        return result

    def search_paths(self,project_id,query):
        mentioned={norm(p.replace('\\','/').removeprefix('./')) for p in re.findall(r'[\w./\\-]+\.[a-zA-Z0-9]+',query)}
        with self.db() as db:rows=db.execute('SELECT path,symbols FROM files WHERE project=?',(project_id,)).fetchall()
        paths=[r['path'] for r in rows if norm(r['path']) in mentioned or norm(PurePosixPath(r['path']).name) in mentioned]
        if paths:return paths
        # A pasted call/decorator is an exact source lookup, not a bag of its
        # common tokens. Keep values parameterized and fall back if not found.
        literal=query.strip().strip('`')
        if re.fullmatch(r'@?[\w.]+\([^\n]*\)',literal):
            with self.db() as db:
                exact=db.execute('SELECT DISTINCT path FROM search WHERE project=? AND instr(body,?)>0',(project_id,literal)).fetchall()
            if exact:return [r['path'] for r in exact]
        # A distinctive observed function name should locate its definition,
        # not a translation string mentioning it or a guessed service filename.
        terms=set(re.findall(r'\w+',query))
        identifiers={w for w in terms if '_' in w or re.search(r'[a-z][A-Z]',w)}
        if terms & {'def','class','function'}:identifiers|=terms
        definitions=[r['path'] for r in rows if any(s['name'] in identifiers for s in json.loads(r['symbols']))]
        if definitions:return definitions
        # Unknown compound names are guesses, but their components can locate
        # an existing implementation (generate_image_video -> image_video.py).
        # Never claim the guessed symbol actually exists.
        compounds=[set(re.findall(r'[a-zA-Z][a-z]*',w.replace('_',' '))) for w in identifiers]
        return [r['path'] for r in rows if PurePosixPath(r['path']).suffix in ('.py','.js','.ts','.tsx','.jsx') and any(len({norm(x) for x in parts}&set(re.findall(r'\w+',norm(PurePosixPath(r['path']).stem).replace('_',' '))))>=2 for parts in compounds)]

    @staticmethod
    def query_terms(query):
        terms=re.findall(r'\w+',norm(query),re.U)[:16]
        boilerplate={'a','an','the','to','from','for','of','in','on','with','and','or','add','existing','project','feature','implementation','integration','architecture','library','api','pipeline'}
        focused=[term for term in terms if term not in boilerplate]
        if focused:terms=focused
        parts=[p for term in terms if '_' in term for p in term.split('_') if len(p)>2]
        return list(dict.fromkeys(terms+parts))[:32]

    def rank_paths(self,project_id,query):
        terms=set(self.query_terms(query))
        with self.db() as db:rows=db.execute('SELECT path FROM files WHERE project=?',(project_id,)).fetchall()
        ranked=[]
        vocabulary={r['path']:set(re.findall(r'\w+',norm(PurePosixPath(r['path']).stem).replace('_',' ').replace('-',' '))) for r in rows}
        frequency=Counter(term for words in vocabulary.values() for term in words)
        for row in rows:
            path=PurePosixPath(row['path']);stem=norm(path.stem)
            if path.suffix not in ('.py','.js','.ts','.tsx','.jsx'):continue
            if (stem.startswith('test_') or 'tests' in path.parts) and not terms&{'test','tests','testing'}:continue
            if stem.startswith(('install_','download_','setup')) and not terms&{'install','installation','download','setup'}:continue
            matched=terms&vocabulary[row['path']]
            if matched:
                ranked.append((len(matched),sum(1/frequency[word] for word in matched),row['path']))
        # Matching two requested concepts is a stronger source lead than a
        # generic worker matching only one. Path breaks ties deterministically.
        return [path for _,_,path in sorted(ranked,key=lambda item:(-item[0],-item[1],item[2]))]

    def search(self,project_id,query,limit=10,offset=0):
        result=super().search(project_id,query,limit,offset)
        result['lookup_policy']='Exact filenames/definitions first; unknown compound identifiers may return component-matched files. A match is not proof that a guessed symbol exists.'
        root=self.project(project_id)['path']
        terms=re.findall(r'\w+',norm(query),re.U)[:16]
        identifiers=set(re.findall(r'\w+',query))
        for hit in result['results']:
            path=self.safe_path(root,hit['path'])
            if not path.is_file():
                hit['stale']=True
                continue
            if file_digest(path)!=hit['hash']:
                hit['stale']=True
                continue
            matches=[]
            with path.open('r',encoding='utf-8-sig') as source:
                for number,line in enumerate(source,1):
                    score=sum(term in norm(line) for term in terms)
                    if score:
                        matches.append((score,number,line.rstrip('\r\n')[:400]))
                        matches.sort(key=lambda m:(-m[0],m[1]));matches=matches[:5]
            if file_digest(path)!=hit['hash']:
                hit['stale']=True
                continue
            matches.sort(key=lambda m:(-m[0],m[1]))
            hit['matches']=[{'line':n,'text':line[:400]} for _,n,line in matches[:5]]
            if matches:hit['suggested_start']=max(1,matches[0][1]-5)
            # Navigate to the definition requested, even when an import or
            # registration string near the top mentions more query terms.
            row=self.row(project_id,hit['ref'])
            definitions=[s for s in json.loads(row['symbols']) if s['name'] in identifiers]
            if definitions:
                hit['matched_definitions']=definitions
                hit['suggested_start']=max(1,definitions[0]['line']-5)
        return result

    def overview(self, project_id, offset=0, limit=40):
        if offset < 0 or not 1 <= limit <= 80:
            raise ValueError('Invalid map page')
        result = super().overview(project_id)
        with self.db() as db:
            rows = db.execute('SELECT * FROM files WHERE project=? ORDER BY path', (project_id,)).fetchall()
        priorities={'project_instructions':0,'dependency_manifest':1,'possible_entrypoint':2,'source':3,'possible_test':4,'supporting_file':5}
        rows=sorted(rows,key=lambda r:(priorities[self.role(r['path'])],r['path']))
        page = rows[offset:offset+limit]
        parser_counts=Counter(r['extractor'] for r in rows)
        parse_errors=[r['path'] for r in rows if r['extractor'].startswith('syntax_error')]
        # A compact filename tree supplies project vocabulary before the model
        # guesses feature names. It is navigation only, never inferred behavior.
        tree={};tree_bytes=0;tree_count=0
        for row in rows:
            path=PurePosixPath(row['path']);directory=str(path.parent)
            cost=len(path.name.encode('utf-8'))+4+(len(directory.encode('utf-8'))+6 if directory not in tree else 0)
            if tree_bytes+cost>12000:continue
            tree.setdefault(directory,[]).append(path.name);tree_bytes+=cost;tree_count+=1
        result.update(mode='fast', paths=[r['path'] for r in page], total_files=len(rows),
                      coverage={'basis':'Indexed snapshot under the source-file policy, not every physical file in the folder.',
                                'parser_counts':dict(parser_counts),
                                'symbol_count':sum(len(json.loads(r['symbols'])) for r in rows),
                                'syntax_error_count':len(parse_errors),
                                'syntax_error_paths':parse_errors[:20],
                                'omitted_syntax_error_paths':max(0,len(parse_errors)-20),
                                'excluded_directory_names':sorted(EXCLUDED),
                                'limitations':'Python AST symbols and static import candidates only. Other indexed languages are searchable text; filename roles and companions are hypotheses. Syntax-error files retain text search but have no parsed symbol graph. Secret-like filenames, unsupported extensions and links are excluded.'},
                      navigation_tree={'directories':tree,'listed_files':tree_count,'omitted_files':len(rows)-tree_count,'basis':'Indexed filenames only; read source before inferring behavior. Use paged capsules/search for omitted files.'},
                      next_offset=offset+limit if offset+limit<len(rows) else None,
                      groups=dict(Counter(r['path'].split('/')[0] if '/' in r['path'] else '(root)' for r in rows)),
                      entrypoints=[{'path':r['path'],'ref':self.handle(r)} for r in rows if r['path'] in ('AGENTS.md','README.md','docs/ARCHITECTURE.md')],
                      navigation_candidates=[{'path':r['path'],'ref':self.handle(r),'role_hint':self.role(r['path']),'basis':'filename heuristic; verify by reading source'} for r in rows if self.role(r['path']) in ('dependency_manifest','possible_entrypoint')][:16],
                      capsules=[{'path':r['path'], 'ref':self.handle(r), 'hash':r['hash'],
                                 'symbols':json.loads(r['symbols'])[:8],
                                 'symbol_count':len(json.loads(r['symbols'])),
                                 'parser':r['extractor']} for r in page],
                      exploration={'steps':['Read project instructions and entrypoints',
                                            'Search task concepts and exact symbols',
                                            'Expand source and inspect dependencies and reverse dependencies',
                                            'Verify assumptions against source and tests before changes'],
                                   'facts':'Paths, hashes and Python syntax are measured; file roles and runtime behavior require source verification.',
                                   'limits':'Lexical search; Python import resolution is static, not a complete call graph. Other languages remain searchable source.'})
        return result

    @staticmethod
    def dependencies(row, files, modules=None):
        path=PurePosixPath(row['path'])
        package=list(path.parent.parts) if str(path.parent)!='.' else []
        if modules is None:
            modules={f['path'][:-3].replace('/','.').removesuffix('.__init__'):f['path'] for f in files if f['path'].endswith('.py')}
        found=set()
        for name in json.loads(row['imports']):
            level=len(name)-len(name.lstrip('.'))
            candidates=[]
            if level:
                if level<=len(package):
                    candidates=['.'.join(package[:len(package)-level+1]+[name[level:]]).rstrip('.')]
            else:
                candidates=[name, '.'.join(package+[name])]
            for candidate in candidates:
                if candidate in modules:found.add(modules[candidate])
        return found

    def related(self, project_id, ref):
        row=self.row(project_id,ref)
        with self.db() as db:
            files=db.execute('SELECT * FROM files WHERE project=? ORDER BY path',(project_id,)).fetchall()
        modules={f['path'][:-3].replace('/','.').removesuffix('.__init__'):f['path'] for f in files if f['path'].endswith('.py')}
        outgoing=self.dependencies(row,files,modules); related=[]
        for f in files:
            if f['path']==row['path']:continue
            kinds=[]
            if f['path'] in outgoing:kinds.append('imports')
            if row['path'] in self.dependencies(f,files,modules):kinds.append('imported_by')
            if PurePosixPath(f['path']).stem=='test_'+PurePosixPath(row['path']).stem:kinds.append('tested_by')
            current=PurePosixPath(row['path']);candidate=PurePosixPath(f['path'])
            if (current.parent==candidate.parent and current.suffix!=candidate.suffix
                and current.suffix in ('.py','.js','.ts','.tsx','.jsx','.html')
                and candidate.suffix in ('.py','.js','.ts','.tsx','.jsx','.html')
                and current.stem.replace('-','_')==candidate.stem.replace('-','_')):
                kinds.append('possible_companion')
            for kind in kinds:
                related.append({'path':f['path'],'ref':self.handle(f),'kind':kind,
                                'confidence':'filename_heuristic' if kind in ('tested_by','possible_companion') else 'static_module_candidate'})
        related.sort(key=lambda r:(PurePosixPath(r['path']).name=='__init__.py',{'imports':0,'imported_by':1,'tested_by':2,'possible_companion':3}[r['kind']],r['path']))
        return {'ref':self.handle(row),'symbols':json.loads(row['symbols']), 'imports':json.loads(row['imports']),
                'related':related[:80], 'total_related':len(related), 'truncated':len(related)>80}
