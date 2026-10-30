import os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/mnt/raid0/llm/tmp/yarn-judged-cell-prep-20261029')
from descendant_custody import Custody,proc
from src.repl_environment.exec_sandbox import wrap,Policy
root=Path(__file__).parent/'custody-fixture';root.mkdir()
cmd=[sys.executable,str(Path(__file__).parent/'custody_child_fixture.py'),str(root)]
cmd,extra=wrap(cmd,policy=Policy(),extra_allow=[str(root)])
env=os.environ.copy();env.update(extra)
custody=Custody();p=subprocess.Popen(cmd,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 deadline=time.monotonic()+10
 while not (root/'descendant.pid').exists() and time.monotonic()<deadline:time.sleep(.02)
 assert (root/'descendant.pid').exists(),'descendant did not start'
 child=int((root/'descendant.pid').read_text());known=custody.scan()
 assert p.pid in known and child in known,(p.pid,child,known)
 assert custody.drain(), 'drain failed'
 assert proc(p.pid) is None and proc(child) is None
 print('outer containment + captured-PID custody drained parent and forked descendant; no model')
finally:
 if proc(p.pid) is not None:assert custody.drain(), 'final drain failed'
