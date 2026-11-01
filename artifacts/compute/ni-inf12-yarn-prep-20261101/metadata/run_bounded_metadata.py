"""Bounded CPU metadata count, adapted from the established R6 worker wrapper."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCRATCH = Path(__file__).resolve().parent
PACKET = SCRATCH / 'yarn-packet-r2'
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
COMMAND = ['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python', str(PACKET / 'prepare_500k_request_metadata.py')]
CPUS = (130, 131)
FAMILY = '34-35'
LOCK_PATH = FLAGS / 'prep-locks' / f'{FAMILY}.lock'
sys.path.insert(0, '/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r14-dispatch-20261031')
sys.path.insert(0, '/mnt/raid0/llm/tmp/evl31-mathsmith-hc-prep-20261029')
from entry_custody import Ledger, cleanup, Refused
import pidfd_subreaper_v3 as subreaper


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
            raise RuntimeError(f'unknown active grant class: {path.stem}')
        if given & set(CPUS):
            raise RuntimeError(f'live grant names actual prep CPUs {CPUS}: {path.stem}')
        projected = {cpu % 96 for cpu in given}
        if 'timing' in kind and (set(range(96)) <= projected or projected & physical):
            raise RuntimeError(f'timing grant affects physical CPUs {CPUS}: {path.stem} ({fields["regions"]})')
        records.append({'id': path.stem, 'class': kind, 'regions': fields['regions']})
    return records


lock = LOCK_PATH.open('a+')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    lock.close()
    raise SystemExit(f'NI {FAMILY} prep mutex busy; no work started')

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
    lock.seek(0)
    lock.truncate()
    lock.write(f'owner=codex-ni worker=inf12-yarne1 family={FAMILY} cpus={CPUS[0]},{CPUS[1]} pid={os.getpid()} task=500k-request-metadata-only\n')
    lock.flush()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    logfile = (SCRATCH / '500k-request-metadata.log').open('w')
    proc = subprocess.Popen(COMMAND, cwd=PACKET, env=env, stdout=logfile, stderr=subprocess.STDOUT)
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
            raise RuntimeError('sampled process-tree RSS exceeded 8 GiB')
        if time.monotonic() - started > 900:
            raise RuntimeError('900-second cap exceeded')
        time.sleep(0.1)
    rc = proc.returncode
    logfile.close()
    if rc:
        raise RuntimeError(f'metadata count rc={rc}')
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
        'scope': 'MODEL_FREE_METADATA_ONLY', 'family': FAMILY, 'actual_cpus': CPUS,
        'live_grants': snapshot, 'returncode': rc, 'failure': failure,
        'elapsed_s': time.monotonic() - started, 'sampled_peak_tree_rss_bytes': peak,
        'kernel_childset_empty': True, 'captured': records,
        'inference_or_GPU_execution': False, 'original_wrapper': '/mnt/raid0/llm/tmp/codex-ni-dp5-delegated-publication-20261031/run_bounded_r6.py',
    }
    (SCRATCH / 'R6-METADATA-RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('returncode', 'failure', 'elapsed_s', 'sampled_peak_tree_rss_bytes', 'actual_cpus', 'live_grants')}), flush=True)
raise SystemExit(1 if failure else rc)
