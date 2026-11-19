#!/usr/bin/env python3
"""Paired DFlash2 source-input capture and isolated CPU publisher smoke."""
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

from pair import CAP, CAP_KEY, verify_pairs, verify_response

D = Path(__file__).resolve().parent
PORT = 19480
PROFILE = 'dspark-dflash'


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


def verify_pin(entry, *, verify_digest=False):
    path = Path(entry['path'])
    if path.resolve(strict=True) != path or stat_id(path) != entry['stat']:
        raise ValueError(f'prepared file identity drift: {path}')
    if verify_digest and file_sha(path) != entry['sha256']:
        raise ValueError(f'prepared file content drift: {path}')


def verify_files(pins):
    if pins['profile'] != PROFILE or pins['validated_cap'] != CAP:
        raise ValueError('profile or DFlash2 cap differs')
    for arm in pins['arms'].values():
        for entry in (*arm['build_witnesses'], *arm['runtime_files'].values()):
            verify_pin(entry)
    for entry in (*pins['model_shards'], pins['draft_model'], pins['smoke_model']):
        verify_pin(entry)  # Large asset content was hashed before the grant.
    verify_pin(pins['template'], verify_digest=True)
    for entry in pins['source_witnesses']:
        path = Path(entry['path'])
        if path.parent == D:
            # Full rowflow grants stage packet files on a new filesystem.
            if file_sha(path) != entry['sha256']:
                raise ValueError(f'copied source witness content drift: {path}')
        else:
            verify_pin(entry, verify_digest=True)
    for witness in (pins['smoke_model'], pins['model_hash_witness'], pins['prior_frontdoor_json_mismatch']):
        if file_sha(Path(witness['snapshot'])) != witness['receipt_sha256']:
            raise ValueError('pregrant hash witness drift')


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
        raise RuntimeError('server main thread affinity drift')
    expected = runtime['runtime_files'].copy()
    binary = expected.pop(runtime['binary'])
    if isinstance(binary, dict) and stat_id(proc / 'exe') != binary['stat']:
        raise RuntimeError('tracked executable inode differs from prepared store')
    observed = {}
    for row in (proc / 'maps').read_text().splitlines():
        fields = row.split(maxsplit=5)
        if len(fields) != 6:
            continue
        path = fields[5]
        name = Path(path).name
        relevant = name.startswith(('libggml', 'libllama', 'libamdhip64', 'libhipblas',
                                    'librocblas', 'libhsa-runtime64'))
        if not relevant:
            continue
        if path not in expected or path.endswith(' (deleted)'):
            raise RuntimeError(f'unpinned mapped library: {path}')
        major, minor = (int(field, 16) for field in fields[3].split(':'))
        identity = expected[path]
        mapped = [os.makedev(major, minor), int(fields[4])]
        file_stat = stat_id(Path(path))
        if mapped != file_stat[:2] or (isinstance(identity, dict) and file_stat != identity['stat']):
            raise RuntimeError(f'mapped library inode differs from its prepared pin: {path}')
        observed[path] = {'device': mapped[0], 'inode': mapped[1], 'sha256':
                          identity['sha256'] if isinstance(identity, dict) else identity}
    if set(observed) != set(expected):
        raise RuntimeError(f'missing pinned libraries: {set(expected) - set(observed)}')
    return observed


def request(path, timeout, body=None, observe=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    try:
        method = 'GET' if body is None else 'POST'
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        if observe is not None:
            observe()
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response exceeds capture limit')
        return response.status, raw
    finally:
        connection.close()


def read_requests(plan):
    requests = {}
    items = [*plan['items'], *plan['smoke_items']]
    if sha(canonical(plan['items'])) != plan['question_pool_sha256']:
        raise ValueError('prospective item pool drifted')
    for item in items:
        name = item['id']
        entry = plan['request_files'][name]
        path = D / 'requests' / f'{name}.json'
        wire = path.read_bytes()
        if (entry['path'] != f'requests/{name}.json' or sha(wire) != entry['sha256']
                or wire != canonical(item['request_body']) or name in requests):
            raise ValueError(f'prospective request bytes drifted: {name}')
        requests[name] = wire
    if requests.keys() != plan['request_files'].keys() or len(plan['items']) != 8:
        raise ValueError('prospective request roster differs')
    return requests


def capture_arm(arm, runtime, recipe, items, requests, out, cpus, deadline, stop):
    if listeners():
        raise RuntimeError('isolated port already in use')
    arm_dir = out / arm
    arm_dir.mkdir()
    binary = Path(runtime['binary'])
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': str(binary.parent),
           'GGML_IQK': '1', 'ROCR_VISIBLE_DEVICES': '-1', 'HIP_VISIBLE_DEVICES': '-1',
           'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '1', 'FILLER_ID': os.environ['FILLER_ID']}
    argv = [str(binary), '--host', '127.0.0.1', '--port', str(PORT), '--threads', str(len(cpus)),
            *recipe['args']]
    records = []
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
            if not recipe.get('smoke'):
                shape = (f"n_slots = {recipe['slots']}, n_ctx_slot = {recipe['context_tokens']}, "
                         "kv_unified = 'false'")
                if shape not in (arm_dir / 'server.log').read_text():
                    raise RuntimeError('native startup did not echo pinned slot and KV context')
            write_json(arm_dir / 'server.json', {'argv': argv, 'pid': child.pid, 'cpus': cpus,
                       'mapped_libraries': mapped, 'image': runtime, 'recipe': recipe, 'environment': env})
            for item in items:
                prove_server(child, runtime, cpus)
                name = item['id']
                wire = requests[name]
                write(arm_dir / f'{name}.request.json', wire)
                def observe():
                    write_json(arm_dir / f'{name}.request-custody.json',
                               {'pid': child.pid, 'cpus': cpus, 'monotonic_ns': time.monotonic_ns(),
                                'phase': 'after-request-send-before-response-read',
                                'mapped_libraries': prove_server(child, runtime, cpus)})
                status, raw = request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']), wire, observe)
                write(arm_dir / f'{name}.response.json', raw)
                budget(deadline, stop, 1)
                prove_server(child, runtime, cpus)
                if status != 200:
                    raise RuntimeError(f'{arm}/{name} response status {status}')
                data = json.loads(raw)
                if not isinstance(data, dict) or 'error' in data:
                    raise ValueError(f'{arm}/{name} response is not a successful object')
                counters = verify_response(data, item, recipe)
                record = {'id': name, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
                          'response_b64': base64.b64encode(raw).decode('ascii'),
                          'request_custody_sha256': file_sha(arm_dir / f'{name}.request-custody.json')}
                if not recipe.get('smoke'):
                    record.update({'dflash_pair': item['dflash_pair'], 'draft_counters': counters,
                                   'server_instance': f"{os.environ['FILLER_ID']}:{arm}:{child.pid}",
                                   'parallel_slots': recipe['slots'],
                                   'effective_n_max': data['generation_settings'][CAP_KEY]})
                records.append(record)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            state = {'pid': child.pid, 'dead': child.poll() is not None,
                     'port_closed': not listeners(), 'exit_status': child.returncode}
            write_json(arm_dir / 'cleanup.json', state)
            if not state['dead'] or not state['port_closed']:
                raise RuntimeError('captured server or listener remains after cleanup')
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
    requests = read_requests(plan)
    verify_pairs(plan['items'])
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
    recipe = plan['recipes']['smoke_control' if smoke else 'cpu_slice']
    if not smoke and (len(os.sched_getaffinity(0)) != args.threads or os.environ.get('FILLER_NEEDGPU') == '1'):
        raise ValueError('full paired capture requires one CPU quarter')
    os.sched_setaffinity(0, cpus)
    out = result.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    write(out / 'scheduler.grant', grant.read_bytes())
    items = plan['smoke_items' if smoke else 'items']
    production = plan['smoke_runtime'] if smoke else plan['arms']['production']
    bank = capture_arm('production', production, recipe, items, requests, out, cpus, deadline, stop)
    identity = {'profile': 'smoke-control' if smoke else plan['profile'],
                'model': plan['smoke_model'] if smoke else plan['model_shards'],
                'recipe_sha256': sha(canonical(recipe)), 'question_pool_sha256': sha(canonical(items)),
                'request_plan_sha256': file_sha(D / 'plan.json'), 'capture_runner_sha256': file_sha(Path(__file__))}
    if not smoke:
        identity['registered_template_sha256'] = plan['template']['sha256']
        identity['prompt_path'] = 'native raw completion with no template transformation'
        identity['draft_model'] = plan['draft_model']
        identity['validated_cap'] = CAP
        identity['prior_frontdoor_receipt_sha256'] = plan['prior_frontdoor_json_mismatch']['receipt_sha256']
    bank_path = out / 'banked-capture.json'
    bank_pin = write_json(bank_path, {'capture_identity': identity, 'runtime': production, 'items': bank})
    write(out / 'banked-capture.sha256', (bank_pin + '\n').encode())
    candidate_pin = None
    if not smoke:
        budget(deadline, stop, 1)
        if file_sha(bank_path) != bank_pin or file_sha(D / 'plan.json') != identity['request_plan_sha256']:
            raise RuntimeError('bank or prospective plan changed before candidate launch')
        verify_files(plan)
        candidate = capture_arm('candidate', plan['arms']['candidate'], recipe, items, requests, out, cpus, deadline, stop)
        verify_files(plan)
        if file_sha(bank_path) != bank_pin or file_sha(D / 'plan.json') != identity['request_plan_sha256']:
            raise RuntimeError('bank or prospective plan changed during candidate capture')
        candidate_pin = write_json(out / 'candidate-capture.json', {'capture_identity': identity,
                                   'runtime': plan['arms']['candidate'], 'bank_sha256': bank_pin, 'items': candidate})
    budget(deadline, stop, 1)
    write_json(result, {'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
                       'mode': 'native-smoke-control' if smoke else 'dflash2-cpu-paired-slice-only',
                       'cpus': cpus, 'capture_identity': identity, 'bank_sha256': bank_pin,
                       'candidate_sha256': candidate_pin, 'request_count_per_arm': len(items),
                       'target_profile': plan['profile'], 'broad_pack_status': 'incomplete',
                       'prior_frontdoor_json_mismatch': True, 'quality_transfer_authorized': False,
                       'promotion_authorized': False})


if __name__ == '__main__':
    try:
        main()
    except InterruptedError as exc:
        raise SystemExit(75) from exc
