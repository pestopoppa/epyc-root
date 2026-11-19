"""--load-threads is the default loader knob for native M4 llama-server launches.

A loader knob cannot change a measured result, so it is emitted by default,
allowed through the inherited-environment purge, and never part of a seal.
"""
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / 'scripts/benchmark/m4_cpu_producer'
RUNNER = PRODUCER / 'native/k35_stack_context_matrix_runner.py'
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('m4_load_threads_native', RUNNER)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
spec = importlib.util.spec_from_file_location('m4_load_threads_dispatch', PRODUCER / 'dispatch.py')
dispatch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dispatch
spec.loader.exec_module(dispatch)

BINARY = Path('/nonexistent-k35-load-threads/bin/llama-server')


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setenv('M4_TREATMENT', 'default-off')
    monkeypatch.delenv('LLAMA_ARG_LOAD_THREADS', raising=False)
    native._LOAD_THREADS_SUPPORT_CACHE.clear()
    yield
    native._LOAD_THREADS_SUPPORT_CACHE.clear()


def argv_for(scenario, binary=BINARY):
    return native.build_server_argv(scenario, binary=binary, port=18000, nominal_context=2048, max_tokens=128)


def flag_value(argv):
    assert argv.count('--load-threads') == 1
    return argv[argv.index('--load-threads') + 1]


@pytest.mark.parametrize('affinity,threads,expected', [
    ('0-95', 96, '96'),
    ('0-95', 48, '96'),
    ('0-47,96-143', 48, '96'),
    ('0-23', 24, '24'),
    (None, 72, '72'),
])
def test_default_flag_carries_claimed_cpu_count(affinity, threads, expected):
    scenario = dataclasses.replace(native.SCENARIOS[0], cpu_affinity=affinity, threads=threads)
    assert flag_value(argv_for(scenario)) == expected


def test_sealed_extra_args_load_threads_wins():
    scenario = dataclasses.replace(native.SCENARIOS[0], cpu_affinity='0-95', extra_args=('--load-threads', '8'))
    assert flag_value(argv_for(scenario)) == '8'
    scenario = dataclasses.replace(scenario, extra_args=('--load-threads=4',))
    argv = argv_for(scenario)
    assert '--load-threads' not in argv and '--load-threads=4' in argv


def test_env_purge_allows_loader_knob_only(monkeypatch):
    monkeypatch.setenv('LLAMA_ARG_LOAD_THREADS', '96')
    native.runtime_env_prefix(Path('/tmp/bin/llama-server'), {'GGML_FA_SPLIT_KV': '0'})
    monkeypatch.setenv('LLAMA_ARG_LOAD_THREADS', 'many')
    with pytest.raises(ValueError, match='invalid loader environment'):
        native.runtime_env_prefix(Path('/tmp/bin/llama-server'), {})
    monkeypatch.setenv('LLAMA_ARG_LOAD_THREADS', '0')
    monkeypatch.setenv('LLAMA_ARG_SEED', '7')
    with pytest.raises(ValueError, match='unbound inherited llama argument'):
        native.runtime_env_prefix(Path('/tmp/bin/llama-server'), {})


def test_recipe_seal_ignores_load_threads_and_keeps_old_digests():
    scenario = native.SCENARIOS[0]
    legacy = hashlib.sha256(json.dumps(dataclasses.asdict(scenario), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    assert dispatch.recipe_digest(scenario) == legacy
    for loader in (('--load-threads', '96'), ('--load-threads=8',)):
        with_loader = dataclasses.replace(scenario, extra_args=scenario.extra_args + loader)
        assert dispatch.recipe_digest(with_loader) == legacy
    changed = dataclasses.replace(scenario, extra_args=scenario.extra_args + ('--no-repack',))
    assert dispatch.recipe_digest(changed) != legacy


def test_strip_loader_args_keeps_everything_else():
    assert native.strip_loader_args(['-b', '512', '--load-threads', '96', '--no-repack', '--load-threads=4']) == ('-b', '512', '--no-repack')


def test_mlock_no_mmap_without_flag_is_refused():
    with pytest.raises(native.LoaderThreadsRefusal, match='single-threaded'):
        native.check_loader_threads(['llama-server', '--mlock', '--no-mmap'], supported=True)
    with pytest.raises(native.LoaderThreadsRefusal):
        native.check_loader_threads(['llama-server', '--mlock', '--no-mmap'], supported=None)
    native.check_loader_threads(['llama-server', '--mlock', '--no-mmap', '--load-threads', '96'], supported=True)
    native.check_loader_threads(['llama-server', '--mlock'], supported=True)


def test_runner_main_refuses_stripped_flag(monkeypatch, tmp_path, capsys):
    scenario = dataclasses.replace(native.SCENARIOS[0], mlock=True, no_mmap=True)
    monkeypatch.setattr(native, 'SCENARIOS', (scenario,))
    monkeypatch.delenv('M4_SCENARIO_JSON', raising=False)
    monkeypatch.setattr(native, 'add_loader_threads',
                        lambda argv, scenario, binary: native.check_loader_threads(argv, supported=True) or argv)
    out = tmp_path / 'out'
    rc = native.main(['--only', scenario.name, '--context', '2048', '--binary', str(BINARY), '--output-dir', str(out)])
    assert rc == 2
    assert 'REFUSED' in capsys.readouterr().err and not out.exists()


def test_v10_style_binary_suppresses_flag(monkeypatch):
    calls = []
    def probe(binary):
        calls.append(binary)
        return False
    monkeypatch.setattr(native, 'binary_supports_load_threads', probe)
    scenario = dataclasses.replace(native.SCENARIOS[0], cpu_affinity='0-95', mlock=True, no_mmap=True)
    argv = argv_for(scenario, Path('/mnt/raid0/llm/kernels/production/cpu/llama-server'))
    assert '--load-threads' not in argv and '--mlock' in argv
    assert calls


def test_strings_probe_reads_binary_libs_and_caches(tmp_path):
    v10 = tmp_path / 'v10/bin'; v10.mkdir(parents=True)
    (v10 / 'llama-server').write_bytes(b'\x7fELF server')
    (v10 / 'libllama-common.so').write_bytes(b'\x7fELF --threads --mlock')
    champion = tmp_path / 'c6/bin'; champion.mkdir(parents=True)
    (champion / 'llama-server').write_bytes(b'\x7fELF server')
    (champion / 'libllama-common.so.0.0.10500').write_bytes(b'\x00' * ((1 << 20) - 5) + b'--load-threads N\x00')
    assert native.binary_supports_load_threads(v10 / 'llama-server') is False
    assert native.binary_supports_load_threads(champion / 'llama-server') is True
    assert native.binary_supports_load_threads(tmp_path / 'absent/llama-server') is None
    (v10 / 'libllama-common.so').write_bytes(b'--load-threads')
    assert native.binary_supports_load_threads(v10 / 'llama-server') is False  # cached per binary path
    scenario = dataclasses.replace(native.SCENARIOS[0], cpu_affinity='0-95')
    assert '--load-threads' not in argv_for(scenario, v10 / 'llama-server')
    assert flag_value(argv_for(scenario, champion / 'llama-server')) == '96'


def test_cpu_list_count_forms():
    assert native.cpu_list_count('0-47,96-143') == 96
    assert native.cpu_list_count('0-95:2') == 48
    assert native.cpu_list_count('3') == 1
    assert native.cpu_list_count('') == 0 and native.cpu_list_count(None) == 0
    assert native.cpu_list_count('x-y') == 0
