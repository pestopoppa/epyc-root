"""Install Linux parent-death containment before an exec, without signalling PIDs."""
import ctypes
import os
import signal

PR_SET_PDEATHSIG = 1


def contain(parent_pid):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    # Covers parent death between fork and the prctl call.
    if os.getppid() != parent_pid:
        raise RuntimeError('parent disappeared before process containment')
