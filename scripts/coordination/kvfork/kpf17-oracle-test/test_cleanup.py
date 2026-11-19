"""Exercise PID reuse, TERM/KILL escalation, and failed verification."""
import signal
import unittest
from cleanup import cleanup
from gdb_job import apply_cleanup


class Fake:
    def __init__(self):self.birth=42;self.now=0;self.sent=[];self.ps_absent=True;self.after_term=None;self.after_kill=None
    def identity(self,pid):return self.birth
    def signal(self,fd,sig):
        self.sent.append(sig)
        if sig==signal.SIGTERM and self.after_term is not None:self.birth=self.after_term
        if sig==signal.SIGKILL and self.after_kill is not None:self.birth=self.after_kill
    def sleep(self,n):self.now+=n
    def run(self):
        return cleanup(123,42,timeout_s=.2,clock=lambda:self.now,sleep=self.sleep,
                       read_identity=self.identity,verify_absent=lambda _:self.ps_absent,
                       open_pidfd=lambda *_:7,send_signal=self.signal,close_fd=lambda _:None)


class CleanupTest(unittest.TestCase):
    def test_cleanup_exception_is_invalid_and_never_claims_death(self):
        def broken(_pid,_birth):raise OSError('ps unavailable')
        verdict={'status':'PASS'}
        result=apply_cleanup(verdict,{'pid':123,'birth_ticks':42},False,broken)
        self.assertEqual(verdict['status'],'INVALID')
        self.assertFalse(result['verified_dead'])
        self.assertIsNone(result['signals'])
        self.assertIn('OSError: ps unavailable',result['reason'])
    def test_already_gone_requires_ps_confirmation(self):
        f=Fake();f.birth=None;self.assertTrue(f.run()['verified_dead']);self.assertEqual(f.sent,[])
        f.ps_absent=False;self.assertFalse(f.run()['verified_dead'])
    def test_term_then_kill_and_verify(self):
        f=Fake()
        def send(fd,sig):
            f.sent.append(sig)
            if sig==signal.SIGKILL:f.birth=None
        f.signal=send;r=f.run()
        self.assertTrue(r['verified_dead']);self.assertEqual(f.sent,[signal.SIGTERM,signal.SIGKILL])
    def test_reused_pid_is_never_signalled(self):
        f=Fake();f.birth=99;r=f.run();self.assertFalse(r['verified_dead']);self.assertEqual(f.sent,[])
    def test_reuse_after_term_stops_escalation(self):
        f=Fake();f.after_term=99;r=f.run();self.assertFalse(r['verified_dead']);self.assertEqual(f.sent,[signal.SIGTERM])
    def test_unverified_live_process_remains_invalid(self):
        f=Fake();r=f.run();self.assertFalse(r['verified_dead']);self.assertEqual(f.sent,[signal.SIGTERM,signal.SIGKILL])

if __name__=='__main__':unittest.main()
