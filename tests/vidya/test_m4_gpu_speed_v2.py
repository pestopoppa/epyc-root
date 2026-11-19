import copy
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya/adapters"))
from claim_tuple import ProjectionError
from m4_gpu_speed_v2 import Trust, project, validate_capture


def digest(data):
    return hashlib.sha256(data).hexdigest()


def setup_capture(tmp_path):
    capture = tmp_path / "captures"
    capture.mkdir()
    files = {}
    for name in ("binary", "model", "prompt", "libggml.so", "producer.py"):
        path = tmp_path / name
        path.write_text(name)
        files[name] = {"path": str(path), "sha256": digest(path.read_bytes())}
    requests = capture / "requests.jsonl"
    rows = [{"success": True, "http_status": 200, "error": "", "request_index": i,
             "stream_id": i, "predicted_tokens": 10, "predicted_ms": 1000, "request_sha256": str(i)*64,
             "response": {"stop":True, "timings":{"predicted_n":10,"predicted_ms":1000}}} for i in range(2)]
    requests.write_text("".join(json.dumps(x) + "\n" for x in rows))
    expected = {"role": "architect_critic", "arm": "CANDIDATE", "source_commit": "a" * 40,
                "model": str(tmp_path / "model"), "recipe": {"flags": "srpf"}, "argv": ["llama-server"],
                "environment": {}, "device": "mi210_0", "np": 2, "files": {k: files[k] for k in ("binary", "model", "prompt")},
                "ggml": {str(tmp_path / "libggml.so"): files["libggml.so"]["sha256"]},
                "grant": {"id": "grant-1", "regions": "mi210_0,184-191", "stopfile": str(tmp_path / "STOP")}, "request_count": 2, "request_sha256": ['0'*64,'1'*64], "vram_limit_bytes": 100}
    watcher = capture / 'watch-result.json'
    watcher.write_text(json.dumps({'status':'closed','reason':'none','rc':0,'containment_empty':True}))
    expected['watch_result_path'] = str(watcher)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"schema": "epyc.m4.gpu.plan.v2", "cells": {"c": expected}}))
    trust = Trust(capture, plan, digest(plan.read_bytes()), ((tmp_path / "producer.py", files["producer.py"]["sha256"]),))
    doc = {k: copy.deepcopy(expected[k]) for k in ("role", "arm", "source_commit", "model", "recipe", "argv", "environment", "device", "np", "grant")}
    doc.update({"schema": "epyc.m4.gpu.capture.v2", "plan_cell": "c", "plan_sha256": trust.plan_sha256,
                "mapped_ggml": expected["ggml"], "process": {"pid": 123, "start_ticks": 45},
                "cleanup": {"owned_pid_dead": True, "start_ticks": 45}, "request_start_ns": 10,
                "request_end_ns": 20, "residency": [{"pid": 123, "device": "mi210_0", "timestamp_ns": 15,
                 "own_vram_bytes": 10, "device_vram_bytes": 20, "kfd_process_count": 1}],
                "requests_path": str(requests), "requests_sha256": digest(requests.read_bytes()),
                "aggregate_decode_tps": 20.0, "measurement_id": "m4_gpu_fixture", "date": "2026-11-02"})
    receipt = capture / 'grant.txt'
    receipt.write_text('regions=mi210_0,184-191 start=1970-01-01T00:00Z end=1970-01-01T00:01Z holds=gpu-quiet,q3')
    doc['grant_receipt_path'] = str(receipt)
    doc['grant_receipt_sha256'] = digest(receipt.read_bytes())
    path = capture / "capture.json"
    path.write_text(json.dumps(doc))
    return path, trust, doc


def test_valid_capture_replays_and_projects(tmp_path):
    path, trust, _ = setup_capture(tmp_path)
    assert validate_capture(path, trust)[2] == 20.0
    assert project(path, trust).value == 20.0


@pytest.mark.parametrize("field,value", [
    ("request_start_ns", 16), ("device", "wrong"), ("cleanup", {}),
    ("aggregate_decode_tps", 21), ("arm", "BASELINE"), ("plan_sha256", "0" * 64),
    ("mapped_ggml", {}), ("grant", "other"), ("requests_path", "/etc/passwd"),
])
def test_capture_mutations_are_rejected(tmp_path, field, value):
    path, trust, doc = setup_capture(tmp_path)
    doc[field] = value
    path.write_text(json.dumps(doc))
    with pytest.raises(ProjectionError):
        validate_capture(path, trust)


@pytest.mark.parametrize("name", ["model", "binary", "prompt", "libggml.so", "producer.py", "plan.json"])
def test_independent_seal_changes_are_rejected(tmp_path, name):
    path, trust, _ = setup_capture(tmp_path)
    (tmp_path / name).write_text("tampered")
    with pytest.raises(ProjectionError):
        validate_capture(path, trust)


def test_partial_or_unreadable_request_refuses(tmp_path):
    path, trust, doc = setup_capture(tmp_path)
    requests = Path(doc["requests_path"])
    requests.write_text('{"success":false}\n')
    doc["requests_sha256"] = digest(requests.read_bytes())
    path.write_text(json.dumps(doc))
    with pytest.raises(ProjectionError):
        validate_capture(path, trust)


def test_write_side_preflight_and_emission(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed'))
    import enrollment
    import write_capture
    path, original, doc = setup_capture(tmp_path)
    plan = json.loads(original.plan_path.read_text())
    cell = plan['cells']['c']
    import importlib.util
    native_path = Path(__file__).resolve().parents[2]/'scripts/benchmark/m4_gpu_speed/server_np_sweep.py'
    native_spec = importlib.util.spec_from_file_location('m4_command_fixture', native_path)
    native = importlib.util.module_from_spec(native_spec); sys.modules[native_spec.name] = native
    native_spec.loader.exec_module(native)
    command = native.build_server_command(binary=Path(cell['files']['binary']['path']),
        model=native.ModelSpec('fixture',Path(cell['model'])), port=18070, np_level=2, threads=2,
        context_size=65536, ubatch_size=512, kv_type='q8_0', flash_attn=True, jinja=True, mlock=False,
        extra_args=['--prefill-order','srpf','--prefill-contend-cap','512'])
    env = {'OMP_PROC_BIND':'spread', 'OMP_PLACES':'cores', 'OMP_WAIT_POLICY':'active', 'OMP_DYNAMIC':'false',
           'KMP_BLOCKTIME':'10', 'LD_LIBRARY_PATH':'/tmp/image'}
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership'))
    import owned
    assert owned.resolve_argv(command)[0] == '/usr/bin/numactl'
    cell['argv'], cell['environment'] = command, env
    original.plan_path.write_text(json.dumps(plan))
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')
    end_dt = (now + timedelta(minutes=3)).replace(second=0, microsecond=0)
    grantdir = tmp_path / 'grants'; grantdir.mkdir()
    (grantdir / 'grant-1.grant').write_text(f'regions=mi210_0,184-191 start={start} end={end_dt.strftime("%Y-%m-%dT%H:%MZ")} holds=gpu-quiet,q3')
    env.update({'FILLER_ID':'grant-1', 'FILLER_NEEDGPU':'1', 'FILLER_END':str(int(end_dt.timestamp())),
                'FILLER_DEADLINE':str(int(end_dt.timestamp())-1), 'FILLER_STOPFILE':str(tmp_path / 'STOP')})
    monkeypatch.setattr(enrollment, 'GRANTS_DIR', str(grantdir))
    monkeypatch.setattr(enrollment, 'HOLD_DIR', str(tmp_path))
    monkeypatch.setattr(enrollment, 'EXECUTION_ENABLED', True)
    monkeypatch.setattr(enrollment, 'CAPTURE_ROOT', str(original.capture_root))
    monkeypatch.setattr(enrollment, 'PLAN_PATH', str(original.plan_path))
    monkeypatch.setattr(enrollment, 'PLAN_SHA256', digest(original.plan_path.read_bytes()))
    root = Path(__file__).resolve().parents[2]
    needed = [root/'scripts/benchmark/m4_gpu_speed'/x for x in ('launcher.py','server_np_sweep.py','write_capture.py')]
    needed += [root/'scripts/vidya/adapters/m4_gpu_speed_v2.py']
    needed += [root/'scripts/benchmark/m4_cpu_ownership'/x for x in ('watch.py','owned.py','m4_cgroup_guard.py')]
    monkeypatch.setattr(enrollment, 'SOURCE_SEALS', tuple((str(p), digest(p.read_bytes())) for p in needed))
    trust, bound, grant_bytes = write_capture.preflight('c', command, env, Path(cell['model']), 2, Path(cell['files']['prompt']['path']))
    now_ns = time.time_ns()
    doc['residency'][0]['timestamp_ns'] = now_ns
    output = path.parent / 'writer-output.json'
    row = {'request_batch_start_ns':now_ns - 1, 'request_batch_end_ns':now_ns + 1, 'gpu_residency_during':doc['residency'],
           'aggregate_decode_tps':20.0, 'timestamp':'2026-11-02T00:00:00Z'}
    write_capture.write(trust=trust, cell=bound, key='c', row=row, requests_path=Path(doc['requests_path']),
                        output_path=output, process=doc['process'], mapped=doc['mapped_ggml'], cleanup=doc['cleanup'], grant_bytes=grant_bytes, env=env)
    assert validate_capture(output, trust)[2] == 20.0
    with pytest.raises(ProjectionError):
        write_capture.preflight('c', command, {**env, 'LLAMA_ARG_PREFILL_ORDER':'srpf'}, Path(cell['model']), 2, Path(cell['files']['prompt']['path']))
    with pytest.raises(ProjectionError, match='unbound runtime override'):
        write_capture.preflight('c', command, {**env, 'LD_PRELOAD':'/tmp/evil.so'}, Path(cell['model']), 2, Path(cell['files']['prompt']['path']))
    with pytest.raises(FileExistsError):
        write_capture.write(trust=trust, cell=bound, key='c', row=row, requests_path=Path(doc['requests_path']),
                            output_path=output, process=doc['process'], mapped=doc['mapped_ggml'], cleanup=doc['cleanup'], grant_bytes=grant_bytes, env=env)
    monkeypatch.setattr(enrollment, 'HOLD_DIR', str(tmp_path/'absent-holds'))
    with pytest.raises(ProjectionError, match='actual grant refusal'):
        write_capture.grant_proof(bound, env)
    monkeypatch.setattr(enrollment, 'HOLD_DIR', str(tmp_path))
    (tmp_path / 'STOP').touch()
    with pytest.raises(ProjectionError, match='actual grant refusal'):
        write_capture.grant_proof(bound, env)
    (tmp_path / 'STOP').unlink()
    (grantdir / 'grant-1.grant').unlink()
    with pytest.raises(ProjectionError, match='actual grant refusal'):
        write_capture.grant_proof(bound, env)
    bad_command = command + ['--prefill-order=srpf']
    plan['cells']['c']['argv'] = bad_command
    original.plan_path.write_text(json.dumps(plan))
    monkeypatch.setattr(enrollment, 'PLAN_SHA256', digest(original.plan_path.read_bytes()))
    with pytest.raises(ProjectionError, match='candidate treatment'):
        write_capture.preflight('c', bad_command, env, Path(cell['model']), 2, Path(cell['files']['prompt']['path']))
    bad_draft = command + ['-md', '/tmp/unsealed-draft']
    plan['cells']['c']['argv'] = bad_draft
    original.plan_path.write_text(json.dumps(plan))
    monkeypatch.setattr(enrollment, 'PLAN_SHA256', digest(original.plan_path.read_bytes()))
    with pytest.raises(ProjectionError, match='auxiliary model'):
        write_capture.preflight('c', bad_draft, env, Path(cell['model']), 2, Path(cell['files']['prompt']['path']))


def test_unenrolled_source_refuses_before_launch(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed'))
    import enrollment
    import write_capture
    monkeypatch.setattr(enrollment, 'PLAN_SHA256', '')
    with pytest.raises(ProjectionError, match='enrollment absent'):
        write_capture.enrolled()


@pytest.mark.parametrize('receipt', [None, {'status':'closed','reason':'STOP','rc':0,'containment_empty':True},
                                    {'status':'closed','reason':'none','rc':0,'containment_empty':False}])
def test_unfinished_or_interrupted_guardian_refuses(tmp_path, receipt):
    path, trust, _ = setup_capture(tmp_path)
    watch = path.parent / 'watch-result.json'
    if receipt is None:
        watch.unlink()
    else:
        watch.write_text(json.dumps(receipt))
    with pytest.raises(ProjectionError):
        validate_capture(path, trust)


@pytest.mark.parametrize("cutoff", [False, True])
def test_actual_launcher_guarded_help_without_model(tmp_path, monkeypatch, cutoff):
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership'))
    import enrollment
    import launcher
    import m4_cgroup_guard
    path, original, _ = setup_capture(tmp_path)
    plan = json.loads(original.plan_path.read_text())
    watch_dir = path.parent / 'watch'; watch_dir.mkdir()
    plan['cells']['c']['watch_result_path'] = str(watch_dir / 'watch-result.json')
    original.plan_path.write_text(json.dumps(plan))
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')
    end_dt = (now + timedelta(minutes=3)).replace(second=0, microsecond=0)
    grant_dir = tmp_path / 'grants'; grant_dir.mkdir()
    (grant_dir / 'grant-1.grant').write_text(f'regions=mi210_0,184-191 start={start} end={end_dt.strftime("%Y-%m-%dT%H:%MZ")} holds=gpu-quiet,q3')
    root = Path(__file__).resolve().parents[2]
    needed = [root/'scripts/benchmark/m4_gpu_speed'/x for x in ('launcher.py','server_np_sweep.py','write_capture.py')]
    needed += [root/'scripts/vidya/adapters/m4_gpu_speed_v2.py']
    needed += [root/'scripts/benchmark/m4_cpu_ownership'/x for x in ('watch.py','owned.py','m4_cgroup_guard.py')]
    for name, value in {'CAPTURE_ROOT':str(original.capture_root),'PLAN_PATH':str(original.plan_path),
                        'PLAN_SHA256':digest(original.plan_path.read_bytes()),'EXECUTION_ENABLED':True,
                        'SOURCE_SEALS':tuple((str(p),digest(p.read_bytes())) for p in needed),
                        'GRANTS_DIR':str(grant_dir),'HOLD_DIR':str(tmp_path)}.items():
        monkeypatch.setattr(enrollment, name, value)
    # The launcher refuses any Python execution override (that guard is the point of the test).
    # CI exports PYTHONPATH for the whole pytest step, so the test must run the launcher in the
    # clean environment production gives it -- sys.path is already populated in-process.
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT'): monkeypatch.delenv(name, raising=False)
    values = {'M4_PLAN_CELL':'c','FILLER_ID':'grant-1','FILLER_NEEDGPU':'1',
              'FILLER_END':str(int(end_dt.timestamp())), 'FILLER_DEADLINE':str(int(end_dt.timestamp())-1),
              'FILLER_STOPFILE':str(tmp_path/'STOP'), 'M4_WATCH_DIR':str(watch_dir),
              'M4_DELEGATED_CGROUP_PARENT':'/sys/fs/cgroup'}
    for name,value in values.items(): monkeypatch.setenv(name,value)
    if cutoff:
        import threading
        fifo = tmp_path / 'blocked-prompt'
        os.mkfifo(fifo)
        def cut():
            deadline = time.monotonic() + 5
            while not (watch_dir/'supervisor.json').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            time.sleep(0.25)
            (tmp_path/'STOP').touch()
        thread = threading.Thread(target=cut); thread.start()
        monkeypatch.setattr(sys, 'argv', ['launcher.py','--skip-clean-check','--model',f'fake={tmp_path / "model"}',
                                         '--llama-server','/bin/true','--question-pool',str(fifo)])
        assert launcher.main() == 124
        thread.join(timeout=5)
        assert json.loads((watch_dir/'watch-result.json').read_text())['reason'] == 'STOP'
    else:
        monkeypatch.setattr(sys, 'argv', ['launcher.py','--help'])
        assert launcher.main() == 0
    assert json.loads((watch_dir/'watch-result.json').read_text())['containment_empty'] is True
    assert not list(path.parent.glob('capture-v2*'))
    if not cutoff:
        with pytest.raises(RuntimeError, match='fresh attempt'):
            launcher.main()


@pytest.mark.parametrize("name", ['PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT'])
def test_launcher_refuses_python_execution_override(monkeypatch, name):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership'))
    import launcher
    monkeypatch.setenv(name, '/somewhere')
    with pytest.raises(RuntimeError, match='unbound Python execution override'):
        launcher.main()


def test_native_request_batch_fake_http_and_partial_records(tmp_path):
    import importlib.util
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    source = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed/server_np_sweep.py'
    spec = importlib.util.spec_from_file_location('m4_native_fixture', source)
    native = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = native
    spec.loader.exec_module(native)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            content = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if content['prompt'] == 'bad':
                self.send_response(503); self.end_headers(); return
            payload = json.dumps({'stop': True, 'timings': {'predicted_n':10, 'predicted_ms':1000, 'prompt_n':5}}).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever); thread.start()
    try:
        prompts = [native.PromptSpec('a', 'fake', 1, 'good'), native.PromptSpec('b', 'fake', 1, 'bad')]
        model = native.ModelSpec('fake', tmp_path/'fake')
        results, _ = native.run_prompt_batch(port=server.server_port, model=model, np_level=2, prompts=prompts,
                                              n_predict=10, request_timeout_s=2, requests_path=tmp_path/'raw.jsonl')
        raw = [json.loads(line) for line in (tmp_path/'raw.jsonl').read_text().splitlines()]
        assert len(raw) == 2 and sum(r['success'] for r in raw) == 1
        assert {r['http_status'] for r in raw} == {200, 503}
        assert sorted(x['request_index'] for x in raw) == [0, 1]
        assert [x.success for x in results] == [True, False]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


@pytest.mark.parametrize('partial', [False, True])
def test_native_cell_fake_http_kfd_and_partial_fail_closed(tmp_path, monkeypatch, partial):
    """Exercise actual run_cell and V2 writer with explicitly synthetic hardware."""
    import importlib.util
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from types import SimpleNamespace
    source = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed/server_np_sweep.py'
    sys.path.insert(0, str(source.parent))
    import write_capture
    spec = importlib.util.spec_from_file_location('m4_native_cell_fixture', source)
    native = importlib.util.module_from_spec(spec); sys.modules[spec.name] = native; spec.loader.exec_module(native)
    _, original, doc = setup_capture(tmp_path)
    plan = json.loads(original.plan_path.read_text()); cell = plan['cells']['c']
    device_vram = original.capture_root/'device-vram'; device_vram.write_text('20')
    kfd = original.capture_root/'kfd'; (kfd/'123').mkdir(parents=True)
    (kfd/'123'/'vram_0').write_text('10')
    maps_file = original.capture_root/'fixture-maps'
    maps_file.write_text('0-1 r-xp 0 00:00 0 ' + str(tmp_path/'libggml.so'))
    cell['kfd_vram_file'] = 'vram_0'; cell['device_vram_path'] = str(device_vram)
    cell['fixture_kfd_root'] = str(kfd); cell['fixture_maps_path'] = str(maps_file)
    cell['request_sha256'] = [digest(json.dumps({'prompt': p, 'n_predict': 10, 'temperature': 0.0, 'cache_prompt': False, 'stream': False}).encode()) for p in ('good','bad')]
    original.plan_path.write_text(json.dumps(plan))
    trust = Trust(original.capture_root, original.plan_path, digest(original.plan_path.read_bytes()), original.sources, qualification_only=True)
    now = datetime.now(timezone.utc)
    start = (now-timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')
    end = (now+timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%MZ')
    grant = f'regions=mi210_0,184-191 start={start} end={end} holds=q3,gpu-quiet schema=epyc.rowflow.dryrun-grant.v1 id=grant-1 kind=rowflow-dryrun'.encode()
    monkeypatch.setenv('M4_PLAN_CELL', 'c')
    monkeypatch.setattr(write_capture, 'preflight', lambda *args: (trust, cell, grant))
    monkeypatch.setattr(write_capture, 'grant_proof', lambda *args: grant)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            content = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            time.sleep(1.15)
            if partial and content['prompt'] == 'bad':
                self.send_response(503); self.end_headers(); return
            payload = json.dumps({'stop': True, 'timings': {'predicted_n':10, 'predicted_ms':1000, 'prompt_n':5}}).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever); thread.start()
    proc = SimpleNamespace(pid=123)
    monkeypatch.setattr(native, 'start_server', lambda *a: proc)
    monkeypatch.setattr(native, 'wait_for_health', lambda *a: None)
    monkeypatch.setattr(native, 'stop_server', lambda *a: {'ps_verified_dead':True})
    monkeypatch.setattr(native.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='pid=123,'))
    original_read = Path.read_text; original_iter = Path.iterdir
    def fixture_read(path, *args, **kwargs):
        if str(path) == '/proc/123/stat':
            return '123 (fake) ' + ' '.join(['S'] + ['0'] * 18 + ['45'])
        if str(path) == '/proc/123/maps':
            return '0-1 r-xp 0 00:00 0 ' + str(tmp_path/'libggml.so')
        if str(path) == '/sys/class/kfd/kfd/proc/123/vram_0':
            return '10'
        return original_read(path, *args, **kwargs)
    def fixture_iter(path):
        if str(path) == '/sys/class/kfd/kfd/proc':
            return iter([Path('/synthetic-kfd-process')])
        return original_iter(path)
    monkeypatch.setattr(Path, 'read_text', fixture_read)
    monkeypatch.setattr(Path, 'iterdir', fixture_iter)
    out = original.capture_root/'run'; out.mkdir()
    args = SimpleNamespace(port_base=server.server_port, llama_server=tmp_path/'binary', threads=2,
        context_size=65536, ubatch_size=512, kv_type='q8_0', no_flash_attn=False, no_jinja=False,
        no_mlock=True, extra_server_arg=[], dry_run=False, startup_timeout=2, warmup_prompts=0,
        warmup_n_predict=4, request_timeout=3, measure_ttft=False, n_predict=10, question_pool=tmp_path/'prompt')
    prompts = [native.PromptSpec('a','fake',1,'good'), native.PromptSpec('b','fake',1,'bad')]
    try:
        if not partial:
            live_trust = Trust(trust.capture_root, trust.plan_path, trust.plan_sha256, trust.sources)
            monkeypatch.setattr(write_capture, 'preflight', lambda *args: (live_trust, cell, grant))
            with pytest.raises(RuntimeError, match='synthetic hardware'):
                native.run_cell(model=native.ModelSpec('fake',tmp_path/'model'), np_level=2, prompts=prompts,
                                args=args, output_dir=out, cell_index=0)
            monkeypatch.setattr(write_capture, 'preflight', lambda *args: (trust, cell, grant))
        if partial:
            with pytest.raises(ProjectionError, match='invalid or incomplete request'):
                native.run_cell(model=native.ModelSpec('fake',tmp_path/'model'), np_level=2, prompts=prompts,
                                args=args, output_dir=out, cell_index=0)
            records = [json.loads(x) for x in (out/'requests.jsonl').read_text().splitlines()]
            assert len(records) == 2 and sum(x['success'] for x in records) == 1
            with pytest.raises(ProjectionError):
                validate_capture(out/'capture-v2-0.json', trust)
        else:
            row = native.run_cell(model=native.ModelSpec('fake',tmp_path/'model'), np_level=2, prompts=prompts,
                                  args=args, output_dir=out, cell_index=0)
            assert row['aggregate_decode_tps'] == 20
            assert validate_capture(out/'capture-v2-0.json', trust)[2] == 20
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_qualification_only_never_projects(tmp_path):
    path, trusted, _ = setup_capture(tmp_path)
    fixture_trust = Trust(trusted.capture_root, trusted.plan_path, trusted.plan_sha256, trusted.sources, qualification_only=True)
    doc = json.loads(path.read_text())
    receipt = Path(doc['grant_receipt_path'])
    receipt.write_text(receipt.read_text() + ' schema=epyc.rowflow.dryrun-grant.v1 id=grant-1 kind=rowflow-dryrun')
    doc['grant_receipt_sha256'] = digest(receipt.read_bytes())
    path.write_text(json.dumps(doc))
    assert validate_capture(path, fixture_trust)[2] == 20
    with pytest.raises(ProjectionError, match='qualification-only'):
        project(path, fixture_trust)


def test_dry_run_does_not_fallback_to_live_enrollment(monkeypatch):
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed'))
    import enrollment
    import write_capture
    monkeypatch.setenv('FILLER_DRYRUN', '1')
    monkeypatch.setattr(enrollment, 'EXECUTION_ENABLED', True)
    monkeypatch.setattr(enrollment, 'DRYRUN_PLAN_SHA256', '')
    with pytest.raises(ProjectionError, match='enrollment absent'):
        write_capture.enrolled()
    with pytest.raises(ProjectionError, match='dry-run grant authority absent'):
        write_capture.grant_directories(os.environ)


def test_rowflow_fixture_grant_is_separate_from_live():
    from m4_gpu_speed_v2 import parse_grant
    identity = {'id':'unit', 'regions':'mi210_0,184-191'}
    raw = b'regions=mi210_0,184-191 start=2026-11-02T12:00Z end=2026-11-02T13:00Z holds=gpu-quiet,q3 schema=epyc.rowflow.dryrun-grant.v1 id=unit kind=rowflow-dryrun'
    assert parse_grant(raw, identity, qualification=True)[1] > parse_grant(raw, identity, qualification=True)[0]
    with pytest.raises(ProjectionError):
        parse_grant(raw, identity, qualification=False)
    with pytest.raises(ProjectionError):
        parse_grant(raw.replace(b'id=unit', b'id=other'), identity, qualification=True)
    with pytest.raises(ProjectionError):
        parse_grant(raw + b' id=unit', identity, qualification=True)
    live = b'regions=mi210_0,184-191 start=2026-11-02T12:00Z end=2026-11-02T13:00Z holds=gpu-quiet,q3'
    assert parse_grant(live, identity, qualification=False)[1] > parse_grant(live, identity, qualification=False)[0]
    with pytest.raises(ProjectionError):
        parse_grant(live.replace(b'gpu-quiet', b'q0'), identity, qualification=False)


@pytest.mark.parametrize('field', ['request', 'timing', 'stop'])
def test_raw_request_or_response_tampering_is_rejected(tmp_path, field):
    path, trust, doc = setup_capture(tmp_path)
    requests = Path(doc['requests_path'])
    rows = [json.loads(x) for x in requests.read_text().splitlines()]
    if field == 'request': rows[0]['request_sha256'] = 'f' * 64
    elif field == 'timing': rows[0]['response']['timings']['predicted_ms'] = 42
    else: rows[0]['response']['stop'] = False
    requests.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    doc['requests_sha256'] = digest(requests.read_bytes())
    path.write_text(json.dumps(doc))
    with pytest.raises(ProjectionError):
        validate_capture(path, trust)


def test_qualification_real_device_path_and_fixture_separation(tmp_path):
    import importlib.util
    from types import SimpleNamespace
    source = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed/server_np_sweep.py'
    spec = importlib.util.spec_from_file_location('m4_qual_device_fixture', source)
    native = importlib.util.module_from_spec(spec); sys.modules[spec.name] = native; spec.loader.exec_module(native)
    root=tmp_path/'capture'; root.mkdir()
    fixture_kfd=root/'kfd'; fixture_kfd.mkdir()
    fixture_maps=root/'maps';fixture_maps.write_text('fixture')
    fixture_dev=root/'device';fixture_dev.write_text('100')
    qual=SimpleNamespace(qualification_only=True,capture_root=root)
    live=SimpleNamespace(qualification_only=False,capture_root=root)
    cell={'fixture_kfd_root':str(fixture_kfd),'fixture_maps_path':str(fixture_maps),'device_vram_path':str(fixture_dev)}
    assert native.residency_paths(qual,cell)==(fixture_kfd,fixture_maps,fixture_dev)
    with pytest.raises(RuntimeError, match='live synthetic'):
        native.residency_paths(live,cell)
    with pytest.raises(RuntimeError, match='partial'):
        native.residency_paths(qual,{k:v for k,v in cell.items() if k!='fixture_maps_path'})
    with pytest.raises(RuntimeError, match='non-sysfs'):
        native.residency_paths(qual,{'device_vram_path':str(fixture_dev)})
    sysfs=Path('/sys/class/drm/card2/device/mem_info_vram_used')
    if sysfs.exists():
        assert native.residency_paths(qual,{'device_vram_path':str(sysfs)}) == (Path('/sys/class/kfd/kfd/proc'),None,sysfs)
        assert native.residency_paths(live,{'device_vram_path':str(sysfs)}) == (Path('/sys/class/kfd/kfd/proc'),None,sysfs)


def test_prehashed_custody_binds_content_receipt_and_file_identity(tmp_path):
    import importlib.util
    from m4_gpu_speed_v2 import verify_plan_file
    source = Path(__file__).resolve().parents[2] / 'scripts/champion/m4/prehash_custody.py'
    spec = importlib.util.spec_from_file_location('m4_prehash_fixture', source)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    model=tmp_path/'model.gguf';model.write_bytes(b'fixture model')
    evidence=mod.receipt(model); out=tmp_path/'receipt.json';out.write_text(json.dumps(evidence,sort_keys=True))
    item={'path':str(model),'sha256':evidence['sha256'],'custody':{'path':str(out),'sha256':digest(out.read_bytes())}}
    verify_plan_file(item)
    model.write_bytes(b'changed bytes')
    # Same inode and same size (13 bytes): identity differs only by mtime/ctime, and two writes
    # inside one coarse filesystem timestamp tick can leave them equal -- a flake, not a defect
    # (custody assumes an immutable file). Force a distinct mtime so the mutation is observable.
    stamp = model.stat().st_mtime_ns + 2_000_000_000
    os.utime(model, ns=(stamp, stamp))
    with pytest.raises(ProjectionError, match='custody mismatch'):
        verify_plan_file(item)
    out.write_text('{}')
    with pytest.raises(ProjectionError, match='receipt changed'):
        verify_plan_file(item)


def test_residency_sampler_cadence_fits_subsecond_batches():
    src_path = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_gpu_speed/server_np_sweep.py'
    src = src_path.read_text()
    assert 'sample_stop.wait(RESIDENCY_SAMPLE_INTERVAL_S)' in src and 'sample_stop.wait(1.0)' not in src
    import re
    assert float(re.search(r'RESIDENCY_SAMPLE_INTERVAL_S = ([0-9.]+)', src).group(1)) <= 0.25
