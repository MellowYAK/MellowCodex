"""Candidate pytest execution. Same-account trusted-code profile, not OS isolation."""
import asyncio
import os
import sys
import re
from pathlib import Path
import psutil
from ..context.service import safe_path

async def run_pytest(directory,tests,timeout=120):
    directory=Path(directory).resolve()
    if not 1<=timeout<=300:raise ValueError('Test timeout must be 1–300 seconds')
    if not tests or len(tests)>30:raise ValueError('Select 1–30 project test files')
    paths=[]
    for rel in tests:
        parts=rel.split('::')
        if len(parts)>4 or any(not re.fullmatch(r'[A-Za-z_]\w*',part) for part in parts[1:]):
            raise ValueError('Use a relative .py file, optionally ::TestClass::test_function')
        p=safe_path(directory,parts[0])
        if not p.is_file() or p.suffix!='.py':raise ValueError('Select existing Python test files')
        paths.append('::'.join([str(p),*parts[1:]]))
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC'}}
    env.update(PYTHONUTF8='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','pytest',*paths,'-q','-p','no:cacheprovider',cwd=directory,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,creationflags=getattr(__import__('subprocess'),'CREATE_NO_WINDOW',0))
    chunks=[];size=0;truncated=False
    async def collect():
        nonlocal size,truncated
        while data:=await process.stdout.read(8192):
            keep=data[:max(0,1_000_000-size)]
            if keep:chunks.append(keep)
            size+=len(keep)
            if len(keep)<len(data):truncated=True
        await process.wait()
    timed_out=False
    collector=asyncio.create_task(collect())
    try:await asyncio.wait_for(asyncio.shield(collector),timeout)
    except (TimeoutError,asyncio.CancelledError) as exc:
        try:
            parent=psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                try:child.kill()
                except psutil.Error:pass
            parent.kill()
        except psutil.Error:pass
        try:await asyncio.wait_for(asyncio.shield(collector),5)
        except TimeoutError:
            collector.cancel()
            await asyncio.gather(collector,return_exceptions=True)
        if isinstance(exc,asyncio.CancelledError):raise
        timed_out=True
    return {'exit_code':process.returncode,'output':b''.join(chunks).decode('utf-8',errors='replace'),'truncated':truncated,'timed_out':timed_out,'profile':'same-account-trusted-code-not-os-sandbox'}
