#!/usr/bin/env python3
"""Run native Test 6 with GDB captures made inside both test modes."""
import json, os, re, signal, subprocess, time, uuid
from pathlib import Path
import custody
import cleanup

D=Path(__file__).resolve().parent
GDB='/usr/bin/gdb'
ENTRY='_ZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEj'
DECODE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUlP13llama_contextiiE_clESA_ii'
RESTORE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUliRKS4_IhSaIhEEE_clEiSC_'

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f: json.dump(value,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def judge(log,witness,rc):
    pairs=re.findall(r'Test 6 mutation n_rs_seq=(0|8) mechanism=([a-z_]+)',log)
    allowed={'detected_stale_set_refused_after_valid_control','detected_stale_decode_refused_after_valid_control','detected_stale_logits_above_aa_floor'}
    modes={int(k):v for k,v in pairs}
    points={(x.get('mode'),x.get('point')) for x in witness.get('samples',[])}
    expected={(n,p) for n in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')}
    valid=(rc==0 and len(pairs)==2 and set(modes)=={0,8} and all(x in allowed for x in modes.values())
      and all(re.search(r'Test 6 PASS n_rs_seq='+str(n)+r'\b.*mutation=detected',log) for n in (0,8))
      and 'Test 6 SKIP' not in log and 'Test 6 INVALID' not in log and not witness.get('error')
      and [x['mode'] for x in witness.get('entries',[])]==[0,8] and points==expected)
    return {'status':'PASS' if valid else 'INVALID','mutation_mechanisms':modes,'test_rc':rc}

def safe_cleanup(witness, cleanup_fn=cleanup.cleanup):
    """An unverifiable inferior is INVALID; never claim it was terminated."""
    try:
        return cleanup_fn(witness.get('pid'),witness.get('birth_ticks'))
    except Exception as exc:
        return {'pid':witness.get('pid'),'birth_ticks':witness.get('birth_ticks'),
                'signals':None,'verified_dead':False,
                'reason':'cleanup verification failed: '+type(exc).__name__+': '+str(exc)}

def apply_cleanup(verdict,witness,interrupted,cleanup_fn=cleanup.cleanup):
    inferior=safe_cleanup(witness,cleanup_fn)
    if inferior['signals'] or not inferior['verified_dead'] or interrupted:
        verdict['status']='INVALID'
    return inferior

def main():
    binding=json.loads((D/'binding.json').read_text()); build=custody.build_identity(); model=custody.model_identity(D/'model.json')
    if build!=binding['build'] or model!=binding['model']: raise SystemExit('INVALID: build/model changed')
    for name,h in binding['runner_files'].items():
        if custody.digest(D/name)!=h: raise SystemExit('INVALID: runner changed')
    if custody.digest(GDB)!=binding['gdb_sha256']: raise SystemExit('INVALID: gdb changed')
    symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',build['binary']],text=True)
    for name in (ENTRY,DECODE,RESTORE):
        if sum(line.split()[-1:]==[name] for line in symbols.splitlines())!=1: raise SystemExit('INVALID: missing or ambiguous GDB symbol '+name)
    smoke=os.environ.get('FILLER_DRYRUN')=='1';out=Path(os.environ['FILLER_DRYRUN_DIR'])/'native' if smoke else D/'out'
    out.mkdir(parents=True,exist_ok=True);attempt=out/('attempt-'+uuid.uuid4().hex);attempt.mkdir()
    config={**build,'model_path':str(Path(model['path']).resolve(strict=True)),'model_sha256':model['sha256']};atomic(attempt/'config.json',config)
    stop=Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE']);cpus=os.environ['FILLER_CPUS'];threads=os.environ['FILLER_THREADS']
    if stop.exists() or time.time()>=deadline: raise SystemExit(75)
    env=dict(os.environ,LD_LIBRARY_PATH=str(Path(build['binary']).parent),KPF17_WITNESS_CONFIG=str(attempt/'config.json'),KPF17_WITNESS_OUTPUT=str(attempt/'witness.json'))
    env.pop('GGML_BACKEND_PATH',None)
    argv=['taskset','-c',cpus,GDB,'--batch','-nx','-ex','set confirm off','-ex','set startup-with-shell off','-ex','set auto-load python-scripts off','-ex','set disable-randomization off','-ex','set debuginfod enabled off','-ex','handle SIGTERM nostop noprint pass','-ex','source '+str(D/'witness.py'),'-ex','run','-ex','quit $_exitcode','--args',build['binary'],'-m',model['path'],'-ngl','0','-t',threads,'-b','32','-c','1024','-n','8','--seed','1234']
    interrupted=False
    with (attempt/'test.log').open('wb') as log:
        proc=subprocess.Popen(argv,cwd=attempt,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(proc.pid)+'\n');f.flush()
        try:
            while proc.poll() is None:
                if stop.exists() or time.time()>=deadline:
                    interrupted=True;os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                    break
                time.sleep(.1)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    try:witness=json.loads((attempt/'witness.json').read_text())
    except (OSError,ValueError):witness={'error':'missing native in-test witness'}
    verdict=judge((attempt/'test.log').read_text(errors='replace'),witness,proc.returncode)
    # A survivor is an invalid execution, even if cleanup succeeds.
    inferior=apply_cleanup(verdict,witness,interrupted)
    try:
        if custody.build_identity()!=build or custody.model_identity(D/'model.json')!=model:verdict['status']='INVALID'
    except Exception as exc:
        verdict['status']='INVALID';verdict['postrun_custody_error']=type(exc).__name__+': '+str(exc)
    result={'schema':'kpf17.oracle-test.v1',**verdict,'build':build,'model':model,'argv':argv,'gdb_sha256':binding['gdb_sha256'],
      'cpus':cpus,'threads':threads,'smoke':smoke,'witness':witness,'inferior_cleanup':inferior,
      'process_verified_dead':inferior['verified_dead'] and proc.poll() is not None,
      'mutation':'restore checkpoint one prefix token stale after same-destination valid control and reset',
      'files':{str(p):custody.digest(p) for p in (attempt/'test.log',attempt/'config.json')},'sealed':True,
      'scope':'native Test 6 with in-function mappings; no kernel or production verdict'}
    if (attempt/'witness.json').exists():result['files'][str(attempt/'witness.json')]=custody.digest(attempt/'witness.json')
    atomic(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json',result)
    if interrupted:raise SystemExit(75)
    if smoke and verdict['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
