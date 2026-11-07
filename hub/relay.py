"""Outbound-only SSH forwarding, supervised by the local Hub lifecycle."""
import asyncio,json,os,time
from pathlib import Path
from .config import STATE
from .remote_config import load,GATEWAY_PORT

STATUS=STATE/'relay-status.json'

def command(config):
    return [str(Path(os.environ.get('WINDIR','C:/Windows'))/'System32/OpenSSH/ssh.exe'),
        '-N','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
        '-o','UserKnownHostsFile='+config['known_hosts'],'-o','ExitOnForwardFailure=yes',
        '-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=20',
        '-o','ServerAliveCountMax=3','-i',config['identity_file'],
        '-R',f"127.0.0.1:{int(config['relay_port'])}:127.0.0.1:{GATEWAY_PORT}",
        config['relay_user']+'@'+config['relay_host']]

def status(state,error='',**extra):
    data={'state':state,'error':error,'updated':time.time(),**extra}
    temp=STATUS.with_suffix('.tmp');temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(STATUS)

async def stop(process):
    if process and process.returncode is None:
        process.terminate()
        try:await asyncio.wait_for(process.wait(),5)
        except TimeoutError:process.kill();await process.wait()

async def supervise():
    import sys,httpx
    config=load()
    if not config.get('enabled'):status('disabled');return
    gateway=None;tunnel=None
    try:
        with (STATE/'mcp.stderr.log').open('ab') as log:
            while True:
                if gateway is None or gateway.returncode is not None:
                    gateway=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.mcp_gateway',stdout=log,stderr=log,creationflags=0x08000000)
                    await asyncio.sleep(1)
                status('connecting')
                try:
                    # Do not advertise a port that belongs to another local service.
                    async with httpx.AsyncClient(timeout=5) as client:
                        local=await client.get(f'http://127.0.0.1:{GATEWAY_PORT}/health')
                        if local.json().get('product')!='local_agent':raise RuntimeError('Local gateway is not ready')
                    with (STATE/'relay.stderr.log').open('ab') as tunnel_log:
                        tunnel=await asyncio.create_subprocess_exec(*command(config),stdout=tunnel_log,stderr=tunnel_log,creationflags=0x08000000)
                        failures=0
                        while tunnel.returncode is None:
                            await asyncio.sleep(5)
                            if gateway.returncode is not None:raise RuntimeError('Local gateway stopped')
                            try:
                                async with httpx.AsyncClient(timeout=8) as client:
                                    response=await client.get(config['public_url']+'/health')
                                    response.raise_for_status()
                                    if response.json().get('product')!='local_agent':raise RuntimeError('Unexpected gateway response')
                                failures=0;status('connected',public_url=config['public_url'])
                            except Exception as exc:
                                failures+=1;status('reconnecting',type(exc).__name__+': '+str(exc)[:200])
                                if failures>=3:break
                except Exception as exc:status('reconnecting',type(exc).__name__+': '+str(exc)[:200])
                finally:await stop(tunnel);tunnel=None
                await asyncio.sleep(5)
    finally:
        await stop(tunnel);await stop(gateway);status('stopped')
