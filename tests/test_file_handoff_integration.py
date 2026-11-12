"""Real ToolRunner file handoff, with only permission policy stubbed."""
import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from hub.tools import ToolRunner

class FakeEvents:
    def __init__(self): self.observations={}
    def event(self,task_id,kind,data): self.observations[(task_id,kind)]={'data':data}
    def latest_event(self,task_id,kind): return self.observations.get((task_id,kind))

def runner_and_task(base,task_id):
    runner=ToolRunner();runner.context_store=FakeEvents()
    return runner,{'id':task_id,'mode':'code','workspace':str(base),'revision':1}

class HandoffIntegration(unittest.TestCase):
    def test_list_to_read_and_normal_policy_target(self):
        with TemporaryDirectory() as home:
            base=Path(home);directory=base/'961841f95a974b459b05396bd6bfe2f7'
            directory.mkdir();(directory/'supervisor.log').write_text('correct update log')
            runner,task=runner_and_task(base,'handoff-integration')
            observed=[]
            def owner_gate(task,name,args,spec,**kwargs):
                observed.append((name,args.get('path')))
                return None
            async def execute():
                roots=await runner.execute(task,'list_files',{'path':str(base)})
                directory_ref=next(item['ref'] for item in roots['files'] if item['name']==directory.name)
                listed=await runner.execute(task,'list_files',{'ref':directory_ref})
                ref=next(item['ref'] for item in listed['files'] if item['name']=='supervisor.log')
                return await runner.execute(task,'read_file',{'ref':ref})
            with patch('hub.development.guidance.Guidance',return_value=SimpleNamespace(allowed_tools=lambda task_id:None)),patch('hub.owner_policy_adapter.check_native_action',side_effect=owner_gate):
                output=asyncio.run(execute())
            self.assertEqual(output['content'],'correct update log')
            self.assertEqual(Path(observed[-1][1]).resolve(),(directory/'supervisor.log').resolve())

    def test_path_and_ref_cannot_be_combined(self):
        with TemporaryDirectory() as home:
            base=Path(home);target=base/'a.txt';target.write_text('correct')
            runner,task=runner_and_task(base,'handoff-exclusion')
            async def execute():
                listed=await runner.execute(task,'list_files',{'path':str(base)})
                with self.assertRaisesRegex(ValueError,'exactly one'):
                    await runner.execute(task,'read_file',{'path':str(target),'ref':listed['files'][0]['ref']})
            with patch('hub.development.guidance.Guidance',return_value=SimpleNamespace(allowed_tools=lambda task_id:None)),patch('hub.owner_policy_adapter.check_native_action',return_value=None):
                asyncio.run(execute())
