#!/usr/bin/python3
"""Actual current-CPU W2 image path; smoke is explicitly non-admitted geometry."""
import concurrent.futures
import hashlib,json,os,socket,subprocess,sys,time,urllib.request,urllib.error,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;sys.path[:0]=[str(D),str(D/'producer')]
from server_probe_full import request,own_sample
from affinity_scope import within
from golden_lifecycle import await_port_ready,wait_owned_health,stop_owned
from multimodal_request import smoke_body,require_capabilities
from mm_evidence import image_evidence
from server_evidence_full import graph_evidence
from w2_microbatch import native_prefill_witnesses
from types import SimpleNamespace

def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()
def wire(root,port,body,index,windows):
    raw=json.dumps(body,sort_keys=True).encode();stem=root/f'request-{index:04d}'
    stem.with_suffix('.request.json').write_bytes(raw)
    w={'start_mono_ns':time.monotonic_ns(),'start_utc_ns':time.time_ns(),'success':False}
    try:
        req=urllib.request.Request(f'http://127.0.0.1:{port}/completion',data=raw,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=180) as response:data=response.read((16<<20)+1)
        except urllib.error.HTTPError as error:
            data=error.read((16<<20)+1);stem.with_suffix('.error.raw').write_bytes(data);raise
        stem.with_suffix('.response.raw').write_bytes(data)
        if len(data)>16<<20:raise ValueError('response exceeds bound')
        result=json.loads(data);w['success']=True;return result
    finally:
        w['end_mono_ns']=time.monotonic_ns();w['end_utc_ns']=time.time_ns();windows.append(w)
        write(stem.with_suffix('.window.json'),w)

def smoke(root,state):
    cpus=sorted(os.sched_getaffinity(0));mask=','.join(map(str,cpus));p=json.loads((D/'recipes.json').read_text())['workloads'][0]
    if len(cpus)!=2 or max(cpus)>=96 or cpus[0]//24!=cpus[-1]//24:raise ValueError('two primary CPUs in free quarter required')
    argv=list(p['argv']);argv[argv.index('-c')+1]=mask;argv[argv.index('--interleave=0,1')]='--membind='+str(cpus[0]//24)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    for flag,value in [('--port',port),('-c',4096),('-t',2),('-ub',64),('--image-min-tokens',16),('--cache-ram',0),('--slot-save-path',root/'runtime-slots')]:
        start=argv.index(p['binary']);index=next((i for i in range(start,len(argv)) if argv[i]==flag),None)
        if index is None:argv.extend([flag,str(value)])
        else:argv[index+1]=str(value)
    if '--mlock' in argv:argv.remove('--mlock')
    (root/'runtime-slots').mkdir();env=dict(p['env'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',FILLER_CPUS=mask)
    trace_path=root/'native-trace.log';trace_path.touch(mode=0o600,exist_ok=False);env['CENSUS_NATIVE_TRACE']=str(trace_path)
    proc=None
    try:
        await_port_ready(port)
        with (root/'server.log').open('wb') as log:
            proc=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
            wait_owned_health(proc,port,lambda:request(port,'health').get('status')=='ok',timeout=120)
            models=request(port,'v1/models');props=request(port,'props');write(root/'capabilities.json',{'models':models,'props':props});require_capabilities(models,props,p['model'])
            if props.get('media_marker')!=p['env']['LLAMA_MEDIA_MARKER']:raise ValueError('actual native media marker differs from pinned request input')
            first=time.time();samples=[];components=[]
            while True:
                index=state['requests_completed'];body=smoke_body(index);body['prompt']['prompt_string'] += ' red square'*48;windows=[];offset=(root/'server.log').stat().st_size;trace_offset=trace_path.stat().st_size
                with concurrent.futures.ThreadPoolExecutor(1) as pool:
                    future=pool.submit(wire,root,port,body,index,windows)
                    while not future.done():
                        row=own_sample(proc.pid,gpu=False,phase='requests',port=port);samples.append(row)
                        if not within(row['task_affinity'],mask):raise ValueError('native server thread escaped smoke mask')
                        time.sleep(.05)
                    response=future.result()
                # Exact response bytes were written by wire before any semantic guard.
                if response.get('tokens_predicted',response.get('timings',{}).get('predicted_n'))!=16:raise ValueError('native image completion incomplete')
                blob=(root/'server.log').read_bytes();trace=trace_path.read_bytes();full=blob.decode(errors='replace')+'\n'+trace.decode(errors='replace');phase=blob[offset:].decode(errors='replace')+'\n'+trace[trace_offset:].decode(errors='replace');image=image_evidence(full,phase,model=p['model'],mmproj=p['projector'],windows=windows)
                native=graph_evidence(full,phase,p['model'])
                witnesses=native_prefill_witnesses(SimpleNamespace(phase='prefill',n_tokens=64,n_seq=1),native,phase,windows,[64],smoke=True)
                if not witnesses:raise ValueError('smoke lacks exact64 native microbatch inside successful single-sequence request window')
                write(root/f'request-{index:04d}.microbatch.json',{'scope':'non-admitted smoke64; full512 unchanged','witnesses':witnesses})
                components.append(image);write(root/'image-evidence.json',components)
                state.update(first_request_ok=True,requests_completed=index+1,real_request_span_s=time.time()-first,result_writer_ok=True,image_encodes=sum(len(x['encodes']) for x in components))
                write(root/'WORK-RESULT.json',state)
                if state['real_request_span_s']>=60:break
            if not samples or not any(str(Path(p['instrument_library']).resolve()) in row['loaded_instrument'] for row in samples):raise ValueError('exact additive instrument not mapped')
            for row in samples:
                if any(not Path(f).resolve().is_relative_to(Path(p['build_dir']).resolve()/'bin') for f in row['loaded_ggml']):raise ValueError('foreign GGML mapping')
            write(root/'samples.json',samples);state['native_trace_sha256']=sha(trace_path)
    finally:state['server_cleanup']=stop_owned(proc)

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
    root=Path(os.environ['W3_WORK_ROOT']);state={'rc':1,'partial':False,'first_request_ok':False,'result_writer_ok':False,'requests_completed':0,'current_W2_CPU_observed':False,'historical_GPU_W2_closed':False,'scope':'non-admitted twoCPU4096ctx/ub64/image-min16 actual image-encoder+LLM smoke' if mode else 'fresh current exported W2 CPU prefill512/decode1+image component; oldGPUW2 and fullP0d open'};rc=1
    try:
        models=json.loads((D/'MODELS.json').read_text())
        for path,pin in models.items():
            if sha(path)!=pin['sha256']:raise ValueError('canonical full model/projector hash changed: '+path)
        state['models_full_hash_verified']=list(models)
        if mode:smoke(root,state);rc=0
        else:
            import full_main
            rc=full_main.main();latest=sorted((root/'native-full').glob('out/*/SUMMARY.json'))[-1];summary=json.loads(latest.read_text());state.update(current_W2_CPU_observed=summary['state']=='OBSERVED',native_summary=str(latest),**full_census_request_fields(latest))
    except BaseException as error:
        state['error']=str(error);state['error_type']=type(error).__name__; (root/'error.traceback.txt').write_text(traceback.format_exc())
    finally:
        if (root/'server.log').exists():state['server_log_tail']=(root/'server.log').read_text(errors='replace')[-4096:]
        state['rc']=rc;write(root/'WORK-RESULT.json',state)
    return rc
if __name__=='__main__':raise SystemExit(main())
