"""Fixtures for isolated hot-stack admission, request witnesses and cleanup."""

import importlib.util
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/benchmark/kernel_promotion_hot_stack_runner.py'
SPEC = importlib.util.spec_from_file_location('kernel_promotion_hot_stack_runner', SOURCE)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


@pytest.mark.parametrize(('regions', 'holds', 'devices', 'valid'), [
    ('0-95,184-191,mi210_0', 'q0,q1,q2,q3,gpu-quiet', ['ROCm0'], True),
    ('q0,q1,q2,q3', 'q0,q1,q2,q3', [], True),
    ('0-95,mi210_0', 'q0,q1,q2,q3', ['ROCm0'], False),
    ('24-95,mi210_0', 'q1,q2,q3,gpu-quiet', ['ROCm0'], False),
    ('0-95,mi210_0', 'q0,q1,q2,q3,gpu-quiet', ['ROCm1'], False),
    ('0-95,mi210_0', 'q0,q1,q2,q3,gpu-quiet', [], False),
])
def test_grant_scope(regions, holds, devices, valid):
    grant = runner.parse_grant(f'regions={regions} holds={holds} start=2026-11-18T05:20Z end=2026-11-18T06:30Z lock=0-95')
    resources = {'physical_cpus': '0-95', 'gpu_devices': devices}
    if valid:
        assert runner.grant_scope(grant, resources) == bool(devices)
    else:
        with pytest.raises(ValueError):
            runner.grant_scope(grant, resources)


def test_grant_refuses_duplicate_fields():
    with pytest.raises(ValueError, match='malformed'):
        runner.parse_grant('regions=0-95 regions=0-23')


def test_grant_rejects_narrower_explicit_lock():
    with pytest.raises(ValueError, match='full-host CPU plan'):
        runner.grant_scope({'regions': '0-95', 'holds': 'q0,q1,q2,q3', 'lock': '0-47'},
                           {'physical_cpus': '0-95', 'gpu_devices': []})


def test_model_alias_cannot_retarget_after_preparation(tmp_path):
    model = tmp_path / 'approved.gguf'
    model.touch()
    alias = tmp_path / 'alias.gguf'
    alias.symlink_to(model)
    endpoint = {'argv': ['llama-server', '-m', str(alias)],
                'models': [{'path': str(model), 'stat': runner.evidence.stat_identity(model.stat())}]}
    runner.verify_models(endpoint)
    replacement = tmp_path / 'replacement.gguf'
    replacement.touch()
    alias.unlink()
    alias.symlink_to(replacement)
    with pytest.raises(ValueError, match='prepared model changed'):
        runner.verify_models(endpoint)


def test_gpu_rowflow_fence_contract(tmp_path):
    engine = tmp_path / 'engine.sh'
    fence = tmp_path / 'state/gpu_fence-abcdef012345.so'
    fence.parent.mkdir()
    fence.touch()
    env = {'FILLER_ID': 'fixture', 'FILLER_STOPFILE': '/private/stop', 'FILLER_DEADLINE': '100', 'FILLER_GPU_FENCE': '1'}
    cpu = env | runner.FENCE_ENV | {'LD_PRELOAD': f'{fence} /ambient.so'}
    assert runner.rowflow_environment(False, engine, cpu) == env | runner.FENCE_ENV | {'LD_PRELOAD': str(fence)}
    with pytest.raises(ValueError, match='visibility fence'):
        runner.rowflow_environment(False, engine, env)
    gpu = env | {'FILLER_GPU_FENCE': '0', 'LD_PRELOAD': '/ambient.so'}
    assert 'LD_PRELOAD' not in runner.rowflow_environment(True, engine, gpu)
    with pytest.raises(ValueError, match='visibility overrides'):
        runner.rowflow_environment(True, engine, gpu | {'ROCR_VISIBLE_DEVICES': ''})


@pytest.mark.parametrize(('shape', 'refusal'), [
    ('keeper_snapshot', None),
    ('legacy_engine', None),
    ('changed_snapshot', 'invalid or changed pin'),
    ('foreign_snapshot', 'inner launcher ancestor'),
    ('linked_snapshot', 'canonical regular file'),
    ('self_claim', 'CPU lock provider'),
    ('wrong_parent', 'CPU lock provider'),
    ('duplicate_inner', 'inner launcher ancestor'),
    ('duplicate_provider', 'CPU lock provider'),
])
def test_rowflow_ancestors_require_the_pinned_engine_and_lock_provider(tmp_path, monkeypatch, shape, refusal):
    flags = tmp_path / 'compute-flags'
    monkeypatch.setattr(runner, 'FLAGS', flags)
    row_id = 'v9-8-fixture'
    engine = flags / 'bin/rowflow/filler_run15.sh'
    engine.parent.mkdir(parents=True)
    engine.write_text('#!/bin/bash\n')
    engine_sha = runner.planner.digest(engine)

    snapshot_row = 'different-row' if shape == 'foreign_snapshot' else row_id
    snapshot = flags / 'dryrun' / snapshot_row / 'engine' / engine.name
    snapshot.parent.mkdir(parents=True)
    if shape == 'linked_snapshot':
        snapshot.symlink_to(engine)
    else:
        snapshot.write_bytes(b'changed' if shape == 'changed_snapshot' else engine.read_bytes())

    running_engine = engine if shape == 'legacy_engine' else snapshot
    inner_cmd = [b'/bin/bash', os.fsencode(running_engine), b'--inner', b'--id', row_id.encode(),
                 b'--class', b'cpu', b'--cmd', b'python -I -B acquire.py --acquire']
    inner = (102, 1002, inner_cmd)
    provider = (101, 1001, [b'/orchestrator/.venv/bin/python3', b'-m', b'src.runtime.region_lock_cli',
                             b'run', b'--cpu-list', b'0-95', b'--role', b'bench', b'--timeout-s', b'2100',
                             b'--tag', f'filler-{row_id}'.encode(), b'--', *inner_cmd])
    poller = (100, 1000, [b'/bin/bash', os.fsencode(running_engine), b'--id', row_id.encode()])
    chain = [inner, provider, poller]
    if shape == 'self_claim':
        chain.remove(provider)
    elif shape == 'wrong_parent':
        chain.insert(1, (103, 1003, [b'bash']))
    elif shape == 'duplicate_inner':
        chain.insert(0, (103, 1003, inner_cmd))
    elif shape == 'duplicate_provider':
        chain.append((99, 999, provider[2]))

    # Rowflow unsets this before exec. Custody comes from /proc ancestry.
    monkeypatch.delenv('FILLER_ENGINE_SNAPSHOT', raising=False)
    if refusal:
        with pytest.raises(ValueError, match=refusal):
            runner.rowflow_ancestors(chain, row_id, engine, engine_sha)
    else:
        assert runner.rowflow_ancestors(chain, row_id, engine, engine_sha) == (provider[:2], inner[:2])


def test_regenerate_refuses_mutated_argv_and_restores_environment(tmp_path, monkeypatch):
    expected = {'schema': runner.planner.PLAN_SCHEMA, 'status': 'prepared_only', 'spec': {'test': True},
                'contention_matrix_status': 'ok', 'endpoints': [{'argv': ['safe'], 'env': {}}]}
    ledger = tmp_path / 'ledger.json'

    def prepare(spec, directory):
        assert spec == expected['spec'] and directory == tmp_path
        assert os.environ['ARTIFACT_FINGERPRINT_LEDGER'] == str(ledger)
        assert 'LD_PRELOAD' not in os.environ
        return expected

    monkeypatch.setenv('LD_PRELOAD', '/ambient.so')
    monkeypatch.setattr(runner.planner, 'prepare_plan', prepare)
    assert runner.regenerate(expected, tmp_path, ledger) == expected
    altered = expected | {'endpoints': [{'argv': ['changed'], 'env': {'LD_PRELOAD': '/foreign.so'}}]}
    with pytest.raises(ValueError, match='regenerated pinned plan'):
        runner.regenerate(altered, tmp_path, ledger)
    assert os.environ['LD_PRELOAD'] == '/ambient.so'
    monkeypatch.setattr(runner.planner, 'prepare_plan',
                        lambda *_: expected | {'contention_matrix_status': 'stale'})
    with pytest.raises(ValueError, match='must be fresh'):
        runner.regenerate(expected, tmp_path, ledger)


def test_lock_witness_requires_an_exact_exclusive_flock(tmp_path, monkeypatch):
    path = tmp_path / 'gpu_device.mi210_0.lock'
    path.touch()
    stat = path.stat()
    device = f'{os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x}:{stat.st_ino}'
    proc = tmp_path / 'proc'
    fdinfo = proc / '50/fdinfo'
    fdinfo.mkdir(parents=True)
    (fdinfo / '9').write_text(f'lock: 1: FLOCK ADVISORY WRITE 51 {device} 0 EOF\n')
    (proc / 'locks').write_text(f'1: FLOCK ADVISORY WRITE 51 {device} 0 EOF\n')
    monkeypatch.setattr(runner, 'PROC', proc)
    assert runner.live_flocks(50, [path])[str(path)]['fd'] == 9
    (fdinfo / '9').write_text(f'lock: 1: FLOCK ADVISORY READ 51 {device} 0 EOF\n')
    with pytest.raises(ValueError, match='exclusive flocks'):
        runner.live_flocks(50, [path])


def test_numa_witness_binds_executable_to_policy(tmp_path):
    binary = Path('/stage/llama-server')
    maps = tmp_path / 'numa_maps'
    maps.write_text(f'400000 interleave:0-3 file={binary} mapped=2 N0=2\n')
    assert runner.observed_numa(tmp_path, binary, ('interleave', set(range(4)))) == 'interleave:0-3'
    with pytest.raises(ValueError, match='differs'):
        runner.observed_numa(tmp_path, binary, ('bind', {3}))
    with pytest.raises(ValueError, match='no executable'):
        runner.observed_numa(tmp_path, binary.with_name('wrong'), ('interleave', set(range(4))))


def test_hip_residency_requires_positive_vram(tmp_path, monkeypatch):
    process = tmp_path / 'proc/123'
    process.mkdir(parents=True)
    (process / 'pasid').write_text('4')
    vram = process / 'vram_25466'
    vram.write_text('1024')
    monkeypatch.setattr(runner, 'KFD', tmp_path)
    assert runner.backend_residency(123, 'hip', 25466)['vram_bytes'] == 1024
    with pytest.raises(ValueError, match='unexpectedly opened KFD'):
        runner.backend_residency(123, 'cpu', None)
    vram.write_text('0')
    with pytest.raises(ValueError, match='nonzero device VRAM'):
        runner.backend_residency(123, 'hip', 25466)


@pytest.mark.parametrize(('before_headers', 'identity_changed'), [(True, False), (False, False), (True, True)])
def test_smoke_requires_complete_request_time_witness(tmp_path, monkeypatch, before_headers, identity_changed):
    sampled = threading.Event()
    headers = threading.Event()
    admission = SimpleNamespace(deadline=time.time() + 15, check=lambda: None)
    runtime = runner.Runtime({}, tmp_path / 'plan.json', tmp_path, admission, 5, 5)
    endpoint = {'test': 'chat', 'endpoint': 'http://127.0.0.1:19520'}
    raw = b'{"choices":[{"message":{"role":"assistant","content":"text"}}]}'

    def pretend_request(server, method, path, body, timeout, request_sent, response_started, send_barrier):
        assert method == 'POST' and path == '/v1/chat/completions'
        assert json.loads(body)['stream'] is False
        assert send_barrier is None
        request_sent()
        assert sampled.wait(3)
        if before_headers:
            time.sleep(0.2)
        response_started()
        headers.set()
        return 200, raw

    def sample(server):
        sampled.set()
        if not before_headers:
            assert headers.wait(3)
        return {'threads': {123: {'cpus': [0], 'numa_policy': 'bind:0'}},
                'backend': {'kfd_client': True, 'vram_bytes': 1024}}

    def verify_identity(server):
        if identity_changed:
            raise ValueError('identity changed after raw capture')

    monkeypatch.setattr(runtime, 'request_http', pretend_request)
    monkeypatch.setattr(runtime, 'sample', sample)
    monkeypatch.setattr(runtime, 'verify_identity', verify_identity)
    server = SimpleNamespace(endpoint=endpoint)
    if before_headers and not identity_changed:
        runtime.smoke(server, tmp_path)
        assert runner.planner.read_json(tmp_path / 'response-comparability.json') == {
            'status': 'diagnostic_incomplete', 'completion': 'incomplete', 'completion_tokens': None,
            'content': 'complete', 'token_ids': 'incomplete',
        }
    else:
        with pytest.raises(ValueError, match='identity changed' if identity_changed else 'inside request'):
            runtime.smoke(server, tmp_path)
        assert not (tmp_path / 'response-comparability.json').exists()
    observations = runner.planner.read_json(tmp_path / 'during-request.json')
    assert bool(observations['samples']) == before_headers
    assert (tmp_path / 'response.raw.json').read_bytes() == raw


def pair_endpoint(port, canonical_port, role, logical_cpu, device='none'):
    return {'port': port, 'canonical_port': canonical_port, 'roles': [role], 'logical_cpus': [logical_cpu],
            'physical_cpus': [logical_cpu % 96], 'device': device, 'numa_instance': 0, 'argv': ['llama-server', '-t', '1']}


def matrix_row(left, right):
    def instance(endpoint):
        return {'port': endpoint['canonical_port'], 'role': endpoint['roles'][0],
                'instance_idx': endpoint['numa_instance'], 'cpu_list': str(endpoint['logical_cpus'][0]), 'threads': 1}
    return {'roles': [left['roles'][0], right['roles'][0]], 'verdict': 'allow',
            'instance_a': instance(left), 'instance_b': instance(right)}


def test_select_pair_orders_by_canonical_port_and_binds_matrix_shape():
    left = pair_endpoint(19530, 8080, 'a', 0)
    middle = pair_endpoint(19520, 8081, 'b', 96)
    right = pair_endpoint(19521, 8082, 'c', 2)
    selected = matrix_row(right, left)
    matrix = {'pairs': [matrix_row(middle, right), matrix_row(left, middle), selected]}
    assert runner.select_concurrency_pair([right, middle, left], matrix) == ((left, right), selected)


@pytest.mark.parametrize('defect', ['absent', 'ambiguous', 'blocked', 'shape', 'sibling', 'same_device', 'unknown'])
def test_select_pair_fails_closed(defect):
    left = pair_endpoint(19520, 8080, 'a', 0, 'ROCm0')
    right = pair_endpoint(19521, 8081, 'b', 96 if defect == 'sibling' else 1,
                          'ROCm0' if defect == 'same_device' else 'none')
    row = matrix_row(left, right)
    matrix = {'pairs': [row]}
    if defect == 'absent':
        matrix['pairs'].clear()
    if defect == 'ambiguous':
        matrix['pairs'].append(row | {'verdict': 'block'})
    if defect == 'blocked':
        row['verdict'] = 'block'
    if defect == 'shape':
        row['instance_b']['instance_idx'] = 1
    if defect == 'unknown':
        matrix['unknown_pairs'] = [{'roles': row['roles']}]
    with pytest.raises(ValueError, match='no distinct, disjoint endpoint pair'):
        runner.select_concurrency_pair([left, right], matrix)


@pytest.mark.parametrize(('left_start', 'left_end', 'right_start', 'right_end', 'expected'), [
    (3, 5, 4, 6, True),
    (2, 5, 4, 6, False),
    (3, 4, 4, 6, False),
    (3, 5, 4, 8, False),
])
def test_overlapping_samples_requires_both_full_scans_in_shared_request(left_start, left_end,
                                                                      right_start, right_end, expected):
    left = {'request_sent_s': 1, 'response_headers_s': 7, 'samples': [{'start_s': left_start, 'end_s': left_end}]}
    right = {'request_sent_s': 3, 'response_headers_s': 9, 'samples': [{'start_s': right_start, 'end_s': right_end}]}
    assert bool(runner.overlapping_samples(left, right)) == expected


@pytest.mark.parametrize('overlap', [True, False])
def test_paired_smoke_dispatches_together_and_preserves_both_captures(tmp_path, monkeypatch, overlap):
    ports = (19520, 19521)
    raw = b'{"choices":[{"message":{"role":"assistant","content":"text"}}]}'
    admission = SimpleNamespace(deadline=time.time() + 15, check=lambda: None)
    runtime = runner.Runtime({}, tmp_path / 'plan.json', tmp_path, admission, 5, 5)
    runtime.servers = [SimpleNamespace(port=port, endpoint={'test': 'chat', 'endpoint': f'http://127.0.0.1:{port}'})
                       for port in ports]
    headers = {port: threading.Event() for port in ports}
    responses = {port: threading.Event() for port in ports}
    first_scan = set()

    def release_headers():
        for ready in headers.values():
            ready.set()

    # Start the countdown after both complete scans have begun.
    sample_gate = threading.Barrier(2, action=lambda: threading.Timer(0.2, release_headers).start())
    first_waiting = threading.Event()
    connected = set()
    original_barrier = threading.Barrier

    def dispatch_barrier(parties):
        barrier = original_barrier(parties)

        def wait(timeout):
            first_waiting.set()
            return barrier.wait(timeout)

        return SimpleNamespace(wait=wait, abort=barrier.abort)

    class Response:
        status = 200

        def __init__(self):
            self.chunks = iter((raw, b''))

        def read1(self, _):
            return next(self.chunks)

    class Connection:
        def __init__(self, host, port, timeout):
            assert host == '127.0.0.1' and timeout > 0
            self.port = port
            self.sock = SimpleNamespace(settimeout=lambda _: None)

        def connect(self):
            if self.port == ports[1]:
                assert first_waiting.wait(3)
            connected.add(self.port)

        def request(self, method, path, body, headers):
            assert connected == set(ports)
            assert method == 'POST' and path == '/v1/chat/completions' and json.loads(body) == runner.chat_body()

        def getresponse(self):
            assert headers[self.port].wait(3)
            return Response()

        def close(self):
            pass

    def sample(server):
        if server.port not in first_scan:
            first_scan.add(server.port)
            sample_gate.wait(3)
            if server.port == ports[1] and not overlap:
                assert responses[server.port].wait(3)
        return {'threads': {}, 'backend': {'kfd_client': False}}

    request_http = runtime.request_http

    def record_headers(server, method, path, body, timeout, sent, response_started, barrier):
        def observed():
            response_started()
            responses[server.port].set()
        return request_http(server, method, path, body, timeout, sent, observed, barrier)

    monkeypatch.setattr(runner.threading, 'Barrier', dispatch_barrier)
    monkeypatch.setattr(runner.http.client, 'HTTPConnection', Connection)
    monkeypatch.setattr(runtime, 'request_http', record_headers)
    monkeypatch.setattr(runtime, 'verify_identity', lambda _: None)
    monkeypatch.setattr(runtime, 'sample', sample)
    selected = {'endpoints': [{'port': port} for port in ports]}
    if overlap:
        runtime.paired_smoke(selected)
    else:
        with pytest.raises(ValueError, match='overlapping complete witness scans'):
            runtime.paired_smoke(selected)
    path = tmp_path / 'paired-concurrency'
    result = runner.planner.read_json(path / 'result.json')
    assert result['status'] == ('pass' if overlap else 'failed')
    assert bool(result['overlap']) == overlap
    for port in ports:
        assert (path / str(port) / 'response.raw.json').read_bytes() == raw


def test_execute_preserves_requested_pair_refusal(tmp_path):
    def refused():
        raise ValueError('no allowed pair')

    runtime = SimpleNamespace(output=tmp_path, select_pair=refused, servers=[],
                              cleanup=lambda: {'spawn_unproved': False, 'servers': {}})
    assert runner.execute(runtime, paired_concurrency=True) == 2
    assert runner.planner.read_json(tmp_path / 'result.json')['paired_concurrency_requested'] is True
    assert (tmp_path / 'COMPLETE').is_file()


@pytest.mark.parametrize('outcome', ['pass', 'late', 'scan-failure', 'dispatch-refusal'])
def test_isolated_api_observes_upstream_generation_and_keeps_raw_capture(tmp_path, monkeypatch, outcome):
    port = 19520
    url = f'http://127.0.0.1:{port}'
    role = 'frontdoor'
    plan_sha = 'a' * 64
    cgroup = '0::/rowflow/example@1234'
    manifest = {'schema': runner.isolated_api.MANIFEST_SCHEMA,
                'endpoints': [{'base_url': url, 'role': role, 'kind': 'chat'}]}
    admission = SimpleNamespace(deadline=time.time() + 15, check=lambda: None, env={}, cgroup=cgroup)
    runtime = runner.Runtime({'endpoint_manifest': manifest}, tmp_path / 'plan.json', tmp_path, admission,
                             5, 5, plan_sha256=plan_sha)
    runtime.servers = [SimpleNamespace(pid=100, birth=1000, port=port, image={},
                                      endpoint={'test': 'chat', 'roles': [role], 'endpoint': url})]
    worker_proc = tmp_path / 'proc' / '200'
    worker_proc.mkdir(parents=True)
    (worker_proc / 'cgroup').write_text(cgroup)
    monkeypatch.setattr(runner, 'PROC', worker_proc.parent)
    monkeypatch.setattr(runner.owned, 'birth', lambda pid: 2000 if pid == 200 else None)
    sampled = threading.Event()
    headers = threading.Event()
    checks = []
    raw = b'{"routed_to":"frontdoor","answer":"ok"}'

    def verify(server):
        assert server is runtime.servers[0]
        checks.append(server.pid)
        if len(checks) == 3 and outcome == 'dispatch-refusal':
            raise ValueError('listener identity changed before dispatch')

    def sample(server):
        sampled.set()
        if outcome == 'late':
            assert headers.wait(3)
        if outcome == 'scan-failure':
            raise ValueError('NUMA policy changed')
        return {'threads': {100: {'cpus': [0], 'numa_policy': 'bind:0'}}, 'backend': {'kfd_client': False}}

    class Worker:
        pid = 200

        def __init__(self, command, *, env, stdout, stderr, pass_fds):
            assert command[command.index('--plan-sha256') + 1] == plan_sha
            assert command[command.index('--port') + 1] == str(port)
            output = Path(command[command.index('--output-dir') + 1])
            fd = os.dup(pass_fds[0])
            self.returncode = None
            self.failure = None

            def dispatch():
                with socket.socket(fileno=fd) as channel:
                    channel.settimeout(3)

                    def emit(event):
                        channel.send(json.dumps([event, 1, time.monotonic_ns()]).encode())

                    emit('connect')
                    assert channel.recv(16) == b'allow'
                    emit('dispatch')
                    allowed = channel.recv(16) == b'allow'
                    assert allowed == (outcome != 'dispatch-refusal')
                    if allowed:
                        emit('sent')
                        assert sampled.wait(3)
                        if outcome == 'pass':
                            time.sleep(0.1)
                        emit('headers')
                        headers.set()
                    output.mkdir()
                    (output / 'response.body').write_bytes(raw if allowed else b'Internal Server Error')
                    runner.planner.write_new(output / 'result.json', {
                        'status': 'passed' if allowed else 'failed', 'plan_sha256': plan_sha, 'role': role,
                        'base_url': url, 'error': 'refused dispatch',
                        'outbound': [{'method': 'POST', 'path': '/completion'}],
                    })
                    self.returncode = 0 if allowed else 1

            def run():
                try:
                    dispatch()
                except BaseException as exc:
                    self.failure = exc
                    self.returncode = 1

            self.thread = threading.Thread(target=run, daemon=True)
            self.thread.start()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.thread.join(timeout)
            assert not self.thread.is_alive()
            if self.failure is not None:
                raise self.failure
            return self.returncode

        def terminate(self):
            pytest.fail('worker should have completed normally')

    monkeypatch.setattr(runtime, 'verify_identity', verify)
    monkeypatch.setattr(runtime, 'sample', sample)
    monkeypatch.setattr(runner.subprocess, 'Popen', Worker)
    if outcome == 'pass':
        runtime.isolated_api_smoke(role, port)
    else:
        errors = {'late': 'inside isolated API generation', 'scan-failure': 'NUMA policy changed',
                  'dispatch-refusal': 'refused dispatch'}
        with pytest.raises(ValueError, match=errors[outcome]):
            runtime.isolated_api_smoke(role, port)
    directory = tmp_path / 'isolated-api'
    observed = runner.planner.read_json(directory / 'during-request.json')['requests']['1']
    assert bool(observed['samples']) == (outcome == 'pass')
    assert (directory / 'consumer' / 'response.body').read_bytes() == (
        b'Internal Server Error' if outcome == 'dispatch-refusal' else raw)
    result = runner.planner.read_json(directory / 'result.json')
    assert result['status'] == ('pass' if outcome == 'pass' else 'failed')
    assert result['worker_pid'] == 200 and result['worker_birth'] == 2000
    assert result['worker_cgroup'] == cgroup and result['worker_cleanup_proved'] is True
    assert result['worker_returncode'] == int(outcome == 'dispatch-refusal')


def test_isolated_api_refuses_role_without_ready_owned_chat_server(tmp_path):
    url = 'http://127.0.0.1:19520'
    manifest = {'schema': runner.isolated_api.MANIFEST_SCHEMA,
                'endpoints': [{'base_url': url, 'role': 'frontdoor', 'kind': 'chat'}]}
    runtime = runner.Runtime({'endpoint_manifest': manifest}, tmp_path / 'plan.json', tmp_path,
                             SimpleNamespace(check=lambda: None), 5, 5)
    with pytest.raises(ValueError, match='no ready owned chat server'):
        runtime.isolated_api_smoke('frontdoor', None)
    assert runner.planner.read_json(tmp_path / 'isolated-api' / 'result.json')['status'] == 'failed'
    assert not (tmp_path / 'isolated-api' / 'consumer').exists()


@pytest.mark.parametrize(('choice_override', 'response_override', 'expected'), [
    ({}, {}, ('complete', 'complete', 'complete')),
    ({'finish_reason': 'length'}, {}, ('incomplete', 'complete', 'complete')),
    ({'finish_reason': 'length'}, {'usage': {'completion_tokens': 64}, 'tokens': list(range(64))},
     ('complete', 'complete', 'complete')),
    ({}, {'usage': {'completion_tokens': True}}, ('incomplete', 'complete', 'incomplete')),
    ({}, {'timings': {'predicted_n': 3}}, ('incomplete', 'complete', 'complete')),
    ({}, {'tokens': None}, ('complete', 'complete', 'incomplete')),
    ({}, {'tokens': [4]}, ('complete', 'complete', 'incomplete')),
    ({}, {'tokens': [4, False]}, ('complete', 'complete', 'incomplete')),
    ({}, {'tokens': [4, -1]}, ('complete', 'complete', 'incomplete')),
    ({'message': {'role': 'assistant', 'reasoning_content': 'thinking'}}, {},
     ('complete', 'incomplete', 'complete')),
    ({}, {'choices': []}, ('incomplete', 'incomplete', 'complete')),
])
def test_chat_comparability_requires_a_complete_exact_capture(choice_override, response_override, expected):
    choice = {'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'text'}}
    response = {'choices': [choice | choice_override], 'usage': {'completion_tokens': 2}, 'tokens': [4, 7]}
    report = runner.chat_comparability(runner.chat_body(), response | response_override)
    assert tuple(report[field] for field in ('completion', 'content', 'token_ids')) == expected
    assert report['status'] == ('comparable' if all(field == 'complete' for field in expected)
                                else 'diagnostic_incomplete')


def test_embedding_rejects_bad_indices_and_zero_vectors():
    request = {'input': ['sample', 'second']}
    good = {'data': [{'index': 0, 'embedding': [0.1, -0.2]}, {'index': 1, 'embedding': [0.2, -0.1]}]}
    runner.response_check('embedding', request, good)
    with pytest.raises(ValueError, match='indices'):
        runner.response_check('embedding', request, {'data': [good['data'][0]] * 2})
    with pytest.raises(ValueError, match='zero vectors'):
        runner.response_check('embedding', request, {'data': [good['data'][0], {'index': 1, 'embedding': [0, 0]}]})


@pytest.mark.parametrize(('failed_start', 'proved', 'api', 'verdict'), [
    (False, True, False, 'pass'), (True, True, False, 'failed'), (False, False, False, 'failed'),
    (False, True, True, 'pass'), (True, True, True, 'failed'), (False, False, True, 'failed'),
])
def test_execute_serial_startup_and_seal_only_after_cleanup(tmp_path, failed_start, proved, api, verdict):
    order = []
    servers = []
    ports = (19520, 19521)
    endpoints = [{'port': port, 'log': str(tmp_path / f'{port}.log')} for port in ports]

    def start(endpoint):
        port = endpoint['port']
        order.append(('start', port))
        if failed_start and port == ports[-1]:
            raise RuntimeError('startup failed')
        Path(endpoint['log']).write_text('candidate log')
        server = SimpleNamespace(port=port, endpoint=endpoint)
        servers.append(server)
        return server

    def cleanup():
        order.append(('cleanup',))
        assert not (tmp_path / 'COMPLETE').exists()
        return {'spawn_unproved': not proved, 'servers': {str(server.port): {'pidfd_exited': True, 'reaped_rc': -15,
                'port_closed': True, 'kfd_absent': True} for server in servers}}

    def isolated_api_smoke(role, port):
        assert role == 'frontdoor' and port == ports[0]
        assert order[-1] == ('smoke', ports[1])
        order.append(('api',))

    runtime = SimpleNamespace(output=tmp_path, plan={'endpoints': endpoints}, servers=servers, start=start,
                              preflight=lambda: order.append(('preflight',)),
                              verify_model_inputs=lambda: order.append(('model_inputs',)),
                              ready=lambda server: order.append(('ready', server.port)) or {},
                              verify_identity=lambda server: order.append(('verify', server.port)),
                              smoke=lambda server, _: order.append(('smoke', server.port)), check=lambda: None,
                              cleanup=cleanup, isolated_api_smoke=isolated_api_smoke)
    options = {'api_role': 'frontdoor', 'api_port': ports[0]} if api else {}
    assert runner.execute(runtime, **options) == (0 if verdict == 'pass' else 2)
    assert order[:5] == [('preflight',), ('model_inputs',), ('start', ports[0]), ('ready', ports[0]), ('start', ports[1])]
    assert (('smoke', ports[0]) in order) == (not failed_start)
    assert (('api',) in order) == (api and not failed_start)
    assert order[-1] == ('cleanup',)
    result = runner.planner.read_json(tmp_path / 'result.json')
    assert result['functional_smoke'] == verdict
    if api:
        assert result['isolated_api']['status'] == ('not_run' if failed_start else 'pass')
    else:
        assert 'isolated_api' not in result
    if proved:
        manifest = tmp_path / 'MANIFEST.json'
        assert runner.planner.read_json(manifest)['functional_smoke'] == verdict
        assert (tmp_path / 'COMPLETE').read_text().strip() == runner.planner.digest(manifest)
    else:
        assert not (tmp_path / 'COMPLETE').exists()
