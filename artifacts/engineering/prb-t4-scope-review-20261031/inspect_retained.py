"""Read-only PRB-T4 identity capture. No ledger writer or derived index."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path('/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3')
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from canonical import content_hash
from ledger import GENESIS_PREV_HASH, _link_hash

path = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl')
before = path.stat()
raw = path.read_bytes()
after = path.stat()
assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'concurrent ledger mutation'
assert raw.endswith(b'\n'), 'torn tail'
records = [json.loads(line) for line in raw.splitlines()]
prev = GENESIS_PREV_HASH
for i, record in enumerate(records):
    assert record['seq'] == i and record['prev_hash'] == prev
    assert record['frame_hash'] == content_hash(record['frame'])
    prev = _link_hash(prev, record['frame_hash'], i)
actor = 'vidya.adapters.tale_budget/v1'
run = 'prb_t4_gpu_20260916_191049'
sources = [r for r in records if r['frame'].get('pubinfo', {}).get('actor') == actor and run in json.dumps(r['frame'].get('assertion', {}))]
source_ids = {r['frame']['assertion'].get('source_id') for r in sources} - {None}
claims = [r for r in records if r['frame'].get('assertion', {}).get('source_id') in source_ids and 'claim_proposed' in r['frame']['frame_type']]
claim_ids = {r['frame']['assertion']['claim_id'] for r in claims}
related = [r for r in records if r in sources or r in claims or any(cid in json.dumps(r['frame'].get('assertion', {})) for cid in claim_ids)]
print(json.dumps({'status': 'READ_ONLY_IDENTITY_CAPTURE', 'ledger_sha256': hashlib.sha256(raw).hexdigest(), 'record_count': len(records), 'frontier': prev, 'source_ids': sorted(source_ids), 'claim_ids': sorted(claim_ids), 'records': related}, indent=2))
