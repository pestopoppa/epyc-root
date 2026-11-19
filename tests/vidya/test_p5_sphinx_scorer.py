"""Original native controls and tamper/refusal checks; no scorer execution."""
import json
from pathlib import Path
import shutil
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import p5_sphinx_scorer as ad
from claim_tuple import ProjectionError, grade

PACKET = ROOT / 'data/vidya/p5-sphinx-native-20261118'

@pytest.fixture
def packet(tmp_path):
    dest = tmp_path / 'packet'
    shutil.copytree(PACKET, dest)
    return dest

def result(packet):
    return packet / 'official/RESULT.json'

def attempt(packet):
    return next((packet / 'official').glob('attempt-*'))

def test_original_projection(packet):
    rows = ad.native_rows(result(packet))
    assert len(rows) == 6
    assert [(x['arm'], x['group'], x['status']) for x in rows] == [
        ('gold', 'FAIL_TO_PASS', 'PASSED'), ('gold', 'FAIL_TO_PASS', 'PASSED'),
        ('gold', 'PASS_TO_PASS', 'PASSED'), ('negative', 'FAIL_TO_PASS', 'FAILED'),
        ('negative', 'FAIL_TO_PASS', 'FAILED'), ('negative', 'PASS_TO_PASS', 'PASSED')]
    claims = [ad.project(row) for row in rows]
    assert len({c.measurement_id for c in claims}) == 6
    assert all(grade(c)[:2] == ('Judged', 'Located') and not c.applicability for c in claims)

@pytest.mark.parametrize('name', ['native.json', 'gold-report.json', 'negative-test_output.txt', 'rowflow.grant', 'controls.log', 'terminal.json'])
def test_artifact_tamper_refused(packet, name):
    p = attempt(packet) / name
    p.write_bytes(p.read_bytes() + b' ')
    with pytest.raises(ProjectionError):
        ad.native_rows(result(packet))

@pytest.mark.parametrize('name', ['case.json', 'job.py', 'SOURCE.sha256', 'launch.sh'])
def test_sealed_source_tamper_refused(packet, name):
    p = packet / name
    p.write_bytes(p.read_bytes() + b' ')
    with pytest.raises(ProjectionError):
        ad.native_rows(result(packet))

@pytest.mark.parametrize('changes', [dict(mode='smoke'), dict(status='PARTIAL'), dict(runner_rc=1), dict(decision='FAIL')])
def test_terminal_mutation_refused(packet, changes):
    p = result(packet)
    doc = json.loads(p.read_bytes())
    doc.update(changes)
    p.write_text(json.dumps(doc))
    with pytest.raises(ProjectionError):
        ad.native_rows(p)

def test_forged_row_and_post_read_tamper_refused(packet):
    row = ad.native_rows(result(packet))[0]
    with pytest.raises(ProjectionError):
        ad.project({**row, 'status': 'FAILED'})
    p = attempt(packet) / 'gold-report.json'
    p.write_bytes(p.read_bytes() + b' ')
    with pytest.raises(ProjectionError):
        ad.project(row)

def reseal(packet, name, mutate, monkeypatch):
    """Simulate an attacker rewriting artifact, both terminal copies and all local hashes."""
    import hashlib
    a = attempt(packet)
    p = a / name
    obj = json.loads(p.read_bytes())
    mutate(obj)
    p.write_text(json.dumps(obj))
    t = json.loads(result(packet).read_bytes())
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if name == 'native.json':
        t['native_sha256'] = digest
    else:
        t['arm_artifacts_sha256'][name] = digest
    body = (json.dumps(t, indent=2, sort_keys=True) + '\n').encode()
    result(packet).write_bytes(body)
    (a / 'terminal.json').write_bytes(body)
    return hashlib.sha256(body).hexdigest()

def test_coherent_reseal_cannot_replace_original_terminal(packet, monkeypatch):
    reseal(packet, 'native.json', lambda x: x.update(owned_containers_removed=False), monkeypatch)
    with pytest.raises(ProjectionError, match='pin mismatch'):
        ad.native_rows(result(packet))

@pytest.mark.parametrize('artifact,mutate', [
    ('native.json', lambda x: x.update(owned_containers_removed=False)),
    ('native.json', lambda x: x['arms']['gold']['FAIL_TO_PASS'].pop(next(iter(x['arms']['gold']['FAIL_TO_PASS'])))),
    ('gold-report.json', lambda x: x['sphinx-doc__sphinx-8593']['tests_status']['PASS_TO_PASS']['success'].clear()),
])
def test_independent_semantic_refusal_even_with_synthetic_terminal_pin(packet, monkeypatch, artifact, mutate):
    digest = reseal(packet, artifact, mutate, monkeypatch)
    monkeypatch.setattr(ad, 'TERMINAL', digest)
    with pytest.raises(ProjectionError):
        ad.native_rows(result(packet))

def test_log_report_disagreement_even_with_synthetic_pin(packet, monkeypatch):
    import hashlib
    a = attempt(packet)
    p = a / 'gold-test_output.txt'
    p.write_text(p.read_text().replace('PASSED tests/test_ext_autodoc_private_members.py::test_private_field\n',
                                      'FAILED tests/test_ext_autodoc_private_members.py::test_private_field\n'))
    t = json.loads(result(packet).read_bytes())
    t['arm_artifacts_sha256'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    body = (json.dumps(t, indent=2, sort_keys=True) + '\n').encode()
    result(packet).write_bytes(body)
    (a / 'terminal.json').write_bytes(body)
    monkeypatch.setattr(ad, 'TERMINAL', hashlib.sha256(body).hexdigest())
    with pytest.raises(ProjectionError, match='log status mismatch'):
        ad.native_rows(result(packet))

def test_cli_ingests_original_packet(tmp_path):
    import subprocess
    from datetime import datetime, timezone
    ledger = tmp_path / 'ledger.jsonl'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    run = subprocess.run([sys.executable, str(ROOT / 'scripts/vidya/cli.py'), '--ledger', str(ledger),
                          '--json', 'ingest', ad.SOURCE_KIND, '--path', str(PACKET / 'official/RESULT.json'),
                          '--as-of', now, '--only-new'], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    data = json.loads(run.stdout)
    assert data['rows_projected'] == 6 and data['frames_emitted'] == 18 and not data['refused']

def test_native_task_planning_canary(tmp_path):
    import subprocess
    from datetime import datetime, timezone
    import loop_beliefs
    class Sync:
        def status(self, *args, **kwargs):
            return {'fresh': True, 'lag_entries': 0, 'index_max_id': 1, 'synced_max_id': 1,
                    'last_sync': datetime.now(timezone.utc).isoformat()}
        def sync(self, *args, **kwargs):
            raise AssertionError('unexpected sync')
    ledger = tmp_path / 'ledger.jsonl'
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cmd = [sys.executable, str(ROOT / 'scripts/vidya/cli.py'), '--ledger', str(ledger), '--json',
           'ingest', ad.SOURCE_KIND, '--path', str(PACKET / 'official/RESULT.json'), '--as-of', now, '--only-new']
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    (tmp_path / 'index.yaml').write_text('[]\n')
    cfg = tmp_path / 'alarm.yaml'
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarm.jsonl'}\n")
    def ask(consumer, task):
        return loop_beliefs.prepare(consumer, {'scope': 'task', 'task_id': task}, ledger=ledger,
            index_path=tmp_path / 'index.yaml', as_of=now, sync_module=Sync(),
            known_good=tmp_path / 'kg.json', alarm_state=tmp_path / 'state.json', alarm_config=cfg,
            read_log=tmp_path / 'reads.jsonl')
    ans = ask('p5.scorer_controls', 'VB-P5-SCORER-CONTROLS-WIRE')
    assert ans['status'] == 'ready', ans
    claims = [c for c in ans['evidence']['claims'] if c.get('source_kind') == ad.SOURCE_KIND]
    assert len(claims) == 6 and all(c['grade'] == 'Judged/Located' for c in claims)
    assert 'test_private_field' in json.dumps(ans['evidence'])
    assert not [c for c in ask('p5.scorer_controls', 'OTHER')['evidence']['claims'] if c.get('source_kind') == ad.SOURCE_KIND]
    assert not [c for c in ask('other', 'VB-P5-SCORER-CONTROLS-WIRE')['evidence']['claims'] if c.get('source_kind') == ad.SOURCE_KIND]
