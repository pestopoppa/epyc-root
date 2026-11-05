"""Prospective official-row provider adapter; never acquires a lock."""
import json, os
from pathlib import Path
import current_lock
ROW = 'kpf18-g3-provider-transport-prep-20261104'
SOURCES = json.loads((Path(__file__).parent/'provider-sources.json').read_text())
_witness = None

def capture_gpu():
    global _witness
    if os.environ.get('FILLER_ID') != ROW:
        raise ValueError('successor official row identity absent')
    if _witness is None:
        _witness = current_lock.capture(ROW, SOURCES)
    else:
        current_lock.recheck(_witness)
    return _witness['owner'], _witness

def verify_gpu(owner, witness):
    if os.environ.get('FILLER_ID') != ROW or owner != witness['owner'] or witness['row_id'] != ROW:
        raise ValueError('successor row/provider changed')
    return current_lock.recheck(witness)

def boundary():
    owner, witness = capture_gpu()
    return verify_gpu(owner, witness)
