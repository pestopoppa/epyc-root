"""Candidate APP bridge for prospective v2 trace coverage; default off.

Install only with the review package and a runtime owner.  This is not an
attestation of loaded Python bytecode or a retrieval-quality instrument.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import threading
import uuid
from pathlib import Path

_lock = threading.Lock()
_capture = None
_pid = None
_failed = False


def _finish(owner_pid):
    global _capture
    if os.getpid() != owner_pid:
        return
    with _lock:
        if _capture is not None:
            try:
                _capture.finalize()
            except Exception:
                pass  # No sidecar is preferable to an invented complete capture.
            finally:
                _capture = None


def record(event, *, source_path):
    """Record a native event only as it occurs; failures never interrupt APP.

    Independent enablement is deliberate: the legacy trace setting alone does
    not activate this new writer. A failed writer disables itself for this PID.
    """
    global _capture, _pid, _failed
    if os.environ.get('EPYC_REPL_TRACE_BELIEF_CAPTURE') != '1':
        return
    try:
        with _lock:
            pid = os.getpid()
            if _pid != pid:
                # A forked child must never append to or finalize its parent's stream.
                _pid, _capture, _failed = pid, None, False
            if _failed:
                return
            try:
                if _capture is None:
                    expected = os.environ['EPYC_REPL_TRACE_BELIEF_SOURCE_SHA256']
                    directory = os.environ['EPYC_REPL_TRACE_BELIEF_DIR']
                    if not re.fullmatch(r'[0-9a-f]{64}', expected) or not Path(directory).is_absolute():
                        raise ValueError('invalid source pin or directory')
                    actual = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
                    if actual != expected:
                        raise ValueError('source pin mismatch')
                    from scripts.vidya.producers.repl_trace_capture import TraceCapture
                    _capture = TraceCapture(directory, run_id='app-' + uuid.uuid4().hex,
                                            source_sha256=actual)
                    atexit.register(_finish, pid)
                _capture.record(event)
            except Exception:
                # Leave any partial stream incomplete; never seal after write failure.
                _failed = True
                _capture = None
    except Exception:
        return


def _after_fork_child():
    global _lock, _capture, _pid, _failed
    _lock = threading.Lock()
    _capture, _pid, _failed = None, None, False


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_after_fork_child)
