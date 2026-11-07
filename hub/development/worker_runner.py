"""Bounded subprocess for the patch-only model worker."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from ..config import ROOT,OLLAMA


async def invoke(directory,arguments,payload,timeout):
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC'}}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',LOCAL_AGENT_ROOT=str(ROOT),LOCAL_AGENT_OLLAMA=OLLAMA)
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.development.worker',*arguments,cwd=directory,env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    async def read(stream):
        chunks=[];size=0
        while chunk:=await stream.read(8192):
            size+=len(chunk)
            if size>1_000_000:raise ValueError('Worker output exceeded budget')
            chunks.append(chunk)
        return b''.join(chunks)
    async def communicate():
        process.stdin.write(payload);await process.stdin.drain();process.stdin.close()
        out,err=await asyncio.gather(read(process.stdout),read(process.stderr))
        await process.wait();return out,err
    collector=asyncio.create_task(communicate())
    try:
        out,err=await asyncio.wait_for(collector,timeout)
        result=json.loads(out)
        if process.returncode or result.get('error'):raise ValueError(result.get('error',err.decode(errors='replace')[:1000]))
        return result
    finally:
        if process.returncode is None:
            process.kill();await process.wait()
        if not collector.done():collector.cancel()
        await asyncio.gather(collector,return_exceptions=True)


async def health(directory,release_id,nonce):
    return await invoke(directory,['--health',release_id,nonce],b'',20)


async def run(packet,timeout):
    from ..guardian import Guardian
    payload=json.dumps(packet,ensure_ascii=False).encode()
    if len(payload)>200000:raise ValueError('Worker input exceeded limit')
    with Guardian(ROOT).worker() as (directory,pointer):
        result=await invoke(directory,[],payload,timeout)
        return {**result,'worker_release':pointer}
