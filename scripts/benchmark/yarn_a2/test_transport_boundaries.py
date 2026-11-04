import http.server
import tempfile
import threading
import time
import unittest
from pathlib import Path
import transport

class Tests(unittest.TestCase):
    def test_redirect_is_not_followed(self):
        hits=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                hits.append(self.path)
                self.send_response(302)
                self.send_header('Location', '/destination')
                self.end_headers()
            def do_GET(self):
                hits.append(self.path)
                self.send_response(200)
                self.end_headers()
        server=http.server.HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                result=transport.request(f'http://127.0.0.1:{server.server_port}/initial',{},stop_file=str(Path(d)/'stop'),deadline=time.monotonic()+3)
            self.assertEqual(result['state'],'unknown')
            self.assertEqual(hits,['/initial'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_payload_bound_is_checked_before_worker_start(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            transport.request('http://127.0.0.1:1/',{'data':'x'*(32*1024*1024)},stop_file=str(Path(d)/'stop'),deadline=time.monotonic()+10)

if __name__ == '__main__': unittest.main()
