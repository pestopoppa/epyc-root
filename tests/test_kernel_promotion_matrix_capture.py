"""Software controls for configured-primary contention acquisition."""

import json
import os
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
    _, _, plan, matrix, config, contention = capture.read_prepared(packet, 'cpu')
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
