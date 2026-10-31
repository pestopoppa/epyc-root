"""Full-ledger read-only simulation; no ledger writes or derived store."""
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, '/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3/scripts/vidya')
from fold import fold
plan = json.loads(Path(sys.argv[1]).read_text())
raw = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest() == plan['canonical_sha256'], 'frontier changed; review again'
frames = [json.loads(line)['frame'] for line in raw.splitlines()]
proposed = plan['proposed_frames']
targets = {cid for f in proposed for cid in f['assertion']['claim_ids']}
before = fold(frames, as_of='2026-10-31T19:30:00Z')
after = fold(frames + proposed, as_of='2026-10-31T19:30:00Z')
assert set(before.beliefs) == set(after.beliefs)
changed = []
for cid, old in before.beliefs.items():
    new = after.beliefs[cid]
    left, right = asdict(old), asdict(new)
    if left != right:
        changed.append(cid)
        assert cid in targets, ('unrelated belief changed', cid)
        assert old.pro == new.pro and old.con == new.con
        left.pop('corrections'); right.pop('corrections')
        assert left == right and len(new.corrections) == 1 and new.review_required
assert set(changed) == targets
assert before.alias_map == after.alias_map
print(json.dumps({'status':'PASS_FULL_LEDGER_SIMULATION_ONLY','belief_count':len(before.beliefs),'changed_claims':sorted(changed),'original_grades_preserved':True,'unrelated_beliefs_unchanged':True,'canonical_sha256':plan['canonical_sha256']},indent=2))
