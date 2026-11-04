import json,os,signal,subprocess,sys,tempfile,unittest
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
    def test_supervisor_sigterm_drains_owned_child(self):
        with tempfile.TemporaryDirectory() as root:
            p,started=self.start(root,'import time; time.sleep(20)')
            os.kill(p.pid,signal.SIGTERM)
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertFalse(event['normal']);self.assertEqual(event['reason'],'supervisor-signal')
            self.assertFalse(Path('/proc',str(started['pid'])).exists())
    def test_ipc_eof_drains_owned_child(self):
        with tempfile.TemporaryDirectory() as root:
            p,started=self.start(root,'import time; time.sleep(20)')
            p.stdin.close()
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertEqual(event['reason'],'ipc-eof');self.assertFalse(Path('/proc',str(started['pid'])).exists())
    def test_bad_ipc_drains_owned_child(self):
        with tempfile.TemporaryDirectory() as root:
            p,started=self.start(root,'import time; time.sleep(20)')
            p.stdin.write('not json\n');p.stdin.flush()
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertEqual(event['reason'],'invalid-ipc');self.assertFalse(Path('/proc',str(started['pid'])).exists())
    def test_pidfd_unavailable_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            src=("import sys,os,json;sys.path.insert(0,sys.argv[1]);import supervisor;"
                 "os.pidfd_open=lambda *a: (_ for _ in ()).throw(OSError(24,'injected'));"
                 "sys.exit(supervisor.run(json.loads(sys.stdin.readline())))")
            p=subprocess.Popen([sys.executable,'-B','-c',src,str(HERE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            cfg={'argv':[sys.executable,'-c','import time; time.sleep(20)'],'directory':root,'window':'full-a','run_id':'test1','timeout_s':5}
            p.stdin.write(json.dumps(cfg)+'\n');p.stdin.flush();started=json.loads(p.stdout.readline())
            p.stdin.write('{"command":"stop"}\n');p.stdin.flush()
            event=json.loads(p.stdout.readline());self.assertEqual(p.wait(timeout=8),75,p.stderr.read())
            self.assertFalse(event['normal']);self.assertFalse(Path('/proc',str(started['pid'])).exists())
    def test_initial_birth_failure_kills_owned_child(self):
        with tempfile.TemporaryDirectory() as root:
            pidfile=Path(root,'child.pid')
            src=("import sys,os,json,subprocess;sys.path.insert(0,sys.argv[1]);import supervisor;"
                 "orig=subprocess.Popen;"
                 "supervisor.subprocess.Popen=lambda *a,**k: (lambda p: (open(sys.argv[2],'w').write(str(p.pid)),p)[1])(orig(*a,**k));"
                 "old=supervisor.cleanup.birth;supervisor.cleanup.birth=lambda p: old(p) if p==os.getpid() else None;"
                 "sys.exit(supervisor.run(json.loads(sys.stdin.readline())))")
            p=subprocess.Popen([sys.executable,'-B','-c',src,str(HERE),str(pidfile)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            cfg={'argv':[sys.executable,'-c','import time; time.sleep(20)'],'directory':root,'window':'full-a','run_id':'test1','timeout_s':5}
            _,err=p.communicate(json.dumps(cfg)+'\n',timeout=8)
            self.assertNotEqual(p.returncode,0,err);pid=int(pidfile.read_text())
            self.assertFalse(Path('/proc',str(pid)).exists());self.assertFalse(Path(root,'full-a.cleanup.json').exists())
if __name__=='__main__':unittest.main()
