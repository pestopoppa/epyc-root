import hashlib,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
# Each control gets its own subreaper process; runner never adopts its fixtures.
if len(sys.argv)>1:
    from output_supervision import run
    case=sys.argv[1];base=Path(sys.argv[2]);stop=base/'STOP'
    r=run([sys.executable,'-B',str(D/'writer.py'),str(base/'attempt'),case,str(stop)],base/'attempt',stop,time.monotonic()+(.15 if case=='deadline' else 3),32768)
    expected={'normal':'normal','growth':'budget','stop':'STOP','deadline':'deadline','failure':'child-failure','detached':'normal'}[case]
    assert r['reason']==expected,r
    assert r['pid_absent'] and not r['children_after'],r
    assert len(r['samples'])>=2 and r['samples'][0]['stage']=='before-launch' and r['samples'][-1]['stage']=='after-drain'
    if case=='growth':assert r['observed_sampled_peak_bytes']>=32768
    if case=='failure':assert r['child_rc']==9
    if case=='detached':
        pid=int((base/'attempt/detached.pid').read_text());r['detached_pid']=pid
        assert not Path('/proc',str(pid)).exists()
    print('KPF18_OUTPUT_RECEIPT '+json.dumps(r));raise SystemExit(0)
result=Path(os.environ['QUAL_RESULT']);assert not result.exists() and not result.is_symlink()
base=result.parent/'controls';base.mkdir(parents=True,exist_ok=False)
import owned_drain
assert not owned_drain.children()
owned_drain.enable()
def grant_boundary():
    stop=Path(os.environ['FILLER_STOPFILE'])
    if stop.exists() or stop.is_symlink():raise RuntimeError('grant STOP')
    if time.time()>=int(os.environ['FILLER_END']):raise RuntimeError('grant deadline')
    if (D/'STOP').exists() or (D/'STOP').is_symlink():raise RuntimeError('packet STOP')
rows=[]
for case in ('normal','growth','stop','deadline','failure','detached'):
    assert not (D/'STOP').exists(),'row STOP'
    casebase=base/case;casebase.mkdir()
    grant_boundary()
    p=None;fd=None
    try:
        with (casebase/'stdout').open('w') as stdout, (casebase/'stderr').open('w') as stderr:
            p=subprocess.Popen([sys.executable,'-B',str(D/'job.py'),case,str(casebase)],stdout=stdout,stderr=stderr)
            fd=os.pidfd_open(p.pid)
            limit=time.monotonic()+15
            while p.poll() is None:
                grant_boundary()
                if time.monotonic()>=limit:raise TimeoutError('control timeout')
                time.sleep(.02)
            grant_boundary()
    finally:
        try:
            if p is not None and p.poll() is None:
                if fd is not None:
                    import signal
                    try:signal.pidfd_send_signal(fd,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:p.wait(timeout=.3)
                    except subprocess.TimeoutExpired:
                        try:signal.pidfd_send_signal(fd,signal.SIGKILL)
                        except ProcessLookupError:pass
                        p.wait()
            owned_drain.drain()
            if p is not None:p.wait()
        finally:
            if fd is not None:os.close(fd)
    p=subprocess.CompletedProcess(p.args,p.returncode,(casebase/'stdout').read_text(),(casebase/'stderr').read_text())
    (casebase/'stdout').write_text(p.stdout);(casebase/'stderr').write_text(p.stderr)
    assert p.returncode==0,(case,p.returncode,p.stderr)
    lines=p.stdout.splitlines()
    framed=[line for line in lines if line.startswith('KPF18_OUTPUT_RECEIPT ')]
    assert len(framed)==1 and lines[-1]==framed[0],('missing, extra or nonfinal receipt',p.stdout)
    import re
    assert all(re.fullmatch(r'waiting for owned child to drain: [0-9]+',line) for line in lines[:-1]),('unexpected diagnostic output',p.stdout)
    receipt=json.loads(framed[0][len('KPF18_OUTPUT_RECEIPT '):])
    assert isinstance(receipt,dict) and receipt.get('reason') in ('normal','budget','STOP','deadline','child-failure')
    rows.append({'case':case,'receipt':receipt})
grant_boundary()
r={'grant_boundary':{'stopfile':os.environ['FILLER_STOPFILE'],'end':int(os.environ['FILLER_END']),'checked_at':time.time(),'stop_absent':True},'schema':'kpf18.g3.isolated-output-supervision.v1','status':'PASS','tests':6,'controls':rows,'affinity':sorted(os.sched_getaffinity(0)),
   'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.py')},
   'scope':'New isolated reusable supervisor only; no integrated candidate, native lifecycle, filesystem quota, bounded scan latency or unsampled-peak claim.'}
result.parent.mkdir(parents=True,exist_ok=True)
grant_boundary()
r['grant_boundary']['checked_at']=time.time()
with result.open('x') as f:json.dump(r,f,indent=2)
try:grant_boundary()
except BaseException:
    result.unlink()
    raise
