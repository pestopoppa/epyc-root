"""Strict projection of prospective UFH-12 G-S coverage, not score quality."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from claim_tuple import ProjectionError, register

SOURCE_KIND = 'ufh12-gs-coverage'
ADAPTER_ID = 'vidya.adapters.ufh12_gs_coverage/v1'
AUTHORITY = 'measurement'
_spec = importlib.util.spec_from_file_location('ufh12_gs_capture', Path(__file__).resolve().parents[1] / 'producers/ufh12_gs_capture.py')
_producer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_producer)

def native_rows(path):
    path = Path(path).resolve()
    rows = _producer.c.load_rows(path, _producer.validate)
    if rows is None or len(rows) != 1:
        raise ProjectionError('invalid or mixed UFH-12 G-S coverage sidecar')
    return tuple({'row': row, 'path': str(path)} for row in rows)

@register(SOURCE_KIND)
def project(native):
    if native not in native_rows(native['path']):
        raise ProjectionError('UFH-12 G-S coverage does not rederive')
    try:
        return _producer.project(native['row'])
    except (ValueError, KeyError, OSError) as exc:
        raise ProjectionError('invalid UFH-12 G-S native record') from exc
