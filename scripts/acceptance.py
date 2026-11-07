"""Reproducible probes: no real mouse/keyboard input or external browser launch."""
import argparse
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from PIL import Image,ImageDraw,ImageFont
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from hub.config import ARTIFACTS,ROOT,STATE,MODEL,OLLAMA

async def vision_probe():
    canvas=Image.new('RGB',(640,320),'white')
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',44)
    draw.rectangle((30,30,210,200),fill=(220,20,30))
    draw.ellipse((380,30,560,210),fill=(20,50,230))
    draw.text((45,240),'LOCAL VISION 42',font=font,fill='black')
    path=ARTIFACTS/'vision-fixture.png'
    canvas.save(path)
    started=time.perf_counter()
    async with httpx.AsyncClient(timeout=240,trust_env=False) as client:
        r=await client.post(OLLAMA+'/api/chat',json={'model':MODEL,'stream':False,'think':False,'messages':[{'role':'user','content':'Read the text and describe the two colored shapes and their positions. Be brief.','images':[base64.b64encode(path.read_bytes()).decode()]}],'options':{'num_ctx':8192,'num_predict':150},'keep_alive':'10m'})
        r.raise_for_status()
    result={'elapsed_seconds':time.perf_counter()-started,**r.json()}
    (ARTIFACTS/'vision-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

async def mcp_probe(which):
    if which=='windows':
        command=str(ROOT/'tools/hub-venv/Scripts/windows-mcp.exe')
        args=['serve','--transport','stdio','--tools','Snapshot']
    else:
        command=sys.executable
        args=['-m','hub.mcp_server']
    params=StdioServerParameters(command=command,args=args,cwd=str(Path(__file__).resolve().parents[1]),env={**os.environ,'ANONYMIZED_TELEMETRY':'false','DO_NOT_TRACK':'1'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            initialized=await session.initialize()
            result=await session.list_tools()
            output={'server':initialized.server_info.model_dump(),'tools':[t.name for t in result.tools]}
            if which=='hub':
                capability=await session.call_tool('get_capabilities',{})
                output['capabilities']=capability.model_dump(mode='json')
            (ARTIFACTS/f'{which}-mcp-probe.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(output,ensure_ascii=False,indent=2))

async def collect_task(task_id):
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8876',headers={'X-Hub-Key':(STATE/'hub.key').read_text().strip()},trust_env=False) as client:
        task=(await client.get('/api/tasks/'+task_id)).json()
        bundle=(await client.get('/api/tasks/'+task_id+'/review')).json()
        (ARTIFACTS/f'acceptance-{task_id}.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf-8')
        shell=[a for a in bundle['actions'] if a['tool']=='run_shell']
        print(json.dumps({'state':task['state'],'created':task['created'],'updated':task['updated'],'checks':bundle['checks'],'shell_results':[a['result'] for a in shell]},ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('probe',choices=['vision','hub','windows','task'])
    parser.add_argument('--task-id')
    args=parser.parse_args()
    asyncio.run(vision_probe() if args.probe=='vision' else collect_task(args.task_id) if args.probe=='task' else mcp_probe(args.probe))
