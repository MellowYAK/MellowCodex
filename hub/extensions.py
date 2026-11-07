"""Versioned user-task Python tools. Validation is a test, not a security sandbox."""
import asyncio,hashlib,json,os,re,sys,uuid
from pathlib import Path
from .config import ROOT

class Extensions:
    def __init__(self,root=None):
        self.root=Path(root or ROOT/'extensions');self.root.mkdir(parents=True,exist_ok=True)
    def directory(self,name):
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,60}',name):raise ValueError('Use a short lowercase tool name')
        return self.root/name
    def list(self):
        return [json.loads(p.read_text(encoding='utf-8')) for p in self.root.glob('*/manifest.json')]
    async def process(self,argv,cwd,input_data=None,timeout=90):
        process=await asyncio.create_subprocess_exec(*map(str,argv),cwd=str(cwd),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env={**os.environ,'PYTHONIOENCODING':'utf-8'},creationflags=0x08000000 if os.name=='nt' else 0)
        try:out,err=await asyncio.wait_for(process.communicate(json.dumps(input_data,ensure_ascii=False).encode() if input_data is not None else None),timeout)
        except (asyncio.TimeoutError,asyncio.CancelledError):
            process.kill();await process.wait();raise
        return {'exit_code':process.returncode,'stdout':out.decode('utf-8',errors='replace')[-30000:],'stderr':err.decode('utf-8',errors='replace')[-10000:]}
    async def register(self,task,name,description,source,test,requirements=None):
        root=Path(task['workspace']).resolve()
        def local(value):
            path=(root/value).resolve()
            if not path.is_relative_to(root) or not path.is_file():raise ValueError('Source and test must exist inside workspace')
            return path
        source=local(source);test=local(test)
        if source==test:raise ValueError('Provide a separate functional test')
        folder=self.directory(name);version=uuid.uuid4().hex;build=folder/version;build.mkdir(parents=True)
        (build/'tool.py').write_bytes(source.read_bytes());(build/'test_tool.py').write_bytes(test.read_bytes())
        requirements=requirements or []
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+',r) for r in requirements):raise ValueError('Dependencies must be pinned package==version from the configured package index')
        python=sys.executable
        if requirements:
            result=await self.process([sys.executable,'-m','venv',build/'venv'],build)
            if result['exit_code']:raise RuntimeError('Environment creation failed: '+result['stderr'])
            python=str(build/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
            result=await self.process([python,'-m','pip','install',*requirements],build,timeout=180)
            (build/'install.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            if result['exit_code']:raise RuntimeError('Dependency installation failed: '+result['stderr'])
        result=await self.process([python,'test_tool.py'],build)
        (build/'validation.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        if result['exit_code']:return {'registered':False,'name':name,'test':result,'build':str(build)}
        manifest={'name':name,'description':description,'version':version,'python':python,'source_sha256':hashlib.sha256((build/'tool.py').read_bytes()).hexdigest(),'requirements':requirements,'validated':True,'created_by_task':task['id']}
        temporary=folder/'manifest.tmp';temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(folder/'manifest.json')
        return {'registered':True,**manifest,'test':result}
    async def run(self,task,name,arguments):
        folder=self.directory(name);manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));source=folder/manifest['version']/'tool.py'
        if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['source_sha256']:raise ValueError('Tool changed since validation; register and test a new version')
        result=await self.process([manifest['python'],source],task['workspace'],arguments)
        return {'name':name,'version':manifest['version'],**result}
