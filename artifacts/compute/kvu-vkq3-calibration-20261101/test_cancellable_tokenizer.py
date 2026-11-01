import subprocess
import os
import sys
import unittest
import cancellable_tokenizer as c


class Fake:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.returncode = None
        self.terminated = False
        self.inputs = []

    def communicate(self, input=None, timeout=None):
        self.inputs.append(input)
        outcome = self.outcomes.pop(0)
        if outcome == 'timeout':
            raise subprocess.TimeoutExpired('fake', timeout)
        self.returncode = 0
        return outcome, b''

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.returncode = -15
        return self.returncode

    def kill(self):
        raise AssertionError('fake should not need force')


class Tests(unittest.TestCase):
    def test_benign_real_child_returns_without_signalling(self):
        cmd = [sys.executable, '-B', 'pdeath_exec.py', str(os.getpid()), sys.executable, '-B', '-c', 'print("[1, 2]")']
        got = c.run(cmd, b'', dict(os.environ), lambda: False, 5)
        self.assertEqual(got.strip(), b'[1, 2]')

    def test_output_and_retry_input_only_once(self):
        proc = Fake(['timeout', b'[1,2]'])
        got = c.run(['fake'], b'prompt', {}, lambda: False, 5, popen=lambda *a, **kw: proc)
        self.assertEqual(got, b'[1,2]')
        self.assertEqual(proc.inputs, [b'prompt', None])
        self.assertFalse(proc.terminated)

    def test_stop_during_wait_terminates_captured_fake(self):
        proc = Fake(['timeout'])
        checks = iter([False, False, True])
        with self.assertRaises(c.Stopped):
            c.run(['fake'], b'prompt', {}, lambda: next(checks), 5, popen=lambda *a, **kw: proc)
        self.assertTrue(proc.terminated)
        self.assertEqual(proc.returncode, -15)

    def test_preexisting_stop_does_not_spawn(self):
        def should_not_spawn(*args, **kwargs):
            raise AssertionError('spawned under STOP')
        with self.assertRaises(c.Stopped):
            c.run(['fake'], b'prompt', {}, lambda: True, 5, popen=should_not_spawn)

    def test_timeout_terminates_captured_fake(self):
        proc = Fake([])
        clock = iter([0, 5])
        with self.assertRaises(TimeoutError):
            c.run(['fake'], b'prompt', {}, lambda: False, 5, popen=lambda *a, **kw: proc, clock=lambda: next(clock))
        self.assertTrue(proc.terminated)


if __name__ == '__main__':
    unittest.main()
