import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('fold_gate', ROOT / 'scripts/champion/m4/fold_gate.py')
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sh(*a, cwd):
    return subprocess.check_output(a, cwd=cwd, text=True).strip()


def image(root: Path, source: str, knob: bool):
    (root / 'bin').mkdir(parents=True)
    files = {'bin/llama-server': b'server', 'bin/libllama-common.so': b'common' + (b' srpf' if knob else b''),
             'bin/libggml-cpu.so': b'ggml'}
    for rel, data in files.items():
        (root / rel).write_bytes(data)
    (root / 'SHA256SUMS').write_text(''.join(f'{h(d)}  {r}\n' for r, d in files.items()))
    (root / 'BUILD_COMPLETE').write_text(f'BUILD_COMPLETE source={source} kind=cpu\n')


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
    image(tmp_path / 'base', champ, False)
    image(tmp_path / 'cand', cand, True)
    model = tmp_path / 'm.gguf'
    model.write_bytes(b'weights')
    pool = tmp_path / 'pool.jsonl'
    pool.write_bytes(b'{"p":1}\n')
    authority = tmp_path / 'FOLD-AUTHORITY.md'
    authority.write_text('ratified')
    rule = tmp_path / 'rule.json'
    rule.write_text(json.dumps({'schema': fg.RULE_SCHEMA, 'authority': str(authority),
                                'authority_sha256': h(b'ratified'), 'metric_direction': 'higher',
                                'cpu': {'pass_ratio': 0.98, 'fail_ratio': 0.95},
                                'quality': {'suite': 'x'}}))
    entry = tmp_path / 'entry.py'
    entry.write_text('import sys,pathlib; pathlib.Path(sys.argv[2],"ok").write_text(sys.argv[1])\n')
    s = {'schema': fg.SPEC_SCHEMA, 'llama_tree': str(tree), 'champion_ref': 'champion',
         'champion': champ, 'candidate': cand,
         'images': {'cpu': {'baseline': str(tmp_path / 'base'), 'candidate': str(tmp_path / 'cand')}},
         'knob_probe': {'file': 'bin/libllama-common.so', 'needle': 'srpf'},
         'roles': [{'role': 'architect_general', 'backend': 'cpu', 'model': str(model),
                    'model_sha256': h(b'weights'), 'recipe_authority': 'v11 INF22-Q38-T48',
                    'server_args': ['-t', '48'], 'env': {'GGML_FUSED_DECODE_OFF': '1'}}],
         'prompt_pool': {'path': str(pool), 'sha256': h(b'{"p":1}\n')},
         'decision_rule': str(rule),
         'entries': {'cpu': [sys.executable, str(entry), '{cell}', '{out}']},
         'result_root': str(tmp_path / 'results')}
    return tmp_path, s


def bound(s):
    p = fg.bind(s, env={})
    p['plan_sha256'] = fg.plan_digest(p)
    return p


def test_positive_bind_and_arms(world):
    _, s = world
    p = bound(s)
    assert p['status'] == 'BOUND', p['errors'] + p['needs']
    arms = {c['arm']: c['server_args'] for c in p['cells']}
    assert arms == {'baseline': ['-t', '48'], 'candidate': ['-t', '48', '--prefill-order', 'srpf']}
    assert fg.verify(p, env={}) == []


def test_missing_rule_is_descriptive_only(world):
    _, s = world
    s['decision_rule'] = None
    p = bound(s)
    assert p['status'] == 'DESCRIPTIVE_ONLY' and any('operator decision' in n for n in p['needs'])


@pytest.mark.parametrize('mutate,needle', [
    (lambda t, s: s.update(champion='0' * 40), 'champion moved'),
    (lambda t, s: s['images']['cpu'].update(baseline=s['images']['cpu']['candidate']), 'knob probe'),
    (lambda t, s: (t / 'cand/bin/llama-server').write_bytes(b'tampered'), 'differs from SHA256SUMS'),
    (lambda t, s: s['roles'][0].update(model_sha256='0' * 64), 'model digest mismatch'),
    (lambda t, s: s['roles'][0]['server_args'].append('--prefill-order'), 'arms must differ only'),
    (lambda t, s: s['roles'][0].pop('recipe_authority'), 'best-recipe authority'),
    (lambda t, s: s['prompt_pool'].update(sha256='0' * 64), 'prompt_pool'),
    (lambda t, s: s['images']['cpu'].update(baseline='/mnt/raid0/llm/kernels/production/cpu'), 'frozen production'),
    (lambda t, s: s['roles'].append(dict(s['roles'][0])), 'duplicate'),
    (lambda t, s: (t / 'FOLD-AUTHORITY.md').write_text('edited'), 'authority digest'),
])
def test_mutations_refuse(world, mutate, needle):
    t, s = world
    mutate(t, s)
    p = fg.bind(s, env={})
    assert p['status'] == 'REFUSED' and any(needle in e for e in p['errors']), p['errors']


def test_hidden_env_refused(world):
    _, s = world
    p = fg.bind(s, env={'LLAMA_ARG_PREFILL_ORDER': 'srpf'})
    assert p['status'] == 'REFUSED'


def test_verify_detects_post_bind_tamper(world):
    t, s = world
    p = bound(s)
    (t / 'm.gguf').write_bytes(b'other')
    assert any('model changed' in e for e in fg.verify(p, env={}))
    p2 = bound(s)
    p2['cells'][0]['server_args'] = ['-t', '96']
    assert fg.verify(p2, env={}) == ['plan: seal broken (edited after bind)']


def test_cli_bind_run_status_resume(world, capsys, monkeypatch):
    t, s = world
    monkeypatch.delenv('M4_PLAN_CELL', raising=False)
    (t / 'spec.json').write_text(json.dumps(s))
    assert fg.main(['bind', '--spec', str(t / 'spec.json'), '--out', str(t / 'plan')]) == 0
    assert fg.main(['bind', '--spec', str(t / 'spec.json'), '--out', str(t / 'plan')]) == 2  # write-once
    plan = str(t / 'plan/FOLD-PLAN.json')
    assert fg.main(['run', '--plan', plan]) == 0
    assert (t / 'results/architect_general.candidate/ok').read_text() == 'architect_general.candidate'
    capsys.readouterr()
    fg.main(['status', '--plan', plan])
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith('M4-FOLD status=BOUND ')
    assert out[1:] == ['CELL architect_general.baseline COMPLETE rc=0',
                       'CELL architect_general.candidate COMPLETE rc=0']
    assert fg.main(['run', '--plan', plan]) == 0  # resumable no-op


def test_run_refuses_descriptive_and_retains_failure(world, capsys):
    t, s = world
    s['decision_rule'] = None
    (t / 'spec.json').write_text(json.dumps(s))
    assert fg.main(['bind', '--spec', str(t / 'spec.json'), '--out', str(t / 'd')]) == 3
    assert fg.main(['run', '--plan', str(t / 'd/FOLD-PLAN.json')]) == 2
    t2 = t / 'f'
    s = json.loads((t / 'spec.json').read_text())
    s['decision_rule'] = str(t / 'rule.json')
    s['entries'] = {'cpu': [sys.executable, '-c', 'raise SystemExit(7)']}
    s['result_root'] = str(t2 / 'results')
    (t / 'spec2.json').write_text(json.dumps(s))
    assert fg.main(['bind', '--spec', str(t / 'spec2.json'), '--out', str(t2)]) == 0
    assert fg.main(['run', '--plan', str(t2 / 'FOLD-PLAN.json')]) == 1
    r = json.loads((t2 / 'results/architect_general.baseline/RESULT.json').read_text())
    assert r['rc'] == 7
