import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

class Supervisor(unittest.TestCase):
    def start(self,root,program):
        p=subprocess.Popen([sys.executable,'-B',str(HERE/'supervisor.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        cfg={'argv':[sys.executable,'-c',program],'directory':root,'window':'full-a','run_id':'test1','timeout_s':5}
        p.stdin.write(json.dumps(cfg)+'\n');p.stdin.flush()
        started=json.loads(p.stdout.readline());self.assertEqual(started['event'],'started')
        return p,started
    def test_natural_exit(self):
        with tempfile.TemporaryDirectory() as root:
            p,started=self.start(root,'pass')
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),0,p.stderr.read())
            self.assertTrue(event['normal']);self.assertTrue(event['cleanup']['echild'])
            self.assertEqual(event['cleanup']['captured'][0]['pid'],started['pid'])
            self.assertTrue(Path(root,'full-a.cleanup.json').is_file())
    def test_stop(self):
        with tempfile.TemporaryDirectory() as root:
            p,started=self.start(root,'import time; time.sleep(20)')
            p.stdin.write('{"command":"stop"}\n');p.stdin.flush()
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertFalse(event['normal']);self.assertEqual(event['reason'],'requested-stop')
            self.assertTrue(event['cleanup']['echild']);self.assertFalse(Path('/proc',str(started['pid'])).exists())
    def test_adopted_survivor_is_not_normal(self):
        with tempfile.TemporaryDirectory() as root:
            code='import os,time; p=os.fork(); (time.sleep(20) if p==0 else os._exit(0))'
            p,_=self.start(root,code)
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertFalse(event['normal']);self.assertTrue(event['killed_adopted']);self.assertGreaterEqual(len(event['cleanup']['captured']),2)
if __name__=='__main__':unittest.main()
