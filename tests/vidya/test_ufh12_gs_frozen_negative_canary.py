import json

import pytest
from claim_tuple import ProjectionError
from adapters import ufh12_gs_coverage as adapter
import ufh12_gs_frozen_negative_canary as canary


def make_capture(path, *, synthetic=None):
    fc = adapter._frozen
    gc = fc.v
    rows = [{'id':str(i), 'text':'q'+str(i), 'stratum':'fixture',
             'answer_named_verbatim':False, 'code_intent':False} for i in range(500)]
    cohort = {'n':500, 'rows':rows, 'scope':'synthetic fixture'}
    (path/'cohort.json').write_text(json.dumps(cohort))
    context = {'schema':'epyc.gs-frozen-query-native-context.v1',
        'cohort_sha256':gc.digest((path/'cohort.json').read_bytes()), 'phase':'run',
        'scope':'synthetic fixture', 'filler_id':'fixture'}
    if synthetic is not None:
        context['synthetic'] = synthetic
    (path/'run-context.json').write_text(json.dumps(context))
    context_raw = (path/'run-context.json').read_bytes()
    lane = [{'id':str(i), 'cosine':1-i/100} for i in range(10)]
    row = gc.seal({'id':'0', 'query_sha256':gc.digest(b'q0'),
        'cohort_sha256':context['cohort_sha256'], 'phase':'run', 'stratum':'fixture',
        'answer_named_verbatim':False, 'code_intent':False, 'token_count_eg2':4,
        'context_sha256':gc.digest(context_raw), 'captured_at':'now',
        'stores':{'episodic':{'bge':lane,'eg2':lane},'strategy':{'bge':lane,'eg2':lane}}})
    (path/'results.jsonl').write_text(json.dumps(row)+'\n')
    return fc.emit(path)


def test_original_unscoped_row_cannot_enter_arbitrary_target_context(tmp_path):
    source = tmp_path/'input'; source.mkdir()
    sidecar = make_capture(source)
    receipt = canary.run(sidecar, tmp_path/'output')
    assert receipt['value'] == 1 and receipt['grade'] == ['Judged','Located']
    assert len(receipt['checks']) == 4
    assert all(c['planner_status'] == 'ready' and c['source_claims_visible'] == 0 for c in receipt['checks'])
    assert 'not implemented' in receipt['corpus_matching']


def test_corrupt_native_source_refuses_before_ledger_ingestion(tmp_path):
    source = tmp_path/'input'; source.mkdir()
    sidecar = make_capture(source)
    (source/'results.jsonl').write_text('{}\n')
    with pytest.raises(ProjectionError):
        canary.run(sidecar, tmp_path/'output')
    assert not (tmp_path/'output'/'ledger.jsonl').exists()


def test_planner_positive_control_for_explicit_synthetic_target(tmp_path):
    from datetime import datetime, timezone
    from claim_tuple import ClaimTuple, to_frames
    from ledger import Ledger
    import loop_beliefs

    now = datetime.now(timezone.utc).isoformat()
    # A separate synthetic observation tests planner visibility. It is not the
    # frozen-query capture and never changes that tuple or its source files.
    claim = ClaimTuple(measurement_id='gs-negative-control', metric='fixture_count',
        value=1, date=now, category='CANDIDATE', claim='Synthetic planner control only',
        protocol_id='', attestation_locator='synthetic-control:fixture',
        source_kind='synthetic-gs-canary-control', extra={'synthetic':True},
        applicability={'model_file':'fake-control.gguf','backend':'cpu'})
    ledger = Ledger(tmp_path/'control-ledger.jsonl')
    for frame in to_frames(claim, as_of=now, adapter_id='test.synthetic-control'):
        ledger.append(frame)
    cfg = tmp_path/'alarm.yaml'
    cfg.write_text('backend: file\nfile:\n  path: '+str(tmp_path/'alarms.jsonl')+'\n')
    answer = loop_beliefs.prepare('test.gs_control', {'model_file':'fake-control.gguf','backend':'cpu'},
        ledger=ledger.path, index_path=tmp_path/'index.yaml', as_of=now,
        sync_module=canary._FreshIndex(now), known_good=tmp_path/'known.json',
        alarm_state=tmp_path/'alarm.json', alarm_config=cfg, read_log=tmp_path/'reads.jsonl')
    assert answer['status'] == 'ready'
    assert any(c.get('source_kind') == 'synthetic-gs-canary-control'
               for c in answer.get('evidence',{}).get('claims',[]))


@pytest.mark.xfail(strict=True, reason="producer ignores explicit synthetic fixture declaration")
def test_declared_synthetic_fixture_is_labeled_as_synthetic(tmp_path):
    source = tmp_path/'input'; source.mkdir()
    sidecar = make_capture(source, synthetic=True)
    emitted = json.loads(sidecar.read_text())
    assert emitted['extra']['synthetic'] is True
