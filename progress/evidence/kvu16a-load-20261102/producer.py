#!/usr/bin/env python3
"""Isolated load-only KVU-16a measurement, with own-PID residency sampling."""
import hashlib
import http.client
import json
import os
import re
from pathlib import Path
import signal
import sys
import tempfile
import time
import device_identity
import sampler
import server_lifecycle

D=Path('/mnt/raid0/llm/tmp/kvu16a-load-20261102')
BIN=Path('/mnt/raid0/llm/kernels/production/gpu')
MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFT='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
TEMPLATE='/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja'
PORT=18197

def healthy():
    c=http.client.HTTPConnection('127.0.0.1',PORT,timeout=1)
    try:
        c.request('GET','/health');r=c.getresponse();r.read();return r.status==200
    except OSError:return False
    finally:c.close()

def target_kv_gib(log):
    # Bind the load subtraction to the observed 393216-cell Q8 target KV line.
    pattern=r'llama_kv_cache: size =\s*([0-9.]+) MiB \(393216 cells,\s*16 layers,\s*4/1 seqs\), K \(q8_0\)'
    values=re.findall(pattern,Path(log).read_text(errors='replace'))
    if len(values)!=1:raise RuntimeError('expected one shape-matched target KV allocation in server log')
    return float(values[0])/1024

def main():
    if os.environ.get('FILLER_NEEDGPU')!='1':raise RuntimeError('GPU grant missing')
    mode=os.environ.get('FILLER_DRYRUN')
    if mode not in ('0','1'):raise RuntimeError('mode missing')
    out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if mode=='1' else D/'result.json'
    run=Path(tempfile.mkdtemp(prefix='smoke-' if mode=='1' else 'run-', dir=D));os.chmod(run,0o700)
    (run/'slots').mkdir(mode=0o700)
    stop=False
    def signal_stop(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,signal_stop);signal.signal(signal.SIGINT,signal_stop)
    deadline=int(os.environ['FILLER_DEADLINE'])-30
    device=device_identity.discover()
    cmd=[str(BIN/'llama-server'),'-m',MODEL,'--host','127.0.0.1','--port',str(PORT),'-np','4','-c','393216',
         '-b','512','-ub','512','-t','8','--ctx-checkpoints','32','--flash-attn','on','--jinja',
         '-ctk','q8_0','-ctv','q8_0','--kv-unified','--no-mmap','-ngl','all','--cache-ram','65536',
         '--chat-template-file',TEMPLATE,'-md',DRAFT,'-ngld','99','--spec-type','draft-dflash',
         '--spec-draft-n-max','7','--device','ROCm0','--device-draft','ROCm0','--slot-save-path',str(run/'slots'),
         '--verbosity','4']
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LD_LIBRARY_PATH':str(BIN)+':/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib','HIP_PATH':'/opt/rocm','ROCM_PATH':'/opt/rocm','GGML_IQK':'1'}
    server=server_lifecycle.Server(cmd,env,run/'server.log',os.environ['FILLER_PIDFILE'])
    monitor=None;clean=None;error=None;sample=None;healthy_t=None;resident=[]
    try:
        pid,birth=server.start()
        hip=str((BIN/'libggml-hip.so.0').resolve())
        monitor=sampler.Sampler(pid,birth,hip,run/'samples.jsonl',startup=True,device=device).start()
        while time.time()<deadline and not stop and not Path(os.environ['FILLER_STOPFILE']).exists():
            if not server.alive() or monitor.abort.is_set():raise RuntimeError('server or sampler failed')
            last=monitor.last
            if last and last['hip_resident'] and last['own_vram_b']>0:
                if healthy_t is None and healthy():healthy_t=time.monotonic()
                if healthy_t is not None and last['t']>=healthy_t and (not resident or last['t']>resident[-1]['t']):
                    resident.append(last)
                if len(resident)>=2:sample=max(resident,key=lambda s:s['own_vram_b']);break
            time.sleep(.5)
        if sample is None:raise RuntimeError('no healthy resident sample before stop')
    except BaseException as e:error=f'{type(e).__name__}: {e}'
    finally:
        if monitor and not monitor.stop():error=error or 'sampler did not drain'
        try:clean=server.close()
        except BaseException as e:error=error or f'cleanup: {e}'
    if error or not clean or not clean.get('verified_dead'):raise RuntimeError(error or 'cleanup unverified')
    kv_gib=target_kv_gib(run/'server.log')
    rec={'schema':'kvu16a.load.v1','mode':'qualification' if mode=='1' else 'full','load_sample':sample,
         'healthy_sample_count':len(resident),'load_gib':sample['own_vram_b']/2**30,'kv_pool_gib_observed':kv_gib,
         'non_kv_gib':sample['own_vram_b']/2**30-kv_gib,
         'argv':cmd,'cleanup':clean,'run_dir':str(run),'model_catalog':str(D/'model.sha256'),
         'model_receipt_sha256':hashlib.sha256((D/'model-receipt.json').read_bytes()).hexdigest(),
         'linkage_proof':str(D/('linkage-'+mode+'.txt')),
         'linkage_proof_sha256':hashlib.sha256((D/('linkage-'+mode+'.txt')).read_bytes()).hexdigest(),
         'interpretation':'load sample minus observed target KV; verify runtime shape and identity before registry use'}
    out.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as f:json.dump(rec,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(f'load measurement refused: {e}',file=sys.stderr);sys.exit(75)
