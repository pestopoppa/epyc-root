import fcntl, json, os, subprocess, time
from pathlib import Path
SCRATCH=Path(__file__).resolve().parent
WORKTREE=Path('/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator')
LOCK=Path('/mnt/raid0/llm/tmp/compute-flags/prep-locks/34-35.lock')
CPUS={130,131}
lock=LOCK.open('a+')
try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: raise SystemExit('34-35 mutex busy')
def birth(pid):
    try: return Path(f'/proc/{pid}/stat').read_text().split()[21]
    except (FileNotFoundError,ProcessLookupError): return None
def children(pid):
    found=[]; todo=[pid]
    while todo:
        p=todo.pop()
        try: kids=[int(x) for x in Path(f'/proc/{p}/task/{p}/children').read_text().split()]
        except (FileNotFoundError,ProcessLookupError): kids=[]
        for c in kids:
            if c not in found: found.append(c); todo.append(c)
    return found
os.sched_setaffinity(0,CPUS)
env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(WORKTREE))
cmd=['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python','-m','pytest','-q','tests/unit/test_scout_search.py','tests/unit/test_ufh12_context_search.py']
start=time.monotonic(); proc=subprocess.Popen(cmd,cwd=WORKTREE,env=env,stdout=(SCRATCH/'test.log').open('w'),stderr=subprocess.STDOUT)
owned={proc.pid:birth(proc.pid)}; peak=0; failure=None
try:
    while proc.poll() is None:
        for p in [proc.pid]+children(proc.pid):
            b=birth(p)
            if b is not None: owned[p]=b
        rss=0
        for p,b in owned.items():
            if birth(p)==b:
                try: rss+=int(Path(f'/proc/{p}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
                except (FileNotFoundError,ProcessLookupError): pass
        peak=max(peak,rss)
        if peak>8*1024**3: raise RuntimeError('R6 RSS cap exceeded')
        if time.monotonic()-start>900: raise RuntimeError('R6 time cap exceeded')
        time.sleep(.1)
    rc=proc.returncode
    if rc: failure=f'pytest rc={rc}'
except BaseException as e:
    failure=f'{type(e).__name__}: {e}'
    if birth(proc.pid) is not None:
        os.kill(proc.pid,15)
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: os.kill(proc.pid,9); proc.wait()
        rc=proc.returncode
finally:
    (SCRATCH/'test.log').flush() if hasattr((SCRATCH/'test.log'),'flush') else None
    receipt={'command':cmd,'cwd':str(WORKTREE),'cpus':sorted(CPUS),'started_mono':start,'elapsed_s':time.monotonic()-start,'returncode':locals().get('rc'),'failure':failure,'sampled_peak_tree_rss_bytes':peak,'captured':owned}
    (SCRATCH/'R6-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    lock.close()
print(json.dumps(receipt))
raise SystemExit(1 if failure else rc)
