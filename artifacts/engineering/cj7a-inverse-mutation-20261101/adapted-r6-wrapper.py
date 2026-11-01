"""NI-owned bounded publisher admission; private scratch only."""
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
WORKTREE = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-research-code')
ROOT = None
BASE_WRAPPER_SOURCE = 'epyc-root origin/main:artifacts/engineering/akx-p4a-keep-screen-20261101/evidence/run_r6_postmerge_wrapper.py'
BASE_WRAPPER_SHA256 = '6f5b391ec009206bcd2f48c82e1cdd9fbd8ed0c5fbd6d7e36c6e707cce2fe67b'
BASE_WRAPPER_COMMIT = 'd4593785d6425672581daa91b10ae1232097850a'
COMMAND = ['/bin/bash', '-c', 'set -euo pipefail; cd /mnt/raid0/llm/worktrees/mains/codex-ni-research-code; python3 -m pytest -q scripts/benchmark/inverse_mutation_v1/tests/test_inverse_mutation.py; ruff check scripts/benchmark/inverse_mutation_v1/__init__.py scripts/benchmark/inverse_mutation_v1/fixtures.py scripts/benchmark/inverse_mutation_v1/control_proof.py scripts/benchmark/inverse_mutation_v1/scorer.py scripts/benchmark/inverse_mutation_v1/tests/test_inverse_mutation.py; ruff format --check scripts/benchmark/inverse_mutation_v1/__init__.py scripts/benchmark/inverse_mutation_v1/fixtures.py scripts/benchmark/inverse_mutation_v1/control_proof.py scripts/benchmark/inverse_mutation_v1/scorer.py scripts/benchmark/inverse_mutation_v1/tests/test_inverse_mutation.py; python3 -m scripts.benchmark.inverse_mutation_v1.control_proof']
CPUS = (130, 131)
FAMILY = '34-35'
LOCK_PATH = FLAGS / 'prep-locks' / f'{FAMILY}.lock'

sys.path[:0] = [
    '/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r14-dispatch-20261031',
    '/mnt/raid0/llm/tmp/evl31-mathsmith-hc-prep-20261029',
]
from entry_custody import Ledger, cleanup, Refused
import pidfd_subreaper_v3 as subreaper


def staged_closure(allow_proof_output=False):
    """Pin only CJ-7a inputs; list unrelated dirty paths without claiming their custody."""
    status_lines = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '--untracked-files=all'],
        cwd=WORKTREE, text=True,
    ).splitlines()
    actual = {line[3:]: line[:2] for line in status_lines if len(line) >= 4}
    prefix = 'scripts/benchmark/inverse_mutation_v1/'
    leaf_changes = {path: status for path, status in actual.items() if path.startswith(prefix)}
    proof_path = prefix + 'fixtures/native_control_proof.json'
    permitted = {proof_path: ' M'} if allow_proof_output else {}
    if leaf_changes != permitted:
        raise RuntimeError(f'unexpected CJ-7a leaf changes: {leaf_changes!r}')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORKTREE, text=True).strip()
    leaf_paths = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', 'HEAD', '--', prefix],
        cwd=WORKTREE, text=True,
    ).splitlines()
    if not leaf_paths:
        raise RuntimeError('committed CJ-7a leaf is absent')
    files = {
        path: hashlib.sha256((WORKTREE / path).read_bytes()).hexdigest()
        for path in sorted(leaf_paths) if path != proof_path
    }
    proof_output_sha = hashlib.sha256((WORKTREE / proof_path).read_bytes()).hexdigest()
    dependency = 'scripts/benchmark/gate_verdict_vocab.py'
    dependency_sha = hashlib.sha256((WORKTREE / dependency).read_bytes()).hexdigest()
    dependency_status = actual.get(dependency)
    if dependency_status:
        raise RuntimeError(f'shared verdict vocabulary is dirty: {dependency_status!r}')
    formatter_path = Path(subprocess.check_output(['which', 'ruff'], text=True).strip()).resolve()
    formatter_sha = hashlib.sha256(formatter_path.read_bytes()).hexdigest()
    formatter_version = subprocess.check_output([str(formatter_path), '--version'], text=True).strip()
    if formatter_sha != '88abf248be39383e05419e50811467b9c25ef3f3bc1b8a0874962941c0190ffa':
        raise RuntimeError('Ruff executable digest differs from the CJ-7a pin')
    if formatter_version != 'ruff 0.16.3':
        raise RuntimeError(f'Ruff version differs from the CJ-7a pin: {formatter_version!r}')
    foreign = [{'path': path, 'status': status} for path, status in sorted(actual.items())
               if path not in leaf_paths and path != dependency]
    return {
        'head': head,
        'leaf_files_sha256': files,
        'proof_output_sha256': proof_output_sha,
        'proof_output_status': leaf_changes.get(proof_path),
        'gate_verdict_vocab_sha256': dependency_sha,
        'formatter': {'path': str(formatter_path), 'sha256': formatter_sha,
                      'version': formatter_version, 'config': 'isolated; line-length=100'},
        'foreign_dirty_inventory': foreign,
    }


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
        stamp = lambda value: datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        if not stamp(fields['start']) <= now < stamp(fields['end']):
            continue
        given = set()
        for chunk in fields['regions'].split(','):
            if chunk.startswith('mi210'):
                continue
            low, sep, high = chunk.partition('-')
            given.update(range(int(low), int(high if sep else low) + 1))
        kind = rows.get(path.stem, '')
        if not kind:
            raise RuntimeError(f'unknown live grant class: {path.stem}')
        projected = {cpu % 96 for cpu in given}
        if 'timing' in kind and (set(range(96)) <= projected or projected & physical):
            raise RuntimeError(f'timing grant affects physical CPUs {CPUS}: {path.stem} ({fields["regions"]})')
        if given & set(CPUS):
            raise RuntimeError(f'live grant names actual prep CPUs {CPUS}: {path.stem}')
        records.append({
            'id': path.stem, 'class': kind, 'regions': fields['regions'],
            'start': fields['start'], 'end': fields['end'],
        })
    return records


lock = LOCK_PATH.open('a+')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    lock.close()
    raise SystemExit('NI 36-37 prep mutex already held; no work started')

subreaper.enable()
ledger = Ledger()
proc = None
started = time.monotonic()
peak = 0
rc = None
failure = None
snapshot = []
try:
    os.sched_setaffinity(0, set(CPUS))
    snapshot = live_admission()
    closure = staged_closure()
    lock.seek(0)
    lock.truncate()
    lock.write(f'owner=codex-ni-01a16d6b family={FAMILY} cpus={CPUS[0]},{CPUS[1]} pid={os.getpid()} task=CJ7A-focused-validation\n')
    lock.flush()
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    logfile = (SCRATCH / 'CJ7A-R6.log').open('w')
    run_started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    runner_pid = os.getpid()
    runner_start_ticks = Path(f'/proc/{runner_pid}/stat').read_text().split()[21]
    proc = subprocess.Popen(COMMAND, cwd=WORKTREE, env=env, stdout=logfile, stderr=subprocess.STDOUT)
    own_pid = proc.pid
    own_birth_ticks = Path(f'/proc/{own_pid}/stat').read_text().split()[21]
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    while proc.poll() is None:
        snapshot = live_admission()
        ledger.snapshot()
        rss = 0
        for item in ledger.live():
            try:
                rss += int((Path('/proc') / str(item['pid']) / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            except (FileNotFoundError, ProcessLookupError):
                pass
        peak = max(peak, rss)
        if peak > 8 * 1024**3:
            raise RuntimeError('R6 sampled process-tree RSS exceeded 8 GiB')
        if time.monotonic() - started > 900:
            raise RuntimeError('R6 900-second cap exceeded')
        time.sleep(0.1)
    rc = proc.returncode
    snapshot = live_admission()
    closure_after = staged_closure(allow_proof_output=True)
    start_scope = {key: value for key, value in closure.items() if key not in {'foreign_dirty_inventory', 'proof_output_sha256', 'proof_output_status'}}
    end_scope = {key: value for key, value in closure_after.items() if key not in {'foreign_dirty_inventory', 'proof_output_sha256', 'proof_output_status'}}
    if start_scope != end_scope:
        raise RuntimeError('CJ-7a input closure changed during bounded validation')
    logfile.close()
    run_ended_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if rc:
        raise RuntimeError(f'publisher rc={rc}')
except BaseException as exc:
    failure = f'{type(exc).__name__}: {exc}'
finally:
    while True:
        ledger.snapshot()
        live = ledger.live()
        if live:
            try:
                cleanup(live)
            except Refused:
                pass
        if proc:
            proc.poll()
        try:
            ledger.assert_drained(timeout=0.3)
            break
        except Refused:
            time.sleep(0.1)
    records = ledger.records()
    ledger.close()
    try:
        lock.seek(0)
        lock.truncate()
        lock.flush()
    finally:
        lock.close()
    result = {
        'scope': 'MODEL_FREE_R6_ONLY', 'family': FAMILY, 'actual_cpus': CPUS,
        'root_lane': None, 'root_status': None,
        'implementation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORKTREE, text=True).strip(),
        'merge_commit': None,
        'start_utc': run_started_utc if 'run_started_utc' in locals() else None,
        'end_utc': run_ended_utc if 'run_ended_utc' in locals() else datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'own_pid': own_pid if 'own_pid' in locals() else None,
        'own_start_ticks': own_birth_ticks if 'own_birth_ticks' in locals() else None,
        'runner_pid': runner_pid if 'runner_pid' in locals() else os.getpid(),
        'runner_start_ticks': runner_start_ticks if 'runner_start_ticks' in locals() else Path(f'/proc/{os.getpid()}/stat').read_text().split()[21],
        'boot_id': boot_id if 'boot_id' in locals() else Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'live_grants': snapshot, 'scoped_inputs_before': closure if 'closure' in locals() else None,
        'scoped_inputs_after': closure_after if 'closure_after' in locals() else None,
        'returncode': rc, 'failure': failure, 'elapsed_s': time.monotonic() - started,
        'sampled_peak_tree_rss_bytes': peak, 'kernel_childset_empty': True,
        'captured': records, 'native_or_GPU_execution': False,
        'source_closure': closure if 'closure' in locals() else None,
        'base_wrapper_source': BASE_WRAPPER_SOURCE,
        'base_wrapper_sha256': BASE_WRAPPER_SHA256,
        'base_wrapper_commit': BASE_WRAPPER_COMMIT,
        'adapted_script_sha256': __import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),
        'output_log_sha256': __import__('hashlib').sha256((SCRATCH / 'CJ7A-R6.log').read_bytes()).hexdigest() if (SCRATCH / 'CJ7A-R6.log').exists() else None,
        'rss_sampler': {'interval_s': 0.1, 'limit_bytes': 8 * 1024**3, 'source': '/proc/<pid>/statm'},
    }
    (SCRATCH / 'CJ7A-R6-ACCEPTED-RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('returncode', 'failure', 'elapsed_s', 'sampled_peak_tree_rss_bytes', 'actual_cpus', 'live_grants', 'own_pid', 'own_start_ticks', 'start_utc', 'end_utc')}), flush=True)
raise SystemExit(1 if failure else rc)
