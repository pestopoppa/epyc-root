"""One registered half-A cohort; original write-side census, no timing claim."""
from pathlib import Path
import importlib.util
import json,os,sys,time,subprocess
B=Path(__file__).resolve().parent
D=Path(os.environ['W3_WORK_ROOT'])/'native-full'
sys.path[:0]=[str(B),str(B/'producer')]
from autokernel.loop import census,census_capture

from server_probe_full import ServerProbe
from build_receipt_preflight import validate_build_receipt


def main():
    if os.environ['FILLER_CPUS']!='0-47,96-143':
        raise ValueError('registered half-A literal grant required')
    D.mkdir(parents=True,exist_ok=False)
    p=json.loads((B/'recipes.json').read_text())['workloads'][0]
    validate_build_receipt(p)
    p['argv'][p['argv'].index('--slot-save-path')+1]=str(D/'runtime-slots')
    p['capture_inputs']['owner_start']=str(D/'entry-facts.json')
    p['capture_inputs']['eviction_receipt']=str(D/'out-pre-eviction.json')
    (D/'entry-facts.json').write_text(json.dumps({'pid':os.getpid(),'actual_affinity':sorted(os.sched_getaffinity(0)),'FILLER_CPUS':os.environ['FILLER_CPUS'],'utc_ns':time.time_ns()})+'\n')
    out=D/'out'/str(time.time_ns()); out.mkdir(parents=True,exist_ok=False)
    (D/'runtime-slots').mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('native_eviction',p['capture_inputs']['eviction_source'])
    ev=importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
    notes=[]; attempts=[]; before=ev._query_free_mb()
    def touch(node,gib):
        if node not in (0,1): raise ValueError('foreign NUMA node')
        started=time.monotonic()
        try:
            result=subprocess.run(['numactl',f'--membind={node}','--','python3',str(B/'native-full-touch.py'),str(gib)],capture_output=True,text=True,timeout=120)
            detail={'node':node,'gib':gib,'rc':result.returncode,'stderr':result.stderr[-4096:],'timeout':False}
        except subprocess.TimeoutExpired as exc:
            detail={'node':node,'gib':gib,'rc':None,'stderr':str(exc.stderr or b'')[-4096:],'timeout':True}
        except OSError as exc:
            detail={'node':node,'gib':gib,'rc':None,'stderr':str(exc),'timeout':False}
        detail['elapsed_s']=round(time.monotonic()-started,3); attempts.append(detail)
        return detail['rc']==0
    short,allocations=ev.run_eviction([0,1],40,query_free_mb=ev._query_free_mb,
        evict=touch,log=notes.append)
    receipt={'scope':'owned NUMA0,1 ONLY; explicit startup delta from global pre-eviction',
        'before_free_mb':before,'after_free_mb':ev._query_free_mb(),'short_nodes':short,
        'allocations':allocations,'attempt_details':attempts,'touch_timeout_s':120,'touch_implementation':'four-worker native libc memset all bytes','log':notes,'recorded_ns':time.time_ns()}
    (D/'out-pre-eviction.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
    if short:
        raise ValueError('owned-node canonical memory headroom not established')
    if int(os.environ['FILLER_DEADLINE']) - time.time() < 1200:
        raise ValueError('insufficient time remaining for all three census shapes')
    identity={'kernel':{'commit':p['kernel_commit'],'binary_sha256':census_capture.file_sha256(Path(p['binary']))},
        'model':{'path':p['model'],'sha256':census_capture.file_sha256(Path(p['model']))},
        'recipe':p,'backend':'cpu','claim_cpus':os.environ['FILLER_CPUS'],'env':p['env'],
        'scope':p['scope'],'startup_receipt':receipt}
    probe=ServerProbe(p,out)
    record=census.produce_census(workload_id=p['id'],workload_signature=p['scope'],model=Path(p['model']),
        identity=identity,shapes=[census.Shape('prefill',2048,1),census.Shape('decode',1,1),census.Shape('verify',4,1)],
        binary=Path(p['binary']),expected_ops=p['expected_ops'],require_device=False,probe=probe)
    native=census.store_census(record,out)
    census_capture.seal_record(native.with_suffix('.belief.jsonl'),record=native,journals=probe.journals)
    state=record['validity']['state']
    (out/'SUMMARY.json').write_text(json.dumps({'state':state,'native_record':str(native),
        'scope':p['scope'],'complete_obligated_P0d_set':False},sort_keys=True)+'\n')
    (D/'LAST-RESULT').write_text(str(out)+'\n')
    if state!=census.OBSERVED:return 1
    (D/'COMPLETE').write_text('single registered half-A cohort observed; not full P0d closure\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
