"""Offline rowflow-grant bridge; not a row launcher.

Caller must wire signal handling to guard.on_signal, bind runtime/model identity,
contain child processes on parent death, and enforce CPU and output custody.
"""
import importlib.util
from pathlib import Path
import time

from worker_draft import run_attempt

_GUARD_PATH = Path(__file__).resolve().parent.parent / 'kvu-vkq3-guard-review-20261102' / 'guard.py'
_spec = importlib.util.spec_from_file_location('vkq3_guard', _GUARD_PATH)
_guard_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_guard_module)
GrantGuard = _guard_module.GrantGuard


def run_guarded_attempt(*, env, grant_dir, local_stop, expected_id, attempt_id, root,
                        argv, input_bytes, child_env, now=time.monotonic,
                        wall=time.time, worker=run_attempt, cleanup_margin_s=1):
    """Bind guard mode and remaining grant window to the worker's monotonic clock.

    This does not install signal handlers. An actual launcher must route signals
    to the guard throughout execution, and provide process-tree containment.
    """
    guard = GrantGuard(env, grant_dir, local_stop, expected_id=expected_id, clock=wall)
    remaining = guard.remaining()
    deadline_monotonic = now() + remaining
    return worker(mode=guard.mode, attempt_id=attempt_id, root=root, argv=argv,
                  input_bytes=input_bytes, env=child_env,
                  deadline_monotonic=deadline_monotonic, cleanup_margin_s=cleanup_margin_s,
                  grant_valid=lambda: not guard.check(), stopped=guard.check, now=now)
