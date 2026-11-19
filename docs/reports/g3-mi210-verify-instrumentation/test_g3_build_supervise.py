"""Synthetic-only STOP and process-tree tests; no build or inference."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SUP = Path(__file__).with_name('g3_build_supervise.py')


def wait_file(path, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.exists():
            return
        time.sleep(.01)
    raise AssertionError(f'marker missing: {path}')


class SupervisorTest(unittest.TestCase):
    def launch(self, stop, code, *args, deadline=None):
        return subprocess.Popen([sys.executable, str(SUP), str(stop),
                                 str(deadline or int(time.time()) + 30),
                                 sys.executable, '-c', code, *map(str, args)])

    def test_preexisting_stop_and_expired_deadline_do_not_spawn(self):
        with tempfile.TemporaryDirectory() as d:
            stop, marker = Path(d)/'stop', Path(d)/'marker'
            code = 'from pathlib import Path; import sys; Path(sys.argv[1]).touch()'
            stop.touch()
            self.assertEqual(self.launch(stop, code, marker).wait(timeout=5), 75)
            stop.unlink()
            self.assertEqual(self.launch(stop, code, marker, deadline=int(time.time())-1).wait(timeout=5), 75)
            self.assertFalse(marker.exists())

    def test_stop_drains_term_resistant_child_and_grandchild(self):
        with tempfile.TemporaryDirectory() as d:
            stop, marker = Path(d)/'stop', Path(d)/'marker'
            grandchild = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
            code = '''import os,signal,subprocess,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
p = subprocess.Popen([sys.executable, '-c', sys.argv[2]])
Path(sys.argv[1]).write_text(f'{os.getpid()} {p.pid}')
time.sleep(30)
'''
            proc = self.launch(stop, code, marker, grandchild)
            try:
                wait_file(marker)
                pids = [int(x) for x in marker.read_text().split()]
                stop.touch()
                self.assertEqual(proc.wait(timeout=8), 75)
                for pid in pids:
                    self.assertFalse(Path(f'/proc/{pid}').exists(), f'{pid} survived drain')
            finally:
                if proc.poll() is None:
                    proc.send_signal(signal.SIGTERM)
                    proc.wait(timeout=8)

    def test_successful_parent_with_orphan_cannot_complete(self):
        with tempfile.TemporaryDirectory() as d:
            stop, marker = Path(d)/'stop', Path(d)/'marker'
            code = '''import subprocess,sys
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
Path(sys.argv[1]).write_text(str(p.pid))
'''
            proc = self.launch(stop, code, marker)
            wait_file(marker)
            pid = int(marker.read_text())
            self.assertEqual(proc.wait(timeout=8), 75)
            self.assertFalse(Path(f'/proc/{pid}').exists())

    def test_success_and_failure_return_codes(self):
        with tempfile.TemporaryDirectory() as d:
            stop = Path(d)/'stop'
            for status in (0, 7):
                self.assertEqual(self.launch(stop, 'import sys; sys.exit(int(sys.argv[1]))', status).wait(timeout=5), status)


if __name__ == '__main__':
    unittest.main()
