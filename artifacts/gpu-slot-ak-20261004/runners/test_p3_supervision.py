import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import slot_run as seq

HERE = Path(__file__).resolve().parent


class SupervisionTests(unittest.TestCase):
    def test_parent_death_kills_captured_native_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = Path(tmp) / 'pid'
            worker_code = '''import os,subprocess,sys,time
p=subprocess.Popen([sys.executable,"-B",sys.argv[1],str(os.getpid()),sys.executable,"-c","import time;time.sleep(60)"])
open(sys.argv[2],"w").write(str(p.pid))
time.sleep(60)
'''
            worker = subprocess.Popen([sys.executable, '-B', '-c', worker_code,
                                       str(HERE / 'p3_pdeath_exec.py'), str(pidfile)])
            try:
                deadline = time.monotonic() + 5
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(pidfile.exists())
                child_pid = int(pidfile.read_text())
                # Allow the wrapper to install its handler and exec.
                time.sleep(.2)
                worker.kill()
                worker.wait(timeout=5)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        state = Path(f'/proc/{child_pid}/stat').read_text().split(') ', 1)[1][0]
                    except FileNotFoundError:
                        break
                    if state == 'Z':
                        break
                    time.sleep(.02)
                else:
                    self.fail('parent-death child remained live')
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.wait(timeout=5)

    def test_contained_timeout_checks_port_and_does_not_reap_pid_file(self):
        child = SimpleNamespace(pid=123, returncode=-signal.SIGKILL,
                                poll=lambda: None, send_signal=lambda sig: None,
                                wait=lambda timeout: (_ for _ in ()).throw(subprocess.TimeoutExpired('x', timeout))
                                if timeout == seq.TERM_GRACE_S else None)
        with patch.object(seq.subprocess, 'run') as run, patch.object(seq, 'reap_recorded_server') as reap:
            run.side_effect = [SimpleNamespace(returncode=1), SimpleNamespace(returncode=0, stdout='')]
            result = seq.stop_child(child, Path('/unused'), 18183, contained_p3=True)
        self.assertEqual(result['sent'], ['TERM', 'KILL'])
        self.assertTrue(result['verified_dead'])
        self.assertTrue(result['port_free_after'])
        reap.assert_not_called()

    def test_pair_runs_two_fake_arms_and_stops_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(results=Path(tmp), budget_min=100, p3_phase='a1')
            seq.STOP['flag'] = False
            def fake_driver(label, argv, log, hard_s, arm_dir, contained_p3):
                self.assertTrue(contained_p3)
                self.assertGreater(hard_s, 0)
                self.assertLessEqual(hard_s, 50 * 60)
                return {'rc': 0}
            run = {'items': []}
            with patch.object(seq, 'ARGS', args, create=True), patch.object(seq, 'elapsed_min', return_value=0), \
                 patch.object(seq, 'gpu_clear', return_value={'kfd_holders': {}}), \
                 patch.object(seq, 'p3_argv', return_value=['fake-driver']), \
                 patch.object(seq, 'run_child', side_effect=fake_driver) as child:
                self.assertEqual(seq.run_p3_pair(1, run, lambda: None), 0)
                self.assertEqual(child.call_count, 2)
                self.assertEqual([r['arm'] for r in run['items']], ['on', 'off'])
            run = {'items': []}
            seq.STOP['flag'] = False
            with patch.object(seq, 'ARGS', args, create=True), patch.object(seq, 'elapsed_min', return_value=0), \
                 patch.object(seq, 'gpu_clear', return_value={'kfd_holders': {}}), \
                 patch.object(seq, 'p3_argv', return_value=['fake-driver']), \
                 patch.object(seq, 'run_child', return_value={'rc': 1}) as child:
                self.assertEqual(seq.run_p3_pair(1, run, lambda: None), 1)
                self.assertEqual(child.call_count, 1)
                self.assertTrue(seq.STOP['flag'])
            seq.STOP['flag'] = False

    def test_double_lifecycle_estimate_and_timeout(self):
        self.assertEqual(seq.P3_EST, {'on': 30.0, 'off': 33.0})
        self.assertEqual(seq.P3_HARD_MIN['a1'], 50.0)

if __name__ == '__main__':
    unittest.main()
