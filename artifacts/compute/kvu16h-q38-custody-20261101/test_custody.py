import subprocess
import signal
import errno
import unittest
from custody import Custodian, CustodyError


class FakeProcess:
    def __init__(self):
        self.pid = 123
        self.alive = True
        self.signals = []
        self.timeout_once = False
    def poll(self): return None if self.alive else 0
    def terminate(self):
        self.signals.append('term')
        if not self.timeout_once: self.alive = False
    def kill(self): self.signals.append('kill'); self.alive = False
    def wait(self, timeout):
        if self.alive: raise subprocess.TimeoutExpired('fake', timeout)
        return 0


def make(p, birth):
    def send(fd, sig):
        if sig == signal.SIGTERM: p.terminate()
        elif sig == signal.SIGKILL: p.kill()
    return Custodian(lambda *a, **k: p, birth, lambda pid: 99, send, lambda fd: None, lambda: 41)


class Tests(unittest.TestCase):
    def test_ready_failure_drains_unreturned_child(self):
        p=FakeProcess(); c=make(p, lambda pid: 'birth')
        with self.assertRaisesRegex(ValueError, 'ready'):
            c.start(['server'], lambda h: (_ for _ in ()).throw(ValueError('ready')))
        self.assertEqual(p.signals, ['term']); self.assertIsNotNone(p.poll())

    def test_birth_failure_still_drains(self):
        p=FakeProcess(); c=make(p, lambda pid: (_ for _ in ()).throw(OSError('gone')))
        with self.assertRaises(OSError): c.start(['server'], lambda h: None)
        self.assertEqual(p.signals, ['term'])

    def test_identity_change_refuses_signal(self):
        p=FakeProcess(); current=['a']; c=make(p, lambda pid:current[0])
        h=c.start(['server'],lambda h:None); current[0]='b'
        self.assertFalse(c.stop(h)); self.assertEqual(p.signals,[])

    def test_escalate_only_captured_child(self):
        p=FakeProcess(); p.timeout_once=True
        c=make(p, lambda pid:'a'); h=c.start(['server'],lambda h:None)
        self.assertTrue(c.stop(h)); self.assertEqual(p.signals,['term','kill'])

    def test_reject_shell_before_spawn(self):
        spawned=[]; c=Custodian(lambda *a, **k:spawned.append(1), lambda pid:'a')
        with self.assertRaises(CustodyError): c.start(['server'],lambda h:None,shell=True)
        self.assertEqual(spawned,[])

    def test_emfile_reserve_releases_and_start_failure_drains(self):
        p=FakeProcess(); closed=[]; calls=[]
        def open_pidfd(pid):
            calls.append(pid)
            if len(calls)==1: raise OSError(errno.EMFILE, 'full')
            return 99
        def send(fd, sig):
            if sig==signal.SIGTERM: p.terminate()
        c=Custodian(lambda *a, **k:p, lambda pid:'a', open_pidfd, send, closed.append, lambda:41)
        with self.assertRaisesRegex(ValueError, 'ready'):
            c.start(['server'], lambda h: (_ for _ in ()).throw(ValueError('ready')))
        self.assertEqual(calls,[123,123]); self.assertEqual(closed,[41,99])
        self.assertEqual(p.signals,['term']); self.assertIsNotNone(p.poll())

    def test_interrupted_pidfd_retry(self):
        p=FakeProcess(); calls=[]; closed=[]
        def open_pidfd(pid):
            calls.append(pid)
            if len(calls)==1: raise OSError(errno.EINTR, 'interrupted')
            return 99
        c=Custodian(lambda *a, **k:p, lambda pid:'a', open_pidfd, lambda fd,sig:None, closed.append, lambda:41)
        h=c.start(['server'],lambda h:None)
        self.assertEqual(h.pidfd,99); self.assertEqual(closed,[41]); self.assertEqual(len(calls),2)

    def test_unrecoverable_pidfd_failure_is_unverified_and_never_pid_signals(self):
        p=FakeProcess(); closed=[]
        def fail(pid): raise OSError(errno.ENOSYS, 'unsupported')
        c=Custodian(lambda *a, **k:p, lambda pid:'a', fail, lambda fd,sig:None, closed.append, lambda:41)
        with self.assertRaisesRegex(CustodyError, 'cleanup unverified'):
            c.start(['server'],lambda h:None)
        self.assertEqual(p.signals,[]); self.assertEqual(closed,[41]); self.assertTrue(p.alive)

if __name__ == '__main__': unittest.main()
