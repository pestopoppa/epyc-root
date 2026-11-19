import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('kpf26_native_smoke', Path(__file__).with_name('native_smoke.py'))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class Response:
    status = 200
    def __init__(self, tokens): self.tokens = tokens
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps({'tokens_predicted': self.tokens}).encode()


class NativeSmokeTests(unittest.TestCase):
    def test_listener_requires_current_pid_socket_owner(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            self.assertTrue(smoke.owns_listener(os.getpid(), listener.getsockname()[1]))
        self.assertFalse(smoke.owns_listener(os.getpid(), listener.getsockname()[1] if listener.fileno() >= 0 else 1))

    def invoke(self, output, tokens=1, births=(100, 100), ownership=(True, True)):
        argv = ['native_smoke', '--pid', str(os.getpid()), '--port', '12345', '--arm', 'off', '--out', str(output)]
        with patch.object(sys, 'argv', argv), patch.object(smoke, 'birth', side_effect=births), \
             patch.object(smoke, 'owns_listener', side_effect=ownership), \
             patch.object(smoke.urllib.request, 'urlopen', return_value=Response(tokens)):
            smoke.main()

    def test_positive_native_token_count_writes_qualification_not_full_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, 'result.jsonl')
            self.invoke(output)
            result = json.loads(output.read_text())
            self.assertEqual(result['completion_tokens'], 1)
            self.assertEqual(result['mode'], 'qualification')
            self.assertEqual(result['server_pid'], os.getpid())
            self.assertIn('not three-scout', result['scope'])

    def test_zero_or_unknown_native_tokens_never_create_progress(self):
        for tokens in (0, None, True):
            with self.subTest(tokens=tokens), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp, 'result.jsonl')
                with self.assertRaises(RuntimeError): self.invoke(output, tokens=tokens)
                self.assertFalse(output.exists())

    def test_changed_pid_birth_never_creates_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, 'result.jsonl')
            with self.assertRaises(RuntimeError): self.invoke(output, births=(100, 101))
            self.assertFalse(output.exists())

    def test_other_listener_never_creates_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, 'result.jsonl')
            with self.assertRaises(RuntimeError): self.invoke(output, ownership=(False,))
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
