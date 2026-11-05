#!/usr/bin/env python3
"""Rowflow job supervisor: 120s workload deadline, <=7s cleanup budget."""
import datetime, hashlib, json, os, re, signal, subprocess, sys, time, uuid
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent

def seal():
    manifest=(BASE/'SHA256SUMS').read_bytes()
    checked={}
    for line in manifest.decode().splitlines():
        expected,name=line.split('  ',1); p=BASE/name
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if p.is_symlink() or actual!=expected: raise RuntimeError('custody failure: '+name)
        checked[name]=actual
    return {'manifest_sha256':hashlib.sha256(manifest).hexdigest(),'files':checked}

def main():
    mode='smoke' if os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1' else 'full'
    run=BASE/'out'/(mode+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex)
    run.mkdir(parents=True,exist_ok=False)
    child=None; rc=1; failure=None; dead=True; before=None; after=None
    started=time.monotonic()
    result=Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH','')) if mode=='smoke' else BASE/'out/RESULT.json'
    classification='SMOKE_ONLY' if mode=='smoke' else 'MODEL_FREE_QUALIFICATION'
    def interrupted(signum,frame): raise RuntimeError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    try:
        if len(sys.argv)!=1: raise RuntimeError('no arguments accepted')
        if mode=='smoke' and (not os.environ.get('FILLER_DRYRUN_RESULT_PATH') or result.resolve()==(BASE/'out/RESULT.json').resolve()): raise RuntimeError('separate dryrun result required')
        if result.exists(): raise RuntimeError('refuse existing result')
        before=seal(); (run/'PRE_SEAL.json').write_text(json.dumps(before,indent=2)+'\n')
        if not os.environ.get('FILLER_ID') or not os.environ.get('FILLER_END'): raise RuntimeError('filler engine context required')
        declared_cpus=os.environ.get('FILLER_CPUS','')
        if not re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*',declared_cpus): raise RuntimeError('FILLER_CPUS required')
        # Engine tasksets the job. Preserve actual inherited affinity; never widen it.
        assigned=sorted(os.sched_getaffinity(0))
        if not assigned: raise RuntimeError('empty inherited affinity')
        cpus=','.join(map(str,assigned))
        stop=Path(os.environ['FILLER_STOPFILE'])
        if stop.exists() or (BASE/'STOP').exists(): raise RuntimeError('STOP')
        limit=min(120.0,float(os.environ['FILLER_END'])-time.time()-7)
        if limit<=0: raise RuntimeError('insufficient cleanup reserve')
        with (run/'worker.log').open('x') as log:
            child=subprocess.Popen(['taskset','-c',cpus,sys.executable,'-I','-B',str(BASE/'adapter.py'),str(run/'worker'),mode],stdout=log,stderr=subprocess.STDOUT)
            (run/'OWNED_PID.json').write_text(json.dumps({'pid':child.pid,'cpus':cpus,'engine_declared_cpus':declared_cpus,'filler_id':os.environ['FILLER_ID']})+'\n')
            while True:
                if stop.exists() or (BASE/'STOP').exists(): raise RuntimeError('STOP')
                if time.monotonic()-started>=limit: raise RuntimeError('workload deadline')
                try: rc=child.wait(timeout=.1); break
                except subprocess.TimeoutExpired: pass
        if rc: raise RuntimeError('worker exit '+str(rc))
        qualification=json.loads((run/'worker/QUALIFICATION.json').read_text())
        if qualification['classification']!=classification: raise RuntimeError('classification mismatch')
        after=seal()
        if after!=before: raise RuntimeError('seal changed')
        (run/'POST_SEAL.json').write_text(json.dumps(after,indent=2)+'\n')
    except BaseException as exc:
        rc=1; failure=type(exc).__name__+': '+str(exc)
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN); signal.signal(signal.SIGINT,signal.SIG_IGN)
        if child is not None:
            dead=False
            try:
                if child.poll() is None:
                    try: child.terminate()
                    except ProcessLookupError: pass
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try: child.kill()
                        except ProcessLookupError: pass
                        child.wait(timeout=2)
                child.wait(timeout=.1)
                dead=subprocess.run(['ps','-p',str(child.pid)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=1).returncode==1
                if not dead: raise RuntimeError('owned PID absence not proven')
            except BaseException as exc:
                rc=1; failure=(failure or '')+'; cleanup: '+type(exc).__name__+': '+str(exc)
        receipt={'classification':classification,'rc':rc,'failure':failure,'own_pid_dead':dead,'elapsed_s':time.monotonic()-started,'workload_limit_s':120,'cleanup_budget_s':7,'run_dir':str(run),'inference':False,'pre_seal':before,'post_seal':after}
        (run/'END.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if rc==0 and dead:
            try:
                result.parent.mkdir(parents=True,exist_ok=True)
                with result.open('x') as f: json.dump({**receipt,'status':'PASS','native_equality':qualification['native_equality'],'cases':qualification['cases'],'launch_verdicts':qualification['launch_verdicts']},f,indent=2); f.write('\n')
            except BaseException as exc:
                rc=1; receipt.update(rc=1,failure='result write: '+str(exc)); (run/'END.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return rc
if __name__=='__main__': raise SystemExit(main())
