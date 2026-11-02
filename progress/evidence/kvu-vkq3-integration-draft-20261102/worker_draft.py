"""Offline integration seam, not a launcher or a rowflow worker.

A caller must independently bind the actual grant, deadline, synthetic inputs,
model and executable identities, parent-death containment and CPU environment.
This draft does not establish any of those properties and must not be scheduled.
"""
import math
import os
from pathlib import Path
import re
import stat
import time

from supervisor import supervise
from receipts import write_attempt


def run_attempt(*, mode, attempt_id, root, argv, input_bytes, env, deadline_monotonic,
                cleanup_margin_s, grant_valid, stopped, now=time.monotonic,
                supervise_fn=supervise, write_fn=write_attempt):
    """Connect injected grant checks, bounded child supervision and receipts.

    The deadline and predicates are caller-supplied and untrusted: no row may
    use this draft until its engine's authoritative grant adapter is implemented.
    """
    if mode not in ('qualification', 'full') or not isinstance(attempt_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', attempt_id):
        raise ValueError('invalid mode or attempt identity')
    # Detect unusable receipt custody before starting the child. The receipt
    # writer still creates the attempt exclusively and handles races.
    root_path = Path(root)
    root_stat = root_path.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.geteuid() or stat.S_IMODE(root_stat.st_mode) & 0o077:
        raise ValueError('root must be a private owned directory')
    if os.path.lexists(root_path / (mode + '-' + attempt_id)):
        raise FileExistsError('attempt already exists')
    if not isinstance(input_bytes, bytes) or not argv:
        raise ValueError('invalid child input or argv')
    if not math.isfinite(deadline_monotonic) or not math.isfinite(cleanup_margin_s) or cleanup_margin_s <= 0:
        raise ValueError('invalid deadline or cleanup margin')
    if not grant_valid() or stopped():
        raise ValueError('grant unavailable or cancellation requested')
    ceiling = deadline_monotonic - now() - cleanup_margin_s
    if ceiling <= 0:
        raise ValueError('no time remains before cleanup margin')

    def cancelled():
        return stopped() or not grant_valid() or now() >= deadline_monotonic - cleanup_margin_s

    result = supervise_fn(argv, input_bytes, env, stopped=cancelled, timeout_s=ceiling)
    # No success can be issued after the grant has been lost, even if a child
    # happens to finish between its final check and receipt creation.
    if result['status'] == 'completed' and cancelled():
        result = dict(result, status='cancelled')
    return write_fn(root, attempt_id, mode, result,
                    expected_input_bytes=len(input_bytes), ceiling_s=ceiling)
