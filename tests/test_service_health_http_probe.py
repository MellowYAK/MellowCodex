"""Real loopback health probes: accurate status, no false green responses."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

from hub import service_health


class ProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/json':
            payload=b'{"status":"ok","probe":true}'
            self.send_response(200);self.send_header('Content-Type','application/json')
        elif self.path == '/unhealthy':
            payload=b'{"status":"error"}'
            self.send_response(503);self.send_header('Content-Type','application/json')
        else:
            payload=b'<!doctype html><html>Hub</html>'
            self.send_response(200);self.send_header('Content-Type','text/html')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):pass


def test_loopback_http_probe_returns_real_status_and_data():
    server=ThreadingHTTPServer(('127.0.0.1',0),ProbeHandler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base='http://127.0.0.1:'+str(server.server_address[1])
        assert service_health.api(base+'/')==(200,{})
        assert service_health.api(base+'/json')==(200,{'status':'ok','probe':True})
        assert service_health.api(base+'/unhealthy')==(503,{'status':'error'})
    finally:
        server.shutdown();server.server_close();thread.join(timeout=4)


def test_down_port_does_not_return_green():
    with patch('httpx.Client',side_effect=__import__('httpx').ConnectError('connection refused')):
        status,data=service_health.api('http://127.0.0.1:8897/health')
    assert status is None and data=={}
