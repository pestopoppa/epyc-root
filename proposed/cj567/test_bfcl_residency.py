"""Real Linux proc/socket/mmap controls, using a tiny local HTTP fixture, no model."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bfcl_capture_run import capture_case
from bfcl_residency import LocalNativeTransport, file_sha256
from bfcl_prepare_model import prepare_model

SERVER = '''
import http.server, json, mmap, sys
source = open(sys.argv[sys.argv.index('--model') + 1], 'rb')
mapping = mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ)
class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if data.get('redirect'):
            self.send_response(307)
            self.send_header('Location', 'http://127.0.0.1:1/unbound')
            self.end_headers()
            return
        body = json.dumps({'model': data['model'], 'choices': []}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args): pass
server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
'''


class ResidencyControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / 'fixture.gguf'
        self.model.write_bytes(b'not model weights; residency fixture\n')
        self.prepared = prepare_model(self.model)
        # Pass a reserved socket to the child to avoid port allocation races.
        import socket
        reserve = socket.socket()
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
        server = SERVER.replace("server = http.server.HTTPServer(('127.0.0.1', 0), Handler)",
            "import socket\nserver = http.server.HTTPServer(('127.0.0.1', 0), Handler, bind_and_activate=False)\n"
            "server.socket.close()\nserver.socket = socket.socket(fileno=" + str(reserve.fileno()) + ")\n"
            "server.server_port = server.socket.getsockname()[1]\nserver.server_address = server.socket.getsockname()\nserver.socket.listen()")
        argv = [sys.executable, '-c', server, '--model', str(self.model),
                '--alias', 'fixture', '--host', '127.0.0.1', '--port', str(port), '--n-gpu-layers', '0']
        try:
            self.child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          pass_fds=(reserve.fileno(),), text=True)
        finally:
            reserve.close()
        self.addCleanup(self.stop)
        readable, _, _ = select.select([self.child.stdout], [], [], 10)
        self.assertTrue(readable, 'fixture startup timed out')
        self.port = int(self.child.stdout.readline())
        self.build = self.root / 'build.json'
        self.runtime = self.root / 'runtime.json'
        binary_sha = file_sha256('/proc/' + str(self.child.pid) + '/exe')
        self.build.write_text(json.dumps({'server_binary_sha256': binary_sha, 'libraries': []}))
        self.runtime.write_text(json.dumps({'model': 'fixture', 'model_file': self.prepared, 'argv': argv}))
        self.identity = {'model': 'fixture', 'model_sha256': self.prepared['sha256'],
            'server_binary_sha256': binary_sha, 'build_manifest_sha256': file_sha256(self.build),
            'runtime_manifest_sha256': file_sha256(self.runtime)}

    def stop(self):
        if self.child.poll() is None:
            self.child.terminate()
            try:
                self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=5)
        self.assertIsNotNone(self.child.returncode)
        self.child.stdout.close()
        self.child.stderr.close()

    def transport(self, **kw):
        return LocalNativeTransport(kw.pop('pid', self.child.pid), kw.pop('port', self.port),
            kw.pop('identity', self.identity), self.build, self.runtime, **kw)

    def rewrite(self, path, value, field):
        path.write_text(json.dumps(value))
        self.identity[field] = file_sha256(path)

    def test_real_listener_mmap_exe_and_http_without_runtime_weight_hash(self):
        with patch('bfcl_prepare_model.prepare_model', side_effect=AssertionError('runtime preparation')):
            transport = self.transport()
            proof = transport.probe()
            self.assertEqual(proof['pid'], self.child.pid)
            self.assertEqual(proof['model_sha256'], self.prepared['sha256'])
            self.assertEqual(transport({'model': 'fixture'})['model'], 'fixture')
        with self.assertRaisesRegex(ValueError, 'request model'):
            transport({'model': 'other'})

    def test_wrong_listener_or_pid_refuses(self):
        transport = self.transport()
        transport.port = 1
        with self.assertRaisesRegex(ValueError, 'listener not owned'):
            transport.probe()
        with self.assertRaises(ValueError):
            self.transport(port=1)
        runtime = json.loads(self.runtime.read_text())
        runtime['argv'] = self.child.args.copy()
        runtime['argv'][runtime['argv'].index('--port') + 1] = '1'
        self.rewrite(self.runtime, runtime, 'runtime_manifest_sha256')
        with self.assertRaisesRegex(ValueError, 'argv changed'):
            self.transport(port=1)
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.transport(pid=os.getpid())

    def test_manifest_tamper_and_binary_content_refuse(self):
        self.build.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'manifest digest'):
            self.transport()
        self.identity['server_binary_sha256'] = 'a' * 64
        self.rewrite(self.build, {'server_binary_sha256': 'a' * 64, 'libraries': []}, 'build_manifest_sha256')
        with self.assertRaisesRegex(ValueError, 'content mismatch'):
            self.transport()

    def test_model_mutation_or_replacement_refuses_even_same_size(self):
        transport = self.transport()
        raw = self.model.read_bytes()
        self.model.write_bytes(b'X' * len(raw))
        with self.assertRaisesRegex(ValueError, 'model replaced or mutated'):
            transport.probe()
        self.model.write_bytes(raw)
        replacement = self.root / 'replacement'
        replacement.write_bytes(self.model.read_bytes())
        replacement.replace(self.model)
        with self.assertRaisesRegex(ValueError, 'model replaced or mutated'):
            transport.probe()

    def test_unmapped_prepared_model_refuses(self):
        other = self.root / 'other.gguf'
        other.write_bytes(self.model.read_bytes())
        runtime = json.loads(self.runtime.read_text())
        runtime['model_file'] = prepare_model(other)
        transport = self.transport()
        transport.model = runtime['model_file']
        with self.assertRaisesRegex(ValueError, 'not mapped'):
            transport.probe()
        # Keep declared --model unchanged: path check must fail before exposure.
        self.rewrite(self.runtime, runtime, 'runtime_manifest_sha256')
        with self.assertRaisesRegex(ValueError, 'argument required'):
            self.transport()
        # A matching path with a forged mapped-inode assertion also refuses.
        runtime['model_file']['path'] = str(self.model)
        self.rewrite(self.runtime, runtime, 'runtime_manifest_sha256')
        with self.assertRaisesRegex(ValueError, 'model replaced or mutated'):
            self.transport()

    def test_redirect_refuses_and_pid_restart_refuses(self):
        transport = self.transport()
        with self.assertRaisesRegex(ValueError, 'redirect refused'):
            transport({'model': 'fixture', 'redirect': True})
        transport.start_ticks = 'wrong-generation'
        with self.assertRaisesRegex(ValueError, 'PID reused'):
            transport.probe()

    def test_unmapped_library_refuses(self):
        extra = self.root / 'unmapped.so'
        extra.write_bytes(b'not a library')
        build = json.loads(self.build.read_text())
        build['libraries'] = [{'path': str(extra), 'sha256': file_sha256(extra)}]
        self.rewrite(self.build, build, 'build_manifest_sha256')
        with self.assertRaisesRegex(ValueError, 'not mapped'):
            self.transport()

    def test_live_capture_refuses_plain_unbound_callable_before_inputs(self):
        with self.assertRaisesRegex(ValueError, 'requires bound local residency'):
            capture_case(None, {}, 'fixture', self.identity, self.root,
                         self.root / 'capture', lambda p: self.fail('exposure'))
        self.assertFalse((self.root / 'capture').exists())


if __name__ == '__main__':
    unittest.main()
