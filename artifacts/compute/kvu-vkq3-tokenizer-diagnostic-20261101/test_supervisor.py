import os
import sys
import unittest
from unittest import mock
import subprocess
from supervisor import supervise


class SupervisorTest(unittest.TestCase):
    def run_child(self, code, **kw):
        return supervise([sys.executable, '-c', code], b'input', os.environ.copy(),
                         stopped=kw.pop('stopped', lambda: False), timeout_s=kw.pop('timeout_s', 2), **kw)

    def test_success_and_pipes(self):
        r = self.run_child('import sys; d=sys.stdin.buffer.read(); sys.stdout.buffer.write(d); sys.stderr.write("ok")')
        self.assertEqual((r['status'],r['stdout'],r['stderr'],r['returncode']), ('completed',b'input',b'ok',0))
        self.assertTrue(r['cleanup'])
        self.assertEqual(r['input_bytes_written'], 5)

    def test_nonzero(self):
        self.assertEqual(self.run_child('raise SystemExit(3)')['status'], 'nonzero_exit')

    def test_timeout_reaps(self):
        r = self.run_child('import time; time.sleep(5)', timeout_s=.15)
        self.assertEqual(r['status'], 'timeout'); self.assertTrue(r['cleanup'])

    def test_pre_cancel(self):
        r = self.run_child('raise SystemExit(0)', stopped=lambda: True)
        self.assertEqual(r['status'], 'cancelled'); self.assertIsNone(r['returncode'])

    def test_mid_cancel_reaps(self):
        import time
        end=time.monotonic()+.12
        r=self.run_child('import time; time.sleep(5)', stopped=lambda: time.monotonic() >= end)
        self.assertEqual(r['status'], 'cancelled'); self.assertTrue(r['cleanup'])

    def test_stdout_overflow(self):
        r=self.run_child('import sys; sys.stdout.write("x"*100000);sys.stdout.flush()', stdout_cap=100)
        self.assertEqual(r['status'], 'output_overflow'); self.assertLessEqual(len(r['stdout']),100); self.assertTrue(r['cleanup'])

    def test_stderr_overflow(self):
        r=self.run_child('import sys; sys.stderr.write("x"*100000);sys.stderr.flush()', stderr_cap=100)
        self.assertEqual(r['status'], 'output_overflow'); self.assertLessEqual(len(r['stderr']),100); self.assertTrue(r['cleanup'])

    def test_child_closes_stdin(self):
        r=supervise([sys.executable,'-c','import os;os.close(0)'], b'x'*1000000, os.environ.copy(), stopped=lambda:False, timeout_s=2)
        self.assertTrue(r['cleanup']); self.assertEqual(r['status'],'input_incomplete')
        self.assertLess(r['input_bytes_written'], 1000000)

    def test_selector_failure_reaps_spawned_child(self):
        spawned = []
        real_popen = subprocess.Popen
        def capture(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            spawned.append(child)
            return child
        with mock.patch('supervisor.subprocess.Popen', side_effect=capture), \
             mock.patch('supervisor.selectors.DefaultSelector', side_effect=OSError('selector failed')):
            with self.assertRaisesRegex(OSError, 'selector failed'):
                self.run_child('import time; time.sleep(5)')
        self.assertIsNotNone(spawned[0].poll())

    def test_exit_during_terminate_still_reaps(self):
        spawned = []
        real_popen = subprocess.Popen
        def capture(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            spawned.append(child)
            real_terminate = child.terminate
            def exit_then_raise():
                real_terminate()
                raise ProcessLookupError('simulated exit race')
            child.terminate = exit_then_raise
            return child
        with mock.patch('supervisor.subprocess.Popen', side_effect=capture):
            r = self.run_child('import time; time.sleep(5)', timeout_s=.15)
        self.assertEqual(r['status'], 'timeout')
        self.assertTrue(r['cleanup'])
        self.assertIsNotNone(spawned[0].returncode)

if __name__ == '__main__': unittest.main()
