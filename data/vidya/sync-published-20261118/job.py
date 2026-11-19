#!/usr/bin/python3
import hashlib, json, os, re, signal, subprocess, sys, tempfile, time
from pathlib import Path
D=Path(__file__).resolve().parent
ROW='vb-sync-published-repair-20261118'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(pin):
    m=D/'source-pins.json'
    if sha(m)!=pin: raise ValueError('manifest drift')
    for name,digest in json.loads(m.read_text())['files'].items():
        p=D/name
        if not p.is_file() or p.is_symlink() or sha(p)!=digest: raise ValueError('source drift: '+name)
def check(report, mode, pin):
    if any(report.get(k)!=v for k,v in {'id':ROW,'mode':mode,'authority':'software-control-only','status':'passed','selected':1,'refused':0,'lag':0,'manual_sync_count':0,'source_pins_sha256':pin}.items()): raise ValueError('bad result')
    work=Path(report['run_dir'])
    if work.parent!=D or not work.name.startswith(mode+'-'): raise ValueError('bad run directory')
    receipt=work/'native-run/PASS.json'
    if sha(receipt)!=report['native_receipt_sha256']: raise ValueError('receipt drift')
    native=json.loads(receipt.read_text())
    if native['manual_sync'] or native['production_acceptance'] or not native['postpush_status']['fresh'] or native['postpush_status']['lag_entries']!=0: raise ValueError('native failure')
def publish(p,report):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False) as f:
        temp=Path(f.name); json.dump(report,f,indent=2,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    try: os.link(temp,p)
    finally: temp.unlink()
def main():
    action,pin=sys.argv[1:]; smoke=os.environ.get('FILLER_DRYRUN')=='1'; mode='publisher-smoke' if smoke else 'official'
    if smoke and not os.environ.get('FILLER_DRYRUN_RESULT_PATH'): return 1
    output=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'official/RESULT.json'
    try:
        verify(pin)
        if action=='complete': check(json.loads(output.read_text()),mode,pin); return 0
        if action!='run' or os.environ['FILLER_ID']!=ROW: raise ValueError('row identity')
        stop=Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE']); remaining=min(deadline-time.time(),300)
        if stop.exists() or remaining<=0: raise ValueError('stopped or expired')
        cpus=set()
        for block in os.environ['FILLER_CPUS'].split(','):
            if not re.fullmatch(r'[0-9]{1,4}(?:-[0-9]{1,4})?',block): raise ValueError('invalid CPU grant')
            lo,_,hi=block.partition('-'); cpus.update(range(int(lo),int(hi or lo)+1))
        cpus=sorted(cpus & os.sched_getaffinity(0))[:4]
        if len(cpus)!=4: raise ValueError('four granted CPUs required')
        os.sched_setaffinity(0,cpus)
        work=Path(tempfile.mkdtemp(prefix=mode+'-',dir=D))
        env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}; env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
        with (work/'probe.log').open('w') as log:
            subprocess.run([sys.executable,'-I','-B',str(D/'run.py'),str(work)],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=remaining,check=True)
        if stop.exists() or time.time()>=deadline: raise ValueError('stopped or expired')
        verify(pin)
        report={'id':ROW,'mode':mode,'authority':'software-control-only','status':'passed','selected':1,'refused':0,'lag':0,'manual_sync_count':0,'source_pins_sha256':pin,'cpus':cpus,'run_dir':str(work),'native_receipt_sha256':sha(work/'native-run/PASS.json')}
        check(report,mode,pin); publish(output,report); return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())
