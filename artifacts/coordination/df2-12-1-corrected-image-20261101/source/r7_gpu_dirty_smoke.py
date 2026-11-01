#!/usr/bin/env python3
"""R7 no-grant GPU smoke of the same-image corrected test on small qwen35."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

from owner_pregrant import ROOT, REGION_LOCK, drain_group, members, sha, validate_image_record


FLAGS = pathlib.Path('/mnt/raid0/llm/tmp/compute-flags')
MODEL = pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf')
MODEL_SHA = '0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
RAM_ADMIT = FLAGS / 'ram_admit.sh'
BUSY = pathlib.Path('/sys/class/drm/card2/device/gpu_busy_percent')
KFD = pathlib.Path('/sys/class/kfd/kfd/proc')


def gpu_grant_live():
    now = time.time()
    for path in (FLAGS / 'grants').glob('*.grant'):
        try:
            fields = dict(part.split('=', 1) for part in path.read_text().split())
            start = dt.datetime.fromisoformat(fields['start'].replace('Z', '+00:00')).timestamp()
            end = dt.datetime.fromisoformat(fields['end'].replace('Z', '+00:00')).timestamp()
            if start <= now < end and 'mi210_0' in fields['regions'].split(','):
                return str(path)
        except (OSError, ValueError, KeyError):
            return 'unreadable grant; fail closed'
    return None


def timing_q3_live():
    # R7 permits SMT 184-185 beside correctness q3 grants, not timing grants.
    from run_bounded_r6 import active_grants
    for row in active_grants():
        if 'timing' in row['class'] and {88, 89} & {cpu % 96 for cpu in row['cpus']}:
            return row['id']
    return None


def admission():
    from run_bounded_r6 import active_grants
    rows = active_grants()
    info = {'epoch': time.time(), 'live_grants': rows}
    reason = gpu_grant_live() or timing_q3_live()
    if reason:
        return {**info, 'refusal': 'live grant ' + reason}
    status = subprocess.run([str(REGION_LOCK), 'status'], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=10)
    if status.returncode or 'gpu-quiet  free' not in status.stdout:
        return {**info, 'refusal': 'gpu-quiet region lock held/unreadable',
                'region_lock_status': status.stdout}
    try:
        busy = int(BUSY.read_text().strip())
        kfd = [p.name for p in KFD.iterdir() if p.name.isdecimal()]
    except (OSError, ValueError):
        return {**info, 'refusal': 'GPU telemetry unavailable'}
    info.update(region_lock_status=status.stdout, gpu_busy_percent=busy, kfd_pids=kfd)
    if busy > 5 or kfd:
        return {**info, 'refusal': f'GPU still active: busy={busy}, kfd={kfd}'}
    ram = subprocess.run([str(RAM_ADMIT), '8'], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, timeout=10)
    if ram.returncode:
        return {**info, 'refusal': 'RAM admission refused: ' + ram.stdout.strip(),
                'ram_admit_rc': ram.returncode, 'ram_admit_output': ram.stdout}
    free = shutil.disk_usage(ROOT).free
    info.update(ram_admit_rc=ram.returncode, ram_admit_output=ram.stdout,
                disk_free_bytes=free, smoke_output_reserve_bytes=1 * 1024**3,
                disk_floor_bytes=150 * 1024**3)
    if free < 151 * 1024**3:
        return {**info, 'refusal': f'disk free {free} below 150 GiB floor plus 1 GiB smoke reserve'}
    return {**info, 'refusal': None}


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        raise SystemExit('usage: r7_gpu_dirty_smoke.py MAX_WAIT_SECONDS (<=1800)')
    max_wait = int(sys.argv[1])
    if not 1 <= max_wait <= 1800:
        raise SystemExit('bounded watcher requires 1..1800 seconds')
    image = ROOT / 'corrected-proof/architect_dflash/IMAGE-PREFLIGHT.json'
    binary_dir = ROOT / 'frontend-instrument-corrected/gpu/bin'
    validate_image_record(json.loads(image.read_text()), binary_dir / 'llama-server')
    out = ROOT / 'r7-gpu-dirty-smoke' / f'attempt-{int(time.time())}-{os.getpid()}'
    out.mkdir(parents=True)
    watcher_start = time.monotonic()
    observations = []
    while time.monotonic() - watcher_start < max_wait:
        observed = admission()
        observations.append(observed)
        if observed['refusal'] is None:
            break
        time.sleep(max(.01, min(5, max_wait - (time.monotonic() - watcher_start))))
    else:
        (out / 'WAIT-REFUSED.json').write_text(json.dumps({'status': 'NO_ADMISSION',
             'observations': observations, 'watcher_wall_s': time.monotonic() - watcher_start}, indent=2) + '\n')
        return 75
    # The R7 region lock is acquired after read-only admission. It remains
    # authoritative if state races the check; a lock refusal never loads model.
    command = [str(REGION_LOCK), 'run', '--gpu-quiet', 'exclusive', '--timeout-s', '20',
               '--role', 'df2-r7-smoke', '--tag', 'df2-12-1-gpu-dirty-r7', '--',
               'taskset', '-c', '184-185', '/usr/bin/python3', str(ROOT / 'image_preflight.py'),
               'test', '--backend', 'gpu', '--identity', str(image),
               '--test-binary', str(binary_dir / 'test-recurrent-state-rollback'),
               '--hybrid-model', str(MODEL), '--hybrid-model-sha', MODEL_SHA,
               '--ld-library-path', str(binary_dir) + ':/opt/rocm/lib',
               '--timeout', '200', '--out', str(out / 'ROLLBACK-TEST.json')]
    launch = time.monotonic()
    peak = 0
    captured = {}
    failure = None
    with (out / 'R7-SMOKE.log').open('wb') as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        birth = int((pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
        captured[proc.pid] = birth
        try:
            while proc.poll() is None:
                group = members(proc.pid)
                captured.update({pid: data['birth_ticks'] for pid, data in group.items()})
                peak = max(peak, sum(data['rss_bytes'] for data in group.values()))
                if peak > 8 * 1024**3:
                    failure = 'R7 8 GiB smoke RSS cap'
                    break
                if time.monotonic() - launch >= 295:
                    failure = 'R7 300-second total smoke cap'
                    break
                time.sleep(.1)
        except BaseException as exc:
            failure = 'R7 guardian exception: ' + repr(exc)
        if failure:
            try:
                drain_group(proc.pid, birth, captured)
            except RuntimeError as exc:
                failure += '; drain refusal: ' + str(exc)
        try:
            rc = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                drain_group(proc.pid, birth, captured)
                rc = proc.wait(timeout=5)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                failure = (failure or '') + '; drain/wait failure: ' + repr(exc)
                rc = proc.poll()
        try:
            drained = drain_group(proc.pid, birth, captured)
        except RuntimeError as exc:
            failure = (failure or '') + '; final drain refusal: ' + str(exc)
            drained = False
    result = out / 'ROLLBACK-TEST.json'
    result_data = json.loads(result.read_text()) if result.exists() else None
    receipt = {'schema': 'epyc.df2_12_1.r7_gpu_dirty_smoke.v1',
               'scope': 'R7_REAL_SMOKE_NO_GRANT_NO_QUALIFICATION',
               'model': str(MODEL), 'model_sha256': MODEL_SHA, 'model_arch': 'qwen35',
               'image_proof_sha256': sha(image), 'argv': command,
               'region_lock_log_sha256': sha(out / 'R7-SMOKE.log'),
               'leader_pid': proc.pid, 'leader_birth_ticks': birth,
               'captured_pids_birth': captured, 'peak_group_rss_bytes': peak,
               'smoke_wall_s': time.monotonic() - launch, 'returncode': rc,
               'failure': failure, 'owned_group_drained': drained,
               'native_result_path': str(result), 'native_result_sha256': sha(result) if result.exists() else None,
               'native_dirty_context_pass': bool(result_data and result_data.get('pass')),
               'admission_observations': observations, 'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (out / 'R7-SMOKE-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if rc or failure or not drained or not receipt['native_dirty_context_pass'] or receipt['smoke_wall_s'] > 300:
        return 2
    target = ROOT / 'corrected-proof/architect_dflash/ROLLBACK-TEST.json'
    if target.exists():
        raise RuntimeError('refuse to replace role dirty-context proof')
    target.write_bytes(result.read_bytes())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
