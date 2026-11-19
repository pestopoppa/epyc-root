"""Native qwen4exp CPU loader diagnostic replay and write-side sealing."""

import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

ROW = 'handoff-vidya-quality-pack-loader-diag-wire-20261118'
OP = 'QWEN4EXP_CPU_LOADER'
SOURCE_KIND = 'qwen4exp-cpu-loader-diagnostic'
SCHEMA = 'epyc.qwen4exp_cpu_loader_diagnostic.v1'
SEAL_SCHEMA = 'epyc.qwen4exp_cpu_loader_diagnostic_seal.v1'
SEAL_NAME = 'qwen4exp_cpu_loader_diagnostic.json'
PLAN_SHA = '320462354167cdc270420dc6a16122543764ee6e581c2fb958af1b08d14a82cd'
RUNNER_SHA = 'cc58d1143298e5f9725f912fef3bf287c94e54fbc11112d94a35cf1bfa41ac3c'
NATIVE_SHA = 'd3d10c54b741433a43c981ac0bf154ac9fd76f0907cd47e909dac472e70f1e7a'
CAPTURES = {'production': 'banked-capture', 'candidate': 'candidate-diagnostic-capture'}
TERMINAL = {'loader_diagnostic_complete', 'loader_exercised_response_refused'}


def sha(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


LOG_TIME = rb'[0-9]+\.[0-9]{2}\.[0-9]{3}\.[0-9]{3}'
LOAD_START = re.compile(LOG_TIME + rb' I load_tensors: loading model tensors, this can take a while\.\.\. '
                        rb'\(mmap = (true|false), direct_io = (true|false)\)')
CONTEXT_START = re.compile(LOG_TIME + rb' I llama_context: constructing llama_context')


def loader_log_evidence(raw, plan, arm):
    log = raw.split(b'\n')
    starts = {index: match.groups() for index, line in enumerate(log)
              if (match := LOAD_START.fullmatch(line))}
    mapped = [index for index, (mmap, _) in starts.items() if mmap == b'true']
    if len(mapped) != 1:
        raise ValueError(f'{arm} requires one native mmap=true load phase, found {len(mapped)}')
    start, = mapped
    if starts[start] != (b'true', b'false'):
        raise ValueError(f'{arm} native load phase uses unexpected direct I/O')
    end = next((index for index in range(start + 1, len(log)) if CONTEXT_START.fullmatch(log[index])), None)
    if end is None or any(start < index < end for index in starts):
        raise ValueError(f'{arm} native mmap=true load phase lacks an unambiguous context boundary')

    lines, line_numbers = {}, {}
    for name in plan['loader_witness']['tensors']:
        pattern = re.compile(LOG_TIME + rb' D create_tensor: loading tensor ' + re.escape(name.encode('ascii')))
        found = [index for index in range(start + 1, end) if pattern.fullmatch(log[index])]
        if len(found) != 1:
            raise ValueError(f'{arm} requires one native mmap=true load line for {name}, found {len(found)}')
        index, = found
        lines[name], line_numbers[name] = log[index].decode('ascii'), index + 1
    return {
        'native_lines': lines, 'native_line_numbers': line_numbers, 'log_sha256': sha(raw),
        'native_load_phase': {
            'start': {'line': log[start].decode('ascii'), 'line_number': start + 1},
            'context_start': {'line': log[end].decode('ascii'), 'line_number': end + 1},
        },
        'stored_dims': plan['loader_witness']['stored_dims'],
        'runtime_dims_from_pinned_source': plan['loader_witness'][f'{arm}_dims'],
    }


def check_response(item, row, wire, raw, endpoint, parity):
    name = item['id']
    if (row['id'] != name or wire != canonical(item['request_body'])
            or raw != base64.b64decode(row['response_b64'], validate=True)):
        raise ValueError('native request or response bytes differ from capture record')
    record = {key: value for key, value in row.items() if key != 'id'}
    _, limit = parity._request(item['request_body'], endpoint)
    content, reasoning, finish, tokens, count = parity._capture(record, sha(wire), endpoint, None, limit)
    if not content.strip():
        raise ValueError('diagnostic response has empty answer content')
    data = parity._parse(raw)
    verbose = data['__verbose']
    settings = verbose['generation_settings']
    timings = verbose['timings']
    if (set(settings['speculative.types'].split(',')) != {'none'}
            or any(type(timings.get(key, 0)) is not int or timings.get(key, 0) != 0
                   for key in ('draft_n', 'draft_n_accepted'))
            or not tokens or count != len(tokens)
            or timings['predicted_n'] != count or verbose['tokens_predicted'] != count
            or data['usage']['prompt_tokens_details']['cached_tokens'] != 0
            or timings['cache_n'] != 0 or verbose['truncated'] is not False):
        raise ValueError('diagnostic response failed native no-spec, token or cold-prefill checks')
    return {
        'finish': finish, 'expected_finish': item['expected_finish'],
        'semantic_matches': parity._semantic_matches(item['validator'], content),
        'token_ids': tokens, 'completion_tokens': count,
        'content_sha256': sha(content.encode()),
        'reasoning_sha256': None if reasoning is None else sha(reasoning.encode()),
        'request_sha256': record['request_sha256'], 'response_sha256': record['response_sha256'],
    }


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def utc(value):
    dt = datetime.fromisoformat(value)
    require(dt.utcoffset() == timezone.utc.utcoffset(None)
            and dt.isoformat(timespec='microseconds') == value, 'noncanonical UTC timestamp')
    return dt


def inventory(directory):
    native = directory / 'native'
    files = [directory / 'RESULT.json']
    for path in sorted(native.rglob('*')):
        require(not path.is_symlink(), f'symlink in native packet: {path.name}')
        if path.is_file():
            files.append(path)
    require(not native.is_symlink(), 'native directory is a symlink')
    return {path.relative_to(directory).as_posix(): file_bytes(path) for path in files}


def file_bytes(path):
    require(not path.is_symlink() and path.is_file(), f'expected regular artifact: {path.name}')
    require(path.stat().st_size <= 8 * 1024 * 1024, f'artifact exceeds capture bound: {path.name}')
    return path.read_bytes()


def write_seal(source, result, started_at):
    inputs = ('plan.json', 'loader-reshape-witness.json', 'SOURCE.sha256', 'capture.py')
    body = {
        'schema': SEAL_SCHEMA, 'started_at': started_at, 'completed_at': utc_now(),
        'inputs': {name: base64.b64encode(file_bytes(source / name)).decode('ascii') for name in inputs},
        'files': {name: sha(raw) for name, raw in inventory(result.parent).items()},
    }
    with (result.parent / SEAL_NAME).open('xb') as stream:
        stream.write(canonical({**body, 'content_sha256': sha(canonical(body))}) + b'\n')


def selector(plan, validator_sha):
    identity = {
        'arms': plan['arms'], 'model_shards': plan['model_shards'],
        'recipe': plan['recipes']['diagnostic'], 'request': plan['items'],
        'validator_source_sha256': validator_sha, 'input_receipts': plan['receipts_sha256'],
    }
    return {'scope': 'candidate', 'build_sha': plan['arms']['candidate']['kernel_commit'],
            'candidate_sha256': sha(canonical(identity)), 'op': OP, 'run_id': ROW}


def _grant(raw, cpus, started, completed):
    fields = re.fullmatch(rb'regions=([0-9]+)-([0-9]+) start=(\S+) end=(\S+) holds=(q[0-3])\n?', raw)
    require(fields is not None, 'expected a bounded CPU-quarter grant')
    first, last = map(int, fields.groups()[:2])
    require(last - first == 23 and first == 24 * int(fields[5][1:]) and cpus == list(range(first, last + 1)), 'CPU affinity differs from grant')
    start, end = (datetime.strptime(value.decode('ascii'), '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc)
                  for value in fields.groups()[2:4])
    require(start <= started <= completed <= end, 'capture window falls outside grant')


def _arm(files, parity, state, plan, arm, captures, started, completed, runner_sha):
    stem = 'native/' + arm + '/'
    item, = plan['items']
    name = item['id']
    filenames = {stem + key for key in (
        'server.log', 'server.json', 'cleanup.json', f'{name}.request.json',
        f'{name}.response.json', f'{name}.custody.json',
    )}
    raw = files['native/' + CAPTURES[arm] + '.json']
    digest = sha(raw)
    require(files['native/' + CAPTURES[arm] + '.sha256'] == (digest + '\n').encode()
            and state['captures'][arm] == digest, f'{arm}: capture digest differs')
    capture = parity._parse(raw)
    runtime, recipe = plan['arms'][arm], plan['recipes']['diagnostic']
    identity = {
        'profile': plan['profile'], 'model': plan['model_shards'],
        'recipe_sha256': sha(canonical(recipe)), 'request_plan_sha256': PLAN_SHA,
        'grant_sha256': state['grant_sha256'], 'loader_witness_sha256': state['loader_witness_sha256'],
        'capture_runner_sha256': runner_sha, 'cleanup_sha256': sha(files[stem + 'cleanup.json']),
        'server_sha256': sha(files[stem + 'server.json']),
    }
    evidence = loader_log_evidence(files[stem + 'server.log'], plan, arm)
    row, = capture['items']
    expected = {'capture_identity': identity, 'runtime': runtime, 'items': [row], 'loader_log_evidence': evidence}
    if arm == 'candidate':
        expected['production_diagnostic_capture_sha256'] = captures['production']
    require(capture == expected, f'{arm}: capture identity, bank pin or native loader witness differs')
    check = check_response(item, row, files[stem + f'{name}.request.json'],
                           files[stem + f'{name}.response.json'], recipe['endpoint'], parity)
    require(check == state['checks'][arm], f'{arm}: response disposition differs')

    server = parity._parse(files[stem + 'server.json'])
    pid = server['pid']
    mapped = sorted(set(runtime['runtime_files']) - {runtime['binary']})
    cpus = state['cpus']
    binary = Path(runtime['binary'])
    argv = server['argv']
    prefix = [str(binary), '--host', '127.0.0.1', '--port', '19489', '--threads', '24', *recipe['args']]
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': str(binary.parent), 'GGML_IQK': '1',
           'ROCR_VISIBLE_DEVICES': '-1', 'HIP_VISIBLE_DEVICES': '-1', 'CUDA_VISIBLE_DEVICES': '',
           'OMP_NUM_THREADS': '1', 'FILLER_ID': ROW}
    require(type(pid) is int and pid > 0 and server == {
        'argv': argv, 'pid': pid, 'cpus': cpus, 'mapped_libraries': mapped,
        'image': runtime, 'recipe': recipe, 'environment': env,
    } and argv[:-1] == prefix + ['--chat-template-file'] and Path(argv[-1]).is_absolute()
        and Path(argv[-1]).name == recipe['external_chat_template'], f'{arm}: server identity differs')
    cleanup = parity._parse(files[stem + 'cleanup.json'])
    parity._fields(cleanup, {'pid', 'dead', 'port_closed', 'exit_status'}, 'owned cleanup')
    require(cleanup['pid'] == pid and cleanup['dead'] is True and cleanup['port_closed'] is True
            and type(cleanup['exit_status']) is int, f'{arm}: owned cleanup missing')
    custody = parity._parse(files[stem + f'{name}.custody.json'])
    parity._fields(custody, {'before', 'after', 'http_status', 'request_sha256', 'response_sha256'}, 'HTTP custody')
    for label in ('before', 'after'):
        witness = custody[label]
        require(witness == {'pid': pid, 'binary': str(binary), 'cpus': cpus, 'mapped_libraries': mapped,
                            'observed_at': witness['observed_at']}, f'{arm}: {label} HTTP process differs')
    before, after = (utc(custody[label]['observed_at']) for label in ('before', 'after'))
    require(started <= before <= after <= completed and custody['http_status'] == 200
            and all(custody[key] == check[key] for key in ('request_sha256', 'response_sha256')),
            f'{arm}: HTTP bytes, status or observation window differs')
    return digest, check, evidence, filenames, before, after


def replay(path, parity, validator_sha):
    record = parity._parse(file_bytes(path))
    parity._fields(record, {'schema', 'started_at', 'completed_at', 'inputs', 'files', 'content_sha256'}, 'loader seal')
    body = {key: value for key, value in record.items() if key != 'content_sha256'}
    require(record['schema'] == SEAL_SCHEMA, 'expected prospective loader diagnostic seal')
    require(record['content_sha256'] == sha(canonical(body)), 'loader seal digest differs')
    started, completed = (utc(record[key]) for key in ('started_at', 'completed_at'))
    require(started <= completed, 'capture window is reversed')
    files = inventory(path.parent)
    require(record['files'] == {name: sha(raw) for name, raw in files.items()}, 'native artifact manifest differs')
    parity._fields(record['inputs'], {'plan.json', 'loader-reshape-witness.json', 'SOURCE.sha256', 'capture.py'},
                   'loader input snapshots')
    plan_raw, witness_raw, source_raw, runner_raw = (
        base64.b64decode(record['inputs'][name], validate=True)
        for name in ('plan.json', 'loader-reshape-witness.json', 'SOURCE.sha256', 'capture.py')
    )
    require(sha(runner_raw) == RUNNER_SHA, 'prospective capture runner bytes differ')
    require(sha(plan_raw) == PLAN_SHA, 'prospective request plan differs')
    plan = parity._parse(plan_raw)
    pins = plan['receipts_sha256']
    require(sha(witness_raw) == pins['loader-reshape-witness.json'], 'source/header witness bytes differ')
    manifest = {}
    for line in source_raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None and match[2] not in manifest, 'invalid or duplicate source manifest entry')
        manifest[match[2]] = match[1]
    require(all(manifest.get(name) == value for name, value in {
        **pins, 'plan.json': PLAN_SHA, 'capture.py': RUNNER_SHA, 'cpu_native.py': NATIVE_SHA,
        'quality_parity.py': validator_sha,
        'qwen4exp_cpu_loader_contract.py': sha(Path(__file__).read_bytes()),
    }.items()), 'capture/source manifest differs from the pinned validators or inputs')

    state = parity._parse(files['RESULT.json'])
    expect = {
        'schema': SCHEMA, 'profile': plan['profile'], 'row_id': ROW, 'scope': plan['scope'],
        'request_plan_sha256': PLAN_SHA, 'source_manifest_sha256': sha(source_raw),
        'validator_source_sha256': validator_sha, 'loader_witness_sha256': sha(witness_raw),
        'prior_frontdoor_receipt_sha256': pins['frontdoor-full-receipt.json'],
        'broad_pack_status': 'incomplete', 'broad_pack_input': False,
        'quality_transfer_authorized': False, 'promotion_authorized': False,
    }
    require(all(canonical(state[key]) == canonical(value) for key, value in expect.items()),
            'native diagnostic schema, scope or essential source pins differ')
    if state['status'] == 'incomplete':
        parity._fields(state['error'], {'phase', 'type', 'message'}, 'native failure')
        return record, plan, state, {}
    require(state['status'] in TERMINAL and set(state) == set(expect) | {
        'status', 'cpus', 'grant_sha256', 'checks', 'captures', 'comparison',
    }, 'expected a complete native diagnostic disposition')
    require(set(state['checks']) == set(state['captures']) == set(CAPTURES), 'missing native arm')
    grant = files['native/scheduler.grant']
    require(state['grant_sha256'] == sha(grant), 'grant digest differs')
    _grant(grant, state['cpus'], started, completed)
    captures, checks, evidence = {}, {}, {}
    expected_native = {'RESULT.json', 'native/scheduler.grant'}
    previous = started
    for arm, name in CAPTURES.items():
        digest, check, load, filenames, before, after = _arm(
            files, parity, state, plan, arm, captures, started, completed, sha(runner_raw),
        )
        require(previous <= before, 'candidate request predates production request completion')
        previous = after
        captures[arm], checks[arm], evidence[arm] = digest, check, load
        expected_native.update(filenames | {f'native/{name}.json', f'native/{name}.sha256'})
    require(set(files) == expected_native, 'unexpected native artifacts')
    comparison = {key + '_equal': checks['production'][key] == checks['candidate'][key]
                  for key in ('finish', 'token_ids', 'content_sha256', 'reasoning_sha256')}
    accepted = all(c['semantic_matches'] and c['finish'] == c['expected_finish'] for c in checks.values())
    status = 'loader_diagnostic_complete' if accepted else 'loader_exercised_response_refused'
    require(canonical(comparison) == canonical(state['comparison']) and state['status'] == status,
            'native comparison or semantic disposition does not re-derive')
    return record, plan, state, evidence
