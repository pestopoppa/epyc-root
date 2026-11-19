"""Linux parent-death wrapper for a single captured exec, offline draft."""
import ctypes
import os
import signal
import sys


def main(argv):
    if len(argv) < 2:
        raise ValueError('expected parent PID and executable')
    expected_parent = int(argv[0])
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    if os.getppid() != expected_parent:
        raise RuntimeError('parent disappeared before containment')
    os.execvpe(argv[1], argv[1:], os.environ)


if __name__ == '__main__':
    main(sys.argv[1:])
