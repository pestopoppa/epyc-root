import subprocess
import unittest
from server_lifecycle import LifecycleError, with_server


class FakeProcess:
    def __init__(self, *, deadline=False, refuses_kill=False, pid=123):
        self.pid = pid; self.rc = None; self.deadline = deadline
        self.refuses_kill = refuses_kill; self.calls = []
    def poll(self): return self.rc
    def terminate(self):
        self.calls.append('terminate')
        if not self.deadline: self.rc = 0
    def kill(self):
        self.calls.append('kill')
        if not self.refuses_kill: self.rc = -9
    def wait(self, timeout):
        self.calls.append('wait')
        if self.rc is None: raise subprocess.TimeoutExpired('fake', timeout)
        return self.rc


def execute(p, *, admission=lambda: True, verify=lambda p, arm: {'ready': True}, run=lambda s: s.pid):
    return with_server(arm='mtp3', admission_check=admission, spawn=lambda arm: p,
                       verify_ready_and_identity=verify, run=run)


class LifecycleTests(unittest.TestCase):
    def test_success_drains(self):
        p = FakeProcess(); self.assertEqual(execute(p), 123)
        self.assertEqual(p.calls, ['terminate', 'wait'])
    def test_denied_before_spawn(self):
        calls = []
        with self.assertRaises(LifecycleError):
            with_server(arm='mtp3', admission_check=lambda: False, spawn=lambda a: calls.append(a),
                        verify_ready_and_identity=lambda *a: {}, run=lambda s: None)
        self.assertEqual(calls, [])
    def test_verification_fails_closed_and_drains(self):
        p = FakeProcess(); invoked = []
        with self.assertRaises(LifecycleError):
            execute(p, verify=lambda *a: {}, run=lambda s: invoked.append(s))
        self.assertEqual(invoked, []); self.assertEqual(p.calls, ['terminate', 'wait'])
    def test_callback_exception_still_drains(self):
        p = FakeProcess()
        def fail(_): raise ValueError('request failed')
        with self.assertRaises(ValueError): execute(p, run=fail)
        self.assertEqual(p.calls, ['terminate', 'wait'])
    def test_escalation_uses_captured_handle(self):
        p = FakeProcess(deadline=True); execute(p)
        self.assertEqual(p.calls, ['terminate', 'wait', 'kill', 'wait'])
    def test_unverified_drain_fails(self):
        p = FakeProcess(deadline=True, refuses_kill=True)
        with self.assertRaises(LifecycleError): execute(p)
    def test_invalid_pid_still_drains(self):
        p = FakeProcess(pid=0)
        with self.assertRaises(LifecycleError): execute(p)
        self.assertEqual(p.calls, ['terminate', 'wait'])
    def test_already_exited_refuses_work(self):
        p = FakeProcess(); p.rc = 3
        with self.assertRaises(LifecycleError): execute(p)
        self.assertEqual(p.calls, ['wait'])


if __name__ == '__main__': unittest.main()
