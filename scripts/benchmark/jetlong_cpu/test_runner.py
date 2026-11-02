import hashlib
import http.server
import threading
import urllib.request
import json
import tempfile
import unittest
from pathlib import Path
import ledger
import runner

class RunnerTests(unittest.TestCase):
    def setup_plan(self, d):
        root=Path(d); fixture=root/'tokens.json'; raw=json.dumps([1,2,3]).encode(); fixture.write_bytes(raw)
        # Exercise the real plan invariant with a small fixture by patching item length
        # only at the fixture boundary: test below uses a full exact-length array.
        raw=json.dumps([1]*300000, separators=(',',':')).encode(); fixture.write_bytes(raw)
        plan=root/'plan.json'; plan.write_text(json.dumps({'items':[{'id':'x','expected':'answer','length':300000,'tokens_path':'tokens.json','tokens_sha256':hashlib.sha256(raw).hexdigest()}]}))
        return root,plan
    def test_resume_and_one_arm(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan=self.setup_plan(d); calls=[]
            def fake(ids, timeout):
                calls.append((len(ids),timeout)); return {'content':'answer','timings':{'predicted_n':4,'predicted_ms':100}}
            self.assertEqual(runner.run_segment(plan,root/'out',root,'J',fake,10,5,5),0)
            self.assertEqual(runner.run_segment(plan,root/'out',root,'J',fake,10,5,5),0)
            self.assertEqual(len(calls),1)
            p,pin=ledger.initialize(root/'out',plan)
            self.assertEqual(ledger.inventory(root/'out',p,pin)['unstarted'],[('x','Y')])
    def test_budget_timeout_and_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan=self.setup_plan(d); out=root/'out'
            def timeout(ids, seconds): raise TimeoutError()
            self.assertEqual(runner.run_segment(plan,out,root,'J',timeout,1,5,5),75)
            self.assertEqual(runner.run_segment(plan,out,root,'J',timeout,10,5,5),75)
            p,pin=ledger.initialize(out,plan)
            self.assertEqual(ledger.inventory(out,p,pin)['finished'],[('x','J')])
            def fail(ids, seconds): raise ConnectionError()
            self.assertEqual(runner.run_segment(plan,out,root,'Y',fail,10,5,5),1)
            self.assertEqual(runner.run_segment(plan,out,root,'Y',fail,10,5,5),1)
            self.assertEqual(ledger.inventory(out,p,pin)['unknown'],[('x','Y')])
    def test_local_fake_http_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                obj=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert len(obj['prompt']) == 300000
                data=json.dumps({'content':'answer','timings':{'predicted_n':2,'predicted_ms':10}}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                root,plan=self.setup_plan(d)
                def transport(tokens,timeout):
                    req=urllib.request.Request('http://127.0.0.1:%d/completion' % server.server_port, data=json.dumps({'prompt':tokens}).encode(), headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(req,timeout=timeout) as response: return json.load(response)
                self.assertEqual(runner.run_segment(plan,root/'out',root,'J',transport,10,5,5),0)
        finally:
            server.shutdown(); server.server_close(); thread.join()
    def test_mutated_fixture_rejected_before_start(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan=self.setup_plan(d); (root/'tokens.json').write_text('[]')
            with self.assertRaises(runner.ProtocolError): runner.run_segment(plan,root/'out',root,'J',lambda *_: None,10,5,5)
            p,pin=ledger.initialize(root/'out',plan)
            self.assertEqual(len(ledger.inventory(root/'out',p,pin)['unstarted']),2)
if __name__=='__main__': unittest.main()
