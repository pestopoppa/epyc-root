"""Offline qualification lifecycle: only the captured listener receives requests."""
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest import mock

import worker


class Guard:
    mode = 'qualification'
    initial = b'synthetic grant'
    def __init__(self): self.deadline = int(time.time()) + 3600
    def check(self): return False


class FakeResponse:
    def __init__(self, payload=b''):
        self.status = 200
        self.payload = payload
    def read(self): return self.payload
    def __enter__(self): return self
    def __exit__(self, *_): return False


class FakeServer:
    """Models captured server and a real listener, with no inference process."""
    def __init__(self, cmd, *, own_listener, **kwargs):
        self.pid = os.getpid()
        self.returncode = None
        self.listener = None
        if own_listener:
            self.listener = socket.socket()
            self.listener.bind(('127.0.0.1', int(cmd[cmd.index('--port') + 1])))
            self.listener.listen()
    def poll(self): return self.returncode
    def send_signal(self, _):
        if self.listener is not None:
            self.listener.close()
            self.listener = None
        self.returncode = 0
    def wait(self, timeout=None):
        if self.returncode is None:
            raise AssertionError('wait before termination')
        return self.returncode
    def kill(self): self.send_signal(None)


class QualificationListenerTests(unittest.TestCase):
    def exercise(self, owns_listener):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            kernel = root / 'kernel'; kernel.mkdir()
            (kernel / 'llama-server').write_bytes(b'fake server binary')
            plan = {'id': 'fixture', 'arms': [{'id': 'hybrid', 'GGML_FA_VKQ_F16': None}],
                    'request': {'temperature': 0}}
            (source / 'PLAN.json').write_text(json.dumps(plan))
            (source / 'FULL-MODELS.sha256').write_text('fake catalog\n')
            (source / 'RUNTIME-INPUTS.sha256').write_text('fake runtime\n')
            (source / 'SOURCE-SHA256SUMS').write_text('fake source\n')
            drydir = root / 'dry'; attempt = drydir / 'native-attempts' / 'attempt-fixture'
            attempt.mkdir(parents=True)
            output = attempt / 'vkq3-control'; native = attempt / 'native-result.json'
            events = []
            server = []
            def launch(cmd, **kwargs):
                child = FakeServer(cmd, own_listener=owns_listener, **kwargs)
                server.append(child)
                return child
            def http(req, **kwargs):
                if isinstance(req, str):
                    events.append('health')
                    return FakeResponse()
                events.append('completion')
                return FakeResponse(json.dumps({'timings': {'draft_n': 4, 'draft_n_accepted': 2},
                                                'tokens': [1, 2]}).encode())
            real_publish = worker.publish_native
            def publish_after_cleanup(*args):
                self.assertEqual(server[0].returncode, 0)
                self.assertIsNone(server[0].listener)
                events.append('publish')
                return real_publish(*args)
            env = {'FILLER_DRYRUN': '1', 'FILLER_DRYRUN_DIR': str(drydir),
                   'FILLER_STOPFILE': str(root / 'stop')}
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(worker, 'D', source), mock.patch.object(worker, 'K', kernel), \
                 mock.patch.object(worker, 'grant_context', return_value=(Guard(), output, native)), \
                 mock.patch.object(worker.signal, 'signal'), \
                 mock.patch.object(worker.subprocess, 'Popen', side_effect=launch), \
                 mock.patch.object(worker.urllib.request, 'urlopen', side_effect=http), \
                 mock.patch.object(worker, 'publish_native', side_effect=publish_after_cleanup):
                if owns_listener:
                    self.assertEqual(worker.main(), 0)
                    self.assertEqual(events, ['health', 'completion', 'publish'])
                    self.assertEqual(json.loads(native.read_text())['kind'], 'qualification_control')
                    self.assertEqual(json.loads((output/'hybrid.drain.json').read_text())['drained'], True)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'does not own'):
                        worker.main()
                    self.assertEqual(events, ['health'])
                    self.assertFalse(native.exists())
                self.assertEqual(server[0].returncode, 0)
                self.assertIsNone(server[0].listener)

    def test_wrong_listener_refuses_before_completion(self): self.exercise(False)
    def test_owned_listener_completes_only_after_cleanup(self): self.exercise(True)


if __name__ == '__main__': unittest.main()
