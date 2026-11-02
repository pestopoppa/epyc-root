"""Exercise the patched runner entry with controlled residency and clock stubs.

These controls do not prove live GPU residency or qualify an inference run.
"""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SRC = Path(__file__).with_name('run_cell_fixture.py')

def test_fixture_matches_candidate_when_supplied():
    candidate = os.environ.get('M4_GPU_SWEEP_SOURCE')
    if not candidate:
        pytest.skip('set M4_GPU_SWEEP_SOURCE to compare the candidate runner')
    names = {'run_cell', 'residency_sample_inside_batch'}
    def functions(path):
        tree = ast.parse(Path(path).read_text())
        return {n.name: ast.dump(n, include_attributes=False) for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name in names}
    assert functions(candidate) == functions(SRC)

@pytest.mark.parametrize('inside', [True, False])
def test_actual_run_cell_gates_batch_residency(tmp_path, monkeypatch, inside):
    sysroot = tmp_path / 'sys'; procroot = tmp_path / 'proc'
    kfd = sysroot / 'class/kfd/kfd/proc/123'; kfd.mkdir(parents=True)
    (kfd / 'vram_1').write_text('1024')
    card = sysroot / 'class/drm/card2/device'; card.mkdir(parents=True)
    (card / 'mem_info_vram_used').write_text('1024')
    maps = procroot / '123'; maps.mkdir(parents=True)
    (maps / 'maps').write_text('0 0 0 0 0 /image/libggml.so\n')
    real_path = Path
    def path_factory(s):
        s = str(s)
        if s.startswith('/sys/'): return sysroot / s[5:]
        if s.startswith('/proc/'): return procroot / s[6:]
        return real_path(s)
    class Event:
        instances = []
        def __init__(self): self.flag = False; self.instances.append(self)
        def set(self): self.flag = True
        def is_set(self): return self.flag
        def wait(self, _):
            if self is self.instances[0]: self.flag = True
            return self.flag
    class Thread:
        last = None
        def __init__(self, target, daemon): self.target = target; Thread.last = self
        def start(self): self.target()
        def join(self, timeout): pass
        def is_alive(self): return False
    times = iter([10, 11, 20, 21, 22, 30] if inside else [10, 11, 20, 30])
    def batch(**kwargs):
        if inside:
            Event.instances[0].flag = False
            Thread.last.target()
        return ([{'ok': True}], 1.0)
    proc = SimpleNamespace(pid=123)
    stopped = []
    fake_subprocess = SimpleNamespace(Popen=object, run=lambda *a, **kw: SimpleNamespace(stdout='pid=123,'))
    fake_time = SimpleNamespace(monotonic_ns=lambda: next(times))
    tree = ast.parse(SRC.read_text()); names = {'run_cell', 'residency_sample_inside_batch'}
    funcs = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in names]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *funcs], type_ignores=[])
    ns = {'Path':path_factory, 'os':os, 'time':fake_time, 'threading':SimpleNamespace(Event=Event, Thread=Thread),
          'subprocess':fake_subprocess, 'build_server_command':lambda **kw: [], 'build_env':lambda *a: {},
          'start_server':lambda *a: proc, 'wait_for_health':lambda *a: None, 'run_prompt_batch':batch,
          'summarize_cell':lambda **kw: {}, 'utc_now':lambda:'now', 'stop_server':lambda p: stopped.append(p.pid) or {},
          'write_jsonl':lambda *a: None}
    exec(compile(ast.fix_missing_locations(module), str(SRC), 'exec'), ns)
    monkeypatch.setenv('FILLER_PIDFILE', str(tmp_path / 'pids'))
    monkeypatch.setenv('M4_VRAM_LIMIT_BYTES', '2048')
    args = SimpleNamespace(port_base=1234, llama_server=real_path('/image/llama-server'), threads=4,
        context_size=2048, ubatch_size=512, kv_type='q8_0', no_flash_attn=False, no_jinja=False,
        no_mlock=True, extra_server_arg=[], dry_run=False, startup_timeout=2, warmup_prompts=0,
        measure_ttft=False, n_predict=8, request_timeout=2)
    model = SimpleNamespace(label='test', registry_key='test', path=real_path('/tmp/model'))
    kw = dict(model=model, np_level=1, prompts=['x'], args=args, output_dir=tmp_path / 'out', cell_index=0)
    if inside:
        row = ns['run_cell'](**kw)
        assert row['gpu_residency_batch_start_monotonic_ns'] == 20
        assert row['gpu_residency_batch_end_monotonic_ns'] == 30
        assert len(row['gpu_residency_during']) == 2
    else:
        with pytest.raises(RuntimeError, match='no completed own-PID GPU residency'):
            ns['run_cell'](**kw)
    assert stopped == [123]
