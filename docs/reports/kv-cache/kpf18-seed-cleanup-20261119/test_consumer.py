"""Full SeedControl consumer, synthetic HTTP/native peer; no model or GPU.

Only the connection and context are doubles. Real capture, watchdog, parser,
record construction and SeedControl.__call__ execute, without AST extraction.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / 'source.json').read_text())
BASE = Path(PINS['base'])
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu/seed-cleanup-20261119')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Abort(Exception):
    pass


class Consumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if digest(BASE) != PINS['base_sha256'] or digest(HERE / 'transport.patch') != PINS['patch_sha256']:
            raise AssertionError('source or patch drift')
        for name, expected in PINS['dependencies'].items():
            if digest(Path(name)) != expected:
                raise AssertionError('dependency drift: ' + name)
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        target = Path(cls.temp.name) / 'cancel_seed_transport.py'
        target.write_bytes(BASE.read_bytes())
        subprocess.run(['patch', '--batch', '--forward', str(target), str(HERE / 'transport.patch')],
                       check=True, capture_output=True)
        if digest(target) != PINS['patched_sha256']:
            raise AssertionError('patched source drift')
        sys.path.insert(0, str(BASE.parent))
        spec = importlib.util.spec_from_file_location('cleanup_consumer', target)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        sys.path.remove(str(BASE.parent))

    def exercise(self, fault=None, log_order='ordered'):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            out = Path(directory)
            log = out / 'native.log'
            log.touch()
            state = types.SimpleNamespace(slots=0, closed=0, response_closed=0, posted=False,
                                          records=[], rows=[], reads=0)
            sock, peer = socket.socketpair()
            self.addCleanup(sock.close)
            self.addCleanup(peer.close)
            stop = Abort('STOP from consumer boundary')
            payload = b'data: {"id_slot":-1,"prompt_progress":{"total":32512,"processed":31744}}\n'
            if fault == 'malformed':
                payload = b'data: invalid-json\n'
            stream = io.BytesIO(payload)

            class Response:
                status = 200

                def readline(self):
                    state.reads += 1
                    if fault in ('stop', 'stop-close'):
                        raise stop
                    return stream.readline()

                def close(self):
                    state.response_closed += 1
                    if fault in ('response-close', 'stop-close'):
                        raise OSError('injected response close error')

            class Connection:
                def __init__(self, *args, **kwargs):
                    self.sock = sock

                def connect(self):
                    if fault == 'connect':
                        raise OSError('injected connect error')

                def request(self, *args, **kwargs):
                    state.posted = True
                    launch = 'slot launch_slot_: id 1 | task 9 | processing task, is_child = 0\n'
                    log.write_text(launch)

                def getresponse(self):
                    if fault == 'headers':
                        raise OSError('injected header error')
                    return Response()

                def close(self):
                    state.closed += 1
                    sock.close()
                    cancel = 'cancel task, id_task = 9\n'
                    release = 'slot release: id 1 | task 9 | stop processing: n_tokens = 32000, truncated = 0\n'
                    with log.open('a') as f:
                        f.write(cancel + release if log_order == 'ordered' else release + cancel)

            def slots():
                state.slots += 1
                if not state.posted:
                    return [dict(id=1, n_prompt_tokens=0, kv_cells={'private': 0}, is_processing=False)]
                return [dict(id=1, id_task=9, is_processing=not state.closed, n_prompt_tokens=32000)]

            def write_json(path, record):
                state.records.append(record)
                path.write_text(json.dumps(record))

            gate = types.SimpleNamespace(Abort=Abort, body_for=lambda *a, **k: {},
                                         write_json=write_json, sha256_file=lambda p: digest(Path(p)))
            ctx = types.SimpleNamespace(check_boundary=lambda: None, out=out,
                                        client=types.SimpleNamespace(base='http://127.0.0.1:8083', slots=slots),
                                        args=types.SimpleNamespace(port=8083),
                                        deadline=types.SimpleNamespace(remaining=lambda: 60))
            srv = types.SimpleNamespace(proc=types.SimpleNamespace(pid=123, poll=lambda: None), log=log)
            run = types.SimpleNamespace(rows=types.SimpleNamespace(add=state.rows.append))
            error = None
            result = None
            with patch.object(self.module.http.client, 'HTTPConnection', Connection), \
                 patch.object(self.module, 'pid_owns_port', return_value=True):
                try:
                    result = self.module.SeedControl(delay_s=0)(gate=gate, ctx=ctx, R=run, srv=srv,
                        slot=1, source_ids=[1]*32512, checkpoint=32000, n_predict=256, control=1, attempt=1)
                except Exception as exc:
                    error = exc
            self.assertEqual(state.closed, 1, 'connection must close exactly once')
            self.assertEqual(sock.fileno(), -1, 'captured own socket leaked')
            self.assertFalse(any(t.name.startswith('Thread-') and t.is_alive()
                                 for t in __import__('threading').enumerate()), 'watchdog leaked')
            if fault:
                self.assertIsInstance(error, Abort)
                self.assertIsNone(result)
                self.assertEqual(state.slots, 2 if fault == 'response-close' else 1,
                                 'post-failure slot polling occurred')
                self.assertEqual(state.rows, [], 'failed capture published a success row')
                self.assertIn('unqualified', state.records[-1]['refusal'])
                if fault in ('stop', 'stop-close'):
                    self.assertIs(error, stop, 'typed STOP identity was lost')
            else:
                self.assertIsNone(error)
                self.assertEqual(state.slots, 3)
                self.assertEqual(result['observed_cancel_task'], log_order == 'ordered')
                self.assertEqual(len(state.rows), 1)
            return state

    def test_ordered_success(self):
        self.exercise()

    def test_bad_native_order_still_refused(self):
        self.exercise(log_order='bad')

    def test_connection_failure(self):
        self.exercise('connect')

    def test_header_failure(self):
        self.exercise('headers')

    def test_stop_propagates(self):
        self.exercise('stop')

    def test_stop_survives_cleanup_error(self):
        self.exercise('stop-close')

    def test_malformed_stream(self):
        self.exercise('malformed')

    def test_response_cleanup_failure_still_closes_connection(self):
        state = self.exercise('response-close')
        self.assertEqual(state.response_closed, 1)


if __name__ == '__main__':
    unittest.main()
