#!/usr/bin/python3
"""Same pinned C5 server, actual request primitive and common writer; smoke is non-admitted."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
D=Path(__file__).resolve().parent
sys.path[:0]=[str(D),str(D/'producer')]
from server_probe_full import request,own_sample
from affinity_scope import within
from golden_lifecycle import await_port_ready,wait_owned_health,stop_owned

MODEL=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
MODEL_SHA='c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'

def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()

def smoke(root,state):
    cpus=sorted(os.sched_getaffinity(0));mask=','.join(map(str,cpus))
    if len(cpus)!=2 or max(cpus)>=96 or cpus[0]//24!=cpus[-1]//24:raise ValueError('two primary CPUs in one free quarter required')
    p=json.loads((D/'recipes.json').read_text())['workloads'][0]
    argv=list(p['argv']);argv[argv.index('-c')+1]=mask
    argv[argv.index('--interleave=0,1')]='--membind='+str(cpus[0]//24)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    for flag,value in [('--port',port),('-c',512),('-t',2),('-ub',64),('--cache-ram',0),('--slot-save-path',root/'runtime-slots')]:
        index=argv.index(flag,argv.index(p['binary'])) if flag=='-c' else argv.index(flag)
        argv[index+1]=str(value)
    argv.remove('--mlock');(root/'runtime-slots').mkdir()
    env=dict(p['env'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',FILLER_CPUS=mask)
    proc=None
    try:
        await_port_ready(port)
        with (root/'server.log').open('wb') as log:
            proc=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
            wait_owned_health(proc,port,lambda:request(port,'health').get('status')=='ok',timeout=120)
            rendered=request(port,'apply-template',{'messages':[{'role':'user','content':'Count from one to ten in English.'}]})['prompt']
            ids=request(port,'tokenize',{'content':rendered,'add_special':True,'parse_special':True})['tokens']
            body={'prompt':ids,'n_predict':16,'temperature':0,'seed':42,'ignore_eos':True,'stream':False,'return_tokens':True,'cache_prompt':False}
            first=time.time();samples=[]
            while True:
                started=time.time()
                with concurrent.futures.ThreadPoolExecutor(1) as pool:
                    future=pool.submit(request,port,'completion',body,180)
                    while not future.done():
                        row=own_sample(proc.pid,gpu=False,phase='requests',port=port);samples.append(row)
                        if not within(row['task_affinity'],mask):raise ValueError('native server thread escaped smoke mask')
                        time.sleep(.05)
                    response=future.result()
                if response.get('tokens_predicted',response.get('timings',{}).get('predicted_n'))!=16:raise ValueError('native request not complete')
                finish=time.time()
                with (root/'requests.jsonl').open('a') as f:f.write(json.dumps({'started':started,'finished':finish,'body':body,'response':response})+'\n')
                state.update(first_request_ok=True,requests_completed=state['requests_completed']+1,real_request_span_s=finish-first,result_writer_ok=True)
                write(root/'WORK-RESULT.json',state)
                if finish-first>=60:break
            if not samples or not any(r['loaded_instrument'] for r in samples):raise ValueError('pinned native instrument not mapped')
            for row in samples:
                if any(not Path(f).resolve().is_relative_to(Path(p['build_dir']).resolve()/'bin') for f in row['loaded_ggml']):raise ValueError('foreign GGML mapping')
            (root/'samples.json').write_text(json.dumps(samples)+'\n')
    finally:
        state['server_cleanup']=stop_owned(proc)

def full_census_request_fields(summary_path):
    """Project request status from native windows; preserve result-writer success."""
    error = None
    windows = []
    try:
        summary = json.loads(Path(summary_path).read_text())
        record = json.loads(Path(summary['native_record']).read_text())
        per_shape = record.get('graph', {}).get('per_shape')
        if not isinstance(per_shape, list):
            error = 'native graph.per_shape missing or malformed'
        else:
            for shape in per_shape:
                if not isinstance(shape, dict) or not isinstance(shape.get('request_windows'), list):
                    error = 'per-shape request_windows missing or malformed'
                    break
                windows.extend(shape['request_windows'])
            if error is None and not windows:
                error = 'no native request windows captured'
            if error is None and any(not isinstance(w, dict) or type(w.get('success')) is not bool for w in windows):
                error = 'native request window success flag missing or malformed'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error = f'native request evidence unavailable: {exc}'
    if error is not None:
        request_count = None
        first_request_ok = None
    else:
        request_count = sum(window['success'] is True for window in windows)
        first_request_ok = windows[0]['success']
    return {'requests_completed': request_count, 'first_request_ok': first_request_ok,
            'request_count_evidence_error': error, 'result_writer_ok': True}


def main():
    mode=sys.argv[1:]
    if mode not in ([],['--smoke']):return 64
    root=Path(os.environ['W3_WORK_ROOT']);state={'rc':1,'partial':False,'first_request_ok':False,'result_writer_ok':False,'requests_completed':0,
      'canonical_W3_observed':False,'scope':'non-admitted twoCPU small-context native-instrument smoke' if mode else 'fresh canonical half-A W3 structural census; not fullP0d'}
    rc=1
    try:
        if sha(MODEL)!=MODEL_SHA:raise ValueError('canonical model full hash changed')
        if mode:smoke(root,state);rc=0
        else:
            import full_main
            rc=full_main.main()
            native_root=root/'native-full'
            latest=sorted(native_root.glob('out/*/SUMMARY.json'))[-1]
            summary=json.loads(latest.read_text());state.update(canonical_W3_observed=summary['state']=='OBSERVED',native_summary=str(latest),**full_census_request_fields(latest))
    except BaseException as error:state['error']=repr(error)
    finally:
        if (root/'server.log').exists():state['server_log_tail']=(root/'server.log').read_text(errors='replace')[-4096:]
        state['rc']=rc;write(root/'WORK-RESULT.json',state)
    return rc

if __name__=='__main__':raise SystemExit(main())
