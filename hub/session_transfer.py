"""User-initiated, single-site Chrome session transfer. Never log credential values."""
import secrets
import time
from urllib.parse import urlsplit

class Pairing:
    def __init__(self):self.codes={}
    def issue(self):
        self.codes={k:v for k,v in self.codes.items() if v>time.monotonic()}
        code=secrets.token_urlsafe(24);self.codes[code]=time.monotonic()+180
        return {'code':code,'expires_seconds':180}
    def consume(self,code):
        expiry=self.codes.pop(code,0)
        if expiry<time.monotonic():raise ValueError('Pairing code is invalid or expired. Create a new code in Local Agent.')

def validate_transfer(data):
    url=data.get('url','');parts=urlsplit(url)
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:raise ValueError('Invalid source URL')
    host=parts.hostname
    origin=f'{parts.scheme}://{parts.netloc}'
    cookies=[];skipped=0
    source=data.get('cookies',[])
    if not isinstance(source,list) or len(source)>500:raise ValueError('Too many cookies')
    for cookie in source:
        domain=cookie.get('domain','').lstrip('.').lower()
        if not domain or not (host==domain or host.endswith('.'+domain)):raise ValueError('Cookie belongs to a different site')
        if cookie.get('partitionKey'):
            skipped+=1;continue
        if not isinstance(cookie.get('name'),str) or not isinstance(cookie.get('value'),str):raise ValueError('Invalid cookie')
        if len(cookie['value'])>20000:raise ValueError('Cookie is too large')
        same={'no_restriction':'None','lax':'Lax','strict':'Strict','unspecified':'Lax','None':'None','Lax':'Lax','Strict':'Strict'}.get(cookie.get('sameSite'),'Lax')
        normalized={'name':cookie['name'],'value':cookie['value'],'domain':cookie['domain'],'path':cookie.get('path','/'),'httpOnly':bool(cookie.get('httpOnly',False)),'secure':bool(cookie.get('secure',False)),'sameSite':same}
        if not cookie.get('session',False) and cookie.get('expirationDate',-1)>0:normalized['expires']=cookie['expirationDate']
        cookies.append(normalized)
    storage={}
    for key in ('localStorage','sessionStorage'):
        values=data.get(key,{})
        if not isinstance(values,dict) or len(values)>500 or any(not isinstance(k,str) or not isinstance(v,str) or len(v)>200000 for k,v in values.items()):raise ValueError('Invalid site storage')
        storage[key]=values
    return {'url':url,'origin':origin,'cookies':cookies,'skipped_partitioned':skipped,**storage}
