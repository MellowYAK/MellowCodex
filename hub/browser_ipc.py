"""Send an application-owned UI request to the desktop runtime."""
import sys,json
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalSocket
from .config import DESKTOP_IPC
app=QCoreApplication([]);socket=QLocalSocket();socket.connectToServer(DESKTOP_IPC)
if not socket.waitForConnected(2000):raise RuntimeError('Desktop runtime is unavailable')
payload=({'select_target':sys.argv[2]} if sys.argv[1]=='--select-target' else {'capture_target':sys.argv[2]} if sys.argv[1]=='--capture-target' else {'presentation':sys.argv[2]} if sys.argv[1]=='--presentation' else {'open_url':sys.argv[1]})
if sys.argv[1] in ('--runtime-status','--show-runtime'):payload={'runtime_status':True,'show':sys.argv[1]=='--show-runtime'}
if sys.argv[1]=='--print-target':payload={'print_target':sys.argv[2],'expected_url':sys.argv[3],'name':sys.argv[4]}
if sys.argv[1]=='--reload-target':payload={'reload_target':sys.argv[2],'expected_url':sys.argv[3]}
if sys.argv[1]=='--prepare-target':payload={'prepare_target':sys.argv[2]}
if sys.argv[1]=='--close-targets':payload={'close_targets':json.loads(sys.argv[2])}
if sys.argv[1]=='--virtual-drag':payload={'virtual_drag':json.loads(sys.argv[2])}
if sys.argv[1]=='--extensions':payload={'browser_extensions':json.loads(sys.argv[2])}
socket.write(b'quit' if sys.argv[1]=='--quit' else b'focus-browser' if sys.argv[1]=='--focus-browser' else json.dumps(payload).encode());socket.waitForBytesWritten(2000)
if sys.argv[1] in ('--runtime-status','--show-runtime','--extensions','--virtual-drag','--close-targets','--capture-target','--presentation','--print-target','--reload-target','--prepare-target'):
    response=b''
    while b'\n' not in response:
        if not socket.bytesAvailable() and not socket.waitForReadyRead(40000 if sys.argv[1]=='--print-target' else 5000):break
        response+=bytes(socket.readAll())
    if not response:raise RuntimeError('Browser did not provide a rendered frame')
    print(response.decode().strip())
socket.disconnectFromServer()
