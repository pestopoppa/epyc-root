#!/usr/bin/env python3
"""Prospective architect-general HIP slice and isolated CPU publisher smoke."""
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
import threading
import time

D = Path(__file__).resolve().parent
PORT = 19478
PROFILE = 'architect-general-hip'
KFD = Path('/sys/class/kfd/kfd/proc')


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
    if pins.get('profile') != PROFILE:
        raise ValueError('architect-general HIP profile identity differs')
    for entry in pins['arms'].values():
        for identity in (*entry['build_witnesses'], *entry['runtime_files'].values(), *entry['rocm_files'].values()):
            verify_pin(identity)
    cpu = pins['smoke_runtime']
    if file_sha(Path(cpu['build_manifest'])) != cpu['build_manifest_sha256']:
        raise ValueError('CPU smoke runtime manifest drift')
    for path, expected in cpu['runtime_files'].items():
        if file_sha(Path(path)) != expected:
            raise ValueError(f'CPU smoke runtime hash drift: {path}')
    model = pins['model_shards']
    if len(model) != 3 or len({entry['path'] for entry in model}) != 3:
        raise ValueError('model shard roster is incomplete')
    for entry in model:
        verify_pin(entry)  # A hash witness predates the grant. No weight hashing here.
    verify_pin(pins['template'], verify_digest=True)
    smoke = pins['smoke_model']
    verify_pin(smoke)
    if file_sha(Path(smoke['receipt_snapshot'])) != smoke['original_hash_receipt_sha256']:
        raise ValueError('CPU smoke model hash witness drift')
    witness = pins['profile_provenance']['model_hash_witness']
    if file_sha(Path(witness['snapshot'])) != witness['sha256']:
        raise ValueError('model shard hash witness drift')
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
        raise RuntimeError('server main thread affinity drift')
    expected = (runtime['runtime_files'] | runtime.get('rocm_files', {})).copy()
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


def vram_device(recipe):
    node = KFD.parent / 'topology/nodes' / str(recipe['kfd_topology_node'])
    props = dict(line.split(maxsplit=1) for line in (node / 'properties').read_text().splitlines())
    if (int((node / 'gpu_id').read_text()) != recipe['gpu_id']
            or int(props['drm_render_minor']) != recipe['render_minor']
            or int(props['vendor_id']) != 4098 or int(props['gfx_target_version']) != 90010):
        raise RuntimeError('pinned KFD topology entry does not identify the MI210')
    return Path('/sys/class/drm') / f"renderD{recipe['render_minor']}" / 'device/mem_info_vram_used'


def sample_hip(child, runtime, recipe, cpus, device_vram):
    maps = prove_server(child, runtime, cpus)
    vram = KFD / str(child.pid) / f"vram_{recipe['gpu_id']}"
    own = int(vram.read_text())
    total = int(device_vram.read_text())
    kfd_pids = sorted(int(entry.name) for entry in KFD.iterdir() if entry.name.isdecimal())
    if child.pid not in kfd_pids or not (0 < own <= recipe['max_vram_bytes'] and 0 < total):
        raise RuntimeError('tracked PID lacks valid same-device MI210 residency or exceeds the VRAM cap')
    affinity = {}
    for task in (Path('/proc') / str(child.pid) / 'task').iterdir():
        try:
            mask = os.sched_getaffinity(int(task.name))
        except ProcessLookupError:
            continue
        if not mask or not mask <= set(cpus):
            raise RuntimeError(f'thread {task.name} affinity exceeds the grant')
        affinity[task.name] = sorted(mask)
    return {'t_ns': time.monotonic_ns(), 'pid': child.pid, 'gpu_id': recipe['gpu_id'],
            'device_vram_bytes': total, 'process_vram_bytes': own, 'kfd_process_count': len(kfd_pids),
            'kfd_pids': kfd_pids, 'thread_affinity': affinity, 'mapped_libraries': maps}


def request(path, timeout, body=None, *, observe=None, residency_path=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    stop = threading.Event()
    samples = []
    failures = []
    sampler = None

    def capture_samples():
        while not stop.is_set():
            try:
                samples.append(observe())
            except Exception as exc:
                failures.append(f'{type(exc).__name__}: {exc}')
                return
            stop.wait(.1)

    try:
        method = 'GET' if body is None else 'POST'
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        start_ns = time.monotonic_ns()
        if observe is not None:
            sampler = threading.Thread(target=capture_samples, daemon=True)
            sampler.start()
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response exceeds native capture limit')
        return response.status, raw
    finally:
        end_ns = time.monotonic_ns()
        stop.set()
        connection.close()
        if sampler is not None:
            sampler.join(timeout=2)
            in_window = [sample for sample in samples if start_ns <= sample['t_ns'] <= end_ns]
            if sampler.is_alive():
                failures.append('sampler did not join')
            write_json(residency_path, {'request_sent_ns': start_ns, 'response_end_ns': end_ns,
                                       'samples': in_window, 'errors': failures})


def verify_residency(path):
    evidence = json.loads(path.read_bytes())
    times = {sample['t_ns'] for sample in evidence['samples']}
    if evidence['errors'] or len(times) < 2:
        raise RuntimeError(f'request lacks two clean, distinct in-window HIP samples: {path}')

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
    if requests.keys() != plan['request_files'].keys() or len(plan['items']) != 4:
        raise ValueError('prospective request roster differs')
    return requests


def verify_no_spec_response(data, item, recipe):
    verbose = data['__verbose']
    settings = verbose['generation_settings']
    timings = verbose['timings']
    spec_types = settings['speculative.types']
    # Both parsers add the explicit spec type to the default list, so "none,none" is valid.
    if (not isinstance(spec_types, str) or set(spec_types.split(',')) != {'none'}
            or any(type(timings.get(key, 0)) is not int or timings.get(key, 0) != 0
                   for key in ('draft_n', 'draft_n_accepted'))):
        raise ValueError('native response did not prove zero-draft no-spec generation')

    tokens = verbose['tokens']
    counts = (data['usage']['completion_tokens'], verbose['tokens_predicted'], timings['predicted_n'])
    choice, = data['choices']
    finish = choice['finish_reason']
    content = choice['message']['content']
    limit = item['request_body']['max_tokens']
    if (not isinstance(tokens, list) or not tokens
            or any(type(token) is not int or token < 0 for token in tokens)
            or any(type(count) is not int or count != len(tokens) for count in counts)
            or not isinstance(content, str) or not content.strip()
            or finish not in ('stop', 'length') or len(tokens) > limit
            or (finish == 'length' and len(tokens) != limit)):
        raise ValueError('native response lacks consistent token, text or finish evidence')

    prompt_n = data['usage']['prompt_tokens']
    minimum = recipe['minimum_long_prompt_tokens'] if item['prompt_shape'] == 'long' else 1
    if (type(prompt_n) is not int or not minimum <= prompt_n <= recipe['context_tokens'] - limit
            or verbose['tokens_evaluated'] != prompt_n or timings['prompt_n'] != prompt_n
            or data['usage']['prompt_tokens_details']['cached_tokens'] != 0
            or timings['cache_n'] != 0 or verbose['truncated'] is not False):
        raise ValueError('native response lacks intact cold-prefill length or truncation evidence')


def capture_arm(arm, runtime, recipe, items, requests, out, cpus, deadline, stop):
    if listeners():
        raise RuntimeError('isolated port already in use')
    arm_dir = out / arm
    arm_dir.mkdir()
    binary = Path(runtime['binary'])
    hip = recipe.get('device') == 'ROCm0'
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': runtime.get('ld_library_path', str(binary.parent)),
           'GGML_IQK': '1', 'ROCR_VISIBLE_DEVICES': '0' if hip else '-1',
           'HIP_VISIBLE_DEVICES': '0' if hip else '-1', 'CUDA_VISIBLE_DEVICES': '0' if hip else '',
           'OMP_NUM_THREADS': '1', 'FILLER_ID': os.environ['FILLER_ID']}
    device_vram = vram_device(recipe) if hip else None
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
            if hip:
                startup = (arm_dir / 'server.log').read_text()
                layer_count = recipe['offloaded_layers']
                if (not re.search(rf'offloaded {layer_count}/[0-9]+ layers to GPU', startup)
                        or not re.search(r'ROCm0[^\n]*(?:MI210|gfx90a)|(?:MI210|gfx90a)[^\n]*ROCm0', startup)):
                    raise RuntimeError('native startup did not prove the pinned MI210 and partial layer count')
                write_json(arm_dir / 'startup-residency.json', sample_hip(child, runtime, recipe, cpus, device_vram))
            if recipe.get('speculation') == 'none':
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
                residency = arm_dir / f'{name}.hip-residency.json'
                def observe():
                    return sample_hip(child, runtime, recipe, cpus, device_vram)
                status, raw = request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']), wire,
                                      observe=observe if hip else None, residency_path=residency)
                write(arm_dir / f'{name}.response.json', raw)
                if hip:
                    verify_residency(residency)
                budget(deadline, stop, 1)
                prove_server(child, runtime, cpus)
                if status != 200:
                    raise RuntimeError(f'{arm}/{name} response status {status}')
                data = json.loads(raw)
                if not isinstance(data, dict) or 'error' in data:
                    raise ValueError(f'{arm}/{name} response is not a successful object')
                if recipe.get('speculation') == 'none':
                    try:
                        verify_no_spec_response(data, item, recipe)
                    except (KeyError, ValueError, TypeError) as exc:
                        raise RuntimeError(f'{arm}/{name}: {exc}') from exc
                records.append({'id': name, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
                                'response_b64': base64.b64encode(raw).decode('ascii'),
                                'hip_residency_sha256': file_sha(residency) if hip else None})
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            kfd_exit = time.monotonic() + 5
            while hip and (KFD / str(child.pid)).exists() and time.monotonic() < kfd_exit:
                time.sleep(.1)
            state = {'pid': child.pid, 'dead': child.poll() is not None,
                     'port_closed': not listeners(), 'exit_status': child.returncode,
                     'kfd_entry_absent': not (KFD / str(child.pid)).exists() if hip else None}
            write_json(arm_dir / 'cleanup.json', state)
            if not state['dead'] or not state['port_closed'] or (hip and not state['kfd_entry_absent']):
                raise RuntimeError('captured server, listener or KFD entry remains after cleanup')
    return records


def stop_signal(signum, _frame):
    raise InterruptedError(f'interrupted by signal {signum}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    plan = json.loads((D / 'plan.json').read_bytes())
    verify_files(plan)
    requests = read_requests(plan)
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
    recipe = plan['recipes']['smoke_control' if smoke else 'hip_slice']
    if not smoke and (cpus != recipe['cpu_affinity'] or os.sched_getaffinity(0) != set(cpus)
                      or os.environ.get('FILLER_NEEDGPU') != '1' or os.environ.get('FILLER_GPU_FENCE') == '1'):
        raise ValueError('full HIP capture requires the pinned MI210 grant and GPU-shepherd affinity')
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
        identity['prompt_template_sha256'] = plan['template']['sha256']
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
                       'mode': 'native-smoke-control' if smoke else 'architect-general-hip-slice-only',
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
