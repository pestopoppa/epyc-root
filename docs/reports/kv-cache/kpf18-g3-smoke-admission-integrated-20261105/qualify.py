import hashlib,json,os,sys,time,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
import test_integrated
suite=unittest.defaultTestLoader.loadTestsFromModule(test_integrated)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful() or result.testsRun!=7:raise SystemExit(1)
stop=os.environ.get('FILLER_STOPFILE');end=os.environ.get('FILLER_END')
if stop and Path(stop).exists():raise SystemExit('STOP')
if end and time.time()>=float(end):raise SystemExit('deadline')
out=Path(os.environ['ADMISSION_RESULT']);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'schema':'kpf18.smoke-admission-integrated.v1','status':'PASS','tests':result.testsRun,'affinity':sorted(os.sched_getaffinity(0)),'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob('*.py')}},indent=2)+'\n')
