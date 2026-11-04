#!/usr/bin/env python3
"""Linux exec wrapper: same process group, unmaskable parent-death kill."""
import ctypes
import os
import signal
import sys


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    expected_parent = int(args[0])
    if os.getppid() != expected_parent:
        return 125
    libc = ctypes.CDLL(None, use_errno=True)
    # PR_SET_PDEATHSIG survives the unprivileged env/server exec chain.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_PDEATHSIG failed')
    if os.getppid() != expected_parent:
        return 125
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    os.execvp(args[1], args[1:])
    return 125


if __name__ == '__main__':
    raise SystemExit(main())
