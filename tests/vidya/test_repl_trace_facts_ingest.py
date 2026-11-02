import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ingest_sources
from scripts.vidya.producers.repl_trace_capture import TraceCapture

ROOT = Path(__file__).resolve().parents[2]


def test_explicit_cli_ingest_and_tamper(tmp_path):
    capture = TraceCapture(tmp_path, run_id='tracefacts', source_sha256='a' * 64)
    capture.record({'v': 2, 'kind': 'open', 'provenance': 'trace', 'session': 'b' * 16,
                    'ts': datetime.now(timezone.utc).isoformat(), 'section': 'section',
                    'content_digest': 'c' * 64, 'content_chars': 5, 'start': 1, 'end': 3})
    sidecar = capture.finalize()
    source = ingest_sources.SOURCES['repl-trace-facts']
    assert source.default is None and source.units(tmp_path) == [] and source.units(sidecar) == [sidecar]
    ledger = tmp_path / 'ledger.jsonl'
    cmd = [sys.executable, str(ROOT / 'scripts/vidya/cli.py'), '--ledger', str(ledger), '--json',
           'ingest', 'repl-trace-facts', '--path', str(sidecar), '--as-of', datetime.now(timezone.utc).isoformat()]
    result = subprocess.run(cmd, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['rows_projected'] == 1
    contents = ledger.read_text()
    assert 'source_sha256=' + 'a' * 64 in contents
    assert 'original query and corpus custody are unknown' in contents
    assert 'content_digest' in contents and 'provenance' in contents
    (tmp_path / 'tracefacts.trace.jsonl').write_text('tampered\n')
    result = subprocess.run(cmd, text=True, capture_output=True)
    assert json.loads(result.stdout)['refused']
