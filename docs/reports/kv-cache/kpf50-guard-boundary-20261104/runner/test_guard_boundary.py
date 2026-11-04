import os, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

class Boundary(unittest.TestCase):
    def test_same_process_guard_captures_and_reaps_before_typed_receipt(self):
        code = r'''
import ctypes, hashlib, json, os, sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);root=Path(sys.argv[2])
import cleanup_receipt as c,runner_receipts as rr,window_custody as wc
assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
g=c.Guard(); wc.begin(root,'full-a','line1')
common={'window':'full-a','run_id':'line1'}
def put(k,v): (root/f'full-a.{k}.json').write_text(json.dumps(v))
put('outcome',{**common,'schema':'kpf50.window-outcome.v1','complete':True})
for phase,tick,ts in [('clock_before',1,100),('clock_after',2,200)]: put(phase,{**common,'schema':'kpf50.clock-sample.v1','phase':phase,'hsa_tick':tick,'hsa_hz':1000,'mono_before_ns':ts,'mono_after_ns':ts+1})
raw=b'profile rows';(root/'trace.csv').write_bytes(raw)
put('trace_manifest',{**common,'schema':'kpf50.trace-manifest.v1','complete':True,'files':[{'file':'trace.csv','sha256':hashlib.sha256(raw).hexdigest()}]})
pid=os.fork()
if pid==0: os._exit(0)
b=c.birth(pid);g.capture(pid,b)
os.waitid(os.P_PID,pid,os.WEXITED|os.WNOWAIT)
try: rr.publish_window(root,0,'line1',True,{'pid':pid,'birth_ticks':b,'verified_dead':True},g);raise AssertionError('unreaped child accepted')
except ValueError: pass
assert not (root/'full-a.complete.json').exists()
g.reap(pid)
try: rr.publish_window(root,0,'line1',True,{'pid':pid,'birth_ticks':b+1,'verified_dead':True},g);raise AssertionError('wrong birth accepted')
except ValueError: pass
assert not (root/'full-a.cleanup.json').exists()
rr.publish_window(root,0,'line1',True,{'pid':pid,'birth_ticks':b,'verified_dead':True},g)
proof=json.loads((root/'full-a.cleanup.json').read_text())
assert proof['echild'] and proof['captured'][0]['pid']==pid and proof['captured'][0]['birth_ticks']==b
assert (root/'full-a.complete.json').exists()
'''
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,'-B','-c',code,str(HERE),d],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
    def test_missing_guard_never_accepts_server_only_proof(self):
        code=r'''
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import runner_receipts as r
try:r.publish_window(Path(sys.argv[2]),0,'line1',True,{'pid':1,'birth_ticks':1,'verified_dead':True})
except ValueError as e: assert 'guard missing' in str(e)
else:raise AssertionError('missing guard accepted')
assert not (Path(sys.argv[2])/'full-a.complete.json').exists()
'''
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,'-B','-c',code,str(HERE),d],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
