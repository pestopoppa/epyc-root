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
