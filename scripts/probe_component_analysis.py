"""Recorded-source diagnostic of staged extraction; not runner acceptance."""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def main():
    if not os.environ.get('LOCAL_AGENT_ROOT'):raise RuntimeError('Use an isolated acceptance root')
    from hub.config import STATE,ROOT
    from hub.store import Store
    from hub.engine import Engine
    from hub.model_settings import load_settings,save_settings
    from hub.context.exploration import checkpoint_sources
    from hub.context.component_analysis import extraction_batches,validate_components,COMPONENT_SCHEMA
    task_id=sys.argv[1]
    store=Store(STATE/'hub.sqlite3');task=store.get(task_id)
    sources=checkpoint_sources(store.actions(task_id))
    settings=load_settings();settings.inference_enabled=True;settings.model='qwen3.5:4b'
    settings.keep_alive_minutes=2;settings.response_tokens=2400;save_settings(settings)
    batches=extraction_batches(task['goal'],sources)
    started=time.monotonic()
    results=[];engine=Engine(store)
    for index,messages in enumerate(batches):
        delivered=json.loads(messages[-1]['content'])['sources']
        for s in delivered:
            if s.get('line_numbered'):
                s['excerpt']='\n'.join(line.partition(': ')[2] for line in s['excerpt'].split('\n'))
        message,metrics=await engine.chat(messages,[],response_tokens=2400,output_schema=COMPONENT_SCHEMA)
        validation=validate_components(message,delivered)
        results.append({'message':message,'metrics':metrics,'validation':validation,'sources':[{'path':s['path'],'start':s['start'],'end':s.get('end')} for s in delivered]})
        print(json.dumps({'batch':index+1,'total':len(batches),'accepted':len(validation['accepted']),'rejected':len(validation['rejected'])}),flush=True)
    result={'kind':'recorded-source adapter diagnostic, not runner acceptance','task_id':task_id,
            'seconds':round(time.monotonic()-started,2),'source_ranges':len(sources),'batches':results}
    output=ROOT/(task_id+'-components-anchors.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'seconds':result['seconds']}),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
