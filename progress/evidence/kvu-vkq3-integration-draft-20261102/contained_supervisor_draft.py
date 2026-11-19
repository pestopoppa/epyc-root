"""Supervisor adapter: parent-death containment for the direct child only.

This is not a row launcher, provenance check or process-tree cleanup proof.
A caller must pin the interpreter and wrapper with its other runtime inputs.
"""
import os
from pathlib import Path
import sys
from supervisor import supervise

_WRAPPER = Path(__file__).resolve().with_name('pdeath_exec_draft.py')


def contained_supervise(argv, input_bytes, env, **kwargs):
    if not argv or not os.path.isabs(argv[0]):
        raise ValueError('an absolute executable path is required')
    if not os.path.isabs(sys.executable):
        raise ValueError('an absolute interpreter path is required')
    wrapped = [sys.executable, str(_WRAPPER), str(os.getpid()), *argv]
    return supervise(wrapped, input_bytes, env, **kwargs)
