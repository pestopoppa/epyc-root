import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest
from claim_tuple import ProjectionError, grade
from scripts.vidya.producers.repl_trace_capture import TraceCapture

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('trace_facts_test', ROOT / 'scripts/vidya/adapters/repl_trace_facts.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def capture(path):
    writer = TraceCapture(path, run_id='capture', source_sha256='a' * 64)
    writer.record({'v': 2, 'kind': 'open', 'provenance': 'trace', 'session': 'b' * 16,
                   'ts': datetime.now(timezone.utc).isoformat(), 'section': 'section',
                   'content_digest': 'c' * 64, 'content_chars': 5, 'start': 1, 'end': 3})
    return writer.finalize()


def test_event_projects_only_recorded_fact_and_unknown_custody(tmp_path):
    sidecar = capture(tmp_path)
    native, = adapter.native_rows(sidecar)
    fact = adapter.project(native)
    assert grade(fact)[:2] == ('Judged', 'Located')
    assert fact.extra['event']['start'] == 1 and fact.extra['event']['provenance'] == 'trace'
    assert fact.extra['source_sha256'] == 'a' * 64
    assert fact.extra['query_and_corpus_custody'] == 'unknown'
    assert fact.protocol_id == '' and fact.value == 1


def test_refuses_altered_event_or_source_after_enumeration(tmp_path):
    sidecar = capture(tmp_path)
    native, = adapter.native_rows(sidecar)
    forged = dict(native, event=dict(native['event'], end=4))
    with pytest.raises(ProjectionError):
        adapter.project(forged)
    (tmp_path / 'capture.trace.jsonl').write_text('changed\n')
    with pytest.raises(ProjectionError):
        adapter.project(native)
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)


def test_unfinished_capture_cannot_be_offered(tmp_path):
    writer = TraceCapture(tmp_path, run_id='unfinished', source_sha256='a' * 64)
    writer.stream.close()
    with pytest.raises(ProjectionError):
        adapter.native_rows(tmp_path / 'unfinished.belief_measurements.jsonl')
