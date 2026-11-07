"""Read-only public Hugging Face metadata; no remote code or credential access."""
import re
from urllib.parse import quote
import httpx

API='https://huggingface.co/api/models'

async def search(query,limit=10):
    if not isinstance(query,str) or not 1<=len(query)<=160 or not 1<=limit<=30:raise ValueError('Query and limit (1–30) required')
    async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
        response=await client.get(API,params={'search':query,'filter':'gguf','limit':limit,'sort':'downloads','direction':-1});response.raise_for_status()
    return {'provider':'huggingface','results':[{'id':m['id'],'revision':m.get('sha'),'downloads':m.get('downloads'),'gated':m.get('gated',False),'tags':m.get('tags',[])[:40],'compatibility':'GGUF candidate; inspect files/runtime compatibility before installation'} for m in response.json()],'limit':limit,'truncated_possible':len(response.json())==limit}

async def details(repo):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or '..' in repo:raise ValueError('Use an exact Hugging Face owner/repository id')
    async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
        response=await client.get(API+'/'+quote(repo,safe='/'),params={'blobs':'true'});response.raise_for_status()
    data=response.json();files=[]
    for item in data.get('siblings',[]):
        name=item.get('rfilename','')
        if not name.lower().endswith('.gguf'):continue
        split=bool(re.search(r'-\d{5}-of-\d{5}\.gguf$',name,re.I))
        projection='mmproj' in name.lower()
        files.append({'name':name,'bytes':item.get('size') or item.get('lfs',{}).get('size'),'sha256':item.get('lfs',{}).get('sha256'),
                      'install_supported':not split and not projection and '/' not in name,'split':split,'projection':projection,
                      'ollama_name':'hf.co/'+repo+':'+name if not split and not projection and '/' not in name else None})
    return {'provider':'huggingface','id':repo,'revision':data.get('sha'),'license':data.get('cardData',{}).get('license'),'gated':bool(data.get('gated')),'private':bool(data.get('private')),'files':files,'runtime':'ollama','remote_code_allowed':False,'runtime_compatibility':'not runtime tested','source_url':'https://huggingface.co/'+repo}
