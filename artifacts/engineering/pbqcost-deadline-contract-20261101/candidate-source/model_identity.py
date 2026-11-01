"""Edge-identity checks for the immutable PB-QCOST model and draft weights."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDENTITY = HERE / 'model-identity.json'


def edge_sha(path: Path, size: int, block: int) -> tuple[str, str]:
    with path.open('rb') as f:
        first = f.read(block)
        f.seek(size - block)
        last = f.read(block)
    if len(first) != block or len(last) != block:
        raise RuntimeError(f'model edge block truncated: {path}')
    return hashlib.sha256(first).hexdigest(), hashlib.sha256(last).hexdigest()


def verify_model_identity() -> dict:
    record = json.loads(IDENTITY.read_text())
    if record.get('schema') != 'epyc.model-identity.edge64m.v1':
        raise RuntimeError('unsupported model identity record')
    checked = []
    for item in record['models']:
        path = Path(item['path'])
        size = path.stat().st_size
        if size != item['size_bytes']:
            raise RuntimeError(f'model size changed: {path}: {size} != {item["size_bytes"]}')
        first, last = edge_sha(path, size, item['edge_block_bytes'])
        if first != item['first_edge_sha256'] or last != item['last_edge_sha256']:
            raise RuntimeError(f'model edge identity changed: {path}')
        checked.append({'path': str(path), 'size_bytes': size, 'first_edge_sha256': first, 'last_edge_sha256': last})
    return {'schema': record['schema'], 'verified': True, 'models': checked}
