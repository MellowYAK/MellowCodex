import asyncio,io,time,threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from PIL import Image
from hub import vmware_control as v
from hub.vmware_rfb.client import VNCClient,VNCError
from hub import mcp_gateway as g

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(v,"_FRAMES",{})
    monkeypatch.setattr(v.time,"sleep",lambda _:None)

def test_shift_mapping_exact():
    client=Mock()
    v._type_text(client,"C:\\Windows")
    keys=[c.args for c in client.key.call_args_list]
    assert keys[:8]==[(0xffe1,True),(ord('c'),True),(ord('c'),False),(0xffe1,False),
                     (0xffe1,True),(ord(';'),True),(ord(';'),False),(0xffe1,False)]
    assert keys[8:10]==[(92,True),(92,False)]
    assert keys[10:14]==[(0xffe1,True),(ord('w'),True),(ord('w'),False),(0xffe1,False)]
    assert v._SHIFT==dict(zip('!@#$%^&*()_+{}|:"<>?~',"1234567890-=[]\\;',./"+chr(96)))
    with pytest.raises(v.Blocked):v._type_text(client,"שלום")

def test_disabled_without_local_config(tmp_path,monkeypatch):
    monkeypatch.setattr(v,"STATE",tmp_path)
    assert v._dispatch("status")=={"state":"blocked","reason":"OWNER_VMWARE_CONFIGURATION_REQUIRED"}

def test_reject_wildcard_listener(tmp_path,monkeypatch):
    import psutil
    vmx=tmp_path/"test.vmx"
    vmx.write_text('RemoteDisplay.vnc.enabled = "TRUE"\nRemoteDisplay.vnc.port = "5900"\nRemoteDisplay.vnc.ip = "127.0.0.1"\n')
    monkeypatch.setattr(psutil,"net_connections",lambda **_: [SimpleNamespace(status="LISTEN",laddr=SimpleNamespace(ip="0.0.0.0",port=5900),pid=123)])
    with pytest.raises(v.Blocked,match="LOOPBACK"):v._verify_listener(vmx,5900)

def png(color="white"):
    b=io.BytesIO();Image.new("RGB",(64,64),color).save(b,"PNG")
    return b.getvalue()

def setup_frame(monkeypatch,color="white"):
    identity=("vm",5900,123,1.)
    raw=png(color)
    v._FRAMES["fresh"]={"raw":raw,"width":64,"height":64,"identity":identity,"tick":time.monotonic()}
    client=Mock()
    monkeypatch.setattr(v,"_connect",lambda:(client,identity))
    monkeypatch.setattr(v,"_grab",lambda c:(png(),64,64))
    return client

def test_input_reconnects_and_no_replay(monkeypatch):
    client=setup_frame(monkeypatch)
    second=Mock()
    monkeypatch.setattr(v,"_screenshot",second)
    second.return_value={"frame_id":"new"}
    r=v._input("fresh","click",30,30,"","")
    assert r["state"]=="input_sent" and not r["effect_verified"]
    client.click.assert_called_once_with(30,30)
    client.close.assert_called_once()
    second.assert_called_once()
    with pytest.raises(v.Blocked,match="USED"):v._input("fresh","click",30,30,"","")

def test_stale_content_blocks_input(monkeypatch):
    client=setup_frame(monkeypatch,"black")
    with pytest.raises(v.Blocked,match="CONTENT_CHANGED"):v._input("fresh","click",30,30,"","")
    client.click.assert_not_called()

def test_expired_frame_blocks_before_connection(monkeypatch):
    client=setup_frame(monkeypatch)
    v._FRAMES["fresh"]["tick"]-=46
    with pytest.raises(v.Blocked,match="EXPIRED"):v._input("fresh","click",30,30,"","")
    client.click.assert_not_called()

def test_uncertain_after_input_never_retries(monkeypatch):
    client=setup_frame(monkeypatch)
    monkeypatch.setattr(v,"_screenshot",Mock(side_effect=TimeoutError))
    r=v._input("fresh","click",30,30,"","")
    assert r["state"]=="input_sent_observation_unavailable" and not r["retry_permitted"]
    client.click.assert_called_once()

def test_wrong_vm_identity_blocks(monkeypatch):
    client=setup_frame(monkeypatch)
    v._FRAMES["fresh"]["identity"]=("other",5900,123,1.)
    with pytest.raises(v.Blocked,match="VM_OR_FRAME"):v._input("fresh","click",30,30,"","")
    client.click.assert_not_called()

def test_rfb_rejects_none(monkeypatch):
    import socket
    client=VNCClient("127.0.0.1",5900,"test",timeout=1)
    fake=Mock()
    data=iter([b"RFB 003.008\n",b"\x01",b"\x01"])
    fake.recv.side_effect=lambda n:next(data)
    monkeypatch.setattr(socket,"create_connection",lambda *a,**k:fake)
    with pytest.raises(VNCError,match="Authenticated VNC required"):client.connect()
    assert fake.sendall.call_count==1

def test_mcp_registration():
    async def check():
        tools=await g.mcp.list_tools()
        assert {"vmware_status","vmware_screenshot","vmware_input"} <= {t.name for t in tools}
    asyncio.run(check())

def test_real_mcp_transport_error_result(monkeypatch):
    async def unavailable(*a,**kw):
        raise g.LocalTransportError("Hub transport ReadTimeout; write_outcome_uncertain")
    monkeypatch.setattr(g,"local",unavailable)
    async def check():
        r=await g.mcp.call_tool("sync_conversation_message",dict(project_id="a"*32,conversation_key="thread-test",message_id="stable",text="test",speaker="user"))
        assert r.is_error
        assert "HUB_TRANSPORT_UNAVAILABLE" in r.content[0].text
        assert "write_outcome_uncertain" in r.content[0].text
    asyncio.run(check())
