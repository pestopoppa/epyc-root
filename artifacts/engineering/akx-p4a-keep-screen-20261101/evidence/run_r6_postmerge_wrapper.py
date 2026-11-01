"""NI-owned bounded publisher admission; private scratch only."""
import datetime
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
WORKTREE = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-research-code')
ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030')
COMMAND = ['/bin/bash', '-c', 'set -euo pipefail; cd /mnt/raid0/llm/worktrees/mains/codex-ni-research-code; PYTHONPATH=scripts/kernel_rnd python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_lane_watchdog.py::test_direct_run_is_supervised_and_rejects_forged_marker; PYTHONPATH=scripts/kernel_rnd python3 -m autokernel.loop.run --help | grep -E -- \"--store|--out\" >/dev/null; git diff --check -- scripts/kernel_rnd/autokernel/loop/run.py']
CPUS = (130, 131)
FAMILY = '34-35'
LOCK_PATH = FLAGS / 'prep-locks' / f'{FAMILY}.lock'

sys.path[:0] = [
    '/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r14-dispatch-20261031',
    '/mnt/raid0/llm/tmp/evl31-mathsmith-hc-prep-20261029',
]
from entry_custody import Ledger, cleanup, Refused
import pidfd_subreaper_v3 as subreaper


def staged_closure():
    lines = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '--untracked-files=all'],
        cwd=WORKTREE, text=True,
    ).splitlines()
    actual = {line[3:]: line[:2] for line in lines if len(line) >= 4}
    allowed = {
        'scripts/kernel_rnd/autokernel/loop/run.py',
        'scripts/kernel_rnd/autokernel/loop/hotspots.py',
        'scripts/kernel_rnd/autokernel/loop/actors.py',
        'scripts/kernel_rnd/autokernel/loop/test_actors.py',
        'scripts/kernel_rnd/autokernel/prior_art.py',
        'scripts/kernel_rnd/autokernel/loop/test_hotspots.py',
    }
    if set(actual) != allowed:
        raise RuntimeError(f'unexpected Research lane status during validation: {actual!r}')
    if any(status not in {' M', '??'} for status in actual.values()):
        raise RuntimeError(f'unexpected staged/status flags: {actual!r}')
    root_lines = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '--untracked-files=all'],
        cwd=ROOT, text=True,
    ).splitlines()
    root_actual = {line[3:]: line[:2] for line in root_lines if len(line) >= 4}
    root_expected = set()
    root_paths = set(root_actual)
    scanner_paths = {path for path in root_paths if path.startswith('scanner-migration/')}
    if (root_paths - scanner_paths) != root_expected or not scanner_paths or any(
            status not in {' M', '??'} for status in root_actual.values()):
        raise RuntimeError(f'unexpected ROOT lane status during validation: {root_actual!r}')
    return lines


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
    lock.write(f'owner=codex-ni-s-code-batch-luna family={FAMILY} cpus={CPUS[0]},{CPUS[1]} pid={os.getpid()} task=AKX-P4a-focused-validation\n')
    lock.flush()
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    logfile = (SCRATCH / 'publication.log').open('w')
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
        'root_lane': str(ROOT), 'root_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        'implementation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD^2'], cwd=WORKTREE, text=True).strip(),
        'merge_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORKTREE, text=True).strip(),
        'start_utc': run_started_utc if 'run_started_utc' in locals() else None,
        'end_utc': run_ended_utc if 'run_ended_utc' in locals() else datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'own_pid': own_pid if 'own_pid' in locals() else None,
        'own_start_ticks': own_birth_ticks if 'own_birth_ticks' in locals() else None,
        'runner_pid': runner_pid if 'runner_pid' in locals() else os.getpid(),
        'runner_start_ticks': runner_start_ticks if 'runner_start_ticks' in locals() else Path(f'/proc/{os.getpid()}/stat').read_text().split()[21],
        'boot_id': boot_id if 'boot_id' in locals() else Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'live_grants': snapshot, 'staged_closure': closure if 'closure' in locals() else None,
        'returncode': rc, 'failure': failure, 'elapsed_s': time.monotonic() - started,
        'sampled_peak_tree_rss_bytes': peak, 'kernel_childset_empty': True,
        'captured': records, 'native_or_GPU_execution': False,
        'source_closure': closure if 'closure' in locals() else None,
        'adapted_script_sha256': __import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),
        'output_log_sha256': __import__('hashlib').sha256((SCRATCH / 'publication.log').read_bytes()).hexdigest() if (SCRATCH / 'publication.log').exists() else None,
        'rss_sampler': {'interval_s': 0.1, 'limit_bytes': 8 * 1024**3, 'source': '/proc/<pid>/statm'},
    }
    (SCRATCH / 'R6-WRAPPER-RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('returncode', 'failure', 'elapsed_s', 'sampled_peak_tree_rss_bytes', 'actual_cpus', 'live_grants', 'own_pid', 'own_start_ticks', 'start_utc', 'end_utc')}), flush=True)
raise SystemExit(1 if failure else rc)
