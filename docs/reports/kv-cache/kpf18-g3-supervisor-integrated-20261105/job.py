#!/usr/bin/env python3
import hashlib,json,os,sys,time,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import test_supervisor

def boundary():
    if os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists(): raise RuntimeError('STOP')
    if os.environ.get('FILLER_END') and time.time()>=float(os.environ['FILLER_END']): raise RuntimeError('deadline')
boundary()
suite=unittest.defaultTestLoader.loadTestsFromModule(test_supervisor)
result=unittest.TextTestRunner(verbosity=2).run(suite)
boundary()
if not result.wasSuccessful() or result.testsRun!=4: raise RuntimeError('control failure')
out=Path(os.environ['SUPERVISOR_RESULT']); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'schema':'epyc.kpf18.supervisor.v1','status':'PASS','controls':result.testsRun,'affinity':sorted(os.sched_getaffinity(0)),'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.py')}},indent=2)+'\n')
