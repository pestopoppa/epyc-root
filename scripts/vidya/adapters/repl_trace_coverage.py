"""Project prospective v2 trace coverage, never retrieval quality."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from claim_tuple import ProjectionError, register

SOURCE_KIND = 'repl-trace-coverage'
ADAPTER_ID = 'vidya.adapters.repl_trace_coverage/v1'
AUTHORITY = 'measurement'
_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
_spec = importlib.util.spec_from_file_location(
    'repl_trace_capture', _root / 'scripts/vidya/producers/repl_trace_capture.py')
_producer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_producer)


def native_rows(path):
    path = Path(path).resolve()
    # The producer validator expects a mapping. A valid JSON scalar or list is
    # still untrusted input and must refuse the whole sidecar, not crash ingest.
    rows = _producer.carrier.load_rows(
        path, lambda row: ['row is not an object'] if not isinstance(row, dict)
        else _producer.validate(row))
    if rows is None or len(rows) != 1 or path.name != rows[0]['run_id'] + '.belief_measurements.jsonl':
        raise ProjectionError('invalid or mixed REPL trace coverage sidecar')
    return ({'row': rows[0], 'path': str(path)},)


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or set(native) != {'row', 'path'} or not isinstance(native['path'], str):
        raise ProjectionError('invalid REPL trace coverage native record')
    if native not in native_rows(native['path']):
        raise ProjectionError('REPL trace coverage does not rederive')
    try:
        return _producer.project(native['row'])
    except (ValueError, KeyError, OSError) as exc:
        raise ProjectionError('invalid REPL trace coverage record') from exc
