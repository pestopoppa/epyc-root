#!/usr/bin/env python3
"""C5 candidate row-4c diagnostic producer; invoked only inside a keeper claim.

The result is a sampled diagnostic, not a deployment or promotion result.
Qualification has a separate short control, and publishes its first rowflow
unit only after sampler and captured server drain. Full target traffic is
single-exposure; a marker survives interruption. Never run this outside rowflow.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

import evaluate_replay
import device_identity
import mode_controller
import protocol_runner
import request_transport
import sampler
import server_lifecycle
import t7a_protocol
import target_guard
import warmup_protocol

D = Path('/mnt/raid0/llm/tmp/handoff-kvu-16i-c5-20261101')
BIN = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildhip/bin')
HIP = str(BIN / 'libggml-hip.so.0.16.0')
MODEL = '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFT = '/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
TEMPLATE = '/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja'
ID = 'handoff-kvu-16i-c5-replay-20261101'
PORT = 18196
EXPECTED_WARM = ['be915322f2cf616534a2525f0f08080a176facb131e7c24301d0128be2744f67',
                 '9fd468a92eca9af18d0a5e1523f9bf8ae45dfce470e19f9e6e4b5eadbc32275e']
SINK = D / 'progress.jsonl'


def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as src:
        for block in iter(lambda:src.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def atomic(path, data):
    path=Path(path);tmp=path.with_name(path.name+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:
        json.dump(data,out,sort_keys=True,allow_nan=False);out.write('\n');out.flush();os.fsync(out.fileno())
    os.replace(tmp,path)
    dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(dfd)
    finally:os.close(dfd)


class Stop:
    def __init__(self,path): self.path=Path(path);self.event=threading.Event()
    def is_set(self):return self.event.is_set() or self.path.exists()


def ensure(condition, reason):
    if not condition:raise RuntimeError(reason)


def command(slots):
    return [str(BIN/'llama-server'),'-m',MODEL,'--host','127.0.0.1','--port',str(PORT),
        '-np','4','-c','393216','-t','8','-ub','2048','--flash-attn','on','--jinja',
        '-ctk','q8_0','-ctv','q8_0','--kv-unified','--no-mmap','-ngl','all',
        '--cache-ram','65536','--chat-template-file',TEMPLATE,'-md',DRAFT,'-ngld','99',
        '--spec-type','draft-dflash','--spec-draft-n-max','7','--device','ROCm0',
        '--slot-save-path',str(slots),'--device-draft','ROCm0','--verbosity','4']


def healthy(port):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
    try:
        conn.request('GET','/health');resp=conn.getresponse();resp.read();return resp.status==200
    except OSError:return False
    finally:conn.close()


def sample_rows(path):
    if not path.exists():return []
    # Sampler may be appending concurrently: only complete newline-terminated
    # records count, so a transient final fragment is never parsed as evidence.
    raw=path.read_bytes();lines=raw.split(b'\n')[:-1]
    return [json.loads(line) for line in lines if line.strip()]


def run_session(*, raw_mode, stop, deadline, event_sink, exposure, grant_path, run_dir,
                server, sampler_factory, transport, device, wait_health=healthy, nap=time.sleep):
    """Execute one captured process; dependencies injected for offline tests.

    Completion and the qualification unit occur only after both sampler and
    server have drained; a fail/partial run produces no complete verdict.
    """
    selected=mode_controller.mode(raw_mode)
    ensure(not stop.is_set() and time.monotonic() < deadline,'stopped before start')
    ensure(not (selected=='full' and exposure.exists()),'prior target exposure; no redraw')
    grant_sha=file_hash(grant_path);plan_sha=file_hash(D/'PLAN.json')
    proof=os.environ.get('KVU16I_PIN_PROOF')
    ensure(proof and Path(proof).is_file(),'missing verified launcher pin/linkage proof')
    pin_sha=file_hash(proof)
    t7a=t7a_protocol.verified_t7a_bodies() if selected=='full' else []
    warm=warmup_protocol.bodies() if selected=='full' else []
    warm_sha=[hashlib.sha256(json.dumps(x).encode()).hexdigest() for x in warm]
    if selected=='full':ensure(warm_sha==EXPECTED_WARM,'warm-up source mismatch')
    phase={'name':'load'};samples=run_dir/'samples.jsonl';start=time.monotonic()
    info={'schema':'kvu16i.c5.capture-start.v1','mode':selected,'plan_sha256':plan_sha,
          'grant_sha256':grant_sha,'pin_proof_sha256':pin_sha,'pin_proof_path':proof,
          'source_catalog_sha256':file_hash(D/'SOURCE-SHA256SUMS'),
          'runtime_catalog_sha256':file_hash(D/'RUNTIME-INPUTS.sha256'),
          'start_monotonic':start,'argv':command(run_dir/'slots'),
          'server_binary_sha256':'802a3e0c7bcfcb23c661dd879ec6b12d76048a4525ac8a2aa3b336f561bfa6f4',
          'model_sha256':'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',
          'draft_sha256':'7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751',
          'regions':os.environ.get('WS58_REGIONS'),'cpus':os.environ.get('FILLER_CPUS'),
          'gpu_device_binding':device}
    atomic(run_dir/'capture-start.json',info)
    monitor=None; cleanup=None; outcome=None; work_error=None; load_end=None
    try:
        pid,birth=server.start()
        monitor=sampler_factory(pid,birth,HIP,samples,interval=.5,startup=True,phase=lambda:phase['name'],device=device).start()
        while True:
            ensure(not stop.is_set() and time.monotonic()<deadline,'stop or deadline during load')
            ensure(server.alive(),'server exited during load')
            ensure(not monitor.abort.is_set(),f'sampler refused: {monitor.reason}')
            rows=sample_rows(samples)
            ensure(all(r.get('gpu_id')==device['gpu_id'] and r.get('gpu_unique_id')==device['unique_id']
                       and r.get('gpu_bdf')==device['bdf'] for r in rows),'sampled GPU identity mismatch')
            resident=[r for r in rows if r.get('hip_resident') is True and r.get('own_vram_b',0)>0]
            if len(resident)>=2 and wait_health(PORT):break
            nap(.25)
        load_end=time.monotonic();phase['name']='warm'
        def target_guard_once():
            ensure(not stop.is_set() and not monitor.abort.is_set() and time.monotonic()<deadline,'stop before target')
            ensure(file_hash(grant_path)==grant_sha,'grant changed before target')
            target_guard.mark_once(exposure,plan_sha,grant_sha)
        def run_full():
            def wrapped(port,tag,body,digest,stop_,abort_,deadline_):
                if tag.startswith('warm-'):phase['name']='warm'
                else:phase['name']='t7a'
                return transport(port,tag,body,digest,stop_,abort_,deadline_)
            result=protocol_runner.run_sequence(PORT,warm,EXPECTED_WARM,t7a,wrapped,stop,monitor.abort,
                                                deadline,event_sink,target_guard_once)
            # Let a post-boundary sample arrive to bracket the end of T7A.
            limit=time.monotonic()+1.5
            while time.monotonic()<limit:
                ensure(not stop.is_set() and not monitor.abort.is_set(),'stop before trailing sample')
                rows=sample_rows(samples)
                if rows and rows[-1]['t']>=result['end_t']:break
                nap(.1)
            phase['name']='post'
            return result
        outcome=mode_controller.execute(raw_mode,PORT,stop,monitor.abort,deadline,event_sink,
                                        transport=transport,run_full=run_full)
    except BaseException as exc:
        work_error=f'{type(exc).__name__}: {exc}'
    finally:
        if monitor is not None and not monitor.stop():work_error=work_error or 'sampler did not drain'
        try:cleanup=server.close()
        except BaseException as exc:
            cleanup={'verified_dead':False,'error_type':type(exc).__name__};work_error=work_error or 'server cleanup failed'
    if monitor is not None and monitor.abort.is_set():work_error=work_error or f'sampler refusal: {monitor.reason}'
    if not cleanup or cleanup.get('verified_dead') is not True:work_error=work_error or 'server death unverified'
    rows=sample_rows(samples)
    ensure(rows or work_error,'no sampled residency')
    result={'schema':'kvu16i.c5.native-result.v1','mode':selected,'error':work_error,
            'cleanup':cleanup,'source_bound':True,'device_binding':device,'load_start_t':start,'load_end_t':load_end,
            'sample_count':len(rows),'verdict':'UNKNOWN'}
    if work_error is None and selected=='qualification':
        control=outcome['control'];result.update(verdict='CONTROL_COMPLETE',control=control)
    elif work_error is None:
        evidence={'capture_complete':True,'load_complete':True,'t7a_complete':True,
                  'cleanup_verified':True,'source_bound':True,'device_binding':device,'load_start_t':start,'load_end_t':load_end,
                  't7a_start_t':outcome['start_t'],'t7a_end_t':outcome['end_t']}
        result.update(evaluate_replay.evaluate([(t,h) for t,_,h in t7a],outcome['rows'],rows,evidence))
        result['t7a_start_t']=outcome['start_t'];result['t7a_end_t']=outcome['end_t']
    atomic(run_dir/'result.json',result)
    # Native receipt is emitted at the run boundary, binding all original raw inputs.
    receipt={'schema':'kvu16i.c5.native-receipt.v1','start_sha256':file_hash(run_dir/'capture-start.json'),
             'result_sha256':file_hash(run_dir/'result.json'),'sample_sha256':file_hash(samples) if samples.exists() else None,
             'events_sha256':file_hash(event_sink) if Path(event_sink).exists() else None,
             'grant_sha256':grant_sha,'partial':work_error is not None or result['verdict']=='UNKNOWN'}
    atomic(run_dir/'native-receipt.json',receipt)
    if selected=='qualification' and work_error is None:
        # First qualification result unit: only after cleanup and receipt durability.
        protocol_runner.append_event(event_sink,{'kind':'qualification_complete','result':str(run_dir/'result.json'),
                                               'receipt':str(run_dir/'native-receipt.json')})
    return result


def main():
    raw=os.environ.get('FILLER_DRYRUN');selected=mode_controller.mode(raw)
    ensure(os.environ.get('FILLER_ID')==ID,'wrong keeper row id')
    ensure(os.environ.get('FILLER_NEEDGPU')=='1','GPU grant required')
    ensure('mi210_0' in os.environ.get('WS58_REGIONS',''),'MI210 region required')
    ensure(str(PORT) in os.environ.get('FILLER_PORTS','').split(','),'scratch port not granted')
    device=device_identity.discover()
    stop=Stop(os.environ['FILLER_STOPFILE'])
    deadline=time.monotonic()+float(os.environ['FILLER_DEADLINE'])-time.time()
    ensure(deadline>time.monotonic(),'invalid or expired deadline')
    signal.signal(signal.SIGTERM,lambda *_:stop.event.set());signal.signal(signal.SIGINT,lambda *_:stop.event.set())
    run_dir=D/'runs'/f'{selected}-{time.time_ns()}';run_dir.mkdir(mode=0o700,parents=True)
    (run_dir/'slots').mkdir(mode=0o700)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LD_LIBRARY_PATH':str(BIN)+':/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib',
         'HIP_PATH':'/opt/rocm','ROCM_PATH':'/opt/rocm','GGML_IQK':'1'}
    server=server_lifecycle.Server(command(run_dir/'slots'),env,run_dir/'server.log',os.environ['FILLER_PIDFILE'])
    result=run_session(raw_mode=raw,stop=stop,deadline=deadline,event_sink=SINK,exposure=D/'TARGET-EXPOSED.json',
        grant_path=Path(os.environ['FILLER_GRANTS_DIR'])/(ID+'.grant'),run_dir=run_dir,
        server=server,sampler_factory=sampler.Sampler,transport=request_transport.execute,device=device)
    if result['verdict'] in ('CONTROL_COMPLETE','HOLDS','FAILS'):
        # Mode-specific completion is written after cleanup; use a new run id for retry.
        atomic(D/('QUALIFICATION.json' if selected=='qualification' else 'TERMINAL.json'),
               {'schema':'kvu16i.c5.complete.v1','mode':selected,'verdict':result['verdict'],
                'result':str(run_dir/'result.json'),'receipt':str(run_dir/'native-receipt.json')})
        return 0
    return 75

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(f'producer refused: {type(exc).__name__}: {exc}',file=sys.stderr);sys.exit(75)
