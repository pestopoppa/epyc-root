import os,json,subprocess,sys,hashlib,time
from pathlib import Path
D=Path(__file__).resolve().parent
out=Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(D/'out/RESULT.json')))
assert not out.exists(), 'result already exists'
assert not (D/'STOP').exists(), 'STOP'
cpus=os.sched_getaffinity(0)
if os.environ.get('FILLER_SMOKE')=='1':assert len(cpus)==4 and os.environ.get('FILLER_THREADS')=='4'
p=subprocess.run([sys.executable,'-B','-m','unittest','test_socket_deadline'],cwd=D,capture_output=True,text=True,timeout=15)
assert p.returncode==0,p.stderr
assert not (D/'STOP').exists(), 'STOP'
r={'schema':'kpf18.g3.rowflow-socket-qualification.v1','status':'PASS','model':None,'tests':6,'stdout':p.stdout,'stderr':p.stderr,'affinity':sorted(cpus),'smoke':os.environ.get('FILLER_SMOKE')=='1','time_ns':time.time_ns(),'sources':{n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ('socket_deadline.py','test_socket_deadline.py','job.py')},'scope':'Real socket deadline controls under current rowflow entry; no native cancellation/task release, model, GPU, construction or historical-layout verdict.'}
out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(r)+'\n');os.replace(tmp,out)
