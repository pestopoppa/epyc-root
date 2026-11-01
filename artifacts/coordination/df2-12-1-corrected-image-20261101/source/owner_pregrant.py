#!/usr/bin/env python3
"""ws58-owned pregrant native test/calibration entry; never an official FILLERS grant."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parent
FLAGS = pathlib.Path('/mnt/raid0/llm/tmp/compute-flags').resolve()
REGION_LOCK = pathlib.Path('/workspace/repos/epyc-orchestrator/scripts/region-lock')
PROMPT_SHA = 'de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1'
MODEL = {
    'cpu': ('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf',
            'c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'),
    'gpu': ('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf',
            'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348'),
}


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def members(pgid):
    found = {}
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(') ', 1)[1].split()
            if int(fields[2]) != pgid or fields[0] in ('Z', 'X', 'x'):
                continue
            rss = int((entry / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            found[int(entry.name)] = {'birth_ticks': int(fields[19]), 'rss_bytes': rss,
                                      'uid': entry.stat().st_uid}
        except (OSError, ValueError, IndexError):
            pass
    return found


def signal_owned(pgid, leader_birth, captured, sig):
    current = members(pgid)
    if not current:
        return
    leader_path = pathlib.Path('/proc') / str(pgid)
    if leader_path.exists():
        stat = (leader_path / 'stat').read_text().rsplit(') ', 1)[1].split()
        if (int(stat[19]) != leader_birth or int(stat[2]) != pgid or
            leader_path.stat().st_uid != os.getuid()):
            raise RuntimeError('refuse group signal: captured leader PID reused or owner/PGID changed')
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        return
    # The leader exited before a descendant. Signal only previously captured
    # exact PIDs with matching birth/UID/PGID; never infer ownership from a name.
    for pid, data in current.items():
        if captured.get(pid) != data['birth_ticks'] or data['uid'] != os.getuid():
            raise RuntimeError('refuse orphan signal: live PID lacks captured birth/owner')
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def drain_group(pgid, leader_birth, captured):
    if not members(pgid):
        return True
    signal_owned(pgid, leader_birth, captured, signal.SIGTERM)
    for _ in range(30):
        if not members(pgid):
            return True
        time.sleep(.1)
    signal_owned(pgid, leader_birth, captured, signal.SIGKILL)
    for _ in range(30):
        if not members(pgid):
            return True
        time.sleep(.1)
    return not members(pgid)


def validated_authority(path, purpose, role, binary):
    resolved = pathlib.Path(path).resolve(strict=True)
    if not resolved.is_relative_to(FLAGS):
        raise RuntimeError('owner authority must live under compute-flags custody')
    record = json.loads(resolved.read_text())
    cpus = '0-95' if role == 'cpu' else '184-191'
    regions = '0-95' if role == 'cpu' else 'mi210_0'
    kind = 'ws58.pregrant.native_test.v1' if purpose == 'test' else 'ws58.pregrant.calibration.v1'
    now = time.time()
    if (record.get('kind') != kind or record.get('issuer') != 'ws58' or
        not isinstance(record.get('id'), str) or not record['id'].startswith('codex-ni-df2-12-1-') or
        record.get('purpose') != purpose or record.get('role') != role or
        record.get('regions') != regions or record.get('host_cpus') != cpus or
        record.get('manifest_sha256') != PROMPT_SHA or
        record.get('binary_sha256') != sha(binary) or
        record.get('max_rss_gib') != 120 or
        not float(record.get('start_epoch', 0)) <= now < float(record.get('end_epoch', 0)) - 90 or
        float(record['end_epoch']) - float(record['start_epoch']) > 1800):
        raise RuntimeError('keeper pregrant authority does not match pinned role/image/resource/window')
    if purpose == 'test' and record.get('model_sha256') != MODEL[role][1]:
        raise RuntimeError('native test authority does not pin actual role target model')
    return resolved, record


def validate_image_record(image_record, binary):
    if not image_record.get('pass') or image_record.get('binary') != str(binary):
        raise RuntimeError('exact scratch image identity not PASS')
    if not image_record.get('artifacts') or any(sha(path) != metadata.get('sha256')
            for path, metadata in image_record['artifacts'].items()):
        raise RuntimeError('exact scratch image artifact changed after static PASS')
    current_source = subprocess.check_output(['git', '-C', image_record['source_root'],
                                              'rev-parse', 'HEAD'], text=True).strip()
    if current_source != image_record.get('source_sha'):
        raise RuntimeError('instrument source commit changed after static PASS')
    binding = image_record.get('corrected_test_binding', {})
    if not binding.get('pass'):
        raise RuntimeError('corrected test source/build binding missing')
    for path_key, sha_key in (('build_receipt_path', 'build_receipt_sha256'),
                              ('corrected_test_source_path', 'corrected_test_source_sha256'),
                              ('test_patch_path', 'test_patch_sha256')):
        if sha(binding[path_key]) != binding[sha_key]:
            raise RuntimeError(f'corrected test binding changed: {path_key}')
    if sha(image_record['test_binary']) != binding['corrected_test_binary_sha256']:
        raise RuntimeError('corrected test binary changed')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('purpose', choices=('test', 'calibrate'))
    ap.add_argument('role', choices=('cpu', 'gpu'))
    ap.add_argument('--authority', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    shape = 'frontdoor_mtp' if args.role == 'cpu' else 'architect_dflash'
    binary_dir = ROOT / 'frontend-instrument-corrected' / args.role / 'bin'
    binary = binary_dir / 'llama-server'
    authority_path, authority = validated_authority(args.authority, args.purpose, args.role, binary)
    image = ROOT / 'corrected-proof' / shape / 'IMAGE-PREFLIGHT.json'
    image_record = json.loads(image.read_text())
    validate_image_record(image_record, binary)
    if sha(ROOT / 'PROMPTS.json') != PROMPT_SHA:
        raise RuntimeError('frozen prompt manifest changed')
    run_dir = ROOT / 'pregrant-runs' / authority['id']
    if run_dir.exists():
        raise RuntimeError('refuse to overwrite a previous owner pregrant exposure')
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'id': authority['id'], 'role': args.role,
                          'purpose': args.purpose, 'authority_sha256': sha(authority_path)}))
        return 0
    state = run_dir / 'state'
    state.mkdir(parents=True)
    cpus = authority['host_cpus']
    env = {**os.environ, 'FILLER_ID': authority['id'], 'FILLER_CPUS': cpus,
           'FILLER_STATE_DIR': str(state), 'FILLER_PIDFILE': str(state / (authority['id'] + '.pids')),
           'FILLER_DEADLINE': str(authority['end_epoch'])}
    if args.purpose == 'test':
        remaining = max(1, min(1650, int(float(authority['end_epoch']) - time.time() - 90)))
        command = ['taskset', '-c', cpus, '/usr/bin/python3', str(ROOT / 'image_preflight.py'), 'test',
                   '--backend', args.role, '--identity', str(image),
                   '--test-binary', str(binary_dir / 'test-recurrent-state-rollback'),
                   '--hybrid-model', MODEL[args.role][0], '--hybrid-model-sha', MODEL[args.role][1],
                   '--ld-library-path', str(binary_dir) + (':/opt/rocm/lib' if args.role == 'gpu' else ''),
                   '--timeout', str(remaining), '--out', str(run_dir / 'ROLLBACK-TEST.json')]
    else:
        env['WS58_CALIBRATION_AUTHORITY'] = str(authority_path)
        if args.role == 'gpu':
            env['WS58_CALIBRATION_GPU_HELD'] = '1'
        command = ['/usr/bin/python3', str(ROOT / 'run_role.py'), '--shape', shape,
                   '--binary', str(binary), '--port', '18770' if args.role == 'cpu' else '18783',
                   '--manifest', str(ROOT / 'PROMPTS.json'), '--manifest-sha', PROMPT_SHA,
                   '--proof-dir', str(ROOT / 'corrected-proof'), '--out', str(run_dir / 'calibration'), '--calibrate-only']
    claim = [str(REGION_LOCK), 'run']
    claim += ['--cpu-list', '0-95'] if args.role == 'cpu' else ['--gpu-quiet', 'exclusive']
    claim += ['--role', 'df2-pregrant-' + args.role, '--timeout-s', '60',
              '--tag', authority['id'], '--', *command]
    started = time.time()
    peak = 0
    captured = {}
    failure = None
    with (run_dir / 'REGION-LOCK.log').open('wb') as log:
        proc = subprocess.Popen(claim, stdout=log, stderr=subprocess.STDOUT, env=env,
                                start_new_session=True)
        birth = int((pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
        captured[proc.pid] = birth
        try:
            while proc.poll() is None:
                group = members(proc.pid)
                captured.update({pid: data['birth_ticks'] for pid, data in group.items()})
                peak = max(peak, sum(data['rss_bytes'] for data in group.values()))
                if peak > 120 * 1024**3:
                    failure = 'owner pregrant RSS cap exceeded'
                    break
                if time.time() >= float(authority['end_epoch']) - 20:
                    failure = 'owner pregrant deadline reached'
                    break
                time.sleep(.2)
        except BaseException as exc:
            failure = 'owner pregrant guardian exception: ' + repr(exc)
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
    result_path = (run_dir / 'ROLLBACK-TEST.json' if args.purpose == 'test' else
                   run_dir / 'calibration/calibration-np4/CALIBRATION-RATE-SEALED.json')
    result_sha = sha(result_path) if result_path.is_file() else None
    if not failure and rc == 0 and drained:
        if not result_sha:
            failure = 'native result artifact missing after child rc0'
        else:
            try:
                result = json.loads(result_path.read_text())
                if args.purpose == 'test' and not result.get('pass'):
                    failure = 'same-image dirty-context test result is not PASS'
                elif args.purpose == 'calibrate' and (result.get('production_threads') != (96 if args.role == 'cpu' else 8)
                        or result.get('measured_tok_s', 0) <= 0 or
                        result.get('calibration_authority_sha256') != sha(authority_path)):
                    failure = 'calibrated rate result lacks role/thread/authority evidence'
            except (OSError, ValueError, TypeError) as exc:
                failure = 'native result artifact malformed: ' + repr(exc)
    receipt = {'schema': 'epyc.df2_12_1.owner_pregrant.v1', 'id': authority['id'],
               'purpose': args.purpose, 'role': args.role, 'authority_path': str(authority_path),
               'authority_sha256': sha(authority_path), 'authority': authority,
               'region_lock_argv': claim, 'region_lock_log_sha256': sha(run_dir / 'REGION-LOCK.log'),
               'leader_pid': proc.pid, 'leader_birth_ticks': birth, 'captured_pids_birth': captured,
               'peak_group_rss_bytes': peak, 'started_epoch': started, 'ended_epoch': time.time(),
               'returncode': rc, 'failure': failure, 'owned_group_drained': drained,
               'result_path': str(result_path), 'result_sha256': result_sha,
               'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (run_dir / 'OWNER-PREGRANT-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if failure or rc or not drained:
        raise RuntimeError(f'pregrant native {args.purpose} did not PASS: rc={rc}, failure={failure}, drained={drained}')
    if args.purpose == 'test':
        target = ROOT / 'corrected-proof' / shape / 'ROLLBACK-TEST.json'
        if target.exists():
            raise RuntimeError('refuse to replace earlier accepted role rollback proof')
        target.write_bytes((run_dir / 'ROLLBACK-TEST.json').read_bytes())
    print(json.dumps({'id': authority['id'], 'purpose': args.purpose, 'role': args.role,
                      'receipt': str(run_dir / 'OWNER-PREGRANT-RECEIPT.json'), 'pass': True}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f'OWNER_PREGRANT_REFUSED: {exc}', file=sys.stderr)
        raise SystemExit(2)
