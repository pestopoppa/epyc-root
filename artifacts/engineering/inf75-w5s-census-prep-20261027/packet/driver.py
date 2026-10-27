"""Draft owner-only W5s native shape census; no timing or quality inference."""
from pathlib import Path
import importlib.util,json,os,sys,time,subprocess
D=Path(__file__).resolve().parent
B=D.parent
N=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep')
sys.path[:0]=[str(D),str(B),str(N),str(D/'runtime')]
import private_census as census
import census_belief
from autokernel.loop import census_capture
from server_probe_full import ServerProbe

def main():
    if os.environ['FILLER_CPUS']!='0-95':raise ValueError('whole-host physical claim required')
    p=json.loads((D/'recipes.json').read_text())['workloads'][0]
    native=json.loads((D/'native-builder.json').read_text())
    if any(census_capture.file_sha256(Path(pin['path']))!=pin['sha256'] for pin in native['sources']):
        raise ValueError('current builder source drift')
    out=D/'out'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
    (D/'runtime-slots').mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('native_eviction',p['capture_inputs']['eviction_source'])
    ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
    notes=[];attempts=[];before=ev._query_free_mb()
    def touch(node,gib):
        if node not in (0,1,2,3):raise ValueError('foreign NUMA node')
        started=time.monotonic()
        try:
            result=subprocess.run(['numactl',f'--membind={node}','--','python3',str(D/'native-full-touch.py'),str(gib)],capture_output=True,text=True,timeout=120)
            detail={'node':node,'gib':gib,'rc':result.returncode,'stderr':result.stderr[-4096:],'timeout':False}
        except subprocess.TimeoutExpired as exc:
            detail={'node':node,'gib':gib,'rc':None,'stderr':str(exc.stderr or b'')[-4096:],'timeout':True}
        except OSError as exc:
            detail={'node':node,'gib':gib,'rc':None,'stderr':str(exc),'timeout':False}
        detail['elapsed_s']=round(time.monotonic()-started,3);attempts.append(detail)
        return detail['rc']==0
    short,allocations=ev.run_eviction([0,1,2,3],40,query_free_mb=ev._query_free_mb,evict=touch,log=notes.append)
    receipt={'scope':'claimed nodes 0,1,2,3 only','before_free_mb':before,'after_free_mb':ev._query_free_mb(),
        'short_nodes':short,'allocations':allocations,'attempt_details':attempts,'touch_timeout_s':120,
        'touch_implementation':'four-worker native libc memset all bytes','log':notes,'recorded_ns':time.time_ns()}
    (D/'out-pre-eviction.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
    if short:raise ValueError('owned-node headroom not established')
    if int(os.environ['FILLER_DEADLINE'])-time.time()<4200:raise ValueError('insufficient time for all phases')
    model_refs=[]
    for path in p['ordered_shards']:
        model_refs.append({'path':str(Path(path).resolve(strict=True)),'sha256':census_capture.file_sha256(Path(path))})
    head={'path':str(Path(p['head']).resolve(strict=True)),'sha256':census_capture.file_sha256(Path(p['head']))}
    expected={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (B/'model.sha256').read_text().splitlines()}
    if any(expected.get(ref['path'])!=ref['sha256'] for ref in [*model_refs,head]):raise ValueError('model digest drift')
    identity={'kernel':{'commit':p['kernel_commit'],'binary_sha256':census_capture.file_sha256(Path(p['binary']))},
        'model':{'shards':model_refs,'head':head},'recipe':p,'backend':'cpu','claim_cpus':os.environ['FILLER_CPUS'],
        'env':p['env'],'scope':p['scope'],'startup_receipt':receipt}
    intent=census_belief.begin_capture(out/'belief-intent.json',workload_id=p['id'])
    p['capture_inputs']['belief_intent']=str(intent)
    probe=ServerProbe(p,out)
    record=census.produce_census(workload_id=p['id'],workload_signature=p['scope'],model=Path(p['model']),
        identity=identity,shapes=[census.Shape('prefill',2048,1),census.Shape('decode',1,1),census.Shape('verify',5,1)],
        binary=Path(p['binary']),expected_ops=p['expected_ops'],require_device=False,probe=probe)
    native=census.store_census(record,out)
    census_capture.seal_record(native.with_suffix('.belief.jsonl'),record=native,journals=probe.journals)
    state=record['validity']['state']
    if state==census.OBSERVED:
        census_belief.write_belief_measurements(out,record_path=native,journals=probe.journals,intent_path=intent)
    (out/'SUMMARY.json').write_text(json.dumps({'state':state,'native_record':str(native),
        'scope':p['scope'],'complete_obligated_P0d_set':False},sort_keys=True)+'\n')
    (D/'LAST-RESULT').write_text(str(out)+'\n')
    if state!=census.OBSERVED:return 1
    (D/'COMPLETE').write_text('single W5s registered full-host facet observed; P0d remains open\n')
    return 0
if __name__=='__main__':raise SystemExit(main())
