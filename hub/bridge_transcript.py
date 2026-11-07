"""Persistent correspondence between the human, ChatGPT and local agent."""
import json,time,uuid
from urllib.parse import urlsplit


class BridgeTranscript:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS bridge_messages (
                id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, dedupe_key TEXT UNIQUE,
                speaker TEXT NOT NULL, direction TEXT NOT NULL, text TEXT NOT NULL,
                files TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL)''')
            db.execute('CREATE TABLE IF NOT EXISTS bridge_chat_links(chat_id TEXT PRIMARY KEY,remote_url TEXT UNIQUE NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS bridge_connection_preferences(chat_id TEXT PRIMARY KEY,transport TEXT NOT NULL,favorite INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS bridge_listener_sessions(chat_id TEXT PRIMARY KEY,state TEXT NOT NULL)')

    def save_session(self,state):
        if not state.get('chat_id'):return
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO bridge_listener_sessions VALUES(?,?)',(state['chat_id'],json.dumps(state,ensure_ascii=False)))

    def session(self,chat_id):
        with self.store.connect() as db:
            row=db.execute('SELECT state FROM bridge_listener_sessions WHERE chat_id=?',(chat_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def connection(self,chat_id):
        with self.store.connect() as db:
            if not db.execute('SELECT 1 FROM chats WHERE id=?',(chat_id,)).fetchone():raise KeyError('Chat not found')
            row=db.execute('SELECT transport,favorite FROM bridge_connection_preferences WHERE chat_id=?',(chat_id,)).fetchone()
        return {'chat_id':chat_id,'transport':row[0] if row else 'play','favorite':bool(row[1]) if row else False,'url':self.remote(chat_id),'provider':'chatgpt'}

    def configure(self,chat_id,transport=None,favorite=None,url=None):
        current=self.connection(chat_id)
        if transport is not None and transport not in ('play','mcp'):raise ValueError('Transport must be play or mcp')
        if favorite is not None and type(favorite) is not bool:raise ValueError('Favorite must be boolean')
        if url is not None:
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.netloc!='chatgpt.com' or not parsed.path.startswith('/c/') or not parsed.path[3:] or parsed.query or parsed.fragment:
                raise ValueError('Use an exact https://chatgpt.com/c/... conversation URL')
        with self.store.connect() as db:
            if url is not None:
                existing=db.execute('SELECT chat_id FROM bridge_chat_links WHERE remote_url=?',(url,)).fetchone()
                if existing and existing[0]!=chat_id:raise ValueError('This ChatGPT conversation already belongs to another saved local chat')
                db.execute('INSERT OR REPLACE INTO bridge_chat_links VALUES(?,?)',(chat_id,url))
            db.execute('INSERT OR REPLACE INTO bridge_connection_preferences VALUES(?,?,?)',(chat_id,transport or current['transport'],int(current['favorite'] if favorite is None else favorite)))
        return {**self.connection(chat_id),'applies':'next_connection','connected':False}

    def favorites(self):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT c.id chat_id,c.title,p.transport,l.remote_url url FROM bridge_connection_preferences p JOIN chats c ON c.id=p.chat_id LEFT JOIN bridge_chat_links l ON l.chat_id=c.id WHERE p.favorite=1 ORDER BY c.title,c.id')]

    def link(self,chat_id,url):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.netloc!='chatgpt.com' or not parsed.path.startswith('/c/') or not parsed.path[3:] or parsed.query or parsed.fragment:
            raise ValueError('Use an exact https://chatgpt.com/c/... conversation URL')
        with self.store.connect() as db:
            existing=db.execute('SELECT chat_id FROM bridge_chat_links WHERE remote_url=?',(url,)).fetchone()
            if existing and existing[0]!=chat_id:raise ValueError('This ChatGPT conversation already belongs to another saved local chat')
            db.execute('INSERT OR REPLACE INTO bridge_chat_links VALUES(?,?)',(chat_id,url))

    def remote(self,chat_id):
        with self.store.connect() as db:
            row=db.execute('SELECT remote_url FROM bridge_chat_links WHERE chat_id=?',(chat_id,)).fetchone()
            return row[0] if row else None

    def owned_draft(self,text):
        """Identify exact locally recorded output; never infer ownership from a prefix."""
        if not isinstance(text,str) or not text.strip():return None
        normalized=text.replace('\r\n','\n').strip()
        with self.store.connect() as db:
            rows=db.execute("SELECT id,chat_id,text,status FROM bridge_messages WHERE speaker='local_agent' AND direction='agent_to_chatgpt' ORDER BY created DESC")
            for row in rows:
                if row['text'].replace('\r\n','\n').strip()==normalized:
                    return {'message_id':row['id'],'chat_id':row['chat_id'],'status':row['status'],'match':'exact_local_outbound'}
        return None

    def local(self,url):
        with self.store.connect() as db:
            row=db.execute('SELECT chat_id FROM bridge_chat_links WHERE remote_url=?',(url,)).fetchone()
            return row[0] if row else None

    def append(self,chat_id,speaker,direction,text,key=None,files=None,status='received'):
        if not chat_id:return
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO bridge_messages VALUES(?,?,?,?,?,?,?,?,?)',
                       (uuid.uuid4().hex,chat_id,chat_id+':'+key if key else None,speaker,direction,text,json.dumps(files or []),status,time.time()))

    def delivery(self,chat_id,key,files,status):
        with self.store.connect() as db:
            db.execute('UPDATE bridge_messages SET files=?,status=? WHERE chat_id=? AND dedupe_key=?',
                       (json.dumps(files),status,chat_id,chat_id+':'+key))

    def list(self,chat_id,after=0):
        with self.store.connect() as db:
            return [{**dict(r),'files':json.loads(r['files'])} for r in db.execute('SELECT * FROM bridge_messages WHERE chat_id=? AND created>? ORDER BY created LIMIT 1000',(chat_id,after))]
