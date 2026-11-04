"""fold_entry / fold_verdict: derivation, refusal paths and verdict math. No servers."""
import calendar
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fg = load('fold_gate', 'scripts/champion/m4/fold_gate.py')
fe = load('fold_entry', 'scripts/champion/m4/fold_entry.py')
fv = load('fold_verdict', 'scripts/champion/m4/fold_verdict.py')


def h(b):
    return hashlib.sha256(b).hexdigest()


def sh(*a, cwd):
    return subprocess.check_output(a, cwd=cwd, text=True).strip()


def image(root, source, knob, gpu=False):
    (root / 'bin').mkdir(parents=True)
    files = {'bin/llama-server': b'server' + source.encode(), 'bin/libllama-common.so': b'common' + (b' srpf' if knob else b''),
             'bin/libggml-cpu.so': b'ggml'}
    if gpu:
        files['bin/libggml-hip.so'] = b'hip'
    for rel, data in files.items():
        (root / rel).write_bytes(data)
    (root / 'SHA256SUMS').write_text(''.join(f'{h(d)}  {r}\n' for r, d in files.items()))
    (root / 'BUILD_COMPLETE').write_text(f'BUILD_COMPLETE source={source}\n')


@pytest.fixture
def world(tmp_path):
    tree = tmp_path / 'tree'
    tree.mkdir()
    sh('git', 'init', '-q', cwd=tree)
    for n in ('champ', 'm4'):
        (tree / n).write_text(n)
        sh('git', 'add', n, cwd=tree)
        sh('git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', n, cwd=tree)
    cand = sh('git', 'rev-parse', 'HEAD', cwd=tree)
    champ = sh('git', 'rev-parse', 'HEAD^', cwd=tree)
    sh('git', 'branch', 'champion', champ, cwd=tree)
    for b in ('cpu', 'gpu'):
        image(tmp_path / f'{b}-base', champ, False, b == 'gpu')
        image(tmp_path / f'{b}-cand', cand, True, b == 'gpu')
    for n in ('m.gguf', 'd.gguf', 'g.gguf'):
        (tmp_path / n).write_bytes(n.encode())
    pool = tmp_path / 'pool.jsonl'
    pool.write_bytes(b'{"id":"q1","prompt":"hi","tier":1}\n')
    (tmp_path / 'AUTH.md').write_text('ratified')
    rule = tmp_path / 'rule.json'
    rule.write_text(json.dumps({'schema': fg.RULE_SCHEMA, 'authority': str(tmp_path / 'AUTH.md'),
                                'authority_sha256': h(b'ratified'), 'metric_direction': 'higher',
                                'cpu': {'pass_ratio': 1.0, 'fail_ratio': 0.94},
                                'gpu': {'pass_ratio': 1.0, 'fail_ratio': 0.95},
                                'quality': {'check': 'greedy_token_identity'}}))
    entry = [sys.executable, str(ROOT / 'scripts/champion/m4/fold_entry.py'), '{plan}', '{cell}', '{out}']
    s = {'schema': fg.SPEC_SCHEMA, 'llama_tree': str(tree), 'champion_ref': 'champion',
         'champion': champ, 'candidate': cand,
         'images': {b: {'baseline': str(tmp_path / f'{b}-base'), 'candidate': str(tmp_path / f'{b}-cand')}
                    for b in ('cpu', 'gpu')},
         'knob_probe': {'file': 'bin/libllama-common.so', 'needle': 'srpf'},
         'roles': [
             {'role': 'arch', 'backend': 'cpu', 'model': str(tmp_path / 'm.gguf'), 'model_sha256': h(b'm.gguf'),
              'aux_models': [str(tmp_path / 'd.gguf')], 'aux_sha256': {str(tmp_path / 'd.gguf'): h(b'd.gguf')},
              'recipe_authority': 'x', 'server_args': ['-m', str(tmp_path / 'm.gguf'), '-np', '1', '-t', '48',
                                                       '-md', str(tmp_path / 'd.gguf')],
              'env': {'GGML_FUSED_DECODE_OFF': '1'},
              'placement': {'cpus': '0-95', 'numactl': '--interleave=all', 'device': 'none'}},
             {'role': 'critic', 'backend': 'gpu', 'model': str(tmp_path / 'g.gguf'), 'model_sha256': h(b'g.gguf'),
              'recipe_authority': 'x', 'server_args': ['-m', str(tmp_path / 'g.gguf'), '-np', '4', '-ngl', '99'],
              'env': {'OMP_PROC_BIND': 'spread'},
              'placement': {'cpus': '184-191', 'numactl': '--interleave=all', 'device': 'mi210_0'}}],
         'prompt_pool': {'path': str(pool), 'sha256': h(pool.read_bytes())},
         'decision_rule': str(rule), 'entries': {'cpu': entry, 'gpu': entry}, 'pairs': 2,
         'result_root': str(tmp_path / 'results')}
    return tmp_path, s


def write_plan(t, s, name='plan'):
    p = fg.bind(s, env={})
    p['plan_sha256'] = fg.plan_digest(p)
    d = t / name
    d.mkdir()
    (d / 'FOLD-PLAN.json').write_text(json.dumps(p, indent=2, sort_keys=True))
    return d / 'FOLD-PLAN.json', p


def test_entries_bind_to_bound(world):
    t, s = world
    _, p = write_plan(t, s)
    assert p['status'] == 'BOUND', p['errors'] + p['needs']
    assert len(p['cells']) == 8 and all(c['entry'][-3:] == ['{plan}', '{cell}', '{out}'] for c in p['cells'])


def test_derive_cpu_cell(world):
    t, s = world
    _, p = write_plan(t, s)
    cp = fe.derive_cell(p, 'arch.p1.candidate')
    assert cp['backend'] == 'cpu' and cp['arm'] == 'candidate' and cp['pair'] == 1 and cp['position'] == 0
    assert cp['binary'] == str(t / 'cpu-cand/bin/llama-server')
    assert cp['ld_library_path'] == str(t / 'cpu-cand/bin')
    assert cp['server_args'][-2:] == ['--prefill-order', 'srpf'] and cp['np'] == 1
    assert cp['models'] == {str(t / 'm.gguf'): h(b'm.gguf'), str(t / 'd.gguf'): h(b'd.gguf')}
    assert cp['device'] is None and cp['source_commit'] == p['candidate']
    argv = fe.server_command(cp, 18000)
    assert argv[:7] == ['numactl', '--interleave=all', '--', 'taskset', '-c', '0-95', cp['binary']]
    assert argv[-6:] == ['--host', '127.0.0.1', '--port', '18000', '--log-colors', 'off']
    env = fe.server_env(cp, {'PATH': '/bin', 'LD_LIBRARY_PATH': '/other', 'GGML_X': '1'})
    assert env == {'PATH': '/bin', 'LD_LIBRARY_PATH': str(t / 'cpu-cand/bin'), 'GGML_FUSED_DECODE_OFF': '1'}


def test_derive_gpu_cell(world):
    t, s = world
    _, p = write_plan(t, s)
    cp = fe.derive_cell(p, 'critic.p0.baseline')
    assert cp['backend'] == 'gpu'
    assert '--prefill-order' not in cp['server_args'] and cp['np'] == 4
    assert cp['ld_library_path'] == f'{t}/gpu-base/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib'
    assert cp['device']['kfd_vram_file'] == 'vram_57300'
    assert fe.server_command(cp, 1)[5] == '184-191'


@pytest.mark.parametrize('mutate,needle', [
    (lambda p: p.update(status='DESCRIPTIVE_ONLY'), 'seal broken'),
    (lambda p: (p.update(status='DESCRIPTIVE_ONLY'), p.update(plan_sha256=fg.plan_digest(p))), 'not BOUND'),
])
def test_plan_refusals(world, mutate, needle):
    t, s = world
    path, p = write_plan(t, s)
    mutate(p)
    path.write_text(json.dumps(p))
    with pytest.raises(fe.Refused, match=needle):
        fe.load_plan(path)


def test_live_tamper_and_unknown_cell(world):
    t, s = world
    path, p = write_plan(t, s)
    with pytest.raises(fe.Refused, match='not in plan'):
        fe.derive_cell(p, 'nope.p0.baseline')
    (t / 'g.gguf').write_bytes(b'other')
    with pytest.raises(fe.Refused, match='model changed'):
        fe.load_plan(path)


def test_derive_refuses_entry_owned_args(world):
    t, s = world
    s['roles'][0]['server_args'] += ['--port', '9']
    _, p = write_plan(t, s)
    with pytest.raises(fe.Refused, match='--port'):
        fe.derive_cell(p, 'arch.p0.baseline')


def grant_env(t, regions='q0,q1,q2,q3', holds='q0,q1,q2,q3', cpus='0-95,184-191', gpu='1'):
    flags = t / 'flags'
    (flags / 'grants').mkdir(parents=True, exist_ok=True)
    now = time.time()
    fmt = lambda e: time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(e))
    (flags / 'grants/row.grant').write_text(f'regions={regions} start={fmt(now - 120)} end={fmt(now + 7200)}'
                                            + (f' holds={holds}' if holds else ''))
    end = calendar.timegm(time.strptime(fmt(now + 7200), '%Y-%m-%dT%H:%MZ'))
    return {'FILLER_ID': 'row', 'FILLER_DEADLINE': str(end - 90), 'FILLER_END': str(end),
            'FILLER_STOPFILE': str(t / 'STOP'), 'FILLER_CPUS': cpus, 'FILLER_PORTS': '18800',
            'FILLER_NEEDGPU': gpu, 'FILLER_FLAGS_DIR': str(flags)}


def test_runtime_ok_and_refusals(world, monkeypatch):
    t, s = world
    _, p = write_plan(t, s)
    monkeypatch.setattr(fe.os, 'sched_getaffinity', lambda pid: set(range(192)))
    cpu, gpu = fe.derive_cell(p, 'arch.p0.baseline'), fe.derive_cell(p, 'critic.p0.baseline')
    env = grant_env(t)
    rt = fe.runtime(env, cpu)
    assert rt['port'] == 18800 and rt['grant'].endswith('grants/row.grant')
    assert fe.runtime(env, gpu)['row_id'] == 'row'
    with pytest.raises(fe.Refused, match='FILLER_DEADLINE,FILLER_END'):
        fe.runtime({k: v for k, v in env.items() if k not in ('FILLER_DEADLINE', 'FILLER_END')}, cpu)
    with pytest.raises(fe.Refused, match='contract missing'):
        fe.runtime({}, cpu)
    with pytest.raises(fe.Refused, match='FILLER_NEEDGPU'):
        fe.runtime(dict(env, FILLER_NEEDGPU='0'), gpu)
    with pytest.raises(fe.Refused, match='outside granted'):
        fe.runtime(dict(env, FILLER_CPUS='0-47'), cpu)
    with pytest.raises(fe.Refused, match='DRYRUN_DIR'):
        fe.runtime(dict(env, FILLER_DRYRUN='1'), cpu)
    (t / 'flags/HOLD_x').write_text('')
    with pytest.raises(fe.Refused, match='HOLD'):
        fe.runtime(env, cpu)
    (t / 'flags/HOLD_x').unlink()
    (t / 'STOP').write_text('')
    with pytest.raises(fe.Refused, match='STOP'):
        fe.runtime(env, cpu)
    (t / 'STOP').unlink()
    env2 = grant_env(t, holds='q0,q1')
    with pytest.raises(fe.Refused, match='grant refused'):
        fe.runtime(env2, cpu)


def test_cli_refuses_without_rowflow_env(world, capsys, monkeypatch):
    t, s = world
    path, p = write_plan(t, s)
    for k in [k for k in fe.os.environ if k.startswith(('FILLER_', 'M4_'))]:
        monkeypatch.delenv(k)
    out = t / 'out'
    out.mkdir()
    assert fe.main([str(path), 'arch.p0.baseline', str(out)]) == 2
    assert 'REFUSED rowflow job contract missing' in capsys.readouterr().out
    assert not (out / 'cell-plan.json').exists()


def test_fold_gate_run_formats_entry_argv(world, monkeypatch):
    """fold_gate.run -> fold_entry with no grant: first cell refuses rc=2, run stops."""
    t, s = world
    path, p = write_plan(t, s)
    for k in [k for k in fe.os.environ if k.startswith(('FILLER_', 'M4_', 'LLAMA_ARG_PREFILL'))]:
        monkeypatch.delenv(k)
    assert fg.run(path, p) == 1
    first = Path(p['result_root']) / p['cells'][0]['id']
    r = json.loads((first / 'RESULT.json').read_text())
    assert r['rc'] == 2 and r['argv'][-3:] == [str(path), p['cells'][0]['id'], str(first)]
    assert 'REFUSED rowflow job contract missing' in (first / 'entry.log').read_text()


def fake_result(cp, tps, tokens='a'):
    return {'schema': fe.RESULT_SCHEMA, 'plan_sha256': cp['plan_sha256'], 'cell': cp['cell'], 'role': cp['role'],
            'backend': cp['backend'], 'arm': cp['arm'], 'pair': cp['pair'], 'position': cp['position'],
            'aggregate_decode_tps': tps, 'success_count': 8, 'total_count': 8, 'frame': {'prompt_limit': 1},
            'greedy': {'outputs': [{'qid': 'q1', 'success': True, 'tokens_sha256': h(tokens.encode()),
                                    'text_sha256': None}]},
            'image': {'exe_sha256': cp['image_files']['bin/llama-server']}, 'models': cp['models']}


def test_outer_with_fake_watch(world, monkeypatch, capsys):
    t, s = world
    path, p = write_plan(t, s)
    for k in [k for k in fe.os.environ if k.startswith(('M4_', 'LLAMA_ARG_PREFILL'))]:
        monkeypatch.delenv(k)
    monkeypatch.setattr(fe.os, 'sched_getaffinity', lambda pid: set(range(192)))
    monkeypatch.setattr(fe, 'ram_check', lambda cp: {'stub': True})
    _, _, watch = fe.ownership()
    seen = {}

    def fake_run(cmd, grant, stop, hold, deadline, out, env=None):
        seen.update(cmd=cmd, env=env)
        cp = json.loads((Path(out) / 'cell-plan.json').read_text())
        assert fe.sha_bytes((Path(out) / 'cell-plan.json').read_bytes()) == env['FOLD_CELL_PLAN_SHA256']
        (Path(out) / 'cell-result.json').write_text(json.dumps(fake_result(cp, 10.0)))
        (Path(out) / 'watch-result.json').write_text(json.dumps({'status': 'closed', 'containment_empty': True, 'rc': 0}))
        return 0
    monkeypatch.setattr(watch, 'run', fake_run)
    out = t / 'o'
    out.mkdir()
    assert fe.outer(path, 'critic.p1.candidate', out, env=grant_env(t)) == 0
    assert seen['cmd'][-4:] == ['--inner', str(path), 'critic.p1.candidate', str(out)]
    cp = json.loads((out / 'cell-plan.json').read_text())
    assert '--prefill-order' in cp['server_argv'] and cp['runtime']['port'] == 18800
    assert 'OK aggregate_decode_tps=10.000' in capsys.readouterr().out
    # invalid measurement -> nonzero
    out2 = t / 'o2'
    out2.mkdir()
    monkeypatch.setattr(watch, 'run', lambda *a, **k: (fake_run(*a, **k), (Path(a[5]) / 'cell-result.json').write_text(
        json.dumps(dict(json.loads((Path(a[5]) / 'cell-result.json').read_text()), aggregate_decode_tps=0))))[0])
    assert fe.outer(path, 'critic.p1.candidate', out2, env=grant_env(t)) == 1


# ---------------------------------------------------------------- verdict math
def populate(t, p, tps, tokens=None):
    root = Path(p['result_root'])
    for c in p['cells']:
        cp = fe.derive_cell(p, c['id'])
        d = root / c['id']
        d.mkdir(parents=True)
        tok = (tokens or {}).get(c['id'], 'a')
        (d / 'cell-result.json').write_text(json.dumps(fake_result(cp, tps[(c['role'], c['arm'])][c['pair']], tok)))


@pytest.mark.parametrize('tps,verdict', [
    ({('arch', 'baseline'): [10, 10], ('arch', 'candidate'): [10.2, 10.1],
      ('critic', 'baseline'): [100, 100], ('critic', 'candidate'): [100, 101]}, 'PASS'),
    ({('arch', 'baseline'): [10, 10], ('arch', 'candidate'): [9.9, 9.8],
      ('critic', 'baseline'): [100, 100], ('critic', 'candidate'): [100, 101]}, 'INCONCLUSIVE'),
    ({('arch', 'baseline'): [10, 10], ('arch', 'candidate'): [10.5, 10.5],
      ('critic', 'baseline'): [100, 100], ('critic', 'candidate'): [94, 94.8]}, 'FAIL'),
    # cpu fail_ratio 0.94 vs gpu 0.95: 0.945 is FAIL on gpu, INCONCLUSIVE on cpu
    ({('arch', 'baseline'): [100, 100], ('arch', 'candidate'): [94.5, 94.5],
      ('critic', 'baseline'): [100, 100], ('critic', 'candidate'): [100, 100]}, 'INCONCLUSIVE'),
])
def test_verdict_math(world, tps, verdict):
    t, s = world
    _, p = write_plan(t, s)
    populate(t, p, tps)
    doc = fv.verdict_doc(p)
    assert doc['verdict'] == verdict, fv.lines(doc)
    arch = next(r for r in doc['roles'] if r['role'] == 'arch')
    assert arch['ratio'] == pytest.approx(
        (sum(tps[('arch', 'candidate')]) / 2) / (sum(tps[('arch', 'baseline')]) / 2))


def test_verdict_quality_fail_and_lines(world, capsys):
    t, s = world
    _, p = write_plan(t, s)
    good = {('arch', 'baseline'): [10, 10], ('arch', 'candidate'): [11, 11],
            ('critic', 'baseline'): [100, 100], ('critic', 'candidate'): [110, 110]}
    populate(t, p, good, tokens={'critic.p1.candidate': 'b'})
    path = t / 'plan/FOLD-PLAN.json'
    assert fv.main(['--plan', str(path)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith('M4-FOLD-VERDICT verdict=FAIL roles=2 cells=8 ')
    assert any(l.startswith('ROLE critic backend=gpu ratio=1.1000 ') and 'quality=DIFF OK' in l for l in out)
    assert 'QUALITY_DIFF critic pair=1 qid=q1' in out
    doc = json.loads((Path(p['result_root']) / 'VERDICT.json').read_text())
    assert doc['verdict'] == 'FAIL' and doc['rule_sha256'] == p['decision_rule']['sha256']


def test_verdict_incomplete(world):
    t, s = world
    _, p = write_plan(t, s)
    populate(t, p, {k: [10, 10] for k in [('arch', 'baseline'), ('arch', 'candidate'),
                                           ('critic', 'baseline'), ('critic', 'candidate')]})
    (Path(p['result_root']) / p['cells'][3]['id'] / 'cell-result.json').unlink()
    doc = fv.verdict_doc(p)
    assert doc['verdict'] == 'INCOMPLETE' and doc['missing']


def test_inner_with_fake_server(world, monkeypatch):
    """Inner phase result assembly with a fake server (no process, no network)."""
    t, s = world
    path, p = write_plan(t, s)
    monkeypatch.setattr(fe.os, 'sched_getaffinity', lambda pid: set(range(192)))
    cp = fe.derive_cell(p, 'arch.p0.candidate')
    cp['runtime'] = fe.runtime(grant_env(t), cp)
    cp['server_argv'] = fe.server_command(cp, 18800)
    out = t / 'inner'
    out.mkdir()
    raw = json.dumps(cp).encode()
    (out / 'cell-plan.json').write_bytes(raw)
    monkeypatch.setenv('FOLD_CELL_PLAN_SHA256', fe.sha_bytes(raw))
    for k in [k for k in fe.os.environ if k.startswith(('M4_', 'LLAMA_ARG_PREFILL'))]:
        monkeypatch.delenv(k)
    sw = fe.sweep()
    sent = []

    class Proc:
        pid = 4242
    monkeypatch.setattr(sw, 'start_server', lambda cmd, env, log: (sent.append(('env', env)), Proc())[1])
    monkeypatch.setattr(sw, 'wait_for_health', lambda *a: None)
    monkeypatch.setattr(sw, 'stop_server', lambda proc: {'pid': proc.pid, 'ps_verified_dead': True})

    def fake_http(method, url, payload, timeout):
        sent.append(payload)
        return 200, {'content': 'x', 'tokens': [1, 2], 'timings': {'predicted_n': 2, 'predicted_ms': 100.0,
                                                                   'predicted_per_second': 20.0, 'prompt_n': 3}}
    monkeypatch.setattr(sw, 'http_json', fake_http)

    class R:
        def __init__(self, rc, out=''):
            self.returncode, self.stdout = rc, out
    import types
    monkeypatch.setattr(fe, 'subprocess', types.SimpleNamespace(run=lambda a, **k: R(1) if a[0] == 'ps' else R(
        0, 'LISTEN pid=4242,' if '-ltnp' in a else '')))
    monkeypatch.setattr(fe, 'prove_image', lambda cp, pid: {'exe': cp['binary'],
                                                            'exe_sha256': cp['image_files']['bin/llama-server'],
                                                            'mapped': {}})
    monkeypatch.setattr(fe, 'residency_sample', lambda cp, pid: {'timestamp_ns': time.time_ns(), 'pid': pid,
                                                                  'Cpus_allowed_list': '0-95', 'kfd_own_entry': False})
    monkeypatch.setattr(fe, 'FRAME', dict(fe.FRAME, prompt_limit=1))
    cp['frame']['prompt_limit'] = 1
    raw = json.dumps(cp).encode()
    (out / 'cell-plan.json').write_bytes(raw)
    monkeypatch.setenv('FOLD_CELL_PLAN_SHA256', fe.sha_bytes(raw))
    monkeypatch.setattr(fe, 'SAMPLE_S', 0.001)
    orig_batch = sw.run_prompt_batch
    monkeypatch.setattr(sw, 'run_prompt_batch', lambda **k: (time.sleep(0.05), orig_batch(**k))[1])
    assert fe.inner(path, 'arch.p0.candidate', out) == 0
    r = json.loads((out / 'cell-result.json').read_text())
    assert r['aggregate_decode_tps'] == pytest.approx(20.0) and r['arm'] == 'candidate'
    assert r['greedy']['outputs'][0]['tokens'] == [1, 2] and r['greedy']['concurrency'] == 1
    bodies = [b for b in sent if isinstance(b, dict) and 'prompt' in b]
    assert bodies and all(b['seed'] == fe.GREEDY_SEED and b['return_tokens'] and b['temperature'] == 0.0 for b in bodies)
    env = [x[1] for x in sent if isinstance(x, tuple)][0]
    assert env['LD_LIBRARY_PATH'] == str(t / 'cpu-cand/bin') and env['GGML_FUSED_DECODE_OFF'] == '1'
    assert fe.validate_result(out / 'cell-result.json', cp) == []


@pytest.mark.parametrize('seal_shard2', [True, False])
def test_split_gguf_shards(world, seal_shard2):
    t, s = world
    s1, s2 = t / 'q-00001-of-00002.gguf', t / 'q-00002-of-00002.gguf'
    s1.write_bytes(b's1')
    s2.write_bytes(b's2')
    r = s['roles'][0]
    r.update(model=str(s1), model_sha256=h(b's1'))
    r['server_args'][1] = str(s1)
    if seal_shard2:
        r['aux_models'].append(str(s2))
        r['aux_sha256'][str(s2)] = h(b's2')
    _, p = write_plan(t, s)
    if seal_shard2:
        assert fe.derive_cell(p, 'arch.p0.baseline')['models'][str(s2)] == h(b's2')
    else:
        with pytest.raises(fe.Refused, match='split shard'):
            fe.derive_cell(p, 'arch.p0.baseline')


def test_entry_source_sealed(world):
    t, s = world
    ent = t / 'my_entry.py'
    ent.write_text('print(1)\n')
    s['entries'] = {'cpu': [sys.executable, str(ent), '{plan}', '{cell}', '{out}'], 'gpu': [str(ent), '{cell}']}
    _, p = write_plan(t, s)
    assert p['status'] == 'BOUND' and p['entry_files'][str(ent)] == h(b'print(1)\n')
    assert fg.verify(p, env={}) == []
    ent.write_text('print(2)\n')
    assert any('entry source changed' in e for e in fg.verify(p, env={}))
    with pytest.raises(fe.Refused, match='entry source changed'):
        fe.load_plan(t / 'plan/FOLD-PLAN.json')


def test_smoke_grant_pins_to_smoke_cpus(world, monkeypatch):
    t, s = world
    _, p = write_plan(t, s)
    monkeypatch.setattr(fe.os, 'sched_getaffinity', lambda pid: set(range(192)))
    env = grant_env(t, regions='0-3', holds='q0', cpus='0-3')
    g = t / 'flags/grants/row.grant'
    g.write_text(g.read_text().strip() + ' schema=epyc.rowflow.dryrun-grant.v1 id=row kind=rowflow-dryrun\n')
    cp = fe.derive_cell(p, 'arch.p0.baseline')
    monkeypatch.setenv('FILLER_DRYRUN', '1')
    rt = fe.runtime(dict(env, FILLER_DRYRUN='1', FILLER_DRYRUN_DIR=str(t)), cp)
    assert rt['smoke'] and cp['placement']['cpus'] == '0-3' and cp['placement']['planned_cpus'] == '0-95'
