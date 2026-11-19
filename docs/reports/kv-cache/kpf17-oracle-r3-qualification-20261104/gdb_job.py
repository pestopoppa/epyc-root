#!/usr/bin/env python3
"""Run native Test 6 with GDB captures made inside both test modes."""
import ctypes, json, os, re, signal, subprocess, time, uuid
from pathlib import Path
import custody
import cleanup
import runtime_witness

D=Path(__file__).resolve().parent
GDB='/usr/bin/gdb'
ENTRY='_ZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEj'
DECODE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUlP13llama_contextiiE_clESA_ii'
RESTORE='_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUliRKS4_IhSaIhEEE_clEiSC_'

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f: json.dump(value,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def judge(log,witness,rc,build,model):
    pairs=re.findall(r'Test 6 mutation n_rs_seq=(0|8) mechanism=([a-z_]+)',log)
    allowed={'detected_stale_set_refused_after_valid_control','detected_stale_decode_refused_after_valid_control','detected_stale_logits_above_aa_floor'}
    modes={int(k):v for k,v in pairs}
    points={(x.get('mode'),x.get('point')) for x in witness.get('samples',[])}
    expected={(n,p) for n in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')}
    valid=(rc==0 and len(pairs)==2 and set(modes)=={0,8} and all(x in allowed for x in modes.values())
      and all(re.search(r'Test 6 PASS n_rs_seq='+str(n)+r'\b.*mutation=detected',log) for n in (0,8))
      and 'Test 6 SKIP' not in log and 'Test 6 INVALID' not in log and not witness.get('error')
      and [x['mode'] for x in witness.get('entries',[])]==[0,8] and points==expected)
    events=witness.get('debug_events',[])
    terminal=[e for e in events if e.get('kind')=='exit']
    returned=witness.get('continue_return') or {}
    exit_proven=(len(terminal)==1 and terminal[0].get('exit_code')==0 and returned.get('live') is False and returned.get('pid')==0 and terminal[0].get('inferior_num')==returned.get('inferior_num'))
    valid=valid and exit_proven
    custody_error=None
    try:
        runtime_witness.validate(witness,build,model,custody.validate_maps)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        custody_error=type(exc).__name__+': '+str(exc)
        valid=False
    return {'status':'PASS' if valid else 'INVALID','mutation_mechanisms':modes,'test_rc':rc,'runtime_custody_error':custody_error}

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

def proc_birth(pid):
    fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return int(fields[19])

def append_pid(pid,birth_ticks):
    path=Path(os.environ['FILLER_PIDFILE'])
    with path.open('a') as f:
        f.write(f'{pid} {birth_ticks}\n');f.flush();os.fsync(f.fileno())

def process_tree(root_pid):
    found={}
    pending=[root_pid]
    while pending:
        pid=pending.pop()
        try:
            birth=proc_birth(pid)
            found[pid]=birth
            children=[]
            for task in Path(f'/proc/{pid}/task').iterdir():
                raw=(task/'children').read_text().strip()
                children.extend(int(x) for x in raw.split())
            pending.extend(child for child in children if child not in found)
        except (FileNotFoundError,ProcessLookupError,PermissionError):
            continue
    return found

def terminate_exact_processes(processes):
    results=[]
    # Descendants first; cleanup() uses a pidfd and verifies the captured birth identity.
    for pid,birth_ticks in sorted(processes.items(), reverse=True):
        results.append(cleanup.cleanup(pid,birth_ticks))
    return results

def enable_subreaper():
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    enabled=ctypes.c_int()
    if libc.prctl(37,ctypes.byref(enabled),0,0,0)!=0 or enabled.value!=1:
        raise RuntimeError('subreaper verification failed')

def direct_children():
    return [int(x) for x in Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()]

def signal_owned_child(pid,birth):
    """Signal an unreaped direct child; a pidfd is preferred when available.

    When pidfd_open fails, a direct child's PID cannot be reused before this
    single-threaded supervisor reaps it. Recheck birth and parent before kill.
    """
    if pid not in direct_children() or cleanup.identity(pid)!=birth:
        raise RuntimeError('child identity or ownership changed')
    try:fd=os.pidfd_open(pid)
    except OSError:
        if pid not in direct_children() or cleanup.identity(pid)!=birth:
            raise RuntimeError('child identity or ownership changed')
        try:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
        return 'kill-owned-unreaped-child'
    try:
        if pid not in direct_children() or cleanup.identity(pid)!=birth:
            raise RuntimeError('child identity or ownership changed')
        try:signal.pidfd_send_signal(fd,signal.SIGKILL)
        except ProcessLookupError:pass
        return 'pidfd'
    finally:os.close(fd)

def stop_and_drain(proc, known, timeout_s=10):
    """Stop owned debugger first; adopt, identity-bind and reap every descendant.

    This is called only by the isolated runner after proving it has no unrelated
    children. Never signal by process name or without PID/birth revalidation.
    """
    deadline=time.monotonic()+timeout_s
    results=[]
    if proc.poll() is None:
        birth=known.get(proc.pid)
        if birth is None or cleanup.identity(proc.pid)!=birth:
            raise RuntimeError('debugger PID identity missing or changed')
        signal_owned_child(proc.pid,birth)
        proc.wait(timeout=max(0.01,deadline-time.monotonic()))
    while direct_children():
        if time.monotonic()>=deadline:raise TimeoutError('descendant drain exceeded deadline')
        for pid in direct_children():
            birth=cleanup.identity(pid)
            if birth is None:continue
            if pid in known and known[pid]!=birth:raise RuntimeError('descendant PID reused')
            known[pid]=birth
            signal_owned_child(pid,birth)
            while True:
                waited,_=os.waitpid(pid,os.WNOHANG)
                if waited==pid:break
                if time.monotonic()>=deadline:raise TimeoutError('descendant reap exceeded deadline')
                time.sleep(.01)
            if cleanup.identity(pid) is not None:raise RuntimeError('reaped PID still present')
            results.append({'pid':pid,'birth_ticks':birth,'signals':['SIGKILL'],'verified_dead':True})
    try:
        os.waitpid(-1,os.WNOHANG)
    except ChildProcessError:
        pass
    else:
        raise RuntimeError('ECHILD not established after descendant drain')
    for pid,birth in known.items():
        if cleanup.identity(pid)==birth:raise RuntimeError('captured process remains alive')
        if cleanup.identity(pid) is not None:raise RuntimeError('captured PID reused')
        if not any(x['pid']==pid for x in results):
            results.append({'pid':pid,'birth_ticks':birth,'signals':[],'verified_dead':True})
    return results

def pin_debugger(proc,known):
    try:
        return os.pidfd_open(proc.pid)
    except ProcessLookupError:
        proc.wait(timeout=5)
        stop_and_drain(proc,known)
        raise RuntimeError('debugger exited before identity capture')
    except OSError:
        # An owned, unreaped child cannot have its PID reused. Capture identity
        # and drain before propagating the inability to establish custody.
        try:known[proc.pid]=proc_birth(proc.pid)
        except FileNotFoundError:proc.wait(timeout=5)
        stop_and_drain(proc,known)
        raise

def read_pidfile():
    result=[]
    try:
        lines=Path(os.environ['FILLER_PIDFILE']).read_text().splitlines()
    except FileNotFoundError:
        return result
    for line in lines:
        parts=line.split()
        if len(parts)==2 and parts[0].isdigit() and parts[1].isdigit():
            result.append((int(parts[0]),int(parts[1])))
    return result

def read_witness():
    try:return json.loads(Path(os.environ['KPF17_WITNESS_OUTPUT']).read_text())
    except (OSError,ValueError):return {}

def verify_binding(binding,build):
    if build!=binding.get('build'):
        raise SystemExit('INVALID: build custody changed')
    for name,h in binding.get('runner_files',{}).items():
        if custody.digest(D/name)!=h:
            raise SystemExit('INVALID: runner changed: '+name)
    if custody.digest(GDB)!=binding.get('gdb_sha256'):
        raise SystemExit('INVALID: GDB changed')
    env=dict(os.environ,LD_LIBRARY_PATH=build['runtime_bin'])
    linkage=subprocess.run([build['linkage_helper'],build['binary'],build['runtime_bin']],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
    if linkage.returncode!=0:raise SystemExit('INVALID: copied-runtime linkage check failed')
    symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',build['binary']],text=True)
    for name in (ENTRY,DECODE,RESTORE):
        if sum(line.split()[-1:]==[name] for line in symbols.splitlines())!=1:
            raise SystemExit('INVALID: missing or ambiguous GDB symbol '+name)

def dryrun(binding,build):
    # Publisher smoke: real binary and custody checks, but no model access or inference.
    help_run=subprocess.run([build['binary'],'--help'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            text=True,timeout=30,env=dict(os.environ,LD_LIBRARY_PATH=build['runtime_bin']))
    if help_run.returncode!=0 or '--help' not in help_run.stdout:
        raise SystemExit('INVALID: model-free binary help smoke failed')
    result={'schema':'kpf17.oracle-test.dryrun.v1','smoke':True,'status':'QUALIFIED',
            'qualification_check_count':5,'model_loaded':False,'inference_started':False,
            'binary':build['binary'],'binary_sha256':build['binary_sha256'],
            'build_receipt_sha256':build['receipt_sha256'],
            'checks':['full_build_receipt_and_completion','binary_and_dso_hashes','unique_gdb_symbols',
                      'runner_and_gdb_hashes','binary_help_no_model'],
            'scope':'publisher dry-run qualification only; target model was not opened'}
    atomic(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),result)

def main():
    binding=json.loads((D/'binding.json').read_text())
    build=custody.build_identity();verify_binding(binding,build)
    if os.environ.get('FILLER_DRYRUN')=='1':
        dryrun(binding,build);return
    model=custody.model_identity(D/'model.json')
    if model!=binding.get('model'):
        raise SystemExit('INVALID: model stat identity changed')
    out=D/'out';out.mkdir(parents=True,exist_ok=True)
    attempt=out/('attempt-'+uuid.uuid4().hex);attempt.mkdir()
    config={**build,'model_path':str(Path(model['path']).resolve(strict=True)),
            'model_sha256':model['sha256']};atomic(attempt/'config.json',config)
    stop=Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE'])
    cpus=os.environ['FILLER_CPUS'];threads=os.environ['FILLER_THREADS']
    if stop.exists() or time.time()>=deadline:raise SystemExit(75)
    env=dict(os.environ,LD_LIBRARY_PATH=build['runtime_bin'],
             KPF17_WITNESS_CONFIG=str(attempt/'config.json'),
             KPF17_WITNESS_OUTPUT=str(attempt/'witness.json'))
    env.pop('GGML_BACKEND_PATH',None)
    argv=['taskset','-c',cpus,GDB,'--batch','-nx','-ex','set confirm off',
          '-ex','set startup-with-shell off','-ex','set auto-load python-scripts off',
          '-ex','set disable-randomization off','-ex','set debuginfod enabled off',
          '-ex','handle SIGTERM nostop noprint pass','-ex','source '+str(D/'witness.py'),
          '-ex','python start_capture_continue()','-ex','quit $_exitcode','--args',build['binary'],'-m',model['path'],
          '-ngl','0','-t',threads,'-b','32','-c','1024','-n','8','--seed','1234']
    interrupted=False;known={};termination=[]
    enable_subreaper()
    if direct_children():raise RuntimeError('runner has pre-existing children; refusing ownership')
    with (attempt/'test.log').open('wb') as log:
        proc=subprocess.Popen(argv,cwd=attempt,env=env,stdout=log,stderr=subprocess.STDOUT)
        # Pin the owned process before any operation that can fail; a pidfd
        # cannot retarget a reused PID if reading /proc or the PID file fails.
        debugger_fd=pin_debugger(proc,known)
        try:
            known[proc.pid]=proc_birth(proc.pid);append_pid(proc.pid,known[proc.pid])
        except BaseException:
            try:
                if proc.poll() is None:
                    try:signal.pidfd_send_signal(debugger_fd,signal.SIGKILL)
                    except ProcessLookupError:pass
                proc.wait(timeout=5)
                stop_and_drain(proc,known)
            finally:os.close(debugger_fd)
            raise
        os.close(debugger_fd)
        try:
            while proc.poll() is None:
                for pid,birth_ticks in process_tree(proc.pid).items():
                    if pid not in known:
                        known[pid]=birth_ticks;append_pid(pid,birth_ticks)
                if stop.exists() or time.time()>=deadline:
                    interrupted=True
                    break
                time.sleep(.1)
        finally:
            termination=stop_and_drain(proc,known)
    try:witness=json.loads((attempt/'witness.json').read_text())
    except (OSError,ValueError):witness={'error':'missing native in-test witness'}
    verdict=judge((attempt/'test.log').read_text(errors='replace'),witness,proc.returncode,build,model)
    inferior=apply_cleanup(verdict,witness,interrupted)
    if not termination:
        termination=terminate_exact_processes(known)
    all_children_dead=bool(termination) and all(x.get('verified_dead') for x in termination)
    if not all_children_dead or any(x.get('signals') for x in termination):verdict['status']='INVALID'
    try:
        if custody.build_identity()!=build or custody.model_identity(D/'model.json')!=model:
            verdict['status']='INVALID'
    except Exception as exc:
        verdict['status']='INVALID';verdict['postrun_custody_error']=type(exc).__name__+': '+str(exc)
    result={'schema':'kpf17.oracle-test.v1',**verdict,'build':build,'model':model,'argv':argv,
      'gdb_sha256':binding['gdb_sha256'],'cpus':cpus,'threads':threads,'smoke':False,
      'witness':witness,'captured_processes':[{'pid':pid,'birth_ticks':birth_ticks} for pid,birth_ticks in sorted(known.items())],
      'exact_pid_cleanup':termination if termination else [],'inferior_cleanup':inferior,
      'process_verified_dead':inferior['verified_dead'] and proc.poll() is not None and all_children_dead,
      'mutation':'restore checkpoint one prefix token stale after same-destination valid control and reset',
      'files':{str(p):custody.digest(p) for p in (attempt/'test.log',attempt/'config.json')},'sealed':True,
      'scope':'native Test 6 with in-function mappings; no kernel or production verdict'}
    if (attempt/'witness.json').exists():result['files'][str(attempt/'witness.json')]=custody.digest(attempt/'witness.json')
    atomic(D/'out/RESULT.json',result)
    if interrupted:raise SystemExit(75)

if __name__=='__main__':main()
