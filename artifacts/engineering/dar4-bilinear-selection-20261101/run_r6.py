"""Task-adapted MODEL_FREE_R6 wrapper for bilinear selection unit proof."""
import datetime, fcntl, hashlib, json, os, subprocess, sys, time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
WORKTREE = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator')
CPUS = (132, 133)
FAMILY = '36-37'
LOCK_PATH = FLAGS / 'prep-locks' / f'{FAMILY}.lock'
RUFF = '/opt/uv-tools/ruff/bin/ruff'
FILES = [
    'orchestration/repl_memory/bilinear_scorer.py',
    'orchestration/repl_memory/hybrid_router.py',
    'orchestration/repl_memory/retrieval_config.py',
    'orchestration/repl_memory/retriever.py',
    'tests/unit/test_bilinear_selection.py',
]
COMMAND = ['/bin/bash', '-c', 'set -euo pipefail; cd /mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator; /mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator/.venv/bin/python -m pytest -q tests/unit/test_bilinear_selection.py tests/unit/test_bilinear_scorer.py tests/unit/test_graph_router_integration.py tests/unit/test_retriever_risk_gate.py; /opt/uv-tools/ruff/bin/ruff check --isolated --line-length 100 --select E7,E9,F orchestration/repl_memory/bilinear_scorer.py orchestration/repl_memory/hybrid_router.py orchestration/repl_memory/retrieval_config.py orchestration/repl_memory/retriever.py tests/unit/test_bilinear_selection.py; /opt/uv-tools/ruff/bin/ruff check --isolated --line-length 100 tests/unit/test_bilinear_selection.py; /opt/uv-tools/ruff/bin/ruff format --check --isolated --line-length 100 tests/unit/test_bilinear_selection.py; git diff --check']

sys.path[:0] = [
    '/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r14-dispatch-20261031',
    '/mnt/raid0/llm/tmp/evl31-mathsmith-hc-prep-20261029',
]
from entry_custody import Ledger, cleanup, Refused
import pidfd_subreaper_v3 as subreaper


def closure():
    status_lines = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=WORKTREE, text=True
    ).splitlines()
    actual = {line[3:]: line[:2] for line in status_lines if len(line) >= 4}
    if set(actual) != set(FILES):
        raise RuntimeError(f'unexpected app lane changes: {actual!r}')
    if any(status not in {' M', '??'} for status in actual.values()):
        raise RuntimeError(f'unexpected staged/status flags: {actual!r}')
    roots = [
        'orchestration/repl_memory', 'src/config', 'src/roles.py', 'src/registry',
        'tests/unit/test_bilinear_selection.py', 'tests/unit/test_bilinear_scorer.py',
        'tests/unit/test_graph_router_integration.py', 'tests/unit/test_retriever_risk_gate.py',
    ]
    paths = set()
    for root in roots:
        listed = subprocess.check_output(
            ['git', 'ls-files', '--', root], cwd=WORKTREE, text=True
        ).splitlines()
        paths.update(listed)
    paths.update(FILES)
    hashes = {p: hashlib.sha256((WORKTREE / p).read_bytes()).hexdigest() for p in sorted(paths)}
    return {'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKTREE,text=True).strip(),
            'changed': actual, 'read_closure_sha256': hashes}


def live_admission():
    rows = {}
    for line in (FLAGS / 'FILLERS.md').read_text().splitlines():
        cells = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(cells) == 18:
            rows[cells[0]] = cells[8]
    now = time.time()
    physical = {cpu % 96 for cpu in CPUS}
    records = []
    for path in sorted((FLAGS / 'grants').glob('*.grant')):
        fields = dict(part.split('=', 1) for part in path.read_text().split())
        stamp = lambda v: datetime.datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
        if not stamp(fields['start']) <= now < stamp(fields['end']):
            continue
        given = set()
        for chunk in fields['regions'].split(','):
            if chunk.startswith('mi210'): continue
            low, sep, high = chunk.partition('-')
            given.update(range(int(low), int(high if sep else low) + 1))
        kind = rows.get(path.stem, '')
        if not kind: raise RuntimeError(f'unknown live grant class: {path.stem}')
        projected = {cpu % 96 for cpu in given}
        if 'timing' in kind and (set(range(96)) <= projected or projected & physical):
            raise RuntimeError(f'timing grant affects physical CPUs {CPUS}: {path.stem}')
        if given & set(CPUS): raise RuntimeError(f'live grant names prep CPUs {CPUS}: {path.stem}')
        records.append({'id':path.stem,'class':kind,'regions':fields['regions'],
                        'start':fields['start'],'end':fields['end']})
    return records

lock = LOCK_PATH.open('a+')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    lock.close(); raise SystemExit(f'NI {FAMILY} prep mutex already held')
subreaper.enable(); ledger = Ledger(); proc = None; started = time.monotonic(); peak = 0
rc = None; failure = None; snapshot = []
try:
    os.sched_setaffinity(0, set(CPUS))
    snapshot = live_admission(); before = closure()
    lock.seek(0); lock.truncate()
    lock.write(f'owner=codex-ni-01a16d6b family={FAMILY} cpus={CPUS[0]},{CPUS[1]} pid={os.getpid()} task=NI-DAR4-bilinear-selection\n')
    lock.flush()
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = str(WORKTREE) + os.pathsep + env.get('PYTHONPATH','')
    log = (SCRATCH / 'test.log').open('w')
    run_started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    runner_pid = os.getpid(); runner_birth = Path(f'/proc/{runner_pid}/stat').read_text().split()[21]
    proc = subprocess.Popen(COMMAND, cwd=WORKTREE, env=env, stdout=log, stderr=subprocess.STDOUT)
    own_pid = proc.pid; own_birth = Path(f'/proc/{own_pid}/stat').read_text().split()[21]
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    while proc.poll() is None:
        snapshot = live_admission(); ledger.snapshot(); rss = 0
        for item in ledger.live():
            try: rss += int((Path('/proc')/str(item['pid'])/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
            except (FileNotFoundError, ProcessLookupError): pass
        peak = max(peak, rss)
        if peak > 8*1024**3: raise RuntimeError('sampled process-tree RSS exceeded 8 GiB')
        if time.monotonic()-started > 900: raise RuntimeError('900-second cap exceeded')
        time.sleep(.1)
    rc = proc.returncode; snapshot = live_admission(); after = closure(); log.close()
    run_ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if before != after: raise RuntimeError('source/read closure changed during validation')
    if rc: raise RuntimeError(f'pytest rc={rc}')
except BaseException as exc:
    failure = f'{type(exc).__name__}: {exc}'
finally:
    while True:
        ledger.snapshot(); live = ledger.live()
        if live:
            try: cleanup(live)
            except Refused: pass
        if proc: proc.poll()
        try: ledger.assert_drained(timeout=.3); break
        except Refused: time.sleep(.1)
    captured = ledger.records(); ledger.close()
    lock.seek(0); lock.truncate(); lock.flush(); lock.close()
    result = {
        'scope':'MODEL_FREE_R6_ONLY','family':FAMILY,'actual_cpus':CPUS,'repo':'epyc-orchestrator',
        'implementation_head':before['head'] if 'before' in locals() else None,
        'start_utc':run_started if 'run_started' in locals() else None,
        'end_utc':run_ended if 'run_ended' in locals() else datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'own_pid':own_pid if 'own_pid' in locals() else None,
        'own_start_ticks':own_birth if 'own_birth' in locals() else None,
        'runner_pid':runner_pid if 'runner_pid' in locals() else os.getpid(),
        'runner_start_ticks':runner_birth if 'runner_birth' in locals() else Path(f'/proc/{os.getpid()}/stat').read_text().split()[21],
        'boot_id':boot if 'boot' in locals() else Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'live_grants':snapshot,'read_closure':before if 'before' in locals() else None,
        'returncode':rc,'failure':failure,'elapsed_s':time.monotonic()-started,
        'sampled_peak_tree_rss_bytes':peak,'kernel_childset_empty':True,'captured':captured,
        'native_or_GPU_execution':False,
        'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'output_log_sha256':hashlib.sha256((SCRATCH/'test.log').read_bytes()).hexdigest() if (SCRATCH/'test.log').exists() else None,
    }
    (SCRATCH/'R6-RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('returncode','failure','elapsed_s','sampled_peak_tree_rss_bytes','actual_cpus','live_grants','own_pid','own_start_ticks','start_utc','end_utc')}),flush=True)
raise SystemExit(1 if failure else rc)
