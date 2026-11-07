"""Optional stdio supervision bridge. No public listener or browser session required."""
import json
from typing import Literal
import uuid
import httpx
from mcp.server.mcpserver import MCPServer
from .config import PORT, STATE

server=MCPServer('Local Agent Hub',instructions='Local task supervisor. Submit explicit tasks and poll status. Human review endpoints are deliberately not exposed to the worker.')

async def request(method,path,body=None):
    key=(STATE/'hub.key').read_text(encoding='utf-8').strip()
    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{PORT}',headers={'X-Hub-Key':key},timeout=15,trust_env=False) as client:
        r=await client.request(method,path,json=body)
        r.raise_for_status()
        return r.json()

@server.tool()
async def get_capabilities() -> dict:
    return await request('GET','/api/capabilities')

@server.tool()
async def submit_task(goal: str,workspace: str,mode: Literal['inspect','code','desktop','browser']='desktop',idempotency_key: str='',criteria: list[dict] | None=None) -> dict:
    return await request('POST','/api/tasks',{'goal':goal,'workspace':workspace,'mode':mode,'idempotency_key':idempotency_key or uuid.uuid4().hex,'criteria':criteria or []})

@server.tool()
async def get_task(task_id: str) -> dict:
    return await request('GET','/api/tasks/'+task_id)

@server.tool()
async def get_events(task_id: str,after: int=0) -> list:
    return await request('GET',f'/api/tasks/{task_id}/events?after={after}')

@server.tool()
async def get_review_bundle(task_id: str) -> dict:
    return await request('GET',f'/api/tasks/{task_id}/review')

@server.tool()
async def control_task(task_id: str,command: Literal['pause','resume','cancel'],expected_revision: int) -> dict:
    return await request('POST',f'/api/tasks/{task_id}/control',{'command':command,'expected_revision':expected_revision})

if __name__=='__main__':
    server.run(transport='stdio')
