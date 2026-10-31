#!/usr/bin/env python3
"""One-shot custody: wait for exclusive GPU, then native smoke and publish."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

D = Path(__file__).resolve().parent
READY = Path('/mnt/raid0/llm/tmp/compute-flags/ready')
ID = 'codex-ni-yarn-e1-mem-phase-r1-20261031'
RL = '/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock'
BOOT = Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def put(p, obj):
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, p)


def main():
    start = time.time()
    birth = Path(f'/proc/{os.getpid()}/stat').read_text().split()[21]
    receipt = {'watcher_pid': os.getpid(), 'watcher_birth': birth, 'boot_id': BOOT,
               'started_at': start, 'source': str(D), 'state': 'WAITING_GPU'}
    put(D / 'WATCHER-RECEIPT.json', receipt)
    launch_sha = hashlib.sha256((D / 'launch.sh').read_bytes()).hexdigest()
    command = [RL, 'run', '--gpu-quiet', 'exclusive', '--role', 'bench',
               '--timeout-s', '1', '--tag', ID, '--', 'taskset', '-c', '184,185',
               '/bin/bash', str(D / 'launch.sh'), '--smoke']
    log = READY / f'{ID}.smoke.log'
    deadline = start + 3 * 3600
    while time.time() < deadline:
        with log.open('a') as fh:
            fh.write(f'[{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}] exclusive attempt\n')
            fh.flush()
            p = subprocess.Popen(command, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
            child_birth = Path(f'/proc/{p.pid}/stat').read_text().split()[21]
            receipt.update(state='ATTEMPT', child_pid=p.pid, child_birth=child_birth,
                           child_started_at=time.time())
            put(D / 'WATCHER-RECEIPT.json', receipt)
            try:
                rc = p.wait(timeout=288)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    rc = p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    rc = p.wait(timeout=2)
                rc = 124
        if rc == 75 and not (D / 'out/E1-A0-low/smoke-result.json').exists():
            time.sleep(15)
            continue
        receipt.update(state='SMOKE_DONE', rc=rc, ended_at=time.time(),
                       wall_s=time.time() - receipt['child_started_at'],
                       launcher_sha256=launch_sha, cleanup_verified=False)
        launch_record = D / 'out/E1-A0-low/launch.json'
        if launch_record.is_file():
            own_pid = json.loads(launch_record.read_text())['pid']
            receipt['server_pid'] = own_pid
            receipt['cleanup_verified'] = (not Path(f'/proc/{own_pid}').exists()
                                           and not Path(f'/sys/class/kfd/kfd/proc/{own_pid}').exists())
        if rc == 0 and not receipt['cleanup_verified']:
            rc = 70
            receipt['rc'] = rc
        put(D / 'SMOKE-RECEIPT.json', receipt)
        if rc == 0:
            pub = subprocess.run([sys.executable, str(D / 'publish.py')],
                                 stdout=(D / 'publish.log').open('w'), stderr=subprocess.STDOUT)
            if pub.returncode == 0:
                (D / 'READY.flag').write_text('READY ' + time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')
                receipt['state'] = 'READY'
                put(D / 'WATCHER-RECEIPT.json', receipt)
                return 0
            rc = pub.returncode
        (D / 'FAILED.flag').write_text(f'FAILED rc={rc} ' + time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')
        receipt['state'] = 'FAILED'
        put(D / 'WATCHER-RECEIPT.json', receipt)
        return rc or 1
    receipt['state'] = 'GPU_UNAVAILABLE_CUTOFF'
    put(D / 'WATCHER-RECEIPT.json', receipt)
    (D / 'FAILED.flag').write_text('GPU_UNAVAILABLE_CUTOFF\n')
    return 75


if __name__ == '__main__':
    raise SystemExit(main())
