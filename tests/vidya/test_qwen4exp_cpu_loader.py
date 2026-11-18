"""Offline replay controls. Native r2 bytes remain immutable and unprojectable."""

import base64
import json
from pathlib import Path
import shutil

import pytest

from adapters import qwen4exp_cpu_loader as adapter, quality_pack_comparison
from canary import qwen4exp_cpu_loader_context as canary
from claim_tuple import ProjectionError, grade
from producers import qwen4exp_cpu_loader_contract as contract

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'data/vidya/quality-pack-loader-reshape-20261118'
ITEM = 'qwen4exp-loader-cpu-json'
START = '2026-11-18T02:38:00.000000+00:00'
END = '2026-11-18T02:45:00.000000+00:00'


def original(path):
    envelope = json.loads(path.with_name(path.name + '.original-bytes.json').read_bytes())
    payload = base64.b64decode(envelope['bytes_b64'], validate=True)
    assert contract.sha(payload) == envelope['sha256']
    return payload


def write(path, value):
    path.write_bytes(contract.canonical(value) + b'\n')


def reseal(path, update=None):
    record = json.loads(path.read_bytes())
    record['files'] = {name: contract.sha(raw) for name, raw in contract.inventory(path.parent).items()}
    if update:
        update(record)
    record.pop('content_sha256')
    write(path, {**record, 'content_sha256': contract.sha(contract.canonical(record))})


@pytest.fixture
def fixture_seal(tmp_path, monkeypatch):
    # Construct software test data in a fresh directory. Input responses exercise the unchanged
    # validator with provenance-labelled r2 response bytes and test-only process records.
    source, out = tmp_path / 'source', tmp_path / 'out'
    source.mkdir()
    out.mkdir()
    for filename in ('plan.json', 'loader-reshape-witness.json'):
        (source / filename).write_bytes(original(PACKET / 'successor-r2' / filename))
    for filename in ('SOURCE.sha256', 'capture.py'):
        shutil.copyfile(PACKET / 'wire' / filename, source / filename)
    raw = PACKET / 'full-r2'
    shutil.copytree(raw / 'native', out / 'native')
    plan = json.loads((source / 'plan.json').read_bytes())
    state = json.loads(original(raw / 'RESULT.json'))
    state['row_id'] = contract.ROW
    state['source_manifest_sha256'] = contract.sha((source / 'SOURCE.sha256').read_bytes())
    for index, (arm, name) in enumerate(contract.CAPTURES.items()):
        target = out / 'native' / arm
        server_path = target / 'server.json'
        server = json.loads(server_path.read_bytes())
        server['argv'][4] = '19489'
        server['environment']['FILLER_ID'] = contract.ROW
        write(server_path, server)
        path = out / 'native' / (name + '.json')
        capture = json.loads(original(path))
        path.with_name(path.name + '.original-bytes.json').unlink()
        capture['capture_identity']['capture_runner_sha256'] = contract.RUNNER_SHA
        capture['capture_identity']['server_sha256'] = contract.sha(server_path.read_bytes())
        if arm == 'candidate':
            capture['production_diagnostic_capture_sha256'] = state['captures']['production']
        write(path, capture)
        digest = contract.sha(path.read_bytes())
        state['captures'][arm] = digest
        path.with_suffix('.sha256').write_text(digest + '\n')
        witness = {
            'pid': server['pid'], 'binary': plan['arms'][arm]['binary'], 'cpus': state['cpus'],
            'mapped_libraries': server['mapped_libraries'],
        }
        write(target / (ITEM + '.custody.json'), {
            'before': {**witness, 'observed_at': f'2026-11-18T02:4{2 * index}:00.000000+00:00'},
            'after': {**witness, 'observed_at': f'2026-11-18T02:4{2 * index + 1}:00.000000+00:00'},
            'http_status': 200, **{key: state['checks'][arm][key] for key in ('request_sha256', 'response_sha256')},
        })
    result = out / 'RESULT.json'
    write(result, state)
    monkeypatch.setattr(contract, 'utc_now', lambda: END)
    contract.write_seal(source, result, START)
    return out / contract.SEAL_NAME


def test_semantic_refusal_grade_and_real_planning_reader(fixture_seal, tmp_path):
    claim = adapter.project(fixture_seal)
    assert grade(claim)[:2] == ('Judged', 'Located')
    assert claim.value == 1
    assert claim.observation == {'outcome_native': 'loader_exercised_response_refused'}
    assert claim.extra['load_witnesses']['candidate']['runtime_dims_from_pinned_source'] == [2560, 4]
    assert len(claim.extra['load_witnesses']['production']['native_lines']) == 2
    report = canary.run(fixture_seal, tmp_path / 'context', 1)
    assert report['wiring_status'] == 'passed'
    assert report['native_status'] == 'loader_exercised_response_refused'
    assert report['native_exit_code'] == 1
    assert report['reads']['exact']['claim_ids'] == [report['claim_id']]
    assert all(not row['claim_ids'] for key, row in report['reads'].items() if key != 'exact')


@pytest.mark.parametrize(('mutation', 'message'), [
    ('original_r2', 'essential source pins differ'),
    ('request', 'request or response bytes differ'),
    ('response', 'request or response bytes differ'),
    ('native_log', 'one native mmap=true load line'),
    ('cleanup', 'owned cleanup missing'),
    ('custody', 'after HTTP process differs'),
    ('bank', 'capture digest differs'),
    ('mooted_witness', 'source/header witness bytes differ'),
    ('writer', 'capture runner bytes differ'),
    ('smoke_grant', 'bounded CPU-quarter grant'),
    ('false_pass', 'semantic disposition does not re-derive'),
])
def test_resealed_inconsistent_evidence_refused(fixture_seal, mutation, message):
    directory = fixture_seal.parent
    result = directory / 'RESULT.json'
    state = json.loads(result.read_bytes())
    arm = directory / 'native/production'
    update = None
    if mutation == 'original_r2':
        state['row_id'] += '-r2'
    elif mutation in ('request', 'response'):
        wire = arm / f'{ITEM}.{mutation}.json'
        wire.write_bytes(wire.read_bytes() + b' ')
    elif mutation == 'native_log':
        path = arm / 'server.log'
        path.write_bytes(path.read_bytes().replace(b'loading tensor blk.0.hc_attn_norm.weight',
                                                  b'loading tensor blk.0.other.weight'))
    elif mutation == 'cleanup':
        path = arm / 'cleanup.json'
        cleanup = json.loads(path.read_bytes())
        cleanup['dead'] = False
        write(path, cleanup)
        for runtime in ('production', 'candidate'):
            stem = contract.CAPTURES[runtime]
            capture_path = directory / 'native' / (stem + '.json')
            capture = json.loads(capture_path.read_bytes())
            if runtime == 'production':
                capture['capture_identity']['cleanup_sha256'] = contract.sha(path.read_bytes())
            else:
                capture['production_diagnostic_capture_sha256'] = state['captures']['production']
            write(capture_path, capture)
            digest = contract.sha(capture_path.read_bytes())
            (directory / 'native' / (stem + '.sha256')).write_text(digest + '\n')
            state['captures'][runtime] = digest
    elif mutation == 'custody':
        path = arm / f'{ITEM}.custody.json'
        custody = json.loads(path.read_bytes())
        custody['after']['pid'] += 1
        write(path, custody)
    elif mutation == 'bank':
        path = directory / 'native/banked-capture.json'
        path.write_bytes(path.read_bytes() + b' ')
    elif mutation in ('mooted_witness', 'writer'):
        name = 'loader-reshape-witness.json' if mutation == 'mooted_witness' else 'capture.py'
        def update(record):
            record['inputs'][name] = 'e30='
    elif mutation == 'smoke_grant':
        grant = directory / 'native/scheduler.grant'
        grant.write_bytes(grant.read_bytes().strip() + b' kind=rowflow-dryrun\n')
        state['grant_sha256'] = contract.sha(grant.read_bytes())
    elif mutation == 'false_pass':
        state['status'] = 'loader_diagnostic_complete'
    write(result, state)
    reseal(fixture_seal, update)
    with pytest.raises(ProjectionError, match=message):
        adapter.project(fixture_seal)


def test_partial_declines_and_other_schemas_refused(fixture_seal):
    result = fixture_seal.parent / 'RESULT.json'
    state = json.loads(result.read_bytes())
    state['status'] = 'incomplete'
    state['error'] = {'phase': 'candidate', 'type': 'RuntimeError', 'message': 'cleanup failed'}
    write(result, state)
    reseal(fixture_seal)
    assert adapter.frames_for_path(fixture_seal, as_of=END) == []
    with pytest.raises(ProjectionError, match='incomplete CPU diagnostic'):
        adapter.project(fixture_seal)
    with pytest.raises(ProjectionError, match='loader seal requires fields'):
        adapter.project(result)
    with pytest.raises(ProjectionError, match='sealed comparison requires fields'):
        quality_pack_comparison.native_rows(fixture_seal)
