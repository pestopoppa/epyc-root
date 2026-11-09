import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from scripts.vidya.producers.repl_trace_capture import TraceCapture, project, validate


def event():
    return {'v': 2, 'kind': 'search', 'provenance': 'trace', 'session': 'a' * 16,
            'ts': datetime.now(timezone.utc).isoformat(), 'section': 'h:' + 'a' * 12,
            'content_digest': 'b' * 64, 'content_chars': 30, 'query_digest': 'c' * 64,
            'k': 1, 'mode': 'grep', 'hits': [['h:' + 'a' * 12, 0, 10]]}


def test_prospective_capture_projects_without_protocol(tmp_path):
    capture = TraceCapture(tmp_path, run_id='run1', source_sha256='a' * 64)
    capture.record(event())
    sidecar = capture.finalize()
    row = json.loads(sidecar.read_text())
    assert row['value'] == 1 and not validate(row)
    assert project(row).protocol_id == ''
    assert project(row).source_kind == 'repl-trace-coverage'
    with pytest.raises(FileExistsError):
        TraceCapture(tmp_path, run_id='run1', source_sha256='a' * 64)


def test_refuses_raw_data_old_events_and_out_of_range(tmp_path):
    capture = TraceCapture(tmp_path, run_id='run2', source_sha256='a' * 64)
    bad = event(); bad['raw_query'] = 'private'
    with pytest.raises(ValueError): capture.record(bad)
    bad = event(); bad['ts'] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError): capture.record(bad)
    bad = event(); bad['hits'][0][2] = 31
    with pytest.raises(ValueError): capture.record(bad)
    row = json.loads(capture.finalize().read_text())
    assert row['value'] == 0 and row['extra']['rejected'] == 3
    assert not validate(row)
    assert 'private' not in (tmp_path / 'run2.trace.jsonl').read_text()


def test_tampering_voids_projection(tmp_path):
    capture = TraceCapture(tmp_path, run_id='run3', source_sha256='a' * 64)
    capture.record(event())
    row = json.loads(capture.finalize().read_text())
    (tmp_path / 'run3.trace.jsonl').write_text('changed')
    assert validate(row)
    with pytest.raises(ValueError): project(row)


def test_resealed_forged_claim_is_refused(tmp_path):
    from scripts.vidya.adapters import _native_sidecar as carrier
    capture = TraceCapture(tmp_path, run_id='run4', source_sha256='a' * 64)
    capture.record(event())
    row = json.loads(capture.finalize().read_text())
    row['claim'] = 'retrieval quality improved'
    carrier.seal(row)
    assert validate(row)


def test_actual_app_spill_events_are_accepted(tmp_path, monkeypatch):
    import subprocess
    import hashlib
    from types import SimpleNamespace

    # The genuine producer bytes are read from a git object, never from a moving working tree.
    # CI checks out exactly this commit and exports EPYC_REPL_TRACE_SOURCE_ROOT (a configured but
    # broken root FAILS); with no root configured the default clone is used and, if it does not
    # hold the commit (a hosted runner), the test is skipped rather than reported as a defect.
    configured = os.environ.get('EPYC_REPL_TRACE_SOURCE_ROOT')
    app = configured or '/workspace/repos/epyc-orchestrator'
    spec = '488b31c96c6c148768508b3dcaefcb6c4c297664:src/repl_environment/trace_capture.py'
    shown = subprocess.run(['git', '-C', app, 'show', spec], capture_output=True, text=True)
    if shown.returncode != 0 and not configured:
        pytest.skip('orchestrator clone with the pinned REPL trace-capture commit is unavailable')
    assert shown.returncode == 0, shown.stderr
    source = shown.stdout
    ns = {'__file__': app + '/src/repl_environment/trace_capture.py', '__name__': 'native_trace_capture'}
    exec(compile(source, ns['__file__'], 'exec'), ns)
    monkeypatch.setenv('EPYC_REPL_TRACE_CAPTURE', '1')
    records = []
    ns['_write'] = lambda record: records.append(record) or True
    environment = SimpleNamespace()
    path = str(tmp_path / 'genuine-spill.txt')
    content = 'first target second'
    ns['register_spill'](environment, path, content)
    ns['record_spill_search'](environment, path, content, 'target', 1, [{'start': 6, 'end': 12}])
    ns['record_spill_open'](environment, path, content, 6, 12)
    assert [record['kind'] for record in records] == ['search', 'open']
    capture = TraceCapture(tmp_path, run_id='native1', source_sha256=hashlib.sha256(source.encode()).hexdigest())
    for record in records:
        capture.record(record)
    row = json.loads(capture.finalize().read_text())
    assert row['value'] == 2 and not validate(row)


def test_valid_safe_section_and_out_of_order_event_refused(tmp_path):
    capture = TraceCapture(tmp_path, run_id='order', source_sha256='a' * 64)
    first = event(); first['section'] = 'section'; first['hits'][0][0] = 'section'
    capture.record(first)
    second = event()
    second['ts'] = (datetime.fromisoformat(first['ts']) - timedelta(milliseconds=1)).isoformat()
    with pytest.raises(ValueError): capture.record(second)
    row = json.loads(capture.finalize().read_text())
    assert row['extra']['rejected'] == 1 and not validate(row)


def test_resealed_event_with_out_of_order_timestamp_refused(tmp_path):
    from scripts.vidya.adapters import _native_sidecar as carrier
    capture = TraceCapture(tmp_path, run_id='tampertime', source_sha256='a' * 64)
    capture.record(event())
    row = json.loads(capture.finalize().read_text())
    path = tmp_path / 'tampertime.trace.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[1]['event']['ts'] = '2000-01-01T00:00:00+00:00'
    path.write_text(''.join(json.dumps(item, sort_keys=True) + '\n' for item in records))
    row['results_sha256'] = carrier.file_sha256(path)
    carrier.seal(row)
    assert validate(row)


def test_refuses_mismatched_content_and_section(tmp_path):
    capture = TraceCapture(tmp_path, run_id='mismatch', source_sha256='a' * 64)
    bad = event(); bad['hits'][0][0] = 'h:' + 'b' * 12
    with pytest.raises(ValueError): capture.record(bad)
    bad = event(); bad['content_digest'] = 'not-a-digest'
    with pytest.raises(ValueError): capture.record(bad)
    row = json.loads(capture.finalize().read_text())
    assert row['extra']['rejected'] == 2 and not validate(row)


def test_future_events_and_backward_end_are_refused(tmp_path, monkeypatch):
    from scripts.vidya.producers import repl_trace_capture as producer
    capture = TraceCapture(tmp_path, run_id='future', source_sha256='a' * 64)
    future = event()
    future['ts'] = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError):
        capture.record(future)
    real_time = producer._time
    monkeypatch.setattr(producer, '_time', lambda: '2000-01-01T00:00:00+00:00')
    with pytest.raises(ValueError, match='capture end precedes'):
        capture.finalize()
    monkeypatch.setattr(producer, '_time', real_time)
    row = json.loads(capture.finalize().read_text())
    assert row['extra']['rejected'] == 1 and not validate(row)


def test_resealed_empty_capture_with_backward_end_is_refused(tmp_path):
    from scripts.vidya.adapters import _native_sidecar as carrier
    capture = TraceCapture(tmp_path, run_id='backward', source_sha256='a' * 64)
    row = json.loads(capture.finalize().read_text())
    path = tmp_path / 'backward.trace.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[-1]['ended_at'] = '2000-01-01T00:00:00+00:00'
    path.write_text(''.join(json.dumps(item, sort_keys=True) + '\n' for item in records))
    row['date'] = row['emitted_at'] = records[-1]['ended_at']
    row['results_sha256'] = carrier.file_sha256(path)
    carrier.seal(row)
    assert validate(row)
