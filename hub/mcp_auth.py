"""Separate OAuth store with PKCE (MCP SDK) and local-owner approval."""
import hashlib,json,secrets,sqlite3,time
from urllib.parse import urlsplit
from mcp.server.auth.provider import AuthorizationCode,RefreshToken,AccessToken,TokenError,AuthorizeError,RegistrationError,construct_redirect_uri
from mcp.shared.auth import OAuthClientInformationFull,OAuthToken
from .remote_config import HOME,PUBLIC
SCOPE='agent'
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
class db:
    def __enter__(self):
        HOME.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(HOME/'oauth.sqlite',timeout=20)
        self.conn.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,data TEXT,expires REAL,PRIMARY KEY(kind,id))')
        return self.conn
    def __exit__(self,kind,value,trace):
        try:
            if kind:self.conn.rollback()
            else:self.conn.commit()
        finally:self.conn.close()
def put(conn,kind,key,data,expires=0):
    conn.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(kind,key,json.dumps(data),expires))
def get(conn,kind,key):
    row=conn.execute('SELECT data FROM records WHERE kind=? AND id=? AND (expires=0 OR expires>?)',(kind,key,time.time())).fetchone()
    return json.loads(row[0]) if row else None
def consume(conn,kind,key):
    value=get(conn,kind,key)
    if not value:raise TokenError('invalid_grant')
    conn.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,key));return value
def issue(conn,client,subject):
    if not get(conn,'grant',subject):raise TokenError('invalid_grant')
    access=secrets.token_urlsafe(36);refresh=secrets.token_urlsafe(48);now=time.time()
    data=dict(client_id=client,subject=subject,scopes=[SCOPE],resource=PUBLIC+'/mcp',expires_at=int(now+3600))
    put(conn,'access',digest(access),data,now+3600)
    put(conn,'refresh',digest(refresh),{**data,'expires_at':int(now+2592000)},now+2592000)
    return OAuthToken(access_token=access,token_type='Bearer',expires_in=3600,refresh_token=refresh,scope=SCOPE)
class Provider:
    async def get_client(self,client_id):
        with db() as c:data=get(c,'client',client_id)
        return OAuthClientInformationFull(**data) if data else None
    async def register_client(self,client_info):
        if not client_info.redirect_uris:raise RegistrationError('invalid_redirect_uri')
        for uri in client_info.redirect_uris:
            u=urlsplit(str(uri))
            if u.scheme!='https' or u.hostname not in ('chatgpt.com','chat.openai.com') or u.port not in (None,443) or u.username or u.fragment:raise RegistrationError('invalid_redirect_uri')
        with db() as c:
            if c.execute("SELECT count(*) FROM records WHERE kind='client'").fetchone()[0]>=100:raise RegistrationError('invalid_client_metadata')
            put(c,'client',client_info.client_id,client_info.model_dump(mode='json'))
    async def authorize(self,client,params):
        if params.resource not in (None,PUBLIC+'/mcp') or params.scopes not in (None,[],[SCOPE]):raise AuthorizeError('invalid_scope')
        ticket=secrets.token_urlsafe(32)
        with db() as c:
            c.execute('DELETE FROM records WHERE expires>0 AND expires<?',(time.time(),))
            if c.execute("SELECT count(*) FROM records WHERE kind='request'").fetchone()[0]>=100:raise AuthorizeError('temporarily_unavailable')
            put(c,'request',digest(ticket),dict(client_id=client.client_id,client_name=client.client_name,params=params.model_dump(mode='json')),time.time()+600)
        return PUBLIC+'/consent?ticket='+ticket
    async def load_authorization_code(self,client,authorization_code):
        with db() as c:data=get(c,'code',digest(authorization_code))
        return AuthorizationCode(code=authorization_code,**data) if data else None
    async def exchange_authorization_code(self,client,authorization_code):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');data=consume(c,'code',digest(authorization_code.code))
            if data['client_id']!=client.client_id:raise TokenError('invalid_grant')
            return issue(c,client.client_id,data['subject'])
    async def load_refresh_token(self,client,refresh_token):
        with db() as c:data=get(c,'refresh',digest(refresh_token))
        return RefreshToken(token=refresh_token,**data) if data else None
    async def exchange_refresh_token(self,client,refresh_token,scopes):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');data=consume(c,'refresh',digest(refresh_token.token))
            if data['client_id']!=client.client_id or scopes!=[SCOPE]:raise TokenError('invalid_grant')
            return issue(c,client.client_id,data['subject'])
    async def load_access_token(self,token):
        with db() as c:
            data=get(c,'access',digest(token))
            if data and not get(c,'grant',data['subject']):data=None
        return AccessToken(token=token,**data) if data else None
    async def revoke_token(self,token):
        with db() as c:c.execute("DELETE FROM records WHERE kind='grant' AND id=?",(token.subject,))
provider=Provider()
def pending():
    with db() as c:return [dict(id=r[0],client_name=json.loads(r[1]).get('client_name')) for r in c.execute("SELECT id,data FROM records WHERE kind='request' AND expires>?",(time.time(),))]
def approve(key,allow):
    with db() as c:
        c.execute('BEGIN IMMEDIATE');data=consume(c,'request',key);p=data['params']
        if allow:
            subject=secrets.token_hex(16);code=secrets.token_urlsafe(36)
            put(c,'grant',subject,dict(client_id=data['client_id']),time.time()+2592000)
            put(c,'code',digest(code),dict(client_id=data['client_id'],subject=subject,scopes=[SCOPE],resource=PUBLIC+'/mcp',expires_at=time.time()+120,code_challenge=p['code_challenge'],redirect_uri=p['redirect_uri'],redirect_uri_provided_explicitly=p['redirect_uri_provided_explicitly']),time.time()+120)
            url=construct_redirect_uri(p['redirect_uri'],code=code,state=p.get('state'))
        else:url=construct_redirect_uri(p['redirect_uri'],error='access_denied',state=p.get('state'))
        put(c,'approved',key,dict(url=url),time.time()+120)
