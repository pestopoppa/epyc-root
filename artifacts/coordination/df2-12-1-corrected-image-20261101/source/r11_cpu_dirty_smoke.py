#!/usr/bin/env python3
"""Standing R11 no-grant CPU smoke of actual small qwen35 rollback model."""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import pathlib
import shutil
import struct
import subprocess
import time

from owner_pregrant import ROOT, drain_group, members, sha, validate_image_record
from run_bounded_r6 import LOCK, active_grants

MODEL = pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf')
MODEL_SHA = '0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
PAIRS = ((128, 129), (152, 153), (176, 177), (104, 105))
RSS_LIMIT = 8 * 1024**3


def model_arch():
    with MODEL.open('rb') as stream:
        if stream.read(4) != b'GGUF' or struct.unpack('<I', stream.read(4))[0] != 3:
            raise RuntimeError('small rollback model is not GGUF v3')
        stream.read(16)  # tensor count and KV count
        key_len = struct.unpack('<Q', stream.read(8))[0]
        key = stream.read(key_len)
        value_type = struct.unpack('<I', stream.read(4))[0]
        value_len = struct.unpack('<Q', stream.read(8))[0]
        value = stream.read(value_len)
    if key != b'general.architecture' or value_type != 8 or value != b'qwen35':
        raise RuntimeError('small rollback model is not actual qwen35 architecture')
    return value.decode()


def admitted(pair=None):
    rows = active_grants()
    if pair is None:
        pair = next((candidate for candidate in PAIRS
                     if not any('timing' in row['class'] and
                                set(range((candidate[0] % 96 // 24) * 24,
                                          (candidate[0] % 96 // 24 + 1) * 24)).intersection(
                                    {cpu % 96 for cpu in row['cpus']})
                                for row in rows)
                     and not any(set(candidate).intersection(row['cpus']) for row in rows)), None)
    if pair is None:
        raise RuntimeError('R11 has no SMT pair outside timing-class quarters')
    quarter = set(range((pair[0] % 96 // 24) * 24, (pair[0] % 96 // 24 + 1) * 24))
    if any('timing' in row['class'] and quarter.intersection({cpu % 96 for cpu in row['cpus']})
           for row in rows):
        raise RuntimeError('R11 selected quarter has timing-class grant')
    if any(set(pair).intersection(row['cpus']) for row in rows):
        raise RuntimeError('R11 smoke CPUs are held by grant')
    ram = subprocess.run(['/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh', '8'],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
    if ram.returncode:
        raise RuntimeError('R11 RAM admission refused: ' + ram.stdout.strip())
    free = shutil.disk_usage(ROOT).free
    if free < 151 * 1024**3:
        raise RuntimeError('R11 disk below 150 GiB floor plus 1 GiB reserve')
    return {'grants': rows, 'cpus': pair, 'ram_admit_output': ram.stdout, 'disk_free_bytes': free}


def main():
    image = ROOT / 'corrected-proof/frontdoor_mtp/IMAGE-PREFLIGHT.json'
    binary_dir = ROOT / 'frontend-instrument-corrected/cpu/bin'
    validate_image_record(json.loads(image.read_text()), binary_dir / 'llama-server')
    if sha(MODEL) != MODEL_SHA or model_arch() != 'qwen35':
        raise RuntimeError('small qwen35 GGUF changed')
    source = pathlib.Path('/mnt/raid0/llm/llama.cpp/src/llama-arch.cpp').read_text()
    for fn in ('llm_arch_is_hybrid', 'llm_arch_supports_rs_rollback'):
        segment = source.split('bool ' + fn + '(', 1)[1].split('\n}', 1)[0]
        if 'case LLM_ARCH_QWEN35:' not in segment:
            raise RuntimeError(f'frozen source no longer supports qwen35 in {fn}')
    lock = LOCK.open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    before = admitted()
    pair = before['cpus']
    out = ROOT / 'r11-cpu-dirty-smoke' / f'attempt-{int(time.time())}-{os.getpid()}'
    out.mkdir(parents=True)
    command = ['taskset', '-c', ','.join(map(str, pair)), '/usr/bin/python3',
               str(ROOT / 'image_preflight.py'), 'test', '--backend', 'cpu',
               '--identity', str(image),
               '--test-binary', str(binary_dir / 'test-recurrent-state-rollback'),
               '--hybrid-model', str(MODEL), '--hybrid-model-sha', MODEL_SHA,
               '--ld-library-path', str(binary_dir), '--timeout', '240',
               '--out', str(out / 'ROLLBACK-TEST.json')]
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    started = time.monotonic()
    captured = {}
    peak = 0
    failure = None
    with (out / 'R11-SMOKE.log').open('wb') as log:
        proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        birth = int((pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
        captured[proc.pid] = birth
        try:
            while proc.poll() is None:
                group = members(proc.pid)
                captured.update({pid: data['birth_ticks'] for pid, data in group.items()})
                peak = max(peak, sum(data['rss_bytes'] for data in group.values()))
                if peak > RSS_LIMIT:
                    raise RuntimeError('R11 sampled group RSS exceeded 8 GiB')
                if time.monotonic() - started >= 295:
                    raise RuntimeError('R11 smoke approaching 300-second hard end')
                if int((time.monotonic() - started) * 10) % 10 == 0:
                    admitted(pair)
                time.sleep(.1)
        except BaseException as exc:
            failure = repr(exc)
        try:
            drained = drain_group(proc.pid, birth, captured)
            rc = proc.wait(timeout=4)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            drained = False
            rc = proc.poll()
            failure = (failure or '') + '; drain failure: ' + repr(exc)
    result = out / 'ROLLBACK-TEST.json'
    native = json.loads(result.read_text()) if result.exists() else None
    receipt = {'schema': 'epyc.df2_12_1.r11_cpu_dirty_smoke.v1',
               'scope': 'R11_REAL_SMALL_HYBRID_SMOKE_NO_GRANT_NO_QUALIFICATION',
               'model': str(MODEL), 'model_sha256': MODEL_SHA, 'model_arch': 'qwen35',
               'image_proof_sha256': sha(image), 'argv': command,
               'before_admission': before, 'leader_pid': proc.pid, 'leader_birth_ticks': birth,
               'captured_pids_birth': captured, 'peak_group_rss_bytes': peak,
               'wall_s': time.monotonic() - started, 'returncode': rc,
               'failure': failure, 'owned_group_drained': drained,
               'native_result_sha256': sha(result) if result.exists() else None,
               'native_dirty_context_pass': bool(native and native.get('pass')),
               'log_sha256': sha(out / 'R11-SMOKE.log'),
               'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (out / 'R11-SMOKE-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    lock.close()
    if rc or failure or not drained or not receipt['native_dirty_context_pass'] or receipt['wall_s'] > 300:
        return 2
    target = ROOT / 'corrected-proof/frontdoor_mtp/ROLLBACK-TEST.json'
    if target.exists():
        raise RuntimeError('refuse to replace role dirty-context proof')
    target.write_bytes(result.read_bytes())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
