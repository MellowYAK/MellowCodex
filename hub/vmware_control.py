"""Owner-enabled, authenticated, local VMware guest control.

Never accepts remote VM paths, network addresses or credentials. No VM power,
configuration, guest shell API, or host desktop input.
"""
import asyncio
import hashlib
import io
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Literal

from .config import STATE
from .vmware_rfb.client import VNCClient

class Blocked(RuntimeError):
    pass

_LOCK=threading.Lock()
_FRAMES={}
MAX_AGE=45
_CREDENTIAL="MellowCodex/VMware/QA"
# Explicit map rather than trusting a VNC server to infer Shift.
_SHIFT=dict(zip('!@#$%^&*()_+{}|:"<>?~','1234567890-=[]\\;\x27,./\x60'))
_KEYS=frozenset(("esc","tab","enter","backspace","left","right","up","down","home","end","delete","ctrl+a","ctrl+c","ctrl+v","ctrl+l","ctrl+esc","alt+f4","alt+tab","win+r","win+e","f2","f5"))

def _norm(path):
    return os.path.normcase(os.path.abspath(str(path)))

def _configuration():
    p=STATE/"vmware-control.json"
    if not p.is_file() or p.is_symlink():raise Blocked("OWNER_VMWARE_CONFIGURATION_REQUIRED")
    data=json.loads(p.read_text(encoding="utf-8-sig"))
    if set(data)!={"enabled","vmrun","vmx","port","keyboard_layout"} or data["enabled"] is not True:
        raise Blocked("OWNER_VMWARE_NOT_ENABLED")
    exe,vmx=Path(data["vmrun"]),Path(data["vmx"])
    if not exe.is_absolute() or exe.name.lower()!="vmrun.exe" or not exe.is_file() or exe.is_symlink():
        raise Blocked("VMRUN_NOT_VERIFIED")
    if not vmx.is_absolute() or vmx.suffix.lower()!=".vmx" or not vmx.is_file() or vmx.is_symlink():
        raise Blocked("VMX_NOT_VERIFIED")
    if type(data["port"]) is not int or not 5900<=data["port"]<=6001 or data["keyboard_layout"]!="en-US":
        raise Blocked("INVALID_OWNER_VMWARE_CONFIG")
    return exe,vmx,data["port"]

def _running(exe,vmx):
    p=subprocess.run([str(exe),"-T","ws","list"],capture_output=True,text=True,timeout=5)
    if p.returncode:raise Blocked("VMWARE_INVENTORY_UNAVAILABLE")
    rows=p.stdout.strip().splitlines()
    if not rows or not re.fullmatch(r"Total running VMs: \d+",rows[0]):raise Blocked("VMWARE_INVENTORY_INVALID")
    if int(rows[0].split(":")[1])!=len(rows)-1:raise Blocked("VMWARE_INVENTORY_INVALID")
    return sum(_norm(x)==_norm(vmx) for x in rows[1:])==1

def _verify_listener(vmx,port):
    import psutil
    values={}
    for line in vmx.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        m=re.fullmatch(r'\s*(RemoteDisplay\.vnc\.(?:enabled|port|ip))\s*=\s*"([^"]*)"\s*',line,re.I)
        if m:
            key=m[1].lower()
            if key in values:raise Blocked("AMBIGUOUS_VNC_CONFIG")
            values[key]=m[2]
    if values.get("remotedisplay.vnc.enabled","").lower()!="true" or values.get("remotedisplay.vnc.ip")!="127.0.0.1" or values.get("remotedisplay.vnc.port")!=str(port):
        raise Blocked("OWNER_LOOPBACK_VNC_CONFIGURATION_REQUIRED")
    rows=[c for c in psutil.net_connections(kind="tcp") if c.status=="LISTEN" and c.laddr.port==port]
    if len(rows)!=1 or rows[0].laddr.ip!="127.0.0.1" or not rows[0].pid:
        raise Blocked("VNC_LISTENER_NOT_VERIFIED_LOOPBACK")
    proc=psutil.Process(rows[0].pid)
    if proc.name().lower()!="vmware-vmx.exe" or not any(_norm(a)==_norm(vmx) for a in proc.cmdline()):
        raise Blocked("VNC_LISTENER_WRONG_VM")
    return proc.pid,proc.create_time()

def _password():
    import win32cred
    try:
        raw=win32cred.CredRead(_CREDENTIAL,win32cred.CRED_TYPE_GENERIC,0)["CredentialBlob"]
        value=raw.decode("utf-16-le") if isinstance(raw,bytes) else raw
    except Exception:raise Blocked("OWNER_VNC_CREDENTIAL_REQUIRED") from None
    if not isinstance(value,str) or not 1<=len(value)<=8 or not value.isascii():
        raise Blocked("INVALID_OWNER_VNC_CREDENTIAL")
    return value

def _connect():
    exe,vmx,port=_configuration()
    if not _running(exe,vmx):raise Blocked("QA_VM_NOT_RUNNING")
    identity=(_norm(vmx),port,*_verify_listener(vmx,port))
    client=VNCClient("127.0.0.1",port,_password(),timeout=5)
    try:
        client.connect()
        return client,identity
    except Exception:
        client.close()
        raise

def _grab(client):
    client.capture()
    return client.png()

def _publish(raw,w,h,identity):
    from .file_library import FileLibrary
    for key,value in list(_FRAMES.items()):
        if time.monotonic()-value["tick"]>MAX_AGE:_FRAMES.pop(key,None)
    while len(_FRAMES)>=8:_FRAMES.pop(next(iter(_FRAMES)))
    fid=uuid.uuid4().hex
    item=FileLibrary().import_bytes("vmware-guest-"+fid+".png",raw,"image/png","Owner-configured QA VM")
    _FRAMES[fid]={"raw":raw,"width":w,"height":h,"identity":identity,"tick":time.monotonic()}
    return {"frame_id":fid,"file_id":item["id"],"width":w,"height":h,"sha256":hashlib.sha256(raw).hexdigest(),"backend":"vmware-vnc","expires_in":MAX_AGE}

def _screenshot():
    client,identity=_connect()
    try:return _publish(*_grab(client),identity)
    finally:client.close()

def _type_text(client,text):
    if not 1<=len(text)<=160 or any(not 32<=ord(c)<=126 for c in text):
        raise Blocked("ASCII_US_LAYOUT_ONLY")
    for c in text:
        if c in _SHIFT:
            base=_SHIFT[c]
            client.key(0xffe1,True)
            try:
                client.key(ord(base),True);time.sleep(.03);client.key(ord(base),False)
            finally:client.key(0xffe1,False)
        elif "A"<=c<="Z":
            client.key(0xffe1,True)
            try:
                client.key(ord(c.lower()),True);time.sleep(.03);client.key(ord(c.lower()),False)
            finally:client.key(0xffe1,False)
        else:
            client.key(ord(c),True);time.sleep(.03);client.key(ord(c),False)
        time.sleep(.03)

def _input(frame_id,action,x,y,key,text):
    if action=="key" and key not in _KEYS:raise Blocked("UNSUPPORTED_VMWARE_KEY")
    if action=="type" and (not 1<=len(text)<=160 or any(not 32<=ord(c)<=126 for c in text)):
        raise Blocked("ASCII_US_LAYOUT_ONLY")
    meta=_FRAMES.pop(frame_id,None)
    if meta is None or not 0<=time.monotonic()-meta["tick"]<=MAX_AGE:
        raise Blocked("FRAME_EXPIRED_OR_USED")
    if action=="click" and (type(x) is not int or type(y) is not int or not 0<=x<meta["width"] or not 0<=y<meta["height"]):
        raise Blocked("OUTSIDE_FRAME")
    from PIL import Image,ImageChops,ImageStat
    client,identity=_connect()
    started=False
    try:
        raw,w,h=_grab(client)
        if identity!=meta["identity"] or (w,h)!=(meta["width"],meta["height"]):
            raise Blocked("VM_OR_FRAME_GEOMETRY_CHANGED")
        with Image.open(io.BytesIO(meta["raw"])) as a,Image.open(io.BytesIO(raw)) as b:
            a,b=a.convert("RGB"),b.convert("RGB")
            # Check whole screen and the click target; no blind input after change.
            if max(ImageStat.Stat(ImageChops.difference(a,b)).mean)>1:
                raise Blocked("FRAME_CONTENT_CHANGED")
            if action=="click":
                region=(max(0,x-16),max(0,y-16),min(w,x+17),min(h,y+17))
                if ImageChops.difference(a.crop(region),b.crop(region)).getbbox():
                    raise Blocked("TARGET_CONTENT_CHANGED")
        started=True
        if action=="click":client.click(x,y)
        elif action=="key":client.press_combo(key)
        elif action=="type":_type_text(client,text)
        else:raise Blocked("UNSUPPORTED_ACTION")
    except Exception as e:
        if started:return {"state":"input_outcome_uncertain","error_type":type(e).__name__,"effect_verified":False,"retry_permitted":False}
        raise
    finally:client.close()
    # VMware may not return a second unchanged framebuffer on the same RFB
    # session. Disconnect, then request a new frame; never replay input.
    time.sleep(1)
    try:
        after=_screenshot()
    except Exception as e:
        return {"state":"input_sent_observation_unavailable","error_type":type(e).__name__,"effect_verified":False,"retry_permitted":False}
    return {"state":"input_sent","effect_verified":False,"after":after,"retry_permitted":False}

def _dispatch(action,**kwargs):
    if not _LOCK.acquire(timeout=1):return {"state":"busy","reason":"VMWARE_OPERATION_IN_PROGRESS"}
    try:
        if action=="status":
            exe,vmx,port=_configuration()
            if not _running(exe,vmx):return {"state":"stopped","configured":True,"input_verified":False}
            _verify_listener(vmx,port)
            return {"state":"configured","running":True,"authentication_verified":False,"input_verified":False}
        if action=="screenshot":return _screenshot()
        return _input(action=action,**kwargs)
    except Blocked as e:return {"state":"blocked","reason":str(e)}
    except Exception as e:return {"state":"failed","error_type":type(e).__name__}
    finally:_LOCK.release()

def register_mcp(mcp,read,write):
    @mcp.tool(annotations=read)
    async def vmware_status()->dict:
        """Read the owner-enabled local QA VMware status; never starts the VM."""
        return await asyncio.to_thread(_dispatch,"status")
    @mcp.tool(annotations=read)
    async def vmware_screenshot()->dict:
        """Capture only the configured QA guest via authenticated loopback VNC. Retrieve returned file_id with get_file. No host capture."""
        return await asyncio.to_thread(_dispatch,"screenshot")
    @mcp.tool(annotations=write)
    async def vmware_input(frame_id:str,action:Literal["click","key","type"],x:int=0,y:int=0,key:str="",text:str="")->dict:
        """Owner-authorized guest input, one-use fresh frame, exact target verification. Get a new screenshot before each action. Never replay uncertain input. ASCII US layout only; inspect returned after frame."""
        return await asyncio.to_thread(_dispatch,action,frame_id=frame_id,x=x,y=y,key=key,text=text)
