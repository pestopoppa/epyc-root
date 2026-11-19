#!/usr/bin/env python3
"""PF1 admitted-window driver. The caller must hold GPU quiet for its lifetime.

CPU ownership is acquired separately for cache preparation and by the canonical
wrapper for each invocation. This file is not a grant or launcher.
"""
import hashlib, json, os, shutil, signal, subprocess, sys, time
from pathlib import Path
import controller, native_executor, prepare_manifest

D=Path(__file__).resolve().parent
RL=Path('/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock')
interrupted=False

def on_signal(signum, frame):
    global interrupted
    interrupted=True
    raise KeyboardInterrupt(f'signal {signum}')

def admit(phase):
    expected=f'brf-exp04-pf1-full-{phase}-20261104-r7'
    if os.environ.get('FILLER_ID')!=expected: raise ValueError('wrong grant identity')
    if os.environ.get('FILLER_CPUS')!='0-95': raise ValueError('whole-host grant required')
    stop=Path(os.environ.get('FILLER_STOPFILE',''))
    if os.environ.get('FILLER_DRYRUN')=='1':
        if not stop.is_absolute() or stop.exists(): raise ValueError('invalid dry-run STOP path')
    elif stop!=D/f'STOP-{phase}' or stop.exists(): raise ValueError('wrong STOP file')
    deadline=int(os.environ['FILLER_DEADLINE'])
    grant=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(expected+'.grant')
    grant_bytes=grant.read_bytes()
    grant_hash=hashlib.sha256(grant_bytes).digest()
    def active():
        try: unchanged=hashlib.sha256(grant.read_bytes()).digest()==grant_hash
        except OSError: unchanged=False
        return not interrupted and unchanged and not stop.exists() and time.time()<deadline
    if not active(): raise ValueError('grant absent, STOP or deadline')
    return deadline,stop,active

def run_owned(argv, active, log):
    with Path(log).open('wb') as output:
        p=subprocess.Popen(argv,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while p.poll() is None:
                if not active(): raise TimeoutError('grant ended, STOP or deadline')
                time.sleep(.25)
        except BaseException:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); p.wait()
            raise
        if p.returncode: raise RuntimeError(f'owned command failed rc={p.returncode}; see {log}')

def revalidate(w,active=None):
    controller.check_warrant(w)
    current=prepare_manifest.served_identity()
    if any(current[k]!=w['served_identity'][k] for k in ('role','model','shard_sha256')): raise ValueError('served identity changed since initial session')
    if any(prepare_manifest.sha(path)!=value for path,value in w['verifier_sources'].items()): raise ValueError('verifier source changed')
    _receipt,receipt_sha=prepare_manifest.verify_build_receipt(active)
    if receipt_sha!=w.get('build_receipt_sha256'): raise ValueError('C6 build receipt changed since frozen manifest')
    for item in w['model_shards']:
        if prepare_manifest.sha(item['path'],check=active)!=item['sha256']: raise ValueError('model shard changed')
    for item in w['binary_inventory'].values():
        if prepare_manifest.sha(item['path'])!=item['sha256']: raise ValueError('binary changed')
        for path,sha in item['libraries'].items():
            if prepare_manifest.sha(path)!=sha: raise ValueError('library changed')
    for path,key in ((native_executor.MONITOR,'monitor_sha256'),(native_executor.WRAPPER,'wrapper_sha256'),(native_executor.ROOT/'scripts/lib/canonical_recipe.py','recipe_sha256')):
        if prepare_manifest.sha(path)!=w[key]: raise ValueError(f'{key} changed')

def require_idle_gpu(w, active, output):
    mon=native_executor.cpu_monitor(w); readings=[]
    for i in range(2):
        if not active(): raise ValueError('grant/STOP/deadline during idle check')
        smi=native_executor.gpu_sample(); owners=mon.kfd_ownership()
        if smi.get('rc')!=0 or owners.get('users'): raise ValueError('GPU not idle or uninspectable')
        readings.append({'gpu':smi,'kfd':owners,'vram_bytes':native_executor.total_vram(smi)})
        if i==0: time.sleep(1)
    if abs(readings[1]['vram_bytes']-readings[0]['vram_bytes'])>1048576: raise ValueError('GPU baseline is unstable')
    controller.write(output,readings)

def smoke(phase):
    """One actual A1/128/ub512 native cell for rowflow first-progress; kept outside the planned denominator."""
    if phase!='initial' or os.environ.get('FILLER_DRYRUN')!='1': raise ValueError('native preflight is initial-row only')
    result_path=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    if not result_path.is_absolute() or result_path.name!='native-result.json' or result_path.exists(): raise ValueError('invalid/used rowflow native-result path')
    deadline,stop,active=admit(phase)
    manifest=result_path.parent/'pf1-build-model-manifest.json'
    warrant=prepare_manifest.create(manifest,check=active)
    cell={'arm':'A1','L':128,'ub':512,'rep':'rowflow-smoke','n':1}
    out=result_path.parent/'native-cell';out.mkdir(exist_ok=False)
    result=native_executor.execute(cell,warrant,out,deadline,str(stop),active=active)
    if result.get('status')!='ok' or not result.get('samples_ts') or not result.get('evidence',{}).get('nonzero_vram_during'):
        raise ValueError('actual short native GPU cell, response, cleanup, or in-window residency failed')
    record={'schema':'pf1.native-first-progress.v1','cell':cell,'prompt_tps_samples':result['samples_ts'],
            'prompt_tps_median':__import__('statistics').median(result['samples_ts']),
            'build_line':result['evidence']['build_line'],'placement':result['evidence']['placement'],
            'vram_during':result['evidence']['vram'],'native_capture':str(out),'manifest_sha256':warrant['manifest_sha256']}
    controller.write(result_path,record)
    return 0

def main(phase):
    if os.environ.get('FILLER_DRYRUN')=='1': return smoke(phase)
    if phase not in ('initial','holdout'): raise ValueError('invalid phase')
    deadline,stop,active=admit(phase)
    attempts=D/'attempts'; attempts.mkdir(exist_ok=True)
    warrant_path=attempts/'initial'/'manifest.json'
    initial=None
    if phase=='holdout':
        initial=json.loads((attempts/'initial'/'run'/'receipt.json').read_text())
        if initial.get('status')!='complete' or initial.get('phase')!='initial' or initial.get('self_sha256')!=controller.digest({k:v for k,v in initial.items() if k!='self_sha256'}): raise ValueError('initial receipt invalid')
        if time.time()-initial['finished_at']<14400: raise ValueError('holdout starts too early')
    session=attempts/phase; resume=session.exists()
    if not resume:
        session.mkdir()
        session_id=f'{phase}-{os.getpid()}-{time.time_ns()}'
        state={'session_id':session_id,'phase':phase,'started_at':time.time()}
        state['self_sha256']=controller.digest(state); controller.write(session/'session.json',state)
    else:
        state=json.loads((session/'session.json').read_text())
        if state.get('phase')!=phase or state.get('self_sha256')!=controller.digest({k:v for k,v in state.items() if k!='self_sha256'}): raise ValueError('session custody mismatch')
        session_id=state['session_id']
        prior=session/'run'/'receipt.json'
        if prior.exists():
            old=json.loads(prior.read_text())
            if old.get('self_sha256')!=controller.digest({k:v for k,v in old.items() if k!='self_sha256'}): raise ValueError('prior receipt corrupted')
            if old.get('status')=='complete': raise ValueError('phase already complete; no redraw')
            existing=list((session/'run').glob('cell-*.json'))
            if len(existing)==old.get('planned') and all(json.loads(p.read_text()).get('attempted',True) for p in existing):
                raise ValueError('no unattempted cells remain; no redraw')
    if phase=='initial':
        if warrant_path.exists(): w=json.loads(warrant_path.read_text()); revalidate(w,active)
        else: w=prepare_manifest.create(warrant_path,check=active)
        initial=None; lengths=controller.LENGTHS
    else:
        w=json.loads(warrant_path.read_text()); revalidate(w,active)
        lengths=tuple(initial['holdout_lengths'])
    require_idle_gpu(w,active,session/'gpu-idle.json')
    cells=session/'native'; cells.mkdir(exist_ok=True)
    run_path=session/'run'
    if resume and run_path.exists():
        history=session/'history'; history.mkdir(exist_ok=True)
        shutil.copytree(run_path,history/f'run-{time.time_ns()}')
    planned=controller.grid(lengths,controller.UBS,phase=='holdout')
    halted=False
    def execute(cell):
        nonlocal halted
        index=planned.index(cell)
        try:
            if not active(): raise ValueError('grant/STOP/deadline')
            prep=session/f'prep-{index:04d}.json'
            # The admitted filler row already owns 0-95 plus GPU quiet. Run cache prep
            # directly under that claim; taking a second region-lock here would deadlock.
            run_owned([sys.executable,'-B',str(D/'cache_prepare.py'),str(warrant_path),str(prep)],active,session/f'prep-{index:04d}.log')
            result=native_executor.execute(cell,w,cells/f'cell-{index:04d}',deadline,str(stop),active=active)
            if result.get('status')!='ok': halted=True
            return result
        except BaseException:
            halted=True
            raise
    receipt=controller.run(run_path,w,execute,phase=phase,lengths=lengths,initial=initial,session_id=session_id,admit_cell=lambda _:active() and not halted,resume=resume and run_path.exists())
    # Preserve the completed holdout receipt only. P3-3's descriptive comparison
    # is not a final crossover/serving decision; that requires the separate planning-context canary.
    rows=[]
    for path in sorted(session.rglob('*')):
        if path.is_file() and path.name!='SHA256SUMS': rows.append(f'{prepare_manifest.sha(path)}  {path.relative_to(session)}\n')
    (session/'SHA256SUMS').write_text(''.join(rows))
    return 0 if receipt['status']=='complete' else 2

if __name__=='__main__':
    signal.signal(signal.SIGTERM,on_signal); signal.signal(signal.SIGINT,on_signal)
    try: sys.exit(main(sys.argv[1]))
    except Exception as exc:
        print(f'PF1 refused: {exc}',file=sys.stderr); sys.exit(2)
