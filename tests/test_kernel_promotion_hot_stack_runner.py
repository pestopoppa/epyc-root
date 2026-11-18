"""Fixtures for isolated hot-stack admission, request witnesses and cleanup."""

import importlib.util
import json
import os
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


@pytest.mark.parametrize('before_headers', [True, False])
def test_smoke_requires_complete_request_time_witness(tmp_path, monkeypatch, before_headers):
    sampled = threading.Event()
    headers = threading.Event()
    admission = SimpleNamespace(deadline=time.time() + 15, check=lambda: None)
    runtime = runner.Runtime({}, tmp_path / 'plan.json', tmp_path, admission, 5, 5)
    endpoint = {'test': 'chat', 'endpoint': 'http://127.0.0.1:19520'}
    raw = b'{"choices":[{"message":{"role":"assistant","content":"text"}}]}'

    def pretend_request(server, method, path, body, timeout, sent, response_started):
        assert method == 'POST' and path == '/v1/chat/completions'
        assert json.loads(body)['stream'] is False
        sent.set()
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

    monkeypatch.setattr(runtime, 'request_http', pretend_request)
    monkeypatch.setattr(runtime, 'sample', sample)
    server = SimpleNamespace(endpoint=endpoint)
    if before_headers:
        runtime.smoke(server, tmp_path)
    else:
        with pytest.raises(ValueError, match='inside request'):
            runtime.smoke(server, tmp_path)
    observations = runner.planner.read_json(tmp_path / 'during-request.json')
    assert bool(observations['samples']) == before_headers
    assert (tmp_path / 'response.raw.json').read_bytes() == raw


def test_embedding_rejects_bad_indices_and_zero_vectors():
    request = {'input': ['sample', 'second']}
    good = {'data': [{'index': 0, 'embedding': [0.1, -0.2]}, {'index': 1, 'embedding': [0.2, -0.1]}]}
    runner.response_check('embedding', request, good)
    with pytest.raises(ValueError, match='indices'):
        runner.response_check('embedding', request, {'data': [good['data'][0]] * 2})
    with pytest.raises(ValueError, match='zero vectors'):
        runner.response_check('embedding', request, {'data': [good['data'][0], {'index': 1, 'embedding': [0, 0]}]})


@pytest.mark.parametrize(('failed_start', 'proved', 'verdict'), [
    (False, True, 'pass'), (True, True, 'failed'), (False, False, 'failed'),
])
def test_execute_serial_startup_and_seal_only_after_cleanup(tmp_path, failed_start, proved, verdict):
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

    runtime = SimpleNamespace(output=tmp_path, plan={'endpoints': endpoints}, servers=servers, start=start,
                              preflight=lambda: order.append(('preflight',)),
                              verify_model_inputs=lambda: order.append(('model_inputs',)),
                              ready=lambda server: order.append(('ready', server.port)) or {},
                              verify_identity=lambda server: order.append(('verify', server.port)),
                              smoke=lambda server, _: order.append(('smoke', server.port)), check=lambda: None,
                              cleanup=cleanup)
    assert runner.execute(runtime) == (0 if verdict == 'pass' else 2)
    assert order[:5] == [('preflight',), ('model_inputs',), ('start', ports[0]), ('ready', ports[0]), ('start', ports[1])]
    assert (('smoke', ports[0]) in order) == (not failed_start)
    assert order[-1] == ('cleanup',)
    assert runner.planner.read_json(tmp_path / 'result.json')['functional_smoke'] == verdict
    if proved:
        manifest = tmp_path / 'MANIFEST.json'
        assert runner.planner.read_json(manifest)['functional_smoke'] == verdict
        assert (tmp_path / 'COMPLETE').read_text().strip() == runner.planner.digest(manifest)
    else:
        assert not (tmp_path / 'COMPLETE').exists()
