"""Managed-process HTTP integration checks; fake servers only, no inference."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request, urlopen

import q38_t7_isolated as coordinator
import q38_t7_runtime as runtime
import q38_t7_supervisor as native_supervisor


FAKE = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
mode = sys.argv[1] if sys.argv[1] in ('drafted', 'nodraft') else ('drafted' if '-md' in sys.argv else 'nodraft')
prefixes = []
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        body = json.dumps({"mode": mode}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text = body.get("prompt") or body["messages"][-1]["content"]
        cached = max((len(p) for p in prefixes if text.startswith(p)), default=0)
        prefixes.append(text)
        result = json.dumps({"http_status": 200, "timings": {"cache_n": cached}, "mode": mode}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(result)
server = HTTPServer(("127.0.0.1", 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
'''


class FakeSupervisor:
    """Owns only the exact fake processes created by this test."""

    def __init__(self, fake_path, wrong_mode=False):
        self.fake_path, self.wrong_mode = fake_path, wrong_mode
        self.spawned = []

    def spawn(self, arm, recipe):
        mode = 'drafted' if self.wrong_mode else arm
        process = subprocess.Popen([sys.executable, '-u', str(self.fake_path), mode],
                                   stdout=subprocess.PIPE, text=True)
        self.spawned.append(process)
        port = process.stdout.readline().strip()
        if not port.isdigit():
            process.terminate()
            process.wait(timeout=5)
            raise runtime.SpawnFailure('fake startup failed', True)
        return {'process': process, 'url': f'http://127.0.0.1:{port}'}

    def verify(self, handle, arm, recipe):
        if handle['process'].poll() is not None:
            return False
        with urlopen(handle['url'] + '/props', timeout=2) as response:
            return json.load(response).get('mode') == arm

    def stop_and_drain(self, handle):
        process = handle['process']
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        return process.poll() is not None


class HttpTransport:
    def __init__(self): self.sent = []

    def send(self, handle, body):
        url = handle['url'] if isinstance(handle, dict) else handle.url
        self.sent.append((url, body))
        req = Request(url + '/v1/chat/completions',
                      data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=2) as response:
            return json.load(response)


class Journal:
    def __init__(self): self.events = []
    def before_request(self, arm, pair_key, kind, digest):
        self.events.append(('before', arm, kind, digest)); return True
    def after_response(self, arm, pair_key, kind, response):
        self.events.append(('after', arm, kind)); return True


class ManagedHttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fake = Path(self.temp.name) / 'fake_server.py'
        self.fake.write_text(FAKE)
        self.supervisor = FakeSupervisor(self.fake)
        self.transport, self.journal = HttpTransport(), Journal()
        self.rt = runtime.Runtime(self.supervisor, self.transport, self.journal, lambda: False)
        base = {'binary': 'bound', 'model': 'bound', 'shape': {'np': 1}}
        self.recipes = {'drafted': dict(base, draft_model='draft', draft_options={'type': 'dflash'}),
                        'nodraft': dict(base, draft_model=None, draft_options={})}

    def tearDown(self):
        for process in self.supervisor.spawned:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            if process.stdout and not process.stdout.closed:
                process.stdout.close()
        self.temp.cleanup()

    def test_two_separate_processes_independently_warm_same_chat_prefix(self):
        warm = {'messages': [{'role': 'user', 'content': 'shared prefix'}], 'max_tokens': 1}
        body = {'messages': [{'role': 'user', 'content': 'shared prefix then ask'}], 'max_tokens': 8}
        report = coordinator.run_pairs(self.rt, self.recipes,
                                       [coordinator.Pair('B/1', body, warm, min_cached_tokens=13)])
        self.assertFalse(report['partial'], report['error'])
        self.assertEqual(report['cleanup'], {'drafted': True, 'nodraft': True})
        self.assertEqual(len(self.supervisor.spawned), 2)
        self.assertNotEqual(*[p.pid for p in self.supervisor.spawned])
        self.assertTrue(all(p.poll() is not None for p in self.supervisor.spawned))
        records = report['records']
        self.assertEqual([r['kind'] for r in records], ['warm', 'measure', 'warm', 'measure'])
        self.assertEqual(records[0]['body_sha256'], records[2]['body_sha256'])
        self.assertEqual(records[1]['body_sha256'], records[3]['body_sha256'])
        self.assertEqual([r['response']['mode'] for r in records],
                         ['drafted', 'drafted', 'nodraft', 'nodraft'])
        self.assertNotEqual(self.transport.sent[0][0], self.transport.sent[2][0])
        self.assertTrue(all('speculative' not in json.dumps(body) for _, body in self.transport.sent))

    def test_mode_mismatch_fails_before_request_and_drains(self):
        self.supervisor.wrong_mode = True
        report = coordinator.run_pairs(self.rt, self.recipes, [coordinator.Pair('A', {'prompt': 'x'})])
        self.assertTrue(report['partial'])
        self.assertEqual(report['cleanup'], {'drafted': True, 'nodraft': True})
        self.assertEqual(len(self.transport.sent), 1)
        self.assertEqual(self.transport.sent[0][1], {'prompt': 'x'})

    def test_missing_cache_witness_stops_before_other_arm(self):
        warm = {'messages': [{'role': 'user', 'content': 'short'}]}
        body = {'messages': [{'role': 'user', 'content': 'short question'}]}
        report = coordinator.run_pairs(self.rt, self.recipes, [coordinator.Pair('B', body, warm, 100)])
        self.assertTrue(report['partial'])
        self.assertIn('cache witness', report['error'])
        self.assertEqual(report['cleanup'], {'drafted': True})
        self.assertEqual(len(self.supervisor.spawned), 1)

    def test_dead_process_refuses_before_journal_or_transport(self):
        server = self.rt.start('drafted', self.recipes['drafted'])
        self.rt.verify(server, 'drafted', self.recipes['drafted'])
        server.handle['process'].terminate()
        server.handle['process'].wait(timeout=5)
        with self.assertRaisesRegex(runtime.RuntimeFailure, 'identity no longer verified'):
            self.rt.request(server, {'prompt': 'x'}, 'measure', 'test')
        self.assertEqual(self.transport.sent, [])
        self.assertEqual(self.journal.events, [])
        self.assertTrue(self.rt.stop(server))

    def test_unsafe_override_and_mismatched_warm_prefix_refuse_before_launch(self):
        bad = coordinator.Pair('A', {'prompt': 'x', 'speculative.n_max': 0})
        with self.assertRaises(coordinator.InvalidRun):
            coordinator.run_pairs(self.rt, self.recipes, [bad])
        warm = {'messages': [{'role': 'user', 'content': 'prefix'}]}
        body = {'messages': [{'role': 'assistant', 'content': 'prefix and more'}]}
        with self.assertRaises(coordinator.InvalidRun):
            coordinator.run_pairs(self.rt, self.recipes, [coordinator.Pair('B', body, warm, 1)])
        self.assertEqual(self.supervisor.spawned, [])

    def test_concrete_owner_drives_both_fake_http_arms(self):
        root = Path(self.temp.name)
        model, draft, log = root / 'model', root / 'draft', root / 'servers.log'
        model.write_bytes(b'model'); draft.write_bytes(b'draft')
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        shape = {'common_argv': [str(self.fake), '-m', str(model)],
                 'binary_sha256': sha(sys.executable), 'model_sha256': sha(model),
                 'env': {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}}
        base = {'binary': sys.executable, 'model': str(model), 'shape': shape}
        recipes = {'drafted': dict(base, draft_model=str(draft),
                                   draft_options={'type': 'draft-dflash', 'n_max': 7,
                                                  'draft_sha256': sha(draft)}),
                   'nodraft': dict(base, draft_model=None, draft_options={})}

        def fake_identity(handle, arm, recipe):
            with urlopen(handle.url + '/props', timeout=2) as response:
                return handle.process.poll() is None and json.load(response)['mode'] == arm

        class BoundFakeSupervisor(native_supervisor.Supervisor):
            def spawn(inner, arm, recipe):
                offset = log.stat().st_size if log.exists() else 0
                handle = super(BoundFakeSupervisor, inner).spawn(arm, recipe)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    lines = log.read_text()[offset:].splitlines()
                    if lines and lines[0].isdigit():
                        handle.url = 'http://127.0.0.1:' + lines[0]
                        return handle
                    if handle.process.poll() is not None:
                        break
                    time.sleep(.01)
                inner.stop_and_drain(handle)
                raise runtime.SpawnFailure('fake server did not bind', True)

        concrete = BoundFakeSupervisor(fake_identity, lambda h: h.process.poll() is not None,
                                       log_path=str(log))
        owner = runtime.Runtime(concrete, self.transport, self.journal, lambda: False)
        warm = {'messages': [{'role': 'user', 'content': 'prefix'}]}
        body = {'messages': [{'role': 'user', 'content': 'prefix test'}]}
        result = coordinator.run_pairs(owner, recipes, [coordinator.Pair('B', body, warm, 6)])
        self.assertFalse(result['partial'], result['error'])
        self.assertEqual(result['cleanup'], {'drafted': True, 'nodraft': True})
        self.assertEqual([r['response']['mode'] for r in result['records']],
                         ['drafted', 'drafted', 'nodraft', 'nodraft'])


if __name__ == '__main__':
    unittest.main()
