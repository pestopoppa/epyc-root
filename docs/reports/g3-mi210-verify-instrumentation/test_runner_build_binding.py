import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from diagnostic_runner import resolve_build_binding


class RunnerBuildBindingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = self.root / 'build/bin/llama-server'
        self.backend = self.root / 'build/bin/libggml-hip.so'
        self.server.parent.mkdir(parents=True)
        self.server.write_bytes(b'server')
        self.backend.write_bytes(b'backend')
        self.result = self.root / 'RESULT.json'
        self.result.write_text(json.dumps({'native': 'result'}))
        self.bound = {'status': 'BUILD_BOUND', 'artifacts': {
            'server': {'path': str(self.server.resolve())},
            'hip': {'path': str(self.backend.resolve()), 'sha256': 'a' * 64}}}
        self.config = {'build_result': str(self.result), 'build_root': str(self.root),
                       'server': str(self.server), 'backend': str(self.backend), 'backend_sha256': 'a' * 64}

    def tearDown(self): self.temp.cleanup()

    def test_uses_full_result_and_bound_artifacts(self):
        with patch('diagnostic_runner.bind_v4_receipt', return_value=self.bound) as bind:
            bound, server, backend, build = resolve_build_binding(self.config)
        bind.assert_called_once_with({'native': 'result'}, str(self.root))
        self.assertEqual((bound, server, backend, build), (self.bound, self.server, self.backend, self.root / 'build'))
        self.assertFalse((self.root / 'BUILD_COMPLETE').exists())

    def test_wrong_server_refused(self):
        other = self.root / 'other-server'
        other.write_bytes(b'wrong')
        self.config['server'] = str(other)
        with patch('diagnostic_runner.bind_v4_receipt', return_value=self.bound), self.assertRaises(ValueError):
            resolve_build_binding(self.config)

    def test_wrong_backend_refused(self):
        other = self.root / 'other-backend'
        other.write_bytes(b'wrong')
        self.config['backend'] = str(other)
        with patch('diagnostic_runner.bind_v4_receipt', return_value=self.bound), self.assertRaises(ValueError):
            resolve_build_binding(self.config)

    def test_wrong_backend_digest_refused(self):
        self.config['backend_sha256'] = 'b' * 64
        with patch('diagnostic_runner.bind_v4_receipt', return_value=self.bound), self.assertRaises(ValueError):
            resolve_build_binding(self.config)

    def test_missing_result_refused(self):
        self.result.unlink()
        with self.assertRaises(OSError): resolve_build_binding(self.config)


if __name__ == '__main__': unittest.main()
