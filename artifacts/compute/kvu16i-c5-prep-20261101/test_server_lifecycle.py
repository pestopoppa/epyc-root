from pathlib import Path
import subprocess
import tempfile
import unittest
from server_lifecycle import Server

class FakeProc:
    pid=1234
    def __init__(self): self.returncode=None;self.signals=[]
    def poll(self): return self.returncode
    def terminate(self): self.signals.append('TERM');self.returncode=0
    def kill(self): self.signals.append('KILL');self.returncode=-9
    def wait(self,timeout=None): return self.returncode

class LifecycleTests(unittest.TestCase):
    def test_child_stays_in_engine_group_and_is_reaped(self):
        with tempfile.TemporaryDirectory() as td:
            p=FakeProc(); captured={}
            def factory(cmd,**kwargs): captured.update(kwargs);return p
            s=Server(['fixture'],{},Path(td)/'log',Path(td)/'pids',factory=factory,birth_reader=lambda _:42)
            self.assertEqual(s.start(),(1234,42));self.assertIs(captured['start_new_session'],False)
            self.assertEqual((Path(td)/'pids').read_text(),'1234\n')
            self.assertTrue(s.close()['verified_dead']);self.assertEqual(p.signals,['TERM'])
    def test_identity_change_refuses_to_signal(self):
        with tempfile.TemporaryDirectory() as td:
            p=FakeProc();n=[]
            def birth(_):n.append(1);return 42 if len(n)==1 else 43
            s=Server(['fixture'],{},Path(td)/'log',Path(td)/'pids',factory=lambda *a,**k:p,birth_reader=birth)
            s.start()
            with self.assertRaises(RuntimeError):s.close()
            self.assertEqual(p.signals,[])
    def test_exited_child_never_signalled(self):
        with tempfile.TemporaryDirectory() as td:
            p=FakeProc();s=Server(['fixture'],{},Path(td)/'log',Path(td)/'pids',factory=lambda *a,**k:p,birth_reader=lambda _:42)
            s.start();p.returncode=0;self.assertTrue(s.close()['verified_dead']);self.assertEqual(p.signals,[])
if __name__=='__main__':unittest.main()
