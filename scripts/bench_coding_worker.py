"""Actual worker benchmark; service-level evidence, not full Engine acceptance."""
import asyncio,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from hub.config import ROOT,STATE,OLLAMA
    from hub.model_settings import ModelSettings,save_settings
    from hub.store import Store
    from hub.development.service import Development
    if ROOT.resolve()==Path('E:/AI').resolve():raise RuntimeError('Use isolated LOCAL_AGENT_ROOT')
    async with httpx.AsyncClient(timeout=60,trust_env=False) as client:
        if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Ollama busy')
        save_settings(ModelSettings(response_tokens=4096,request_timeout_seconds=300,keep_alive_minutes=1,visual_guidance=False))
        store=Store(STATE/'hub.sqlite3');dev=Development(store,ROOT/'candidates');results=[]
        for index,model in enumerate(['qwen3.5:4b','qwen2.5-coder:7b']):
            source=ROOT/f'fixture-{index}';source.mkdir(exist_ok=True)
            original='def total(price, quantity):\n    return price + quantity\n'
            tests='from billing import total\ndef test_total():\n assert total(7,4)==28\n assert total(0,4)==0\n assert total(2.5,2)==5\n'
            (source/'billing.py').write_text(original);(source/'test_billing.py').write_text(tests)
            task=store.create('Correct total(price, quantity) to multiply price by quantity. Preserve the function signature and tests. Stage changes only.',str(source),'code','worker-'+str(time.time_ns()))
            candidate=dev.create(task);started=time.monotonic()
            try:
                result=await dev.repair(task,candidate['id'],0,['billing.py'],['test_billing.py'],model)
                results.append({'model':model,'seconds':round(time.monotonic()-started,2),'result':result,'original_preserved':(source/'billing.py').read_text()==original,'test_preserved':(source/'test_billing.py').read_text()==tests,'events':store.events(task['id'])})
            except Exception as exc:results.append({'model':model,'seconds':round(time.monotonic()-started,2),'error':type(exc).__name__+': '+str(exc)})
            finally:
                await client.post(OLLAMA+'/api/generate',json={'model':model,'keep_alive':0})
            (ROOT/'benchmark.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in results[-1].items() if k not in ('result','events')},ensure_ascii=False),flush=True)
        print(json.dumps({'remaining_models':(await client.get(OLLAMA+'/api/ps')).json().get('models',[])}))

if __name__=='__main__':asyncio.run(main())
