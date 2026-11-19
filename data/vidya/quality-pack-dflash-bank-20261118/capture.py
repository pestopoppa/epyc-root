#!/usr/bin/env python3
"""Strict production-only DFlash2 bank and isolated CPU publisher smoke."""
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
import traceback

import quality_parity as parity
from pair import CAP, CAP_KEY, verify_pairs, verify_response

D = Path(__file__).resolve().parent
PORT = 19488
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


def request(path, timeout, body=None, observe=None, partial_path=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    try:
        method = 'GET' if body is None else 'POST'
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        if observe is not None:
            observe()
        response = connection.getresponse()
        chunks = []
        size = 0
        try:
            while True:
                chunk = response.read1(min(65536, 4 * 1024 * 1024 + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > 4 * 1024 * 1024:
                    raise ValueError('response exceeds capture limit')
            return response.status, b''.join(chunks)
        except BaseException:
            if partial_path is not None:
                write(partial_path, b''.join(chunks))
            raise
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
                status, raw = request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']), wire, observe, arm_dir / f'{name}.response.partial')
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

def validate_plan(plan):
    verify_files(plan)
    if set(plan['arms']) != {'production'} or plan['smoke_runtime'] != plan['arms']['production']:
        raise ValueError('bank packet requires only the production runtime')
    if plan['validator_source_sha256'] != parity.VALIDATOR_SOURCE_SHA256:
        raise ValueError('comparator source differs from prospective pin')
    for filename, key in (('dflash-original-admission.json', 'admission_sha256'),
                          ('r3-owner-receipt.json', 'filing_sha256')):
        if file_sha(D / filename) != plan['prior_dflash'][key]:
            raise ValueError(f'original DFlash witness drifted: {filename}')
    requests = read_requests(plan)
    verify_pairs(plan['items'])
    endpoint = plan['recipes']['cpu_slice']['endpoint']
    for item in plan['items']:
        expected = parity.ITEM_FIELDS - {'production'}
        parity._fields(item, expected, item['id'])
        if (item['shape'] != PROFILE or item['expected_finish'] not in parity.FINISHES
                or item['prompt_shape'] not in parity.PROMPTS or item['output_format'] not in parity.FORMATS
                or item['fixture'] is not None):
            raise ValueError(f"unsupported coverage tags: {item['id']}")
        if item['output_format'] == 'json' and item['validator']['id'] != 'json-object-subset.v1':
            raise ValueError('JSON requires the versioned JSON object validator')
        parity._request(item['request_body'], endpoint)
        parity._semantic_matches(item['validator'], '')
    return requests


def validate_bank(plan, rows, production, server, cleanup):
    recipe = plan['recipes']['cpu_slice']
    requested = parity._named_rows(plan['items'], 'bank item')
    captured = parity._named_rows(rows, 'captured item')
    if captured.keys() != requested.keys():
        raise ValueError('bank inventory differs from the pinned requests')
    if (cleanup['pid'] != server['pid'] or cleanup['dead'] is not True
            or cleanup['port_closed'] is not True):
        raise ValueError('captured PID or listener is not clean')
    checks, pairs, items = {}, {}, []
    for name, item in requested.items():
        body = item['request_body']
        row = captured[name]
        fields = parity.CAPTURE_FIELDS | parity.DFLASH_FIELDS
        parity._fields(row, fields | {'id', 'dflash_pair', 'draft_counters', 'request_custody_sha256'}, name)
        record = {key: row[key] for key in fields}
        request = (production / f'{name}.request.json').read_bytes()
        response = (production / f'{name}.response.json').read_bytes()
        custody_raw = (production / f'{name}.request-custody.json').read_bytes()
        custody = parity._parse(custody_raw)
        if (sha(custody_raw) != row['request_custody_sha256']
                or custody['pid'] != server['pid'] or custody['cpus'] != server['cpus']
                or custody['phase'] != 'after-request-send-before-response-read'
                or custody['mapped_libraries'] != server['mapped_libraries']
                or row['server_instance'] != f"{os.environ['FILLER_ID']}:production:{server['pid']}"):
            raise ValueError(f'{name}: native request custody differs from tracked server')
        if (request != parity.canonical_json(body) or row['dflash_pair'] != item['dflash_pair']
                or response != base64.b64decode(record['response_b64'], validate=True)):
            raise ValueError(f'{name}: original request, response, or pair differs')
        _, limit = parity._request(body, recipe['endpoint'])
        cap = body[CAP_KEY]
        content, reasoning, finish, tokens, count = parity._capture(
            record, sha(request), recipe['endpoint'], cap, limit,
        )
        counters = verify_response(parity._parse(response), item, recipe)
        if row['draft_counters'] != counters or tokens is None or count is None:
            raise ValueError(f'{name}: native draft or output token evidence differs')
        semantic = parity._semantic_matches(item['validator'], content)
        problems = []
        if finish != item['expected_finish']:
            problems.append('finish_mismatch')
        if not semantic:
            problems.append('semantic_validation_failed')
        checks[name] = {
            'expected_finish': item['expected_finish'], 'actual_finish': finish,
            'semantic_matches': semantic, 'validator': item['validator'],
            'completion_count': count, 'output_token_count': len(tokens),
            'content_sha256': sha(content.encode()),
            'reasoning_sha256': None if reasoning is None else sha(reasoning.encode()),
            'response_sha256': row['response_sha256'], 'problems': problems,
        }
        pairs.setdefault(item['dflash_pair'], []).append(parity._pair_row(item, record, cap))
        items.append({**item, 'production': record})
    parity._pair_check(pairs, 'production')
    return checks, items


def run(plan, plan_pin, requests, result, smoke):
    deadline = deadline_epoch(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    budget(deadline, stop, 1)
    grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
    cpus = sorted(os.sched_getaffinity(0))
    if smoke:
        if len(cpus) < 4:
            raise ValueError('native smoke requires at least four granted CPUs')
        cpus = cpus[:4]
        os.sched_setaffinity(0, cpus)
    elif len(cpus) != 24 or os.environ.get('FILLER_NEEDGPU') == '1':
        raise ValueError('production bank requires one granted 24-CPU quarter')
    out = result.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    grant_raw = grant.read_bytes()
    grant_pin = sha(grant_raw)
    write(out / 'scheduler.grant', grant_raw)
    recipe = plan['recipes']['smoke_control' if smoke else 'cpu_slice']
    items = plan['smoke_items' if smoke else 'items']
    runtime = plan['arms']['production']
    rows = capture_arm('production', runtime, recipe, items, requests, out, cpus, deadline, stop)
    budget(deadline, stop, 1)
    validate_plan(plan)
    if file_sha(D / 'plan.json') != plan_pin:
        raise RuntimeError('prospective plan changed during capture')
    identity = {
        'profile': 'smoke-control' if smoke else plan['profile'],
        'model': plan['smoke_model'] if smoke else plan['model_shards'],
        'recipe_sha256': sha(canonical(recipe)), 'question_pool_sha256': sha(canonical(items)),
        'request_plan_sha256': plan_pin, 'capture_runner_sha256': file_sha(Path(__file__)),
        'scheduler_grant_sha256': grant_pin,
    }
    bank = {'capture_identity': identity, 'runtime': runtime, 'items': rows}
    summary = {
        'schema': 'epyc.quality_pack_native_slice.v1' if smoke else 'epyc.quality_pack_dflash_bank.v1',
        'mode': 'native-smoke-control' if smoke else 'strict-production-bank',
        'status': 'capture-complete' if smoke else 'bank_admitted',
        'cpus': cpus, 'capture_identity': identity, 'request_count_per_arm': len(items),
        'candidate_collected': False, 'candidate_sha256': None, 'target_profile': plan['profile'],
        'broad_pack_status': 'incomplete', 'observation_only': True,
        'prior_frontdoor_json_mismatch': True, 'quality_transfer_authorized': False,
        'promotion_authorized': False,
    }
    if not smoke:
        production = out / 'production'
        server_raw = (production / 'server.json').read_bytes()
        cleanup_raw = (production / 'cleanup.json').read_bytes()
        server = parity._parse(server_raw)
        if server['image'] != runtime or server['recipe'] != recipe or server['cpus'] != cpus:
            raise ValueError('captured server does not match the grant or plan')
        identity.update({
            'registered_template_sha256': plan['template']['sha256'],
            'validator_source_sha256': parity.VALIDATOR_SOURCE_SHA256,
            'prompt_path': 'native raw completion with no template transformation',
            'draft_model': plan['draft_model'], 'validated_cap': CAP,
            'prior_dflash': plan['prior_dflash'],
            'prior_frontdoor_receipt_sha256': plan['prior_frontdoor_json_mismatch']['receipt_sha256'],
            'server_sha256': sha(server_raw), 'cleanup_sha256': sha(cleanup_raw),
        })
        checks, pack_items = validate_bank(plan, rows, production, server, parity._parse(cleanup_raw))
        bank.update({'checks': checks, 'pack_items': pack_items, 'shape': plan['shape']})
        summary['checks'] = checks
        if any(check['problems'] for check in checks.values()):
            summary['status'] = 'inadmissible_bank'
    budget(deadline, stop, 1)
    name = 'inadmissible-capture' if summary['status'] == 'inadmissible_bank' else 'banked-capture'
    summary['bank_sha256'] = write_json(out / f'{name}.json', bank)
    write(out / f'{name}.sha256', (summary['bank_sha256'] + '\n').encode())
    write_json(result, summary)
    return 1 if summary['status'] == 'inadmissible_bank' else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    plan_raw = (D / 'plan.json').read_bytes()
    plan = parity._parse(plan_raw)
    requests = validate_plan(plan)
    if args.preflight:
        return 0
    signal.signal(signal.SIGTERM, stop_signal)
    smoke = os.getenv('FILLER_DRYRUN') == '1'
    result = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out' / 'RESULT.json'
    return run(plan, sha(plan_raw), requests, result, smoke)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            root = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).parent if os.getenv('FILLER_DRYRUN') == '1' else D / 'out'
            root.mkdir(parents=True, exist_ok=True)
            write_json(root / 'FAILURE.json', {'exception_type': type(exc).__name__, 'message': str(exc),
                       'traceback': traceback.format_exc(), 'status': 'capture-failed'})
        except Exception:
            traceback.print_exc()
        if isinstance(exc, InterruptedError):
            raise SystemExit(75) from exc
        raise
