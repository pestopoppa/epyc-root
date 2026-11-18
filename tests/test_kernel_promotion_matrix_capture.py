"""Software controls for configured-primary contention acquisition."""

import json
import os
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/benchmark'))
import kernel_promotion_matrix_capture as capture


def test_phase_partition_preserves_all_six_configured_pairs():
    from itertools import combinations

    required = list(combinations(sorted(capture.PORTS), 2))
    harness = SimpleNamespace(_enumerate_full_pairs=lambda config: required)
    all_pairs, cpu = capture.pair_sets(harness, {}, 'cpu')
    _, hip = capture.pair_sets(harness, {}, 'hip')
    _, full = capture.pair_sets(harness, {}, 'full')
    assert all_pairs == full == required
    assert len(cpu) == len(hip) == 3
    assert not set(cpu) & set(hip)
    assert set(cpu + hip) == set(full)
    assert all('architect_critic' not in pair for pair in cpu)


def test_unknown_configured_role_fails_closed():
    harness = SimpleNamespace(_enumerate_full_pairs=lambda config: [('frontdoor', 'worker_vision')])
    with pytest.raises(ValueError, match='scope'):
        capture.pair_sets(harness, {}, 'cpu')


def test_model_shards_must_remain_identical(tmp_path, monkeypatch):
    files = [tmp_path / f'model-{index:05d}-of-00003.gguf' for index in range(1, 4)]
    for path in files:
        path.write_text('gguf')
    first = files[0]
    endpoint = {'port': 19573, 'argv': ['-m', str(first)],
                'models': [{'path': str(first), 'stat': capture.runner.evidence.stat_identity(first.stat())}]}
    monkeypatch.setattr(capture.planner, 'digest', lambda path: pytest.fail(f'GGUF was hashed: {path}'))
    pins = capture.extra_inputs(endpoint)
    assert set(pins) == {str(path) for path in files[1:]}
    capture.verify_inputs(endpoint, pins)
    files[1].write_text('replaced shard')
    with pytest.raises(ValueError, match='shard'):
        capture.verify_inputs(endpoint, pins)
    files[2].unlink()
    with pytest.raises((OSError, ValueError)):
        capture.extra_inputs(endpoint)


def test_cpu_phase_rejects_foreign_kfd_workload(tmp_path, monkeypatch):
    processes = tmp_path / 'proc'
    processes.mkdir()
    (processes / '17').mkdir()
    monkeypatch.setattr(capture.runner, 'KFD', tmp_path)
    runtime = capture.MatrixRuntime({}, None, None, SimpleNamespace(gpu=False), 1, 1)
    with pytest.raises(ValueError, match='foreign KFD workloads.*17'):
        runtime.verify_kfd_clients()


def test_non_live_invocation_never_reads_plan(tmp_path, monkeypatch):
    monkeypatch.delenv('FILLER_ID', raising=False)
    monkeypatch.setattr(capture, 'read_prepared', lambda *args: pytest.fail('non-live invocation read the plan'))
    result = capture.capture(tmp_path, 'cpu', 'v9-8-contention-matrix-cpu-20261118', tmp_path)
    assert result['status'] == 'failed'
    assert result['cleanup_proved'] is True
    assert result['completed_pairs'] == []
    assert result['complete_matrix'] is False
    assert 'acquisition_started_at' not in result
    assert 'real grant' in result['failure']


def test_inventory_binds_original_nested_artifacts_and_refuses_links(tmp_path):
    from hashlib import sha256

    phase = tmp_path / 'solo-a'
    phase.mkdir()
    data = phase / '19575.response.json'
    data.write_bytes(b'{"timings":{}}')
    assert capture.attempt_inventory(tmp_path) == {'solo-a/19575.response.json': sha256(data.read_bytes()).hexdigest()}
    (phase / 'alias').symlink_to(data)
    with pytest.raises(ValueError, match='canonical regular file'):
        capture.attempt_inventory(tmp_path)


def test_pinned_plan_refuses_alternate_and_emits_fixture_matrix(tmp_path):
    packet_path = os.environ.get('MATRIX_TEST_PACKET')
    if not packet_path:
        pytest.skip('published packet integration fixture')
    packet = Path(packet_path)
    _, _, plan, matrix, config, contention = capture.read_prepared(packet, os.environ.get('MATRIX_TEST_PHASE', 'cpu'))
    broken = json.loads(json.dumps(plan['endpoints']))
    broken[0]['numa_instance'] = 1
    with pytest.raises(ValueError, match='configured primary'):
        capture.endpoint_records(matrix, config, broken, plan['phase_pairs'])
    required, _ = capture.pair_sets(matrix, config, 'full')
    instances = {role: matrix._instance_record(role, *matrix._role_footprints(config, role)[0], config)
                 for role in capture.PORTS}
    result = [capture.result_pair(matrix, instances, roles, dict.fromkeys(roles, 4.0), dict.fromkeys(roles, 5.0))
              for roles in required]
    output = tmp_path / 'contention_matrix.yaml'
    output.write_text(matrix._emit_yaml(result, topology_hash=plan['topology_hash']))
    summary = capture.validate_full(output, plan | {'instances': instances}, matrix, config, contention)
    assert 'is fresh' in summary['check_output']
    assert summary['host_health']['decision_grade'] is False
    output.write_text(matrix._emit_yaml(result[:-1], topology_hash=plan['topology_hash']))
    with pytest.raises(ValueError, match='coverage'):
        capture.validate_full(output, plan | {'instances': instances}, matrix, config, contention)


def test_hip_phase_allows_only_owned_current_birth_kfd_workload(tmp_path, monkeypatch):
    processes = tmp_path / 'proc'
    processes.mkdir()
    (processes / '17').mkdir()
    monkeypatch.setattr(capture.runner, 'KFD', tmp_path)
    runtime = capture.MatrixRuntime({}, None, None, SimpleNamespace(gpu=True), 1, 1)
    server = SimpleNamespace(pid=17, birth=123, endpoint={'backend': 'hip'})
    runtime.servers = [server]
    monkeypatch.setattr(capture.runner.owned, 'birth', lambda pid: 123)
    runtime.verify_kfd_clients()
    monkeypatch.setattr(capture.runner.owned, 'birth', lambda pid: 124)
    with pytest.raises(ValueError, match='foreign KFD workloads.*17'):
        runtime.verify_kfd_clients()


def test_acquisition_interval_rejects_missing_malformed_reversed_and_future():
    from datetime import datetime, timezone

    now = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    valid = {'acquisition_started_at': '2026-11-18T10:00:00+00:00',
             'acquisition_finished_at': '2026-11-18T11:00:00+00:00'}
    assert capture.acquisition_interval(valid, now)[0].hour == 10
    for value in ({}, valid | {'acquisition_started_at': 'bad'},
                  valid | {'acquisition_started_at': '2026-11-18T12:01:00+00:00'},
                  valid | {'acquisition_finished_at': '2026-11-18T13:00:00+00:00'},
                  valid | {'acquisition_started_at': '2026-11-18T10:00:00'}):
        with pytest.raises(ValueError):
            capture.acquisition_interval(value, now)


def test_admitted_failure_records_bounds_through_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(capture.acquisition, 'require_live_grant', lambda *args: None)
    def refuse(*args):
        raise ValueError('fixture refusal')
    monkeypatch.setattr(capture, 'read_prepared', refuse)
    result = capture.capture(tmp_path, 'cpu', 'row', tmp_path)
    assert result['status'] == 'failed' and result['cleanup_proved'] is True
    assert capture.acquisition_interval(result)[0] <= capture.acquisition_interval(result)[1]


def test_emitter_timestamp_is_original_capture_start():
    times = {'acquisition_started_at': '2026-01-01T00:00:00+00:00',
             'acquisition_finished_at': '2026-01-01T00:01:00+00:00'}
    assert capture.stamp_acquisition_start('measured_at: "later"\npairs: []\n', times) == (
        'measured_at: "2026-01-01T00:00:00+00:00"\npairs: []\n')
    with pytest.raises(ValueError):
        capture.stamp_acquisition_start('pairs: []\n', times)


@pytest.fixture
def split_native_fixture(tmp_path, monkeypatch):
    import yaml

    now = datetime.now(timezone.utc)
    required = [list(pair) for pair in combinations(sorted(capture.PORTS), 2)]
    stat = [1, 2, 3, 4, 5]
    checksum = 'e' * 64
    images = {backend: {'binary': f'/stage/{backend}/llama-server', 'library_dir': f'/stage/{backend}',
                        'binary_sha256': checksum} for backend in ('cpu', 'hip')}
    plans = {}

    def write(path, data):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        return path

    def pair_record(roles, a, b, *_legs, ratio, seq_aggregate_tps, parallel_aggregate_tps):
        return SimpleNamespace(to_yaml_dict=lambda: {
            'roles': list(roles), 'instance_a': a, 'instance_b': b, 'ratio': ratio,
            'seq_aggregate_tps': seq_aggregate_tps, 'parallel_aggregate_tps': parallel_aggregate_tps, 'samples': 1,
        })

    def emit(records, **kwargs):
        return yaml.safe_dump({'measured_at': 'emission', 'pairs': [record.to_yaml_dict() for record in records]})

    matrix = SimpleNamespace(BenchResult=lambda *args: None, PairBench=pair_record, N_PREDICT=100,
                             _HOST_HEALTH_RULE_SOURCE='fixture-rules', _emit_yaml=emit,
                             _carry_forward_sections=lambda source: [])
    contention = SimpleNamespace(load_contention_matrix=lambda source: SimpleNamespace(
        measured_at='source-time', topology_hash=checksum), topology_fingerprint_for_matrix=lambda *args: checksum)
    modules = matrix, {}, contention

    def prepared(packet, phase, *, trusted_sha, modules=None):
        assert (modules is None) == (phase == 'cpu')
        monkeypatch.setattr(capture.planner, 'ORCHESTRATOR', packet / 'orchestrator')
        path = packet / phase / 'prepared/plan.json'
        capture.planner.check_pin(path, trusted_sha)
        return path, trusted_sha, plans[phase], matrix, {}, contention

    def validate(path, plan, *_):
        data = yaml.safe_load(path.read_text())
        oldest = datetime.fromisoformat(data['measured_at'])
        assert abs(path.stat().st_mtime - oldest.timestamp()) < 0.001
        capture.require(now - oldest <= timedelta(days=30), 'fixture canonical freshness refused')
        assert sorted(row['roles'] for row in data['pairs']) == required
        return {'sha256': capture.planner.digest(path), 'host_health': {'decision_grade': True}}

    monkeypatch.setattr(capture, 'read_prepared', prepared)
    monkeypatch.setattr(capture, 'validate_full', validate)
    monkeypatch.setattr(capture.planner, 'SCRATCH', tmp_path)
    monkeypatch.setattr(capture.planner, 'production_runtime_dirs', lambda: ())
    monkeypatch.setattr(capture.planner, 'verify_stage', lambda image, candidate, backend, production: image)
    monkeypatch.setattr(capture.runner, 'image_pin', lambda image, backend: {
        'binary_sha256': checksum, 'libraries': {'libggml-base.so': checksum}})

    def phase_input(phase, start, damage=None):
        gpu = phase == 'hip'
        packet = tmp_path / f'{phase}-packet'
        root = packet / 'orchestrator'
        prepared_dir = packet / phase / 'prepared'
        path = write(prepared_dir / 'plan.json', {'fixture': phase})
        plan_sha = capture.planner.digest(path)
        source = write(root / capture.runner.MATRIX_CONFIG, 'source bytes')
        manifest = [f'{plan_sha}  {path.relative_to(packet)}']
        for name in ('matrix_capture', 'contention_acquire', 'hot_stack_runner', 'hot_stack', 'evidence'):
            tool = f'sources/scripts/benchmark/kernel_promotion_{name}.py'
            producer = write(packet / tool, f'{phase} fixture producer')
            manifest.append(f'{capture.planner.digest(producer)}  {tool}')
        source_manifest = write(packet / 'SOURCE.sha256', '\n'.join(manifest) + '\n')
        attempt = ('b' if gpu else 'a') * 32
        directory = packet / phase / 'out' / attempt
        logs = prepared_dir / 'logs'
        phase_pairs = [pair for pair in required if ('architect_critic' in pair) == gpu]
        endpoints, startups, locals_, instances = {}, {}, {}, {}
        identities, cleanup = {}, {}

        def workloads(relative):
            write(directory / relative, {'verified': identities, 'observed': [], 'identity_errors': {}, 'foreign': []})

        workloads('preload-workloads.json')
        for role, (canonical_port, port) in capture.PORTS.items():
            if role == 'architect_critic' and not gpu:
                continue
            backend = 'hip' if role == 'architect_critic' else 'cpu'
            pid = port + 1
            endpoints[role] = {'port': port, 'roles': [role], 'backend': backend, 'logical_cpus': [0], 'models': [],
                               'argv': ['numactl', '--membind=0', '--', 'taskset', '-c', '0'],
                               'state_dir': str(prepared_dir / 'state' / str(port)), 'log': str(logs / f'{port}.log')}
            instances[role] = {'port': canonical_port}
            locals_[str(port)] = {} if damage != 'input' or role != 'frontdoor' else {'different-template': checksum}
            workloads(f'preload-{port}-workloads.json')
            witness = {'pid': pid, 'birth': 123, 'threads': {str(pid): {'cpus': [0], 'numa_policy': 'bind:0'}},
                       'backend': {'kfd_client': False} if backend == 'cpu' else
                                  {'kfd_client': True, 'gpu_id': 7, 'pasid': 12, 'vram_bytes': 1000}}
            binary = {'stat': stat, 'sha256': checksum}
            startup = {'pid': pid, 'birth': 123, 'model_mappings': {}, 'witness': witness,
                       'image': {'binary': binary, 'libraries': {f'/stage/{backend}/libggml-base.so': binary}}}
            write(directory / f'{port}.startup.json', startup)
            write(logs / f'{port}.log', 'fixture log\n')
            identities[str(pid)], startups[role] = 123, startup
            cleanup[str(pid)] = {'pid': pid, 'birth': 123, 'port': port, 'pidfd_exited': True, 'kfd_absent': True,
                                 'reaped_rc': 0, 'port_closed': damage != 'cleanup'}
        write(directory / 'owned-pids.txt', ''.join(f'{pid} {birth}\n' for pid, birth in identities.items()))
        write(directory / 'cleanup.json', {'spawn_unproved': False, 'servers': cleanup})
        phase_images = images if gpu else {'cpu': images['cpu']}
        for backend, image in phase_images.items():
            write(directory / f'{backend}-linkage.log', f'binary : {image["binary"]}\n'
                  f'expect : libraries under {image["library_dir"]}\n  OK   libggml-base.so -> /stage/lib\n'
                  f'PASS: all linked ggml libraries resolve inside {image["library_dir"]}\n')
        ports = {str(instances[role]['port']): endpoint['port'] for role, endpoint in endpoints.items()}
        resources = {'physical_cpus': '0-95', 'gpu_devices': ['ROCm0'] if gpu else [], 'ram_gib': capture.RAM[phase]}
        plan = {'phase': phase, 'spec': {'ports': ports, 'resources': resources, 'candidate': images,
                                        'config_sha256': {capture.runner.MATRIX_CONFIG: capture.planner.digest(source)}},
                'images': phase_images, 'endpoints': list(endpoints.values()), 'instances': instances,
                'phase_pairs': phase_pairs, 'required_pairs': required, 'topology_hash': checksum,
                'extra_inputs': locals_, 'source_matrix_measured_at': 'source-time', 'source_matrix_status_at_prepare': 'ok',
                'files': {str(p): checksum for p in capture.integrity_paths(root)}}
        plans[phase] = plan
        for first, second in phase_pairs:
            cell = f'{first}--{second}'
            for leg, roles, ms in [('solo-a', [first], 4000), ('solo-b', [second], 4000), ('parallel', [first, second], 5000)]:
                name = f'{cell}/{leg}'
                workloads(f'{name}/workloads.json')
                write(directory / name / 'request.json', capture.acquisition.REQUEST)
                witnesses, legs = {}, {}
                for role in roles:
                    port = str(endpoints[role]['port'])
                    witnesses[port] = startups[role]['witness']
                    legs[port] = {'sent': 1, 'headers': 6, 'finished': 7, 'status': 200}
                    write(directory / name / f'{port}.response.json', {
                        'timings': {'predicted_n': 100, 'predicted_ms': ms + (damage == 'timing')}})
                if damage == 'residency' and str(capture.PORTS['architect_critic'][1]) in witnesses:
                    port = str(capture.PORTS['architect_critic'][1])
                    witnesses[port] = witnesses[port] | {'backend': witnesses[port]['backend'] | {'vram_bytes': 0}}
                write(directory / name / 'requests.json', {'legs': legs, 'overlap_scans': [
                    {'start': 2, 'end': 8 if damage == 'overlap' else 3, 'witnesses': witnesses}]})
            solo, parallel = dict.fromkeys((first, second), 4.0), dict.fromkeys((first, second), 5.0)
            record = capture.result_pair(matrix, instances, (first, second), solo, parallel)
            write(directory / cell / 'cell.json', record.to_yaml_dict() | {'solo_s': solo, 'parallel_s': parallel,
                  'isolated_ports': {role: endpoints[role]['port'] for role in (first, second)}})
            workloads(f'{cell}/post-workloads.json')
        workloads('post-requests-workloads.json')
        workloads('post-health-workloads.json')
        health = {'status': 'clean', 'decision_grade': damage != 'health', 'attestation_error': '',
                  'attestation_status': 'collected', 'rule_source': 'fixture-rules', 'hostname': 'fixture', 'kernel': 'kernel',
                  'uptime_seconds': 20, 'llama_processes_foreign': [], 'llama_processes_lineup': 0,
                  'llama_processes_at_attestation': 0, 'warnings': [phase], 'structural_for_harness': [phase],
                  'decision_grade_blockers': ['fixture blocker'] if damage == 'health' else []}
        host = {'numa_online': '0', 'numa_cpus': {'node0': '0'}, 'cpu_online': '0', 'cpu_model': 'fixture'}
        write(directory / 'host-before.json', {'health': health, 'identity': host})
        after = health | dict.fromkeys(('llama_processes_lineup', 'llama_processes_at_attestation'), len(endpoints))
        write(directory / 'host-after.json', after)
        end = start + timedelta(minutes=1)
        unit = capture.matrix_row_id(phase)
        grant_regions = 'q0,q1,q2,q3' + (',mi210_0' if gpu else '')
        grant_holds = 'q0,q1,q2,q3' + (',gpu-quiet' if gpu else '')
        locks = {str(tmp_path / f'cpu_region.GLOBAL.q{node}.lock'): {} for node in range(4)}
        env = {'FILLER_ID': unit, 'FILLER_STOPFILE': '/STOP', 'FILLER_GPU_FENCE': str(int(not gpu))}
        if gpu:
            locks[str(tmp_path / 'gpu_device.mi210_0.lock')] = {}
        else:
            env.update(capture.runner.FENCE_ENV, LD_PRELOAD='/engine/state/gpu_fence-123456789abc.so')
        write(directory / 'admission.json', {'row': {'schema': 'epyc.row.v3', 'id': unit, 'regions': grant_regions,
                  'gib': 448, 'ports': list(ports.values()), 'stop_file': '/STOP', 'engine': {'path': '/engine/run'}},
                  'rowflow_env': env, 'row_sha256': checksum, 'flocks': locks, 'mem_available_bytes': 600 * 1024**3,
                  'cgroup': f'0::/rowflow/{unit}@123',
                  'grant': f'regions={grant_regions} holds={grant_holds} start={(start - timedelta(minutes=1)).isoformat()} '
                           f'end={(end + timedelta(minutes=1)).isoformat()}'})
        summary = {'schema': capture.SCHEMA, 'phase': phase, 'phase_scope': capture.SCOPE[phase], 'unit_id': unit,
                   'attempt_id': attempt, 'status': 'captured', 'authority': 'isolated_observation', 'cleanup_proved': True,
                   'complete_matrix': False, 'samples_per_cell': 1, 'required_pairs': required, 'phase_pairs': phase_pairs,
                   'completed_pairs': phase_pairs if damage != 'coverage' else phase_pairs[:-1], 'host_health': after,
                   'acquisition_started_at': start.isoformat() if damage != 'time' else 'malformed',
                   'acquisition_finished_at': end.isoformat(), 'source_matrix': capture.source_identity(plan),
                   'topology_hash': checksum, 'orchestrator_commit': capture.ORCHESTRATOR_PIN,
                   'candidate_commit': capture.C13, 'prepared_plan': {'sha256': plan_sha, 'path': str(path)}}
        write(directory / 'result.json', summary)
        if damage == 'summary':
            summary['acquisition_started_at'] = (start + timedelta(seconds=1)).isoformat()
        result = write(directory.parent / 'RESULT.json', summary | {'capture_dir': str(directory),
                       'attempt_files_sha256': capture.attempt_inventory(directory),
                       'server_logs_sha256': {'path': str(logs), 'files': capture.attempt_inventory(logs)}})
        if damage == 'inventory':
            write(directory / 'cleanup.json', {})
        return result, capture.planner.digest(result), plan_sha, capture.planner.digest(source_manifest)

    return phase_input, now


def test_split_admission_merges_original_hip_first_bounds_and_health(tmp_path, split_native_fixture):
    phase_input, now = split_native_fixture
    oldest = now - timedelta(hours=3)
    hip = phase_input('hip', oldest)
    cpu = phase_input('cpu', now - timedelta(hours=1))
    output = tmp_path / 'admitted'
    args = ['--merge-split', '--output-dir', str(output)]
    for phase, (result_path, result_sha, plan_sha, source_sha) in [('cpu', cpu), ('hip', hip)]:
        args += [f'--{phase}-result', str(result_path), f'--{phase}-result-sha256', result_sha,
                 f'--{phase}-plan-sha256', plan_sha, f'--{phase}-source-sha256', source_sha]
    assert capture.main(args) == 0
    admitted = capture.planner.read_json(output / 'admission.json')
    assert admitted['measured_at'] == oldest.isoformat()
    assert admitted['phases']['hip']['host_after']['warnings'] == ['hip']
    assert admitted['phases']['cpu']['host_before']['health']['warnings'] == ['cpu']
    assert admitted['matrix']['sha256'] == capture.planner.digest(output / 'contention_matrix.yaml')
    assert capture.main(args) == 2
    assert capture.planner.read_json(output / 'admission.json') == admitted


@pytest.mark.parametrize(('damage', 'match'), [
    ('summary', 'inventory-bound native summary'), ('inventory', 'inventory changed'), ('coverage', 'three-pair'),
    ('time', 'Invalid isoformat'), ('health', 'fixture blocker'), ('cleanup', 'cleanup does not cover'),
    ('residency', 'nonzero device VRAM'), ('overlap', 'outside the shared request interval'),
    ('timing', 'native raw decode timings'), ('input', 'shards, templates'), ('stale', 'freshness refused'),
    ('manifest', 'changed SHA-256 pin: .*SOURCE.sha256'),
])
def test_split_admission_refuses_without_emitting(tmp_path, split_native_fixture, damage, match):
    phase_input, now = split_native_fixture
    cpu = phase_input('cpu', now - timedelta(hours=1))
    hip_start = now - (timedelta(days=31) if damage == 'stale' else timedelta(hours=2))
    hip = phase_input('hip', hip_start, damage)
    if damage == 'manifest':
        hip = (*hip[:-1], '0' * 64)
    output = tmp_path / 'refused'
    with pytest.raises(ValueError, match=match):
        capture.merge_split(cpu, hip, output)
    assert not output.exists()
