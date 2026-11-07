"""Durable Ollama installation jobs. Downloads never select or load a model."""
import asyncio
import json
import re
import time
import uuid
import httpx
from .config import OLLAMA

_services={}
def service_for(store):
    key=str(store.path.resolve())
    if key not in _services:_services[key]=ModelCatalog(store)
    return _services[key]


class ModelCatalog:
    def __init__(self,store):
        self.store=store;self.active={}
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS model_downloads(id TEXT PRIMARY KEY,request_id TEXT UNIQUE NOT NULL,model TEXT NOT NULL,state TEXT NOT NULL,progress TEXT NOT NULL,updated REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS model_download_provenance(job TEXT PRIMARY KEY,data TEXT NOT NULL)')

    def jobs(self):
        with self.store.connect() as db:
            rows=db.execute('SELECT * FROM model_downloads ORDER BY updated DESC LIMIT 50').fetchall()
            provenance={r['job']:json.loads(r['data']) for r in db.execute('SELECT * FROM model_download_provenance')}
        return [dict(r)|{'progress':json.loads(r['progress']),'provenance':provenance.get(r['id'])} for r in rows]

    async def catalog(self):
        async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
            response=await client.get(OLLAMA+'/api/tags');response.raise_for_status()
        return {'installed':response.json().get('models',[]),'jobs':self.jobs(),'backend':'ollama','installation_loads_gpu':False}

    async def install_hf(self,repo,filename,request_id):
        from .model_providers import details
        data=await details(repo)
        if data['gated'] or data['private']:raise ValueError('Repository requires external access approval; public installer does not read or transmit credentials')
        chosen=next((f for f in data['files'] if f['name']==filename),None)
        if not chosen or not chosen['install_supported']:raise ValueError('Choose a supported single-file GGUF. Split shards, subdirectories and projection-only files are not supported by this adapter.')
        provenance={'provider':'huggingface','repository':repo,'revision':data['revision'],'license':data['license'],'file':chosen,'source_url':data['source_url'],'revision_pinned':False}
        return self.submit(chosen['ollama_name'],request_id,provenance=provenance)

    def update(self,identifier,state,progress):
        with self.store.connect() as db:
            db.execute('UPDATE model_downloads SET state=?,progress=?,updated=? WHERE id=?',(state,json.dumps(progress),time.time(),identifier))

    def submit(self,model,request_id,*,provenance=None):
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,159}',model) or '..' in model or '://' in model:
            raise ValueError('Use an Ollama model name, not a URL or file path')
        if model.startswith(('hf.co/','huggingface.co/')) and provenance is None:
            raise ValueError('Use the Hugging Face installer with repository and exact filename for compatibility and provenance checks')
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100:raise ValueError('Stable request_id required')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM model_downloads WHERE request_id=?',(request_id,)).fetchone()
            if old:
                if old['model']!=model:raise ValueError('Request identity belongs to a different model')
                return dict(old)|{'progress':json.loads(old['progress'])}
            if db.execute("SELECT 1 FROM model_downloads WHERE state IN ('queued','downloading','verifying')").fetchone():
                raise ValueError('A model download is already active; inspect or cancel it first')
            identifier=uuid.uuid4().hex
            db.execute('INSERT INTO model_downloads VALUES(?,?,?,?,?,?)',(identifier,request_id,model,'queued','{}',time.time()))
            if provenance:db.execute('INSERT INTO model_download_provenance VALUES(?,?)',(identifier,json.dumps(provenance)))
        self.active[identifier]=asyncio.create_task(self.pull(identifier,model))
        return next(j for j in self.jobs() if j['id']==identifier)

    async def pull(self,identifier,model):
        last={};success=False
        try:
            self.update(identifier,'downloading',{})
            async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=10),trust_env=False) as client:
                async with client.stream('POST',OLLAMA+'/api/pull',json={'model':model,'stream':True}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:continue
                        if len(line)>16000:raise ValueError('Unexpected oversized download response')
                        item=json.loads(line)
                        if item.get('error'):raise RuntimeError(str(item['error'])[:1000])
                        last={k:item[k] for k in ('status','digest','total','completed') if k in item}
                        self.update(identifier,'downloading',last)
                        success=item.get('status')=='success'
                if not success:raise RuntimeError('Download ended without success acknowledgement')
                self.update(identifier,'verifying',last)
                response=await client.get(OLLAMA+'/api/tags');response.raise_for_status()
                from .model_memory import matches
                installed=next((m for m in response.json().get('models',[]) if matches(m['name'],model)),None)
                if not installed or not installed.get('digest'):raise RuntimeError('Installed model digest was not found')
                job=next(j for j in self.jobs() if j['id']==identifier)
                provenance=job.get('provenance')
                if provenance:
                    from .model_providers import details
                    current=await details(provenance['repository'])
                    if current['revision']!=provenance['revision']:
                        raise RuntimeError('Hugging Face repository revision changed during installation; downloaded alias must be reviewed before use')
                self.update(identifier,'ready',{'installed':installed,'verified':True,'verification_scope':'Ollama installed digest; inference compatibility not tested','selection_changed':False,'load_requested':False})
        except asyncio.CancelledError:
            self.update(identifier,'interrupted',{**last,'reason':'Download stream closed; partial Ollama layers retained for an explicit resume','loaded':False})
            raise
        except Exception as exc:
            self.update(identifier,'failed',{**last,'error':type(exc).__name__+': '+str(exc)[:1000]})
        finally:self.active.pop(identifier,None)

    async def cancel(self,identifier):
        job=self.active.get(identifier)
        if job:
            job.cancel();await asyncio.gather(job,return_exceptions=True)
            self.active.pop(identifier,None)
            self.update(identifier,'interrupted',{'reason':'Local stream cancelled; partial server layers retained. Inspect catalog before resuming.','load_requested':False})
        found=next((j for j in self.jobs() if j['id']==identifier),None)
        if found is None:raise ValueError('Unknown model download')
        return found

    def recover(self):
        with self.store.connect() as db:
            db.execute("UPDATE model_downloads SET state='interrupted',progress=? WHERE state IN ('queued','downloading','verifying')",(json.dumps({'reason':'Runtime restarted; inspect installed models before explicitly resuming'}),))

    async def close(self):
        tasks=list(self.active.values())
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)


def router(provider):
    from fastapi import APIRouter
    from pydantic import BaseModel,ConfigDict,Field
    class Install(BaseModel):
        model_config=ConfigDict(extra='forbid')
        model:str=Field(min_length=1,max_length=160)
        request_id:str=Field(min_length=1,max_length=100)
    class Cancel(BaseModel):
        id:str=Field(pattern='^[a-f0-9]{32}$')
    class HFInstall(BaseModel):
        model_config=ConfigDict(extra='forbid')
        repo:str=Field(min_length=3,max_length=160)
        filename:str=Field(min_length=1,max_length=200)
        request_id:str=Field(min_length=1,max_length=100)
    routes=APIRouter(prefix='/api/models')
    @routes.get('/catalog')
    async def catalog():return await provider().catalog()
    @routes.post('/install')
    async def install(body:Install):return provider().submit(body.model,body.request_id)
    @routes.post('/cancel')
    async def cancel(body:Cancel):return await provider().cancel(body.id)
    @routes.get('/search')
    async def search(query:str,limit:int=10):
        from .model_providers import search
        return await search(query,limit)
    @routes.get('/details')
    async def details(repo:str):
        from .model_providers import details
        return await details(repo)
    @routes.post('/install-hf')
    async def install_hf(body:HFInstall):return await provider().install_hf(body.repo,body.filename,body.request_id)
    return routes


def register_mcp(mcp,local,read,write):
    from .i18n import t
    from urllib.parse import urlencode
    @mcp.tool(description=t('models.search_tool'),annotations=read)
    async def model_catalog_search(query:str,limit:int=10):return await local('/api/models/search?'+urlencode({'query':query,'limit':limit}))
    @mcp.tool(description=t('models.details_tool'),annotations=read)
    async def model_catalog_details(repo:str):return await local('/api/models/details?'+urlencode({'repo':repo}))
    @mcp.tool(description=t('models.hf_install_tool'),annotations=write)
    async def model_install_huggingface(repo:str,filename:str,request_id:str):return await local('/api/models/install-hf',dict(repo=repo,filename=filename,request_id=request_id))
    @mcp.tool(description=t('models.catalog_tool'),annotations=read)
    async def model_catalog():return await local('/api/models/catalog')
    @mcp.tool(description=t('models.install_tool'),annotations=write)
    async def model_install(model:str,request_id:str):return await local('/api/models/install',{'model':model,'request_id':request_id})
    @mcp.tool(description=t('models.cancel_tool'),annotations=write)
    async def model_install_cancel(id:str):return await local('/api/models/cancel',{'id':id})

def definitions(schema):
    from .i18n import t
    string={'type':'string'}
    return [schema('model_catalog',t('models.catalog_tool'),{}),
            schema('model_memory_status','Read currently resident Ollama models, VRAM usage and Hub inference leases. Read-only; prefer this over shell ollama ps. Catalog lists installed files, not active memory. Unknown ownership is not proof another task is active.',{}),
            schema('model_catalog_search',t('models.search_tool'),{'query':string,'limit':{'type':'integer','minimum':1,'maximum':30}},('query',)),
            schema('model_catalog_details',t('models.details_tool'),{'repo':string},('repo',)),
            schema('model_install_huggingface',t('models.hf_install_tool'),{'repo':string,'filename':string,'request_id':string},('repo','filename','request_id')),
            schema('model_install',t('models.install_tool'),{'model':string,'request_id':string},('model','request_id')),
            schema('model_install_cancel',t('models.cancel_tool'),{'id':string},('id',))]
