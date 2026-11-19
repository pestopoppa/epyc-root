from datetime import datetime, timezone

import pytest
from claim_tuple import ProjectionError, grade
from ledger import Ledger
import ingest_sources
from adapters import repl_shadow_observation as adapter
from scripts.vidya.producers.repl_shadow import Span
from scripts.vidya.producers.repl_shadow_sink import ShadowSink


def capture(path, *, opened):
    sink = ShadowSink(path, run_id='fixture', session='a' * 16, source_sha256='f' * 64,
                      arm_identities={'shown': '1' * 64, 'hidden': '2' * 64})
    span = Span('b' * 64, 'c' * 64, 0, 10, 100)
    sink.search(query_digest='d' * 64, shown_arm='shown', rankings={'shown':[span], 'hidden':[span]})
    if opened:
        sink.opened(span=span)
    return sink.close()


def test_observed_and_unknown_preserve_attribution(tmp_path):
    observed = tmp_path / 'observed'; observed.mkdir()
    unknown = tmp_path / 'unknown'; unknown.mkdir()
    one, = adapter.native_rows(capture(observed, opened=True))
    two, = adapter.native_rows(capture(unknown, opened=False))
    a, b = adapter.project(one), adapter.project(two)
    assert grade(a)[:2] == grade(b)[:2] == ('Judged', 'Located')
    assert a.protocol_id == b.protocol_id == ''
    assert a.extra['event']['interpretation']['hidden'] == 'counterfactual_span_match'
    assert a.extra['event']['result']['arms']['shown'][0]['next_open_overlap'] is True
    assert b.extra['event']['result']['arms']['shown'][0]['next_open_overlap'] is None
    assert b.extra['event']['reason'] == 'capture_closed'
    assert b.extra['identity_scope'] == 'producer-declared'
    assert not a.applicability


def test_altered_or_unfinished_stream_refused(tmp_path):
    p = capture(tmp_path, opened=True)
    native, = adapter.native_rows(p)
    forged = dict(native, event=dict(native['event'], reason='capture_closed'))
    with pytest.raises(ProjectionError): adapter.project(forged)
    p.write_bytes(p.read_bytes()[:-2])
    with pytest.raises(ProjectionError): adapter.native_rows(p)
    with pytest.raises(ProjectionError): adapter.project(native)


def test_explicit_ingest_is_scoped_and_declines_directory(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    p = capture(source, opened=False)
    ledger = Ledger(tmp_path / 'ledger.jsonl')
    as_of = datetime.now(timezone.utc).isoformat()
    report = ingest_sources.ingest(ledger, adapter.SOURCE_KIND, [p], as_of=as_of)
    assert report['rows_projected'] == 1 and not report['refused']
    assert ingest_sources.SOURCES[adapter.SOURCE_KIND].units(source) == []
    with pytest.raises(ValueError): ingest_sources.ingest(ledger, adapter.SOURCE_KIND, None, as_of=as_of)


def test_unscoped_observation_is_not_assigned_to_arbitrary_model(tmp_path):
    import loop_beliefs
    source = tmp_path / 'source'; source.mkdir()
    p = capture(source, opened=True)
    ledger = Ledger(tmp_path / 'ledger.jsonl')
    as_of = datetime.now(timezone.utc).isoformat()
    report = ingest_sources.ingest(ledger, adapter.SOURCE_KIND, [p], as_of=as_of)
    assert report['rows_projected'] == 1
    class Sync:
        def status(self, *args, **kwargs):
            return {'fresh': True, 'lag_entries': 0, 'index_max_id': 0,
                    'synced_max_id': 0, 'last_sync': as_of}
    cfg = tmp_path / 'alarm.yaml'
    cfg.write_text('backend: file\nfile:\n  path: ' + str(tmp_path / 'alarms.jsonl') + '\n')
    context = loop_beliefs.prepare('test.shadow', {'model_file': 'fake.gguf', 'backend': 'cpu'},
        ledger=ledger.path, index_path=tmp_path/'index', as_of=as_of, sync_module=Sync(),
        known_good=tmp_path/'known.json', alarm_state=tmp_path/'alarm.json', alarm_config=cfg,
        read_log=tmp_path/'reads.jsonl')
    assert context['status'] == 'ready'
    assert not any(c.get('source_kind') == adapter.SOURCE_KIND
                   for c in context.get('evidence', {}).get('claims', []))
