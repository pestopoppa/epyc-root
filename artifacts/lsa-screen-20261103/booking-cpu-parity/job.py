#!/usr/bin/env python3
"""A single non-repeatable CPU parity attempt with live process custody."""
import datetime, hashlib, importlib.util, json, os, signal, subprocess, tempfile, time, traceback
from pathlib import Path
S = Path('/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103')
D = Path(__file__).resolve().parent
B = S/'build-cpu/bin'
SRC = S/'llama-champion'
MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
IDS = S/'parity-token-ids.txt'
SEAL = '332167ee6cd9cf569c912dec2bd1203b4c6ea2de1a62ae121f804cca55775875'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def save(path, value):
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value,indent=2)+'\n'); os.replace(tmp,path)
def check():
    if sha(S/'candidate-identity.json') != SEAL: raise ValueError('candidate seal changed')
    seal=json.loads((S/'candidate-identity.json').read_text())
    if seal['base_commit'] != 'c72ec82f5417bb2937310326120f149b665e8400': raise ValueError('base changed')
    ref=subprocess.check_output(['git','-C',str(SRC),'rev-parse','refs/heads/ak/champion/llama-cpp-ffc1bac82eec'],text=True).strip()
    if ref != seal['base_commit']: raise ValueError('champion ref changed')
    if sha(IDS) != '209249faab8ffb4bfe2e966b85b9caaa6628a427da237e0e158a76f31fb495ef' or len(IDS.read_text().split()) != 45: raise ValueError('token fixture changed')
    for f,h in seal['source_sha256'].items():
        if sha(SRC/f) != h: raise ValueError('source changed: '+f)
    for f,h in seal['artifact_sha256'].items():
        if f.startswith(str(B)+'/') and sha(f) != h: raise ValueError('artifact changed: '+f)
    return seal

def proc_stat(pid):
    stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return int(stat[19]),int(stat[11])+int(stat[12])

def run(arm, a, seal):
    if (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()): raise RuntimeError('STOP requested before '+arm)
    env=os.environ.copy()
    for k in list(env):
        if k.startswith('LLAMA_LSA_') or k == 'LSA_THREADS': env.pop(k)
    env['LD_LIBRARY_PATH']=str(B)
    env['OMP_NUM_THREADS']='4'
    env['LSA_PROBE_THREADS']='4'
    if arm=='all': env.update(LLAMA_LSA_SCREEN='all', LLAMA_LSA_PYTHON='/mnt/raid0/llm/epyc-inference-research/.venv/bin/python', LLAMA_LSA_WORKER=str(SRC/'experiments/lsa-screen/mask_worker.py'), LLAMA_LSA_TRACE=str(a/'trace.jsonl'), LSA_THREADS='1')
    with (a/f'{arm}.log').open('wb') as log, (a/f'{arm}-monitor.jsonl').open('w') as witness:
        p=subprocess.Popen([str(B/'lsa-dump-logits'),str(MODEL),str(IDS),str(a/f'{arm}.bin')],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        started=time.monotonic(); loaded=None; last_ticks=None; last_active=started; libs_seen=set(); model_seen=False; identity=None; digests={}
        try:
            while p.poll() is None:
                now=time.monotonic()
                if (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()): raise RuntimeError('STOP requested during '+arm)
                text=(a/f'{arm}.log').read_text(errors='replace')
                if loaded is None and ('llama_init_from_model:' in text or 'llama_context:' in text): loaded=now; last_active=now
                try:
                    start_ticks,ticks=proc_stat(p.pid)
                    exe=os.path.realpath(os.readlink(f'/proc/{p.pid}/exe'))
                    args=Path(f'/proc/{p.pid}/cmdline').read_bytes().split(b'\0'); args=[x.decode(errors='replace') for x in args if x]
                    this=(start_ticks,exe,tuple(args))
                    if identity is None: identity=this
                    if this != identity or exe != str((B/'lsa-dump-logits').resolve()): raise RuntimeError('process identity changed')
                    if args != [str(B/'lsa-dump-logits'),str(MODEL),str(IDS),str(a/f'{arm}.bin')]: raise RuntimeError('process arguments changed')
                    if last_ticks is None or ticks>last_ticks: last_active=now
                    last_ticks=ticks
                    libs=[]; model=[]
                    for line in Path(f'/proc/{p.pid}/maps').read_text().splitlines():
                        parts=line.split(maxsplit=5)
                        if len(parts)<6 or not parts[5].startswith('/'): continue
                        path=parts[5].removesuffix(' (deleted)'); real=os.path.realpath(path)
                        if real==str(MODEL.resolve()):
                            st=MODEL.stat()
                            if int(parts[4]) != st.st_ino: raise RuntimeError('model mapped inode mismatch')
                            model_seen=True; model.append({'path':real,'inode':st.st_ino,'size':st.st_size,'device':st.st_dev})
                        if 'libggml' in path or 'libllama' in path:
                            f=Path(real); st=f.stat()
                            if not f.is_relative_to(B.resolve()) or 'hip' in real.lower(): raise RuntimeError('unexpected library '+real)
                            if int(parts[4]) != st.st_ino: raise RuntimeError('library mapped inode mismatch')
                            key=(real,st.st_ino,st.st_size,st.st_mtime_ns)
                            if key not in digests: digests[key]=sha(f)
                            if seal['artifact_sha256'].get(real) != digests[key]: raise RuntimeError('mapped library differs from seal: '+real)
                            libs_seen.add(real); libs.append({'path':real,'inode':st.st_ino,'size':st.st_size,'sha256':digests[key]})
                    witness.write(json.dumps({'elapsed_s':now-started,'loaded':loaded is not None,'pid':p.pid,'start_ticks':start_ticks,'exe':exe,'argv':args,'cpu_ticks':ticks,'model_mappings':model,'libraries':libs})+'\n');witness.flush()
                except FileNotFoundError:
                    if p.poll() is None: raise
                if loaded is None and now-started>120: raise TimeoutError('model load grace 120s expired')
                if loaded is not None and now-loaded>120: raise TimeoutError('execution exceeded 120s')
                if loaded is not None and now-last_active>30: raise TimeoutError('no CPU progress for 30s')
                time.sleep(1)
            if p.returncode or not libs_seen or not model_seen: raise RuntimeError(f'{arm}: rc={p.returncode}; libs={bool(libs_seen)} model={model_seen}')
            logtext=(a/f'{arm}.log').read_text(errors='replace')
            if 'LSA_LOGITS ' not in logtext: raise RuntimeError('missing final configuration witness')
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);p.wait()
            if p.poll() is None: raise RuntimeError('owned process failed to terminate')
            witness.write(json.dumps({'pid':p.pid,'exit_rc':p.returncode,'verified_dead':p.poll() is not None})+'\n');witness.flush()

def terminal(a, result):
    manifest=D.parent/'parity-manifest.json'
    binding={'source_commit':'c72ec82f5417bb2937310326120f149b665e8400', 'candidate_identity':str(S/'candidate-identity.json'), 'candidate_identity_sha256':SEAL, 'native_paths':result['native_paths'], 'provenance_path':str(a/'provenance.json'), 'decision_rule':'finite full-vocabulary logits, max_abs <= 1e-5, exact argmax, 16 global layers and no mask changes', 'loaded_byte_proof':'model path inode size and live mapping observed; manifest hash is precomputed and is not a fresh loaded-byte hash'}
    for key in ('dense_log','all_log','dense_monitor','all_monitor','trace'):
        path=Path(result['native_paths'][key])
        if path.is_file(): binding[key+'_sha256']=sha(path)
    if (a/'provenance.json').is_file(): binding['provenance_sha256']=sha(a/'provenance.json')
    status={'pass':'pass','fail':'failure'}.get(result['status'],'invalid')
    record={'schema':'lsa-screen-raw-v1','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'manifest_sha256':sha(manifest),'item':json.loads(manifest.read_text())['rows'][0], 'arm':'all_keys','phase':'conformance','status':status,'score':result.get('passed') if status!='invalid' else None,'output':json.dumps({'scope':'45-token all-keys logits conformance only; no retrieval quality or speed claim','passed':result.get('passed'),'max_abs':result.get('max_abs'),'dense_argmax':result.get('dense_argmax'),'oracle_argmax':result.get('oracle_argmax'),'invalid_reason':result.get('invalid_reason')},sort_keys=True),'ttft':None,'tpot':None,'binding':binding}
    raw=a/'parity-conformance.raw.json'
    try:
        with raw.open('x') as f: json.dump(record,f,sort_keys=True,allow_nan=False);f.write('\n')
        spec=importlib.util.spec_from_file_location('lsa_native_evidence',D.parent/'native_evidence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result['evidence_receipt']=str(module.emit(record,manifest,raw))
    except Exception as e:
        result.update(status='invalid',rc=1,invalid_reason='producer evidence hook failed: '+str(e),passed=None)
    save(a/'RESULT.json',result)
    (a/'PENDING.json').unlink(missing_ok=True)

def main():
    a=D/'ATTEMPT_FENCE'
    try: a.mkdir()
    except FileExistsError:
        if (a/'RESULT.json').is_file(): return 0
        pending=a/'PENDING.json'
        if not pending.is_file(): return 75
        result=json.loads(pending.read_text()); owner=result.get('owner_pid'); born=result.get('owner_start_ticks')
        try: current,_=proc_stat(owner)
        except (FileNotFoundError,ProcessLookupError): current=None
        if current==born: return 75
        result.update(status='invalid',rc=1,invalid_reason='previous attempt owner proved dead; no rerun',passed=None)
        terminal(a,result)
        return 1
    # Invalid terminal record is durable even if killed uncatchably; only successful completion replaces it.
    result={'status':'invalid','rc':1,'invalid_reason':'interrupted or incomplete attempt','passed':None,'max_abs':None,'dense_argmax':None,'oracle_argmax':None,'native_paths':{k:str(a/v) for k,v in {'dense':'dense.bin','all':'all.bin','trace':'trace.jsonl','dense_log':'dense.log','all_log':'all.log','dense_monitor':'dense-monitor.jsonl','all_monitor':'all-monitor.jsonl'}.items()}}
    result.update(owner_pid=os.getpid(),owner_start_ticks=proc_stat(os.getpid())[0])
    save(a/'PENDING.json',result)
    def terminate(signum, frame): raise RuntimeError(f'received signal {signum}')
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        cpus=sorted(os.sched_getaffinity(0))
        if cpus not in [list(range(i,i+4)) for i in (0,24,48,72)]: raise RuntimeError(f'invalid four-core affinity: {cpus}')
        grant=Path(os.environ.get('FILLER_GRANTS_DIR','/nonexistent'))/'lsa-screen-1-cpu-parity-20261103.grant'
        lock=subprocess.run(['/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock','status'],text=True,capture_output=True,timeout=10)
        quarter='q'+str(cpus[0]//24)
        if lock.returncode or not any(line.strip().startswith(quarter+' ') and 'filler-lsa-screen-1-cpu-parity-20261103' in line for line in lock.stdout.splitlines()): raise RuntimeError('own quarter lock not visible')
        save(a/'provenance.json',{'affinity':cpus,'admission_classification':'private qualification token' if os.environ.get('FILLER_DRYRUN')=='1' else 'grant token (allocator provenance not independently verified)', 'grant_path':str(grant),'grant_text':grant.read_text() if grant.exists() else None,'region_lock_rc':lock.returncode,'region_lock_stdout':lock.stdout,'region_lock_stderr':lock.stderr,'candidate_seal':SEAL,'launcher_sha256':sha(D/'launcher.sh'),'job_sha256':sha(D/'job.py'),'spec_sha256':sha(D/'spec.json'),'model_manifest':str(D.parent/'parity-manifest.json'),'model_manifest_sha256':sha(D.parent/'parity-manifest.json'),'model_path':str(MODEL),'declared_model_sha256':json.loads((D.parent/'parity-manifest.json').read_text())['model_sha256'],'loaded_byte_proof':'manifest digest plus observed model path inode and size; no fresh model hash', 'model_stat':{'inode':MODEL.stat().st_ino,'size':MODEL.stat().st_size,'device':MODEL.stat().st_dev}})
        seal=check();run('dense',a,seal);run('all',a,seal)
        check_result=a/'checker.json'
        p=subprocess.run(['/usr/bin/python3',str(SRC/'experiments/lsa-screen/check_logits.py'),str(a/'dense.bin'),str(a/'all.bin'),str(a/'trace.jsonl'),str(a/'dense.log'),str(a/'all.log'),','.join(map(str,cpus)),str(check_result)])
        if not check_result.exists(): raise RuntimeError(f'checker failed without result rc={p.returncode}')
        result.update(json.loads(check_result.read_text()))
        result.update(status='pass' if p.returncode==0 else 'fail',rc=p.returncode,invalid_reason=None)
    except BaseException as e:
        result['invalid_reason']=f'{type(e).__name__}: {e}';result['traceback']=traceback.format_exc()
    finally: terminal(a,result)
    return result['rc']
if __name__=='__main__': raise SystemExit(main())
