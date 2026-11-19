"""Real Linux cleanup controls; no model, server, GPU or entry admission."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'kpf18-g3-owned-drain-20261104/owned_drain.py'
PIN = '6cf1d4159ee768b762ba76f911cab16b675a4b115b1fff34cf6c3e35aa461ec4'


def supervisor(mode):
    import importlib.util
    spec = importlib.util.spec_from_file_location('owned_drain', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if helper.children():
        raise RuntimeError('preexisting children')
    helper.enable()
    rd, wr = os.pipe()
    parent = os.fork()
    if parent == 0:
        os.close(rd)
        if mode == 'adopted':
            grandchild = os.fork()
            if grandchild:
                os._exit(0)
        signal.signal(signal.SIGTERM, signal.SIG_IGN if mode == 'kill' else signal.SIG_DFL)
        os.write(wr, (str(os.getpid()) + '\n').encode())
        os.close(wr)
        while True:
            signal.pause()
    os.close(wr)
    with os.fdopen(rd) as stream:
        target = int(stream.readline())
    if mode == 'adopted':
        os.waitpid(parent, 0)
    if target not in helper.children():
        raise RuntimeError('target was not adopted')
    print(json.dumps({'pids': [target], 'mode': mode}), flush=True)
    helper.drain()
    if helper.children() or Path('/proc', str(target)).exists():
        raise RuntimeError('cleanup returned before reap')
    print(json.dumps({'status': 'PASS', 'reaped': target}), flush=True)


class LiveDrain(unittest.TestCase):
    def run_case(self, mode):
        self.assertEqual(hashlib.sha256(HELPER.read_bytes()).hexdigest(), PIN)
        proc = subprocess.Popen([sys.executable, '-B', __file__, mode],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pidfds = []
        try:
            # Bound startup as well as drain; stdout is never used as a polling loop.
            import select
            self.assertTrue(select.select([proc.stdout], [], [], 5)[0], 'startup timeout')
            first = json.loads(proc.stdout.readline())
            for pid in first['pids']:
                try:
                    pidfds.append(os.pidfd_open(pid))
                except ProcessLookupError:
                    pass  # A TERM-responsive child may already have been reaped.
            out, err = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 0, err)
            if mode == 'kill':
                self.assertIn('waiting for owned child to drain:', out)
            records = [json.loads(line) for line in out.splitlines() if line.startswith('{')]
            self.assertEqual(records[-1], {'status': 'PASS', 'reaped': first['pids'][0]})
            for pid in first['pids']:
                self.assertFalse(Path('/proc', str(pid)).exists())
        finally:
            # Signal only captured pidfds and this test's Popen child.
            for fd in pidfds:
                try:
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    os.close(fd)
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)

    def test_term_and_reap(self):
        self.run_case('term')

    def test_term_ignored_escalates_and_reaps(self):
        self.run_case('kill')

    def test_orphan_grandchild_adopted_and_reaped(self):
        self.run_case('adopted')


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] in {'term', 'kill', 'adopted'}:
        supervisor(sys.argv[1])
    else:
        unittest.main()
