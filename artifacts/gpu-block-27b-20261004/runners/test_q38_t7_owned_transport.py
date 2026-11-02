"""Captured fake-server HTTP/tokenizer integration; never runs a model."""

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen

import q38_t7_native_verify as native
import q38_t7_supervisor as supervisor
import q38_t7_transport as transport
import q38_t7_payloads as payloads
import q38_t7_runtime as runtime
import q38_t7_journal as journal


SERVER = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
port=int(sys.argv[sys.argv.index('--port')+1])
mode='drafted' if '-md' in sys.argv else 'nodraft'
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({'mode':mode}).encode())
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/tokenize':
            out=json.dumps({'tokens':[1,2,3]}).encode()
        else:
            timings={'cache_n':5,'predicted_n':3,'predicted_per_second':10}
            if body.get('stream'):
                event={'choices':[{'index':0,'delta':{'content':'answer','reasoning_content':'reason'},
                                  'finish_reason':'stop'}],'timings':timings}
                out=('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode()
            else:
                out=json.dumps({'choices':[{'message':{'content':'answer'},'finish_reason':'stop'}],
                                'timings':timings}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(out)
HTTPServer(('127.0.0.1',port),Handler).serve_forever()
'''


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OwnedTransportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        script, model = root / 'server.py', root / 'model'
        script.write_text(SERVER); model.write_bytes(b'fake model')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        shape = {'common_argv': [str(script), '-m', str(model), '--host', '127.0.0.1', '--port', str(port)],
                 'binary_sha256': sha(sys.executable), 'model_sha256': sha(model), 'env': {}}
        self.recipe = {'binary': sys.executable, 'model': str(model), 'shape': shape,
                       'draft_model': None, 'draft_options': {}}
        libc = next(path for path in native._mapped_paths(os.getpid()) if Path(path).name.startswith('libc.so'))
        def mode(_handle, arm, _recipe):
            with urlopen(f'http://127.0.0.1:{port}/props', timeout=1) as response:
                return json.load(response)['mode'] == arm
        identity = native.NativeIdentityVerifier('127.0.0.1', port, {libc: sha(libc)},
                                                 lambda _: True, mode, require_ggml=False)
        self.sup = supervisor.Supervisor(identity, lambda h: h.process.poll() is not None,
                                          log_path=str(root / 'log'))
        self.handle = self.sup.spawn('nodraft', self.recipe)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.sup.verify(self.handle, 'nodraft', self.recipe):
            time.sleep(.01)
        self.assertTrue(self.sup.verify(self.handle, 'nodraft', self.recipe))
        self.proof = lambda h: {'pid': h.process.pid, 'birth': h.birth,
                                'model_sha256': self.recipe['shape']['model_sha256'],
                                'tokenizer_sha256': 'a' * 64, 'evidence_sha256': 'c' * 64}

    def tearDown(self):
        if not self.handle.closed:
            self.assertTrue(self.sup.stop_and_drain(self.handle))
        self.tmp.cleanup()

    def test_captured_child_serves_stream_and_native_tokenization(self):
        client = transport.OwnedHttpTransport(self.sup, 'a' * 64, self.proof)
        response = client.send(self.handle, {'messages': [{'role': 'user', 'content': 'x'}], 'stream': True})
        self.assertTrue(response['stream_complete'])
        self.assertEqual(response['token_ids'], [1, 2, 3])
        proof = response['tokenizer_provenance']
        self.assertEqual(proof['text_sha256'], hashlib.sha256(b'reason\nanswer').hexdigest())
        self.assertEqual(json.loads(proof['tokenizer_response'])['tokens'], [1, 2, 3])
        self.assertEqual(proof['model_sha256'], self.recipe['shape']['model_sha256'])
        self.assertEqual(proof['pid'], self.handle.process.pid)
        self.assertEqual(proof['birth'], self.handle.birth)

    def test_unknown_or_mutating_identity_is_refused(self):
        client = transport.OwnedHttpTransport(self.sup, 'a' * 64,
                                              lambda h: {**self.proof(h), 'model_sha256': '0' * 64})
        result = client.send(self.handle, {'messages': [{'role': 'user', 'content': 'x'}]})
        self.assertIn('model/tokenizer identity', result['error'])
        self.assertIn('raw_body', result)
        calls = []
        def changes(h):
            calls.append(1)
            return {**self.proof(h), 'evidence_sha256': ('c' if len(calls) == 1 else 'd') * 64}
        client = transport.OwnedHttpTransport(self.sup, 'a' * 64, changes)
        result = client.send(self.handle, {'messages': [{'role': 'user', 'content': 'x'}]})
        self.assertIn('identity changed', result['error'])
        self.assertIn('raw_body', result)

    def test_attested_plan_owns_two_fake_servers_and_scores(self):
        self.assertTrue(self.sup.stop_and_drain(self.handle))
        draft = Path(self.tmp.name) / 'draft'; draft.write_bytes(b'fake draft')
        recipes = {'nodraft': self.recipe,
                   'drafted': dict(self.recipe, draft_model=str(draft),
                                   draft_options={'type': 'draft-dflash', 'n_max': 7,
                                                  'draft_sha256': sha(draft)})}
        prefix = 'nonce 2-4-1-9-ORCHID Mbeki Larsen'
        plan = payloads.build_plan([{'id': 'p1', 'suite': 'test', 'prompt': 'question'}],
                                   [payloads.FrozenContext(2000, 20, (prefix,), 5)],
                                   tokenizer_sha256='a' * 64,
                                   model_sha256=self.recipe['shape']['model_sha256'])
        j = journal.DurableJournal(Path(self.tmp.name) / 'ledger.sqlite', cohort_id=plan.sha256,
                                   model_sha256=plan.model_sha256, run_id='fake-run')
        try:
            rt = runtime.Runtime(self.sup, transport.OwnedHttpTransport(self.sup, 'a' * 64, self.proof),
                                 j, lambda: False)
            run = payloads.run_attested_plan(rt, recipes, plan)
            self.assertFalse(run['partial'], run['error'])
            self.assertEqual(run['cleanup'], {'drafted': True, 'nodraft': True})
            report = payloads.score(plan, run, {})
            self.assertEqual(report['status'], 'COMPLETE', report)
        finally:
            j.close()


if __name__ == '__main__':
    unittest.main()
