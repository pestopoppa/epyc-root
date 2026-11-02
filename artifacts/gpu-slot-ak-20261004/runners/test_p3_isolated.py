import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import p3_kvu_probe_isolated as p


class FakeServer:
    instances = []
    def __init__(self, name, port):
        self.variant = p.ACTIVE_VARIANT
        self.base = 'fake:' + self.variant
        self.rec = {'pid': 101 + len(self.instances)}
        self.slots = {0: 0, 1: 0, 2: 0, 3: 0}
        self.requests = []
        self.stopped = False
        self.instances.append(self)
    def start(self):
        pass
    def stop(self):
        self.stopped = True
        self.rec.update(teardown={'verified_dead': True}, port_free_after=True)


def instance(base):
    return next(s for s in FakeServer.instances if s.base == base)


def fake_chat(base, message, slot, tokens, extra=None):
    assert extra is None
    s = instance(base)
    s.requests.append((message, slot, tokens))
    cached = s.slots[slot]
    s.slots[slot] = 100
    return {'prompt_n': 0 if cached else 100, 'cache_n': 100 if cached else 0,
            'decode_tps': 1, 'draft_acc': 0, 'draft_n': 1 if s.variant == 'drafted' else None, 'text_sha': 'abc',
            'prefill_tps': 1, 'ttft_s': 1}


def fake_resident(base):
    slots = instance(base).slots.copy()
    return {'per_slot': slots, 'sum': sum(slots.values()), 'busy': [], 'frac_pool': 0}


def fake_slot(base, sid, action, filename=None):
    if action == 'erase':
        instance(base).slots[sid] = 0
    return {}


class Poll:
    def __init__(self, base, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def summary(self): return {'n_during_busy': 2}


class P3IsolatedTests(unittest.TestCase):
    def run_pair(self, fail_cleanup=False):
        FakeServer.instances = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def stop(s):
                s.stopped = True
                s.rec.update(teardown={'verified_dead': not fail_cleanup}, port_free_after=True)
            with patch.object(p, 'OUT', root), patch.object(p, 'Server', FakeServer), \
                 patch.object(FakeServer, 'stop', stop), patch.object(p, 'chat', fake_chat), \
                 patch.object(p, 'resident', fake_resident), patch.object(p, 'slot_action', fake_slot), \
                 patch.object(p, 'SlotPoller', Poll), patch.object(p, 'texts', return_value=('x'*100, 'y'*400)), \
                 patch.object(p, 'NB_TOK', 100), patch.object(p.C, 'http_json', return_value={'tokens': list(range(100))}), \
                 patch.object(p.C, 'coherence_check', return_value={}), patch.object(p, 'metrics', return_value={}):
                rc = p.phase_a1(SimpleNamespace(port=18183, park_mode='prefill'))
            result = json.loads((root/'a1.json').read_text())
            return rc, result

    def test_independent_lifecycles_and_matched_warmup(self):
        rc, result = self.run_pair()
        self.assertEqual(rc, 0, result)
        self.assertEqual([x.variant for x in FakeServer.instances], ['drafted', 'nodraft'])
        self.assertTrue(all(x.stopped for x in FakeServer.instances))
        self.assertEqual(FakeServer.instances[0].requests, FakeServer.instances[1].requests)
        self.assertEqual(len(result['rows']), 12)
        self.assertTrue(result['dedicated_server_per_variant'])

    def test_cleanup_failure_never_starts_second_server(self):
        rc, result = self.run_pair(True)
        self.assertEqual(rc, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(FakeServer.instances), 1)

    def test_request_override_refused_before_transport(self):
        with patch.object(p.SB, 'stream_chat') as transport:
            with self.assertRaises(ValueError):
                p.chat('fake', 'prompt', 0, 1, {'speculative.n_max': 0})
            transport.assert_not_called()

    def test_real_http_stream_uses_no_request_override(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append((self.path, body))
                self.send_response(200)
                self.end_headers()
                event = {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}],
                         "timings": {"draft_n": 1, "draft_n_accepted": 1}}
                self.wfile.write(b"data: " + json.dumps(event).encode() + b"\n\ndata: [DONE]\n\n")
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            result = p.chat(f"http://127.0.0.1:{server.server_port}", "fixed", 0, 2)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertEqual(result["draft_n"], 1)
        self.assertEqual(received[0][0], "/v1/chat/completions")
        self.assertNotIn("speculative.n_max", received[0][1])
        self.assertNotIn("speculative", received[0][1])

    def test_no_draft_arguments_removed(self):
        import p3_draft_guard as guard
        self.assertEqual(guard.dedicated_no_draft_argv(['server', '-m', 'target', '-md', 'draft', '--spec-type', 'draft-dflash']), ['server', '-m', 'target'])

if __name__ == '__main__':
    unittest.main()
