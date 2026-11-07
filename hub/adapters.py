"""Optional integrations with pinned local components."""
import os
from pathlib import Path
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .config import ROOT, STATE

async def windows_snapshot():
    """Use Windows-MCP accessibility; do not attach to any browser DOM/session."""
    environment={**os.environ,'ANONYMIZED_TELEMETRY':'false','DO_NOT_TRACK':'1'}
    params=StdioServerParameters(command=str(ROOT/'tools/hub-venv/Scripts/windows-mcp.exe'),args=['serve','--transport','stdio','--tools','Snapshot'],env=environment)
    with (STATE/'windows-mcp.log').open('a',encoding='utf-8') as log:
        async with stdio_client(params,errlog=log) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                result=await session.call_tool('Snapshot',{'use_vision':False,'use_dom':False,'use_ui_tree':True})
                return {'text':'\n'.join(block.text for block in result.content if getattr(block,'type',None)=='text'),'is_error':bool(result.is_error)}

class OpenCode:
    """A single authenticated server; caller owns scheduling and GPU exclusivity."""
    def __init__(self):
        self.base='http://127.0.0.1:4096'

    async def request(self,method,path,workspace,body=None):
        password=(STATE/'hub.key').read_text(encoding='utf-8').strip()
        async with httpx.AsyncClient(base_url=self.base,auth=('opencode',password),timeout=240,trust_env=False) as client:
            response=await client.request(method,path,params={'directory':workspace},json=body)
            response.raise_for_status()
            return response.json()

    async def create_session(self,workspace,title):
        return await self.request('POST','/session',workspace,{'title':title})

    async def prompt(self,workspace,session_id,text):
        return await self.request('POST',f'/session/{session_id}/message',workspace,{'model':{'providerID':'ollama','modelID':'qwen3.5:4b'},'parts':[{'type':'text','text':text}]})

    async def abort(self,workspace,session_id):
        return await self.request('POST',f'/session/{session_id}/abort',workspace,{})
