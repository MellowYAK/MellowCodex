"""Read-only browser entry evidence from registered project documentation."""
import hashlib,re
from pathlib import Path
from urllib.parse import urlsplit
def key(value):
    return ''.join(c for c in str(value).casefold() if c.isalnum())
def discover(projects,application):
    wanted=key(application)
    matches=[p for p in projects if wanted and wanted in {key(p['name']),key(Path(p['path']).name)}]
    if len(matches)!=1:
        return {'application':application,'entries':[],'reason':'No unique registered project matches. Use an exact returned project name.','projects':[{'id':p['id'],'name':p['name']} for p in projects]}
    project=matches[0];root=Path(project['path']).resolve();entries=[]
    for filename in ('README.md','README.rst','README.txt'):
        path=root/filename
        if not path.is_file() or not path.resolve().is_relative_to(root) or path.stat().st_size>500000:continue
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        for line_number,line in enumerate(raw.decode('utf-8',errors='replace').splitlines(),1):
            for url in re.findall(r'https?://[^\s<>"\x27\x60]+',line):
                url=url.rstrip('.,;:)*|]')
                try:
                    parsed=urlsplit(url)
                    if parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:continue
                    if parsed.path not in ('','/'):continue
                    if not parsed.port:continue
                except ValueError:continue
                if any(e['url']==url.rstrip('/')+'/' for e in entries):continue
                entries.append({'url':url.rstrip('/')+'/','label':line.strip()[:250],'source':filename,'line':line_number,'sha256':digest})
                if len(entries)>=12:break
    return {'project_id':project['id'],'application':project['name'],'entries':entries,
            'reason':'Documented entry candidates, not proof of a running service. Select the requested UI by its source label; never confuse a service manager with the application.',
            'health_verified':False}
def for_task(store,task,application):
    from .conversation_memory import ConversationMemory
    chat_id=ConversationMemory(store).chat_for_task(task['id'])
    if not chat_id:raise ValueError('Task has no persistent conversation')
    with store.connect() as db:
        projects=[dict(r) for r in db.execute('SELECT id,name,path FROM projects')]
    return {'chat_id':chat_id,**discover(projects,application)}
def repeated_history(name,args,actions):
    if name!='conversation_history':return False
    previous=[a for a in actions if a.get('tool')==name and a.get('args')==args and isinstance(a.get('result'),dict) and not a['result'].get('error')]
    return len(previous)>=2 and previous[-1]['result']==previous[-2]['result']
