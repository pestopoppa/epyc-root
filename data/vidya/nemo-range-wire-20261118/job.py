"""Allocator-bound, source-sealed NEMO replay and isolated reader canary."""
import hashlib, json, os, signal, subprocess, sys, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ROW='vb-nemo-range-wire-20261118'
SCHEMA='epyc.vidya.nemo_range_wire.v1'
RUN='/mnt/raid0/llm/tmp/akagg/filing-20261105/nemo-sdk-roctx-marker-compare-r2-20261105/run-2f079b3e-eedc-4495-883f-345e83fde160'

def publish(path, obj):
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        try:
            json.dump(obj,f,indent=2,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno()); os.link(f.name,path)
        finally: Path(f.name).unlink()

def passed(r,mode,seal):
    controls={'tamper':'refused','partial':'refused','missing-grant':'refused','source-drift':'refused'} if mode=='publisher_smoke' else {}
    return (r.get('schema')==SCHEMA and r.get('id')==ROW and r.get('mode')==mode and r.get('source_manifest_sha256')==seal and r.get('status')=='PASS' and len(r.get('cpus',[]))==4 and r.get('replayed_runs')==80 and r.get('joins')==480 and r.get('rows')==1 and r.get('frames')==3 and r.get('refusals')==0 and r.get('controls')==controls and r.get('cases')=={'exact':{'recognized':1,'displayed':1}, **{x:{'recognized':0,'displayed':0} for x in ('wrong-task','wrong-consumer','model')}})

def interrupted(*_): raise ValueError('STOP or deadline')

def main():
    action,seal=sys.argv[1:]; smoke=os.environ.get('FILLER_DRYRUN')=='1'; mode='publisher_smoke' if smoke else 'official'
    if smoke and not os.environ.get('FILLER_DRYRUN_RESULT_PATH'): return 1
    output=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else ROOT/'official/RESULT.json'
    if action=='complete':
        try: return int(not passed(json.loads(output.read_bytes()),mode,seal))
        except (OSError,ValueError,KeyError,TypeError): return 1
    if action!='run': return 1
    output.parent.mkdir(parents=True,exist_ok=True)
    attempt=Path(tempfile.mkdtemp(prefix=mode+'-',dir=ROOT)); report={'schema':SCHEMA,'id':ROW,'mode':mode,'source_manifest_sha256':seal,'status':'UNKNOWN','attempt':str(attempt)}
    try:
        if os.environ.get('FILLER_ID')!=ROW or os.environ.get('FILLER_NEEDGPU')!='0': raise ValueError('grant identity')
        if smoke and Path(os.environ['FILLER_DRYRUN_DIR']).resolve() not in output.resolve().parents: raise ValueError('smoke path')
        stop=Path(os.environ['FILLER_STOPFILE']); cutoff=min(time.time()+300,int(os.environ['FILLER_DEADLINE']))
        def checkpoint():
            if stop.exists() or time.time()>=cutoff: raise ValueError('STOP or deadline')
        for sig in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT): signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,max(.001,cutoff-time.time()))
        cpus=sorted(os.sched_getaffinity(0))[:4]
        if len(cpus)!=4: raise ValueError('insufficient CPUs')
        os.sched_setaffinity(0,cpus); report['cpus']=sorted(os.sched_getaffinity(0))
        manifest=(ROOT/'SOURCE.sha256').read_bytes()
        if hashlib.sha256(manifest).hexdigest()!=seal: raise ValueError('manifest seal')
        def verify():
            for line in manifest.decode().splitlines():
                checkpoint(); digest,name=line.split('  ',1); p=ROOT/name
                if not p.resolve(strict=True).is_relative_to(ROOT/'source') or hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise ValueError('source drift '+name)
        verify()
        grant_dir=Path(os.environ['FILLER_DRYRUN_DIR'])/'grants' if smoke else Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))
        env=dict(os.environ,NEMO_GRANT_PATH=str(grant_dir/(ROW+'.grant')))
        result=attempt/'replay.json'
        child=subprocess.run([sys.executable,'-I','-B',str(ROOT/'source/scripts/vidya/nemo_range_replay.py'),RUN,str(result)],env=env,timeout=max(.01,cutoff-time.time()),check=False)
        if child.returncode: raise ValueError('native replay refused')
        native=json.loads(result.read_bytes()); report.update(replayed_runs=len(native['result']),joins=sum(len(v['joins']) for v in native['result'].values()),native=str(result))
        sys.path.insert(0,str(ROOT/'source/scripts/vidya'))
        from canary.nemo_range_context import run
        as_of=(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat().replace('+00:00','Z')
        report.update(run(result,attempt/'canary',as_of,smoke,checkpoint)); verify(); checkpoint()
        report['status']='PASS'
        if not passed(report,mode,seal): raise ValueError('completion predicate')
        publish(output,report)
    except (OSError,ValueError,KeyError,TypeError,ImportError,subprocess.TimeoutExpired) as exc:
        report.update(status='UNKNOWN',error=str(exc)); publish(attempt/'partial.json',report); print(str(exc),file=sys.stderr); return 1
    finally: signal.setitimer(signal.ITIMER_REAL,0)
    return 0
if __name__=='__main__': raise SystemExit(main())
