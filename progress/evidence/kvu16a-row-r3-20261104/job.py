#!/usr/bin/env python3
"""Grant-bound native load qualification and answer; no input hashing/prep here."""
import hashlib,json,os,signal,sys,tempfile,threading,time
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import producer,server_lifecycle


def grant_affinity():
    declared=set()
    for x in os.environ['FILLER_CPUS'].split(','):
        y=list(map(int,x.split('-')));declared.update(range(y[0],y[-1]+1))
    cpus=sorted(declared & os.sched_getaffinity(0) & set(range(184,192)))
    if os.environ.get('FILLER_DRYRUN')=='1':
        if len(cpus)<4:raise RuntimeError('four actual granted CPUs required')
        cpus=cpus[:4]
    elif cpus!=list(range(184,192)):raise RuntimeError('full recipe needs CPUs184-191')
    os.sched_setaffinity(0,cpus)
    return cpus


def watcher(done):
    while not done.wait(.1):
        if Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE'])-30:
            child=server_lifecycle.ACTIVE
            if child is not None and child.poll() is None:
                child.terminate()
                if not done.wait(3) and child.poll() is None:child.kill()
            return


def main():
    receipt=json.loads((D/'source-catalog.json').read_text())
    for name,want in receipt.items():
        if hashlib.sha256((D/name).read_bytes()).hexdigest()!=want:raise RuntimeError('packet source changed: '+name)
    if os.environ.get('FILLER_NEEDGPU')!='1':raise RuntimeError('GPU grant absent')
    cpus=grant_affinity()
    native=os.environ.get('FILLER_DRYRUN')=='1'
    destination=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if native else D/'RESULT.json'
    if destination.exists():raise RuntimeError('refusing preexisting final result')
    parent=Path(os.environ['FILLER_DRYRUN_DIR']) if native else D
    output=Path(tempfile.mkdtemp(prefix='native-load-',dir=parent));output.rmdir()
    done=threading.Event();thread=threading.Thread(target=watcher,args=(done,),daemon=True);thread.start()
    argv=['--output-dir',str(output),'--port','19763','--max-gap-seconds','1.5','--healthy-samples','2']
    try:
        sys.argv=['producer.py',*argv]
        rc=producer.main()
        if rc:return rc
        plan=output/'plan.json';plan_sha=hashlib.sha256(plan.read_bytes()).hexdigest()
        sys.argv=['producer.py',*argv,'--run-plan-sha256',plan_sha]
        rc=producer.main()
        if rc:return rc
        result=json.loads((output/'result.json').read_text())
        if not result.get('coverage_qualified') or not result['cleanup']['verified_dead']:return 75
        sidecar=output/'kvu16a_sampled_load.beliefs.jsonl'
        if not sidecar.is_file() or not sidecar.stat().st_size:raise RuntimeError('belief capture absent')
        result['artifacts']={'output_dir':str(output),'belief_sidecar':str(sidecar),'plan_sha256':plan_sha}
        result['worker_affinity']=cpus
        producer.write_json(destination,result)
        return 0
    finally:
        done.set();thread.join(timeout=5)


if __name__=='__main__':
    raise SystemExit(main())
