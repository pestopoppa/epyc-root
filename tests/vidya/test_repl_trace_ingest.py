"""Registered ingest accepts prospective coverage and refuses altered streams."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import ingest_sources
from claim_tuple import ProjectionError, grade
from scripts.vidya.producers.repl_trace_capture import TraceCapture

ROOT = Path(__file__).resolve().parents[2]


def test_registry_cli_and_refusals(tmp_path):
    capture = TraceCapture(tmp_path, run_id='trace1', source_sha256='a' * 64)
    capture.record({'v': 2, 'kind': 'open', 'provenance': 'trace', 'session': 'a' * 16,
                    'ts': datetime.now(timezone.utc).isoformat(), 'section': 'section',
                    'content_digest': 'b' * 64, 'content_chars': 4, 'start': 0, 'end': 4})
    sidecar = capture.finalize()
    adapter = ingest_sources.SOURCES['repl-trace-coverage'].load()
    native = adapter.native_rows(sidecar)[0]
    claim = adapter.project(native)
    assert claim.value == 1 and claim.protocol_id == ''
    assert grade(claim)[:2] == ('Judged', 'Located')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/vidya/cli.py'),
        '--ledger', str(tmp_path / 'ledger.jsonl'), '--json', 'ingest', 'repl-trace-coverage',
        '--path', str(sidecar), '--as-of', datetime.now(timezone.utc).isoformat()],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)
    (tmp_path / 'trace1.trace.jsonl').write_text('altered')
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)
    with pytest.raises(ProjectionError):
        adapter.project(native)


@pytest.mark.parametrize('value', [None, [], 'text', 1, True])
def test_nondict_sidecar_rows_are_refused(tmp_path, value):
    sidecar = tmp_path / 'bad.belief_measurements.jsonl'
    sidecar.write_text(json.dumps(value) + '\n')
    adapter = ingest_sources.SOURCES['repl-trace-coverage'].load()
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)
    with pytest.raises(ProjectionError):
        adapter.project(value)
