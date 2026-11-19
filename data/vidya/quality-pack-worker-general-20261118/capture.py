#!/usr/bin/env python3
"""Prospective worker-general slice on isolated pinned CPU images; small native smoke."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

D = Path(__file__).resolve().parent
PORT = 19470
PROFILE = 'worker-general-cpu-moe-mtp'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, contents):
    with path.open('xb') as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, obj):
    write(path, canonical(obj) + b'\n')
    return file_sha(path)


def stat_id(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def verify_files(pins):
    if pins.get('profile') != PROFILE:
        raise ValueError('worker-general profile identity differs')
    for entry in pins['arms'].values():
        manifest = Path(entry['build_manifest'])
        if file_sha(manifest) != entry['build_manifest_sha256']:
            raise ValueError(f'kernel runtime manifest drift: {manifest}')
        if 'build_identity' in entry and file_sha(Path(entry['build_identity'])) != entry['build_identity_sha256']:
            raise ValueError('C13 build identity manifest drift')
        for path, expected in entry['runtime_files'].items():
            if file_sha(Path(path)) != expected:
                raise ValueError(f'kernel runtime hash drift: {path}')
    for name in ('worker_general_model', 'smoke_model', 'worker_general_template'):
        entry = pins[name]
        path = Path(entry['path'])
        if stat_id(path) != entry['stat']:
            raise ValueError(f'{name} stat differs from its hash witness')
        if name == 'worker_general_template' and file_sha(path) != entry['sha256']:
            raise ValueError(f'{name} hash drift: {path}')
        if 'receipt_snapshot' in entry and file_sha(Path(entry['receipt_snapshot'])) != entry['original_hash_receipt_sha256']:
            raise ValueError(f'{name} original hash receipt drift')
    mismatch = pins['prior_frontdoor_json_mismatch']
    if file_sha(Path(mismatch['snapshot'])) != mismatch['receipt_sha256']:
        raise ValueError('prior frontdoor mismatch receipt drift')


def deadline_epoch(text):
    if re.fullmatch(r'[0-9]+', text):
        return int(text)
    deadline = datetime.fromisoformat(text.removesuffix('Z') + '+00:00' if text.endswith('Z') else text)
    if deadline.utcoffset() is None:
        raise ValueError('FILLER_DEADLINE requires a time zone')
    return deadline.astimezone(timezone.utc).timestamp()


def budget(deadline, stop, maximum):
    remaining = deadline - time.time()
    if stop.exists() or remaining <= 0:
        raise InterruptedError('STOP or grant deadline reached')
    return min(maximum, remaining)


def listeners():
    found = set()
    for table in (Path('/proc/net/tcp'), Path('/proc/net/tcp6')):
        if not table.exists():
            continue
        for row in table.read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] == '0A' and int(fields[1].split(':')[1], 16) == PORT:
                found.add(f'socket:[{fields[9]}]')
    return found


def owns_listener(child):
    proc = Path('/proc') / str(child.pid)
    owned = set()
    for fd in (proc / 'fd').iterdir():
        try:
            owned.add(os.readlink(fd))
        except FileNotFoundError:
            continue
    active = listeners()
    return bool(active) and active <= owned


def prove_server(child, runtime, cpus):
    proc = Path('/proc') / str(child.pid)
    if child.poll() is not None or (proc / 'exe').resolve(strict=True) != Path(runtime['binary']):
        raise RuntimeError('tracked process differs from the pinned server')
    if not owns_listener(child):
        raise RuntimeError('tracked server does not own the isolated listener')
    if os.sched_getaffinity(child.pid) != set(cpus):
        raise RuntimeError('server affinity drift')
    observed = set()
    for row in (proc / 'maps').read_text().splitlines():
        fields = row.split(maxsplit=5)
        if len(fields) == 6 and Path(fields[5]).name.startswith(('libggml', 'libllama')):
            observed.add(str(Path(fields[5]).resolve(strict=True)))
    expected = set(runtime['runtime_files']) - {runtime['binary']}
    if observed != expected:
        raise RuntimeError(f'unpinned or missing server libraries: {observed ^ expected}')
    return sorted(observed)


def request(path, timeout, body=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    try:
        method = 'GET' if body is None else 'POST'
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response exceeds native capture limit')
        return response.status, raw
    finally:
        connection.close()


def capture_arm(arm, runtime, recipe, items, out, cpus, deadline, stop):
    if listeners():
        raise RuntimeError('isolated port already in use')
    arm_dir = out / arm
    arm_dir.mkdir()
    binary = Path(runtime['binary'])
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': str(binary.parent), 'GGML_IQK': '1',
           'ROCR_VISIBLE_DEVICES': '-1', 'HIP_VISIBLE_DEVICES': '-1', 'CUDA_VISIBLE_DEVICES': '',
           'OMP_NUM_THREADS': '1', 'FILLER_ID': os.environ['FILLER_ID']}
    argv = [str(binary), '--host', '127.0.0.1', '--port', str(PORT), '--threads', str(len(cpus)),
            *recipe['args']]
    records = []
    mtp = recipe['endpoint'] == '/v1/chat/completions'
    drafted = 0
    with (arm_dir / 'server.log').open('xb') as log:
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=arm_dir)
        try:
            ready = time.monotonic() + budget(deadline, stop, recipe['startup_s'])
            while time.monotonic() < ready and child.poll() is None:
                remaining = budget(deadline, stop, 1)
                try:
                    if owns_listener(child) and request('/health', remaining)[0] == 200:
                        break
                except InterruptedError:
                    raise
                except (OSError, http.client.HTTPException):
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError('isolated server failed health before startup limit')
            mapped = prove_server(child, runtime, cpus)
            write_json(arm_dir / 'server.json', {'argv': argv, 'pid': child.pid, 'cpus': cpus,
                       'mapped_libraries': mapped, 'image': runtime, 'recipe': recipe})
            for item in items:
                prove_server(child, runtime, cpus)
                wire = canonical(item['request_body'])
                name = item['id']
                write(arm_dir / f'{name}.request.json', wire)
                status, raw = request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']), wire)
                write(arm_dir / f'{name}.response.json', raw)
                prove_server(child, runtime, cpus)
                if status != 200:
                    raise RuntimeError(f'{arm}/{name} response status {status}')
                data = json.loads(raw)
                if not isinstance(data, dict) or 'error' in data:
                    raise ValueError(f'{arm}/{name} response is not a successful object')
                if mtp:
                    verbose = data['__verbose']
                    settings = verbose['generation_settings']
                    if ('draft-mtp' not in settings['speculative.types'].split(',')
                            or settings['speculative.n_max'] != 4):
                        raise RuntimeError(f'{arm}/{name} did not echo the pinned MTP recipe')
                    amount = verbose['timings'].get('draft_n', 0)
                    if type(amount) is not int or amount < 0:
                        raise RuntimeError(f'{arm}/{name} supplied invalid MTP draft count')
                    drafted += amount
                records.append({'id': name, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
                                'response_b64': base64.b64encode(raw).decode('ascii')})
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            write_json(arm_dir / 'cleanup.json', {'pid': child.pid, 'dead': child.poll() is not None,
                       'port_closed': not listeners(), 'exit_status': child.returncode})
            if child.poll() is None or listeners():
                raise RuntimeError('captured server or listener remains after cleanup')
    if mtp and not drafted:
        raise RuntimeError(f'{arm} produced no native MTP draft tokens')
    return records


def stop_signal(signum, _frame):
    raise InterruptedError(f'interrupted by signal {signum}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, default=24)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    plan = json.loads((D / 'plan.json').read_bytes())
    verify_files(plan)
    if args.preflight:
        return
    signal.signal(signal.SIGTERM, stop_signal)
    smoke = os.getenv('FILLER_DRYRUN') == '1'
    result = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out' / 'RESULT.json'
    deadline = deadline_epoch(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    budget(deadline, stop, 1)
    grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
    cpus = sorted(os.sched_getaffinity(0))
    threads = 4 if smoke else args.threads
    if len(cpus) < threads:
        raise ValueError('grant cpuset does not cover requested threads')
    cpus = cpus[:threads]
    os.sched_setaffinity(0, cpus)
    recipe = plan['recipes']['smoke_control' if smoke else 'worker_general_slice']
    out = result.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    write(out / 'scheduler.grant', grant.read_bytes())
    items = plan['smoke_items' if smoke else 'items']
    bank = capture_arm('production', plan['arms']['production'], recipe, items, out, cpus, deadline, stop)
    identity = {'profile': 'smoke-control' if smoke else plan['profile'],
                'model': plan['smoke_model' if smoke else 'worker_general_model'],
                'recipe_sha256': sha(canonical(recipe)), 'question_pool_sha256': sha(canonical(items)),
                'request_plan_sha256': file_sha(D / 'plan.json'), 'capture_runner_sha256': file_sha(Path(__file__))}
    if not smoke:
        identity['prompt_template_sha256'] = plan['worker_general_template']['sha256']
        identity['prior_frontdoor_receipt_sha256'] = plan['prior_frontdoor_json_mismatch']['receipt_sha256']
    bank_path = out / 'banked-capture.json'
    bank_pin = write_json(bank_path, {'capture_identity': identity, 'runtime': plan['arms']['production'], 'items': bank})
    write(out / 'banked-capture.sha256', (bank_pin + '\n').encode())
    candidate_pin = None
    if not smoke:
        budget(deadline, stop, 1)
        if file_sha(bank_path) != bank_pin or file_sha(D / 'plan.json') != identity['request_plan_sha256']:
            raise RuntimeError('bank or prospective plan changed before candidate launch')
        verify_files(plan)
        candidate = capture_arm('candidate', plan['arms']['candidate'], recipe, items, out, cpus, deadline, stop)
        verify_files(plan)
        if file_sha(bank_path) != bank_pin or file_sha(D / 'plan.json') != identity['request_plan_sha256']:
            raise RuntimeError('bank or prospective plan changed during candidate capture')
        candidate_pin = write_json(out / 'candidate-capture.json', {'capture_identity': identity,
                                   'runtime': plan['arms']['candidate'], 'bank_sha256': bank_pin, 'items': candidate})
    write_json(result, {'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
                       'mode': 'native-smoke-control' if smoke else 'worker-general-slice-only',
                       'cpus': cpus, 'capture_identity': identity, 'bank_sha256': bank_pin,
                       'candidate_sha256': candidate_pin, 'request_count_per_arm': len(items),
                       'target_profile': plan['profile'], 'broad_pack_status': 'incomplete',
                       'prior_frontdoor_json_mismatch': True, 'promotion_authorized': False})


if __name__ == '__main__':
    try:
        main()
    except InterruptedError as exc:
        raise SystemExit(75) from exc
