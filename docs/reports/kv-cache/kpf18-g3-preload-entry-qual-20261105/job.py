import hashlib,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
stop=Path(os.environ['FILLER_STOPFILE']); expected=Path(os.environ['QUAL_EXPECTED_STOP']); end=int(os.environ['FILLER_END']); result=Path(os.environ['QUAL_RESULT'])
def boundary():
 if stop!=expected or stop.exists() or stop.is_symlink() or (D/'STOP').exists() or (D/'STOP').is_symlink() or time.time()>=end: raise RuntimeError('STOP/deadline or unexpected stop path')
boundary()
assert not result.exists() and not result.is_symlink()
p=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_composed_driver.ComposedDriver'],cwd=D,text=True,capture_output=True,timeout=15)
boundary()
assert p.returncode==0 and 'Ran 4 tests' in p.stderr and '\nOK\n' in p.stderr,(p.returncode,p.stderr)
r={'row_id':'kpf18-g3-preload-entry-qual-20261105','schema':'kpf18.g3.preload-entry.v1','status':'PASS','tests':4,'test_stderr':p.stderr,'affinity':sorted(os.sched_getaffinity(0)),'sources':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(D.glob('*.py'))},'boundary':{'stop':str(stop),'end':end,'checked_at':time.time()},'scope':'Copied source-bound actual driver main under fake preload, guard, GPU witness and gate only. No real receipt verification, full driver import, native lifecycle, GPU or layout verdict.'}
result.parent.mkdir(parents=True,exist_ok=True)
boundary()
with result.open('x') as f: json.dump(r,f,indent=2)
try: boundary()
except BaseException: result.unlink(); raise
