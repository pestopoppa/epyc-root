import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

SHIM = r'''
import io,json,os,sys,types
sys.path.insert(0,sys.argv[1]); import outer
case=sys.argv[2]; pidfile=sys.argv[3]; old=outer.subprocess.Popen
def spawn(*a,**kw):
 p=old(*a,**kw); open(pidfile,'w').write(str(p.pid)); return p
outer.subprocess.Popen=spawn
outer.sys.stdin=types.SimpleNamespace(buffer=io.BytesIO((json.dumps({'argv':['/bin/true'],'directory':'/tmp','window':'full-a','run_id':'test','timeout_s':10})+'\n').encode()))
if case=='birth':
 orig=outer.c.birth; hits=[0]
 def birth(pid):
  hits[0]+=1
  return None if hits[0]==1 else orig(pid)
 outer.c.birth=birth
elif case=='pidfd':
 def bad(*a,**k): raise OSError(24,'injected pidfd exhaustion')
 outer.os.pidfd_open=bad
elif case=='stdout':
 def bad(*a,**k): raise BrokenPipeError('injected stdout close')
 outer.send=bad
elif case=='selector':
 def bad(*a,**k): raise OSError('injected selector startup error')
 outer.selectors.DefaultSelector=bad
try:
 outer.run()
except (RuntimeError,OSError): pass
else: raise RuntimeError('failure was not refused')
'''

class StartupTests(unittest.TestCase):
    def test_startup_failures_reap_owned_supervisor(self):
        for case in ('birth','pidfd','stdout','selector'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                pidfile=Path(root)/'pid'
                result=subprocess.run([sys.executable,'-B','-c',SHIM,str(HERE),case,str(pidfile)],capture_output=True,text=True,timeout=8)
                self.assertEqual(result.returncode,0,result.stderr)
                pid=int(pidfile.read_text())
                self.assertFalse(Path('/proc',str(pid)).exists(),f'{case}: owned PID remains')

if __name__=='__main__': unittest.main()
