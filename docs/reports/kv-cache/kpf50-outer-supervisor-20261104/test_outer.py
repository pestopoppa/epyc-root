import json, os, signal, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

class OuterTests(unittest.TestCase):
    def start(self, root, command):
        p=subprocess.Popen([sys.executable,'-B',str(HERE/'outer.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        cfg={'argv':[sys.executable,'-c',command],'directory':root,'window':'full-a','run_id':'test1','timeout_s':10}
        p.stdin.write(json.dumps(cfg)+'\n'); p.stdin.flush()
        outer=json.loads(p.stdout.readline()); self.assertEqual(outer['event'],'supervisor-started')
        inner=json.loads(p.stdout.readline()); self.assertEqual(inner['event'],'started')
        return p,outer,inner
    def test_normal(self):
        with tempfile.TemporaryDirectory() as d:
            p,_,_=self.start(d,'pass')
            rest=[json.loads(x) for x in p.stdout.read().splitlines()]
            self.assertEqual(p.wait(timeout=8),0,p.stderr.read());self.assertTrue(rest[-1]['normal'])
    def test_sigkill_inner_reaps_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            p,outer,inner=self.start(d,'import time;time.sleep(30)')
            os.kill(outer['pid'],signal.SIGKILL)
            rest=[json.loads(x) for x in p.stdout.read().splitlines()]
            self.assertEqual(p.wait(timeout=8),75,p.stderr.read()); self.assertFalse(rest[-1]['normal'])
            self.assertFalse(Path('/proc',str(inner['pid'])).exists())
            self.assertTrue(any(x['pid']==inner['pid'] for x in rest[-1]['adopted']))
            self.assertFalse(Path(d,'full-a.cleanup.json').exists())
    def test_outer_sigterm_drains(self):
        with tempfile.TemporaryDirectory() as d:
            p,_,inner=self.start(d,'import time;time.sleep(30)')
            os.kill(p.pid,signal.SIGTERM)
            rest=[json.loads(x) for x in p.stdout.read().splitlines()]
            self.assertEqual(p.wait(timeout=8),75,p.stderr.read());self.assertFalse(rest[-1]['normal'])
            self.assertFalse(Path('/proc',str(inner['pid'])).exists())
if __name__=='__main__':unittest.main()
