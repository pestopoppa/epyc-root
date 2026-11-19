"""Execute patched native control flow with fake inference only; never launch kernels."""
import ast
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
from types import SimpleNamespace

import pytest

from scripts.vidya.producers import mi210_native_run as native
from scripts.vidya.adapters import mi210_paired_raw as projection
from scripts.vidya.producers import mi210_paired_capture as raw

PACKET = Path(__file__).resolve().parents[2] / 'data/vidya/mi210-paired-wire-20261117'


def patched(tmp_path, name):
    manifest = json.loads((PACKET / 'manifest.json').read_text())['sources'][name]
    original = (PACKET / (name + '.original.py.txt')).read_bytes()
    assert hashlib.sha256(original).hexdigest() == manifest['sha256']
    (tmp_path / 'job.py').write_bytes(original)
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(PACKET / (name + '.patch'))],
                   cwd=tmp_path, check=True, capture_output=True)
    path = tmp_path / 'job.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['patched_sha256']
    compile(path.read_text(), str(path), 'exec')
    return path


def capture_result(out):
    captures = list(out.glob('belief-*'))
    assert len(captures) == 1
    return captures[0], raw.read(captures[0])


def q38_globals(tmp_path, monkeypatch, *, smoke=False, case='invalid'):
    path = patched(tmp_path, 'q38p3a')
    out = tmp_path / 'out'
    proof = {'pid': 123, 'kfd_pids_ours': {'123': 30 * 1024**3}, 'kfd_foreign': [],
             'observations': [{'time': 2, 'vram': 30 * 1024**3,
                               'libs': ['/fake/libggml-hip.so', '/fake/libamdhip64.so']}]}
    timing = {'predicted_ms': 2000, 'predicted_n': 4, 'predicted_per_second': 2}
    decode = {'start': 1, 'end': 3, 'predicted_per_second': 2, 'draft_n': 0, 'timings': timing}
    def serve(*args):
        if case == 'exception':
            raise RuntimeError('native injected failure')
        return {'proof': proof, 'decode': [decode], 'affinity': [],
                'errors': ['invalid native'] if case == 'invalid' else [], 'error': None}
    env = {'__file__': str(path), 'os': os, 'OUT': str(out), 'NativeRun': native.NativeRun,
           'identity': native.identity, 'model_identities':native.model_identities, 'build_identity': native.build_identity, 'grant': native.grant,
           'PLUMB': smoke, 'IDENT': {'model': '/missing/model', 'chat_template': '/missing/template'},
           'ARMS': {a: {'bin': '/missing/bin', 'ld': '/missing/lib', 'hip_prefix': '/fake',
                        'libggml_hip_sha256': 'x'} for a in ('B', 'C')},
           'DECODE': ['prompt'], 'server_argv': lambda a: [a],
           'gate_dependency': lambda: (case != 'gate', None), 'STOPF': str(tmp_path / 'STOP'),
           'DEADLINE': 100000, 'time': SimpleNamespace(time=lambda: 100),
           'serve_phase': serve, 'linkage': lambda p, a: (True, []),
           'release': lambda pid: {'ok': True, 'pid': pid}, 'OWN_VRAM_MIN': 20 * 1024**3,
           'sha': lambda p: 'x', 'med': statistics.median, 'json': json}
    def append(row):
        with (out / 'results.jsonl').open('a') as f:
            f.write(json.dumps(row) + '\n')
    env['append'] = append
    env['atomic'] = lambda p, o: Path(p).write_text(json.dumps(o))
    if case == 'stop':
        (tmp_path / 'STOP').touch()
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main_specoff')
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), env)
    return env, out


@pytest.mark.parametrize('case,state,count,rc', [('invalid','failed',1,3), ('gate','partial',0,2),
                                                ('stop','stopped',0,75)])
def test_q38_early_returns_are_captured(tmp_path, monkeypatch, case, state, count, rc):
    env, out = q38_globals(tmp_path, monkeypatch, case=case)
    assert env['main_specoff']() == rc
    root, run = capture_result(out)
    assert run['state'] == state
    assert len(run['attempts']) == count
    if case == 'invalid':
        assert json.loads((out / 'results.jsonl').read_text())['valid'] is False
        assert run['attempts'][0]['native']['requests'][0]['timings']['predicted_ms'] == 2000
    with pytest.raises(ValueError, match='complete measurement'):
        projection.project(root)


def test_q38_native_exception_survives_terminal_capture(tmp_path, monkeypatch):
    env, out = q38_globals(tmp_path, monkeypatch, case='exception')
    with pytest.raises(RuntimeError, match='injected'):
        env['main_specoff']()
    _, run = capture_result(out)
    assert run['state'] == 'failed'
    assert run['attempts'][0]['native']['state'] == 'failed'
    assert 'injected' in run['terminal']['errors'][0]


@pytest.mark.parametrize('smoke', [False, True])
def test_q38_complete_scope_and_shared_grade(tmp_path, monkeypatch, smoke):
    env, out = q38_globals(tmp_path, monkeypatch, case='valid', smoke=smoke)
    assert env['main_specoff']() == 0
    root, run = capture_result(out)
    assert run['state'] == 'complete'
    assert len(run['attempts']) == (1 if smoke else 4)
    if smoke:
        with pytest.raises(ValueError):
            projection.project(root)
    else:
        tuples = projection.project(root)
        from claim_tuple import grade
        assert len(tuples) == 4
        assert all(grade(t)[:2] == ('Judged', 'Located') for t in tuples)
        assert all(t.protocol_id == '' and t.metric_direction == 'higher_better' for t in tuples)


def npd_run(tmp_path, *, failure=False, smoke=False):
    path = patched(tmp_path, 'npd1')
    out = tmp_path / ('smoke-out' if smoke else 'out')
    class Socket:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def setsockopt(self, *args): pass
        def bind(self, *args): pass
    class Process:
        pid = 123
        returncode = None
        def poll(self): return self.returncode
    process = Process()
    def completion():
        if failure: raise RuntimeError('native timing failure')
        return {'timings': {'predicted_n':4,'predicted_ms':8}, 'predicted_n':4,
                'predicted_ms':8,'tpot_ms':2}
    env = {'__file__':str(path), 'OUT':out, 'D':tmp_path, 'SMOKE':smoke,
           'MODEL':str(tmp_path/'missing.gguf'), 'MTP':str(tmp_path/'missing-mtp.gguf'),
           'CPU':str(tmp_path/'cpu'), 'GPU':str(tmp_path/'gpu'),
           'COMMON':[], 'ENV':{}, 'PROMPT':'fixture',
           'ORDER':[('p1','cpu'),('p1','gpu_cpu'),('p2','gpu_cpu'),('p2','cpu')],
           'NativeRun':native.NativeRun,'identity':native.identity,'grant':native.grant,
           'build_identity':native.build_identity,'model_identities':native.model_identities,'Path':Path, 'PORT':0,
           'stopped':lambda:False, 'socket':SimpleNamespace(socket=Socket,SOL_SOCKET=1,SO_REUSEADDR=1),
           'os':SimpleNamespace(environ={},sched_getaffinity=lambda pid:{1,2}),
           'subprocess':SimpleNamespace(Popen=lambda *a,**k:Process(),STDOUT=None),
           'request':lambda *a,**k:{'status':'ok'},'run_completion':completion,
           'time':SimpleNamespace(time=lambda:1,monotonic=lambda:1),
           'cleanup':lambda p:setattr(p,'returncode',0), 'log':lambda rec:None,
           'cpus':[1,2], 'threads':2, 'load_threads':2, 'json':json}
    tree = ast.parse(path.read_text())
    start = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Expr)
                 and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute)
                 and n.value.func.attr == 'mkdir')
    exec(compile(ast.Module(body=tree.body[start:],type_ignores=[]),str(path),'exec'),env)
    return out


@pytest.mark.parametrize('smoke',[False,True])
def test_npd_marker_and_native_timing_capture(tmp_path, smoke):
    out = npd_run(tmp_path, smoke=smoke)
    root, run = capture_result(out)
    assert (out/'COMPLETE.json').is_file()
    assert run['state'] == 'complete'
    if smoke:
        assert not (tmp_path/'out/COMPLETE.json').exists()
    else:
        tuples = projection.project(root)
        assert all(t.value == 2 and t.metric_direction == 'lower_better' for t in tuples)
        assert all(t.extra['native']['residency_linkage'] is None for t in tuples)


def test_npd_exception_captured_after_cleanup(tmp_path):
    with pytest.raises(RuntimeError,match='timing failure'):
        npd_run(tmp_path,failure=True)
    _, run = capture_result(tmp_path/'out')
    assert run['state'] == 'failed'
    assert run['attempts'][0]['native']['release']['alive'] is False


def test_model_shards_preserve_missing_identities(tmp_path):
    first = tmp_path/'model-00001-of-00003.gguf'
    first.write_bytes(b'fixture shard')
    rows = native.model_identities(first)
    assert len(rows) == 3
    assert rows[0]['sha256'] is not None
    assert all(r['sha256'] is None and r['error'] for r in rows[1:])


def test_projection_rejects_missing_native_timing(tmp_path, monkeypatch):
    env, out = q38_globals(tmp_path, monkeypatch, case='valid')
    serve = env['serve_phase']
    def broken(*args):
        row = serve(*args)
        row['decode'][0]['timings'] = None
        return row
    env['serve_phase'] = broken
    assert env['main_specoff']() == 0
    root, _ = capture_result(out)
    with pytest.raises(ValueError, match='full native timing'):
        projection.project(root)
