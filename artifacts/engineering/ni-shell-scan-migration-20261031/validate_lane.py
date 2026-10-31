from __future__ import annotations
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
REPO = Path('/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030')
LOCK = Path('/mnt/raid0/llm/tmp/compute-flags/prep-locks/32-33.lock')
CPUS = '128,129'
PHYSICAL = '32-33'
TESTS = [
    'scripts/hooks/tests/test_shell_scan.py',
    'scripts/hooks/tests/test_shell_scan_migration_parity.py',
    'scripts/hooks/tests/test_process_pattern_kill.py',
    'scripts/hooks/tests/test_operator_apply_copy.py',
    'tests/hooks/test_pytest_worker_scan.py',
    'scripts/hooks/tests/test_filesystem_containment.py',
]

def proc_stat(pid: int):
    raw = Path(f'/proc/{pid}/stat').read_text()
    end = raw.rfind(')')
    fields = raw[end + 2:].split()
    return {'state': fields[0], 'ppid': int(fields[1]), 'start_ticks': int(fields[19])}

def tree_snapshot(root_pid: int):
    pending = [root_pid]
    visited = set()
    rss = 0
    identities = {}
    while pending:
        pid = pending.pop()
        if pid in visited:
            continue
        visited.add(pid)
        try:
            stat = proc_stat(pid)
            identities[pid] = stat['start_ticks']
            status = Path(f'/proc/{pid}/status').read_text().splitlines()
            rss += next((int(line.split()[1]) * 1024 for line in status if line.startswith('VmRSS:')), 0)
            child_text = Path(f'/proc/{pid}/task/{pid}/children').read_text().strip()
            pending.extend(int(child) for child in child_text.split())
        except (OSError, ValueError, IndexError):
            continue
    return rss, identities

lock = LOCK.open('r+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
lock.seek(0)
lock.truncate()
lock.write('owner=codex-ni-01a16d6b cpus=128-129 R6 scanner migration semantic and hook tests\n')
lock.flush()
command = ['taskset', '-c', CPUS, '/workspace/tmp/pytestenv/bin/python', '-m', 'pytest', '-q', *TESTS]
env = {**os.environ, 'OMP_NUM_THREADS': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
started = time.monotonic()
log_path = SCRATCH / 'lane-validation.log'
with log_path.open('w') as log:
    proc = subprocess.Popen(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    birth = proc_stat(proc.pid)['start_ticks']
    max_rss = 0
    samples = 0
    seen = {proc.pid: birth}
    timed_out = False
    while proc.poll() is None:
        rss, identities = tree_snapshot(proc.pid)
        samples += 1
        max_rss = max(max_rss, rss)
        seen.update(identities)
        if rss > 8 * 1024**3 or time.monotonic() - started > 900:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            break
        time.sleep(0.1)
    rc = proc.wait()
end = time.monotonic()
lock.close()
absent = not Path(f'/proc/{proc.pid}').exists()
receipt = {
    'command': command,
    'tests': TESTS,
    'exit_code': rc,
    'timed_out_or_rss_stop': timed_out,
    'pid': proc.pid,
    'pid_start_ticks': birth,
    'pid_absent_after_wait': absent,
    'captured_process_births': {str(k): v for k, v in sorted(seen.items())},
    'peak_sampled_process_tree_rss_bytes': max_rss,
    'rss_samples': samples,
    'elapsed_seconds': round(end - started, 3),
    'cpu_affinity': CPUS,
    'physical_cpu_region': PHYSICAL,
    'r6_mutex': str(LOCK),
    'omp_num_threads': env['OMP_NUM_THREADS'],
    'log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest(),
}
(SCRATCH / 'lane-validation-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(log_path.read_text(), end='')
print(json.dumps(receipt, sort_keys=True))
if rc or timed_out or not absent or max_rss > 8 * 1024**3:
    raise SystemExit(1)
