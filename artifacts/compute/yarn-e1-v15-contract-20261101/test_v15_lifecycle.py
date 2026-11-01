import tempfile
import unittest
from pathlib import Path
from v15_lifecycle import drive, STEPS

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.stop=Path(self.tmp.name)/'stop'; self.done=set(); self.calls=[]
    def complete(self, s): return s in self.done
    def execute(self, *s): self.calls.append(s); self.done.add(s); return 0
    def go(self, run=None, **kw):
        return drive(run or self.execute, self.complete, self.stop, 1000, now=lambda:0, **kw)
    def test_dryrun_one(self):
        self.assertEqual(self.go(dryrun=True),75); self.assertEqual(self.calls,[STEPS[0]])
    def test_full(self):
        self.assertEqual(self.go(),0); self.assertEqual(self.calls,list(STEPS))
    def test_resume(self):
        self.done.add(STEPS[0]); self.assertEqual(self.go(dryrun=True),75); self.assertEqual(self.calls,[STEPS[1]])
    def test_stop_before(self):
        self.stop.touch(); self.assertEqual(self.go(),75); self.assertEqual(self.calls,[])
    def test_stop_between(self):
        def run(*s): self.done.add(s); self.stop.touch(); self.calls.append(s); return 0
        self.assertEqual(self.go(run=run),75); self.assertEqual(self.calls,[STEPS[0]])
    def test_failure_is_not_completion(self):
        self.assertEqual(self.go(run=lambda *s:72),72); self.assertFalse(self.done)
    def test_false_success_refuses(self): self.assertEqual(self.go(run=lambda *s:0),70)
    def test_deadline_refuses(self):
        self.assertEqual(drive(self.execute,self.complete,self.stop,299,now=lambda:0),75); self.assertEqual(self.calls,[])

if __name__=='__main__': unittest.main()
