import json,sys,pathlib,os
def absolute(value):
 p=pathlib.Path(value)
 if not p.is_absolute(): raise ValueError('Absolute path required')
 return p.resolve()
def output(value):
 p=absolute(value)
 if p.exists(): raise FileExistsError(str(p))
 if not p.parent.is_dir(): raise ValueError('Parent directory must exist')
 return p
import asyncio,base64
from urllib.parse import urlsplit
sys.path.insert(0,'E:/AI/repos/local-agent-hub')
os.environ['PYTHONPATH']='E:/AI/repos/local-agent-hub'+os.pathsep+os.environ.get('PYTHONPATH','')
from hub.browser import Browser
async def execute(a):
 b=Browser()
 try:
  await b.select_tab(a['tab_id']);p=await b.connect();op=a['operation']
  if op=='observe':
   return {'url':p.url,'title':await p.title(),'controls':await p.locator('input,button,textarea,select,a').evaluate_all("(es)=>es.slice(0,100).map(e=>({tag:e.tagName,id:e.id,type:e.type,name:e.name,text:e.innerText,href:e.href}))")}
  if a.get('expected_url')!=p.url: raise ValueError('expected_url must match current observed tab URL')
  if op=='navigate':
   u=urlsplit(a['url'])
   if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: raise ValueError('HTTP(S) URL required')
   await p.goto(a['url'],wait_until='domcontentloaded')
   return {'url':p.url,'title':await p.title()}
  if op in ('fill','click','select'):
   loc=p.locator(a['selector'])
   if await loc.count()!=1: raise ValueError('Selector must match exactly one observed control')
   if op=='fill': await loc.fill(a['text'])
   elif op=='select': await loc.select_option(a['value'])
   else: await loc.click()
   return {'operation':op,'url':p.url,'value':await loc.input_value() if op in ('fill','select') else None}
  if op=='download':
   dst=output(a['destination']);url=a['url']
   links=await p.locator('a[href]').evaluate_all('(es)=>es.map(e=>e.href)')
   if url not in links: raise ValueError('Download URL must be an observed page link')
   encoded=await p.evaluate("""async u=>{
    if(new URL(u).origin!==location.origin)throw Error('Same-origin download required');
    let r=await fetch(u);if(!r.ok)throw Error(r.status);
    let a=new Uint8Array(await r.arrayBuffer());if(a.length>25000000)throw Error('Maximum25MB');
    let s='';for(let i=0;i<a.length;i+=32768)s+=String.fromCharCode(...a.subarray(i,i+32768));return btoa(s)
   }""",url)
   data=base64.b64decode(encoded)
   with dst.open('xb') as f: f.write(data)
   return {'saved':str(dst),'bytes':len(data)}
  raise ValueError('operation observe|navigate|fill|click|select|download')
 finally: await b.disconnect()
def main(a): return asyncio.run(execute(a))

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
