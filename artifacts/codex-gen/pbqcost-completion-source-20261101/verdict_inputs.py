"""Hash the complete mutable file set consumed by verdict_q."""
import hashlib
from pathlib import Path

VERDICT_INPUTS = (
    'run/pb_qcost_1.jsonl',
    'run/graphs_proof_ub256.json',
    'run/graphs_proof_ub512.json',
    'run/graphs_proof_ub1024.json',
    'sibling_summary.json',
    'sibling_load.csv',
)

def hash_verdict_inputs(attempt_dir: Path) -> dict[str, str] | None:
    attempt_dir = Path(attempt_dir)
    result = {}
    for rel in VERDICT_INPUTS:
        path = attempt_dir / rel
        if path.is_symlink() or not path.is_file():
            return None
        # Reject symlinked parents as well as symlinked leaf files.
        parent = path.parent
        while parent != attempt_dir.parent and parent != attempt_dir:
            if parent.is_symlink():
                return None
            parent = parent.parent
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
