"""CONTROL_ONLY: synthetic inputs, no claims about real DHM reports."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
import claim_tuple as ct
from adapters import dev_harness_aggregate as a

# CI supplies the pinned producer checkout; local runs retain the production default.
ORCH = pathlib.Path(os.environ.get('EPYC_ORCHESTRATOR_SOURCE_ROOT', '/mnt/raid0/llm/epyc-orchestrator'))


@pytest.fixture
def produced(tmp_path):
    private = tmp_path / 'private'
    projection = tmp_path / 'projection'
    projection.mkdir()
    (projection / 'sessions.jsonl').write_text('')
    agentrun = tmp_path / 'agentrun'
    agentrun.mkdir()
    (agentrun / 'index.jsonl').write_text('')
    declarations = {'metadata': {'run_id': 'CONTROL_ONLY', 'producer': 'control',
        'declared_code_commit': 'a' * 40, 'semconv': 'control.v1', 'source_schema_keys': ['test.key'],
        'window_start': '2026-10-30T00:00:00Z', 'window_end': '2026-10-31T00:00:00Z',
        'scope': {'backend': 'cpu', 'device': 'control', 'model_file': 'control.gguf'}},
        'metrics': [{'pointer': '/counts/dhm4/sheet_items', 'metric': 'sheet_items',
                     'unit': 'items', 'direction': 'lower_better', 'category': 'BASELINE', 'rule_index': 0}]}
    declaration_file = tmp_path / 'declarations.json'
    declaration_file.write_text(json.dumps(declarations))
    env = dict(os.environ, DEV_HARNESS_PRIVATE_ROOT=str(private), EPYC_ORCHESTRATOR_ROOT=str(ORCH),
               DEV_HARNESS_ALLOW_NOT_NICE='1')
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps({'lessons': [], 'pilot': {}}))
    common = ['--projection', str(projection), '--private-root', str(private), '--run-id', 'CONTROL_ONLY',
              '--belief-declarations', str(declaration_file)]
    for script, extra in [('mine_m1.py', ['--tasks', 'dhm1,dhm5']),
                          ('mine_m2.py', ['--agentrun', str(agentrun), '--registry', str(registry)])]:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/dev_harness' / script), *common, *extra],
                                env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
    return tmp_path, private / 'mining' / 'CONTROL_ONLY', declaration_file, env, declarations


def publish(produced):
    tmp, run, declarations, env, _ = produced
    dest = tmp / 'control.aggregate.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/dev_harness/publish_mining_results.py'),
                             str(run), str(dest), '--belief-declarations', str(declarations)],
                            env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return pathlib.Path(str(dest) + a.SIDECAR_SUFFIX)


def test_real_miners_publisher_cli_and_planning_control(produced):
    import loop_beliefs as lb
    class Sync:
        def status(self, *args):
            return {'fresh': True, 'lag_entries': 0, 'index_max_id': 1, 'synced_max_id': 1, 'last_sync': '2026-10-31T00:00:00Z'}
        def sync(self, *args):
            raise AssertionError('unexpected sync')
    tmp = produced[0]
    side = publish(produced)
    row, = a.native_rows(side)
    tup = a.project(row)
    assert tup.value == 0 and tup.reps is None and tup.protocol_id == ''
    assert ct.grade(tup)[:2] == ('Judged', 'Located')
    file_name, pointer = tup.attestation_locator.split('#', 1)
    raw = pathlib.Path(file_name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == tup.attestation_sha256
    node = json.loads(raw)
    for part in pointer.split('/')[1:]: node = node[part]
    assert node == tup.value and tup.extra['capture_locator'] == str(side)
    as_of = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ledger = tmp / 'ledger.jsonl'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/vidya/cli.py'), '--json', 'ingest',
        'dev-harness-aggregate', '--path', str(side), '--as-of', as_of, '--ledger', str(ledger)],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['rows_projected'] == 1 and not report['refused'], report
    config = tmp / 'alarm.yaml'
    config.write_text('backend: file\nfile:\n  path: ' + str(tmp / 'alarms.jsonl') + '\n')
    ans = lb.prepare('test.dev_harness', {'backend': 'cpu', 'device': 'control', 'model_file': 'control.gguf'},
        ledger=ledger, index_path=tmp / 'index.yaml', as_of=as_of, sync_module=Sync(),
        known_good=tmp / 'known.json', alarm_state=tmp / 'alarm.json', alarm_config=config)
    assert ans['status'] == 'ready' and 'CONTROL_ONLY' in json.dumps(ans['evidence']), ans


def test_legacy_and_new_name_republish_refused(tmp_path):
    with pytest.raises(ct.ProjectionError, match='legacy aggregate'):
        a.native_rows(ROOT / 'data/dev_harness/mining-full-20261022T1310Z.aggregate.json')
    from publish_mining_results import build
    old = tmp_path / 'old'
    (old / 'm1/aggregates').mkdir(parents=True)
    (old / 'aggregate.json').write_text(json.dumps({'generated_at': '2026-10-31T00:00:00Z',
        'counts': {'dhm72': {'clusters': {}}, 'dhm4': {'sheet_items': 0}}, 'notes': '', 'rules': ['rule']}))
    (old / 'run.json').write_text(json.dumps({'run_id': 'CONTROL_ONLY', **{k: 1 for k in
        ('units', 'interrupt_candidates', 'cluster_docs', 'clusters_reported', 'planted_recovered', 'sheet_items', 'would_fire_total')}}))
    (old / 'm1/aggregates/dhm1.aggregate.json').write_text(json.dumps({'counts': {}, 'rules': ['rule']}))
    declarations = tmp_path / 'declarations.json'
    metadata = {'run_id': 'CONTROL_ONLY', 'producer': 'control', 'declared_code_commit': 'a' * 40,
        'semconv': 'control.v1', 'source_schema_keys': ['test.key'], 'scope': {},
        'window_start': '2026-10-30T00:00:00Z', 'window_end': '2026-10-31T00:00:00Z'}
    metrics = [{'pointer': '/counts/dhm4/sheet_items', 'metric': 'sheet_items', 'unit': 'items',
                'direction': 'lower_better', 'category': 'BASELINE', 'rule_index': 0}]
    declarations.write_text(json.dumps({'metadata': metadata, 'metrics': metrics}))
    target = tmp_path / 'newname.aggregate.json'
    with pytest.raises(ct.ProjectionError, match='custody'):
        a.publish_with_beliefs(build(old, allow_partial=True, include_rules=True), target, metadata=metadata, metrics=metrics,
            private_root=tmp_path / 'private', orchestrator_root=ORCH, run_dir=old, declarations_path=declarations)
    assert not target.exists()


def test_tamper_namespace_and_partial_refuse(produced):
    tmp, _, _, _, _ = produced
    side = publish(produced)
    original = side.read_text()
    cap = json.loads(original)
    cap['metrics'][0]['metric'] = 'changed'
    side.write_text(json.dumps(cap))
    with pytest.raises(ct.ProjectionError, match='hash mismatch'): a.native_rows(side)
    side.write_text(original)
    aggregate = tmp / 'control.aggregate.json'
    aggregate.write_bytes(aggregate.read_bytes() + b' ')
    with pytest.raises(ct.ProjectionError, match='digest mismatch'): a.native_rows(side)
    renamed = tmp / 'other.belief.json'
    renamed.write_text(original)
    with pytest.raises(ct.ProjectionError, match='namespace'): a.native_rows(renamed)
    side.write_text('{')
    with pytest.raises(ct.ProjectionError): a.native_rows(side)


def test_custody_tamper_or_partial_refuses(produced):
    from publish_mining_results import build
    tmp, run, declarations, _, supplied = produced
    (run / 'm2.finish.json').unlink()
    with pytest.raises(ct.ProjectionError, match='custody'):
        a.publish_with_beliefs(build(run, allow_partial=True, include_rules=True), tmp / 'new.json', metadata=supplied['metadata'], metrics=supplied['metrics'],
                               private_root=tmp / 'private', orchestrator_root=ORCH, run_dir=run,
                               declarations_path=declarations)
    assert not (tmp / 'new.json').exists()


def test_exclusive_atomic_no_replacement(tmp_path):
    import belief_run_custody as custody
    path = tmp_path / 'capture.json'
    custody.exclusive_write(path, b'first')
    with pytest.raises(FileExistsError): custody.exclusive_write(path, b'second')
    assert path.read_bytes() == b'first'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['capture.json']


def test_copy_renamed_run_and_mutated_outputs_refuse(produced, tmp_path):
    import shutil

    import belief_run_custody as custody
    _, run, declarations, _, _ = produced
    copied = tmp_path / 'copied-run'
    shutil.copytree(run, copied)
    with pytest.raises(ValueError, match='directory identity'):
        custody.verify(copied, declarations)
    output = run / 'aggregate.json'
    output.write_bytes(output.read_bytes() + b' ')
    with pytest.raises(ValueError, match='digest mismatch'):
        custody.verify(run, declarations)


def test_atomic_failure_does_not_expose_partial(tmp_path, monkeypatch):
    import belief_run_custody as custody
    path = tmp_path / 'sealed.json'
    monkeypatch.setattr(custody.os, 'fsync', lambda fd: (_ for _ in ()).throw(OSError('fsync failure')))
    with pytest.raises(OSError, match='fsync failure'):
        custody.exclusive_write(path, b'incomplete')
    assert not path.exists() and list(tmp_path.iterdir()) == []


def test_absent_scope_stays_unknown_and_nonfinite_refused(produced):
    import copy
    side = publish(produced)
    row, = a.native_rows(side)
    cap = copy.deepcopy(row['capture'])
    doc = copy.deepcopy(row['doc'])
    cap['metadata']['scope'] = {}
    cap['capture_sha256'] = a.ns.content_hash({k: v for k, v in cap.items() if k != 'capture_sha256'})
    a._validate(doc, cap)
    doc['counts']['bad'] = float('nan')
    with pytest.raises(ct.ProjectionError, match='noncanonical'):
        a._validate(doc, cap)


def test_privacy_and_invalid_metric_refused(produced):
    import copy
    side = publish(produced)
    row, = a.native_rows(side)
    cap = copy.deepcopy(row['capture'])
    doc = copy.deepcopy(row['doc'])
    doc['counts']['session_id'] = 7
    with pytest.raises(ct.ProjectionError, match='privacy'):
        a._validate(doc, cap)
    del doc['counts']['session_id']
    cap['metrics'][0]['pointer'] = '/counts/not_present'
    cap['capture_sha256'] = a.ns.content_hash({k: v for k, v in cap.items() if k != 'capture_sha256'})
    with pytest.raises(ct.ProjectionError, match='does not exist'):
        a._validate(doc, cap)


def test_completed_run_cannot_publish_again(produced):
    from publish_mining_results import build
    tmp, run, declarations, _, supplied = produced
    publish(produced)
    with pytest.raises(FileExistsError):
        a.publish_with_beliefs(build(run, allow_partial=True, include_rules=True), tmp / 'second.aggregate.json',
            metadata=supplied['metadata'], metrics=supplied['metrics'], private_root=tmp / 'private',
            orchestrator_root=ORCH, run_dir=run, declarations_path=declarations)
    assert not (tmp / 'second.aggregate.json').exists()


def test_default_publisher_preserves_legacy_bytes_and_gate(produced):
    from m2_lessons import ITSPilot, load_registry
    from publish_mining_results import build

    tmp, run, _, env, _ = produced
    m1 = run / 'm1/aggregates'
    for name in ('dhm1_history', 'oab_lb1', 'ufh14_lb8'):
        (m1 / f'{name}.aggregate.json').write_text(json.dumps({'counts': {'units': 1}, 'rules': []}))
    aggregate = run / 'aggregate.json'
    m2 = json.loads(aggregate.read_text())
    default_rules = ITSPilot(load_registry()).meta_rules()
    m2['rules'] = default_rules
    aggregate.write_text(json.dumps(m2))

    # Independent copy of the old reducer: default output is byte-for-byte identical.
    counts = dict(m2['counts'])
    for cluster in counts['dhm72']['clusters'].values():
        cluster.pop('top_terms', None)
    for name in ('dhm1', 'dhm1_history', 'dhm5', 'oab_lb1', 'ufh14_lb8'):
        counts[name] = json.loads((m1 / f'{name}.aggregate.json').read_text())['counts']
    run_record = json.loads((run / 'run.json').read_text())
    counts['run'] = {k: run_record[k] for k in ('units', 'interrupt_candidates', 'cluster_docs',
        'clusters_reported', 'planted_recovered', 'sheet_items', 'would_fire_total')}
    legacy = {'schema': 'dev-harness-aggregate.v1', 'generated_at': m2['generated_at'],
        'source': 'dev-harness mining full run ' + run_record['run_id'] + ' (M1 + M2), reduced; top_terms dropped',
        'spec': 'scripts/dev_harness/mining_m2_aggregate.schema.json', 'notes': m2['notes'],
        'rules': [], 'counts': counts}
    expected = json.dumps(legacy, indent=2, sort_keys=True) + '\n'
    assert json.dumps(build(run), indent=2, sort_keys=True) + '\n' == expected
    dest = tmp / 'default.aggregate.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/dev_harness/publish_mining_results.py'),
                             str(run), str(dest)], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert dest.read_text() == expected

    # The same real registry rule text is still rejected by the unmodified scanner.
    candidate = tmp / 'registry-rules.jsonl'
    candidate.write_text(json.dumps({'rules': default_rules}) + '\n')
    report = tmp / 'registry-rules-preflight.json'
    assert a.privacy.run_preflight(candidate, report, ORCH) != 0
    hits = json.loads(report.read_text())['paths'][0]['hits']
    flagged = {default_rules[int(hit['field_path'].split('[')[1].split(']')[0])] for hit in hits}
    assert any('INC-20261004-glob-rm-deleted-receipt-evidence' in rule for rule in flagged)
    assert any('INC-20260731-broad-process-pattern-kills' in rule for rule in flagged)
