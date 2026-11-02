"""M4 workload depth must not silently alter a declared server KV pool."""
import dataclasses
import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'scripts/benchmark/m4_cpu_producer/native/k35_stack_context_matrix_runner.py'
spec = importlib.util.spec_from_file_location('m4_context_native', RUNNER)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)


def test_legacy_dynamic_context_is_unchanged():
    scenario = dataclasses.replace(native.SCENARIOS[0], max_context=262144, parallel=4)
    assert native.server_context(scenario, 8192, 128) == (8192 + 128 + 1024) * 4


def test_explicit_full_pool_changes_argv_without_changing_workload(monkeypatch):
    scenario = dataclasses.replace(native.SCENARIOS[0], max_context=262144, parallel=4, server_context_size=262144)
    monkeypatch.setenv('M4_TREATMENT', 'default-off')
    argv = native.build_server_argv(scenario, binary=Path('/tmp/bin/llama-server'), port=18000, nominal_context=8192, max_tokens=128)
    assert argv[argv.index('-c') + 1] == '262144'
    assert argv[argv.index('-np') + 1] == '4'
    assert native.prompt_for_context(8192, 128).startswith('You are serving')


@pytest.mark.parametrize('size', [0, -1, 35000, 262145, True, '262144'])
def test_explicit_pool_must_fit_workload_and_respect_cap(size):
    scenario = dataclasses.replace(native.SCENARIOS[0], max_context=262144, parallel=4, server_context_size=size)
    with pytest.raises(ValueError, match='explicit server context'):
        native.server_context(scenario, 8192, 128)


def test_none_reasoning_keeps_vision_server_default(monkeypatch):
    scenario = dataclasses.replace(native.SCENARIOS[0], reasoning=None)
    monkeypatch.setenv('M4_TREATMENT', 'default-off')
    argv = native.build_server_argv(scenario, binary=Path('/tmp/bin/llama-server'), port=18000, nominal_context=2048, max_tokens=128)
    assert '--reasoning' not in argv


def test_vision_request_binds_actual_image_bytes(tmp_path):
    import base64
    import hashlib
    image = tmp_path / 'fixture.png'
    image.write_bytes(b'example-image-bytes')
    scenario = dataclasses.replace(native.SCENARIOS[0], image_path=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    body = native.build_chat_request_body(scenario, 'inspect image', max_tokens=10)
    parts = body['messages'][0]['content']
    assert parts[0]['type'] == 'image_url'
    assert base64.b64decode(parts[0]['image_url']['url'].split(',', 1)[1]) == image.read_bytes()
    assert parts[1] == {'type': 'text', 'text': 'inspect image'}
    image.write_bytes(b'mutated')
    with pytest.raises(ValueError, match='sealed image'):
        native.build_chat_request_body(scenario, 'inspect image', max_tokens=10)


def test_vision_request_cannot_use_text_completion(tmp_path):
    scenario = dataclasses.replace(native.SCENARIOS[0], image_path=str(tmp_path / 'x.png'), image_sha256='0' * 64, request_endpoint='completion')
    with pytest.raises(ValueError, match='chat endpoint'):
        native.build_chat_request_body(scenario, 'inspect image', max_tokens=10)


def test_strict_vision_reader_reopens_request_and_detects_tamper(tmp_path):
    import base64
    import hashlib
    import json
    sys.path.insert(0, str(ROOT / 'scripts/vidya'))
    from adapters.m4_cpu_speed import _verify_bound_image_request
    from claim_tuple import ProjectionError
    image = b'fixture-image'
    request_path = tmp_path / 'request.json'
    request = {'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(image).decode()}},
        {'type': 'text', 'text': 'inspect image'},
    ]}]}
    request_path.write_text(json.dumps(request))
    sample = {'request_path': str(request_path)}
    scenario = {'image_sha256': hashlib.sha256(image).hexdigest()}
    _verify_bound_image_request(sample, scenario, tmp_path, 'inspect image')
    request['messages'][0]['content'][0]['image_url']['url'] = 'data:image/png;base64,' + base64.b64encode(b'tampered').decode()
    request_path.write_text(json.dumps(request))
    with pytest.raises(ProjectionError, match='image digest mismatch'):
        _verify_bound_image_request(sample, scenario, tmp_path, 'inspect image')


def test_flash_recipe_environment_is_bound_and_unknown_keys_refuse(monkeypatch):
    scenario = dataclasses.replace(native.SCENARIOS[0], recipe_env={'GGML_FA_SPLIT_KV': '0', 'GGML_NOHUGEPAGE_PROCESS': None})
    monkeypatch.setenv('M4_TREATMENT', 'default-off')
    argv = native.build_server_argv(scenario, binary=Path('/tmp/bin/llama-server'), port=18000, nominal_context=2048, max_tokens=128)
    assert argv[:3] == ['env', '-u', 'GGML_NOHUGEPAGE_PROCESS']
    assert 'GGML_FA_SPLIT_KV=0' in argv
    scenario = dataclasses.replace(scenario, recipe_env={'LD_PRELOAD': '/bad'})
    with pytest.raises(ValueError, match='unreviewed scenario environment'):
        native.build_server_argv(scenario, binary=Path('/tmp/bin/llama-server'), port=18000, nominal_context=2048, max_tokens=128)


def test_strict_reader_verifies_recipe_environment():
    sys.path.insert(0, str(ROOT / 'scripts/vidya'))
    from adapters.m4_cpu_speed import _verify_recipe_env
    from claim_tuple import ProjectionError
    expected = {'GGML_NOHUGEPAGE_PROCESS': None, 'GGML_FA_SPLIT_KV': '0'}
    argv = ['env', '-u', 'GGML_NOHUGEPAGE_PROCESS', 'LD_LIBRARY_PATH=/tmp/x', 'GGML_FA_SPLIT_KV=0', 'llama-server']
    _verify_recipe_env(argv, expected)
    with pytest.raises(ProjectionError):
        _verify_recipe_env([v for v in argv if v != 'GGML_FA_SPLIT_KV=0'], expected)
    with pytest.raises(ProjectionError):
        _verify_recipe_env(argv + ['GGML_NOHUGEPAGE_PROCESS=1'], expected)


@pytest.mark.parametrize('key,value', [('GGML_FA_TUNING', '1'), ('LLAMA_ARG_SEED', '7'), ('LD_PRELOAD', '/tmp/evil.so'), ('GGML_IQK', '0')])
def test_unbound_inherited_environment_refuses(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match='unbound inherited'):
        native.runtime_env_prefix(Path('/tmp/bin/llama-server'), {'GGML_FA_SPLIT_KV':'0'})


def test_bound_recipe_env_overrides_inherited_value(monkeypatch):
    monkeypatch.setenv('GGML_FA_SPLIT_KV', '1')
    argv = native.runtime_env_prefix(Path('/tmp/bin/llama-server'), {'GGML_FA_SPLIT_KV':'0'})
    assert 'GGML_FA_SPLIT_KV=0' in argv
