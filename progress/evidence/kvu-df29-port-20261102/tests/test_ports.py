"""Model-free port controls; only owned loopback sockets/children, no files deleted."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

D = Path(__file__).resolve().parent
KIT = Path(os.environ.get('DF29_TEST_KIT', D / 'final/scripts/benchmark/df29'))
ATTEMPTS = []


def guard(event, args):
    if event in {'os.remove', 'os.rmdir', 'os.rename', 'sqlite3.connect'}:
        ATTEMPTS.append(event)
        raise AssertionError('forbidden lifecycle operation: ' + event)


sys.addaudithook(guard)


def load(name):
    spec = importlib.util.spec_from_file_location(name, KIT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selection = load('port_selection')
ownership = load('port_owner')


class Ports(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(ATTEMPTS, [])

    def test_busy_explicit_and_exhausted_range_refuse(self):
        with socket.socket() as busy:
            busy.bind(('127.0.0.1', 0))
            port = busy.getsockname()[1]
            with self.assertRaises(RuntimeError):
                selection.select_port(str(port))
            with self.assertRaises(RuntimeError):
                selection.select_port(first=port, last=port)
            env = dict(os.environ, DF29_PORT_FIRST=str(port), DF29_PORT_LAST=str(port))
            refused = subprocess.run(['bash', str(KIT / 'df29_server.sh'), str(D), str(D / 'unused-output'), '--select-port-only'], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(refused.returncode, 2)
            self.assertIn('reason=no-free-port', refused.stderr)
            self.assertFalse((D / 'unused-output').exists())

    def test_available_selection_and_real_launcher_preflight(self):
        # Owned sockets guarantee the occupied first choice. Other ephemeral
        # ports in the bounded range can be occupied by co-tenants; no assumptions.
        with socket.socket() as busy:
            busy.bind(('127.0.0.1', 0))
            first = busy.getsockname()[1]
            first = min(first, 65000)
            env = dict(os.environ, DF29_PORT_FIRST=str(first), DF29_PORT_LAST=str(first + 100))
            result = subprocess.run(['bash', str(KIT / 'df29_server.sh'), str(D), str(D / 'unused-output'), '--select-port-only'], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            chosen = int(result.stdout)
            self.assertTrue(first <= chosen <= first + 100)
            self.assertNotEqual(chosen, busy.getsockname()[1])
            self.assertFalse((D / 'unused-output').exists())

    def test_invalid_options_refuse(self):
        for port in ['0', '65536', 'text', '-1']:
            with self.subTest(port=port), self.assertRaises(ValueError):
                selection.select_port(port)
        with self.assertRaises(ValueError):
            selection.select_port(first=1024, last=65535)

    def test_live_owned_listener_and_foreign_listener_refusal(self):
        # No model, server binary, GPU, files or external requests: this child
        # owns a bare TCP listener until its stdin is closed by this parent.
        code = 'import socket,sys; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); print(s.getsockname()[1],flush=True); sys.stdin.read()'
        child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            port = int(child.stdout.readline())
            birth = ownership.start_time(child.pid)
            self.assertTrue(ownership.listener_owned(child.pid, port, birth))
            with self.assertRaises(ownership.OwnershipError):
                ownership.listener_owned(os.getpid(), port, ownership.start_time(os.getpid()))
            with self.assertRaises(ownership.OwnershipError):
                ownership.listener_owned(child.pid, port, str(int(birth) + 1))
        finally:
            child.stdin.close()
            child.wait(timeout=5)
            child.stdout.close()
            self.assertIsNotNone(child.returncode)
            self.assertFalse(Path('/proc', str(child.pid)).exists())

    def test_actual_shell_health_rejects_foreign_http_listener(self):
        code = 'import socket, sys, threading\ns = socket.socket()\ns.bind(("127.0.0.1", 0))\ns.listen()\ndef serve():\n    while True:\n        c, _ = s.accept()\n        c.recv(4096)\n        c.sendall(b"HTTP/1.0 200 OK\\r\\nContent-Length: 2\\r\\n\\r\\nOK")\n        c.close()\nthreading.Thread(target=serve, daemon=True).start()\nprint(s.getsockname()[1], flush=True)\nsys.stdin.read()\n'
        child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            port = int(child.stdout.readline())
            common = ['bash', '-c',
                      'source "$1"; DF29_SERVER_PID=$2; DF29_SERVER_START_TIME=$3; df29_wait_health "$4" "$5"',
                      'df29-test', str(KIT / 'df29_lib.sh')]
            owned = subprocess.run([*common, str(child.pid), ownership.start_time(child.pid), str(port), str(int(time.time()) + 10)], capture_output=True, text=True, timeout=15)
            self.assertEqual(owned.returncode, 0, owned.stderr)
            # Same reachable HTTP200 listener, unrelated captured PID: fail closed.
            foreign = subprocess.run([*common, str(os.getpid()), ownership.start_time(os.getpid()), str(port), str(int(time.time()) + 10)], capture_output=True, text=True, timeout=15)
            self.assertEqual(foreign.returncode, 3, foreign.stderr)
            self.assertIn('not owned', foreign.stderr)
        finally:
            child.stdin.close()
            child.wait(timeout=5)
            child.stdout.close()
            self.assertFalse(Path('/proc', str(child.pid)).exists())

    def test_missing_process_refuses(self):
        with self.assertRaises(OSError):
            ownership.listener_owned(2 ** 30, 18093, '1')


if __name__ == '__main__':
    unittest.main()
