import hashlib
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
import server_lifecycle as life

FAKE = '''import http.server,json,os,sys\nassert os.sched_getaffinity(0) == {int(os.environ['EXPECTED_CPU'])}\nclass H(http.server.BaseHTTPRequestHandler):\n def log_message(self,*a): pass\n def do_GET(self):\n  b=b"{\\"status\\":\\"ok\\"}"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)\n def do_POST(self):\n  o=json.loads(self.rfile.read(int(self.headers["Content-Length"]))); assert len(o["prompt"]) == 300000\n  b=json.dumps({"content":"answer","timings":{"predicted_n":2,"predicted_ms":10}}).encode(); self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)\nopen(sys.argv[2],"w").write(str(os.getpid()))\nhttp.server.HTTPServer(("127.0.0.1",int(sys.argv[1])),H).serve_forever()\n'''

class TestLifecycle(unittest.TestCase):
    def test_foreign_listener_rejected(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            sock.listen()
            url = f'http://127.0.0.1:{sock.getsockname()[1]}'
            life._owned_listener(os.getpid(), url)
            with self.assertRaises(life.LaunchError):
                life._owned_listener(os.getppid(), url)

    def test_fake_server_and_owned_reap(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); f=root/'fake.py'; f.write_text(FAKE)
            ids=json.dumps([1]*300000,separators=(',',':')).encode(); (root/'tokens').write_bytes(ids)
            plan=root/'plan.json'; plan.write_text(json.dumps({'items':[{'id':'x','length':300000,'expected':'answer','tokens_path':'tokens','tokens_sha256':hashlib.sha256(ids).hexdigest()}]}))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            pidfile=root/'pid'; env=dict(os.environ,LD_LIBRARY_PATH='/tmp',EXPECTED_CPU=str(min(os.sched_getaffinity(0))))
            result=life.run_owned(command=[sys.executable,str(f),str(port),str(pidfile)],env=env,base_url=f'http://127.0.0.1:{port}',plan_path=plan,fixture_root=root,output_dir=root/'out',arm='J',budget_s=15,minimum_cell_s=2,request_timeout_s=2,startup_s=3,term_s=1,kill_s=1,log_path=root/'log',granted_cpus=str(min(os.sched_getaffinity(0))))
            self.assertEqual(result,0)
            self.assertEqual(json.loads((root/'out/x.J.finished.json').read_text())['response'],'answer')
            with self.assertRaises(ProcessLookupError): os.kill(int(pidfile.read_text()),0)
    def test_refuses_unisolated_library(self):
        with self.assertRaises(ValueError):
            life.run_owned(command=['false'],env={},base_url='http://127.0.0.1:1',plan_path='x',fixture_root='x',output_dir='x',arm='J',budget_s=20,minimum_cell_s=2,request_timeout_s=2,log_path='/tmp/x')

    def test_existing_stop_prevents_server_launch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stop = root / 'stop'
            stop.touch()
            result = life.run_owned(
                command=[sys.executable, '-c', 'raise SystemExit(99)'],
                env=dict(os.environ, LD_LIBRARY_PATH='/tmp'),
                base_url='http://127.0.0.1:1', plan_path='x', fixture_root='x',
                output_dir='x', arm='J', budget_s=60, minimum_cell_s=2,
                request_timeout_s=2, log_path=root / 'log', stop_file=stop, granted_cpus=str(min(os.sched_getaffinity(0))))
            self.assertEqual(result, 75)
            self.assertFalse((root / 'log').exists())

if __name__=='__main__': unittest.main()
