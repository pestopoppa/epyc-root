#!/usr/bin/env python3
"""Own-child test: the launching parent dies before its child arms PDEATHSIG."""
import ctypes
import os
import signal
import sys

from outer import parent_death_kill


def main():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0):
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
    started_r, started_w = os.pipe()
    release_r, release_w = os.pipe()
    parent = os.fork()
    if parent == 0:
        os.close(started_r)
        os.close(release_w)
        child = os.fork()
        if child == 0:
            old_parent = os.getppid()
            os.write(started_w, f'{os.getpid()} {old_parent}\n'.encode())
            os.close(started_w)
            if os.read(release_r, 1) != b'R':
                os._exit(126)
            # The parent has been reaped before release. The candidate must
            # refuse rather than execute the target with no death protection.
            parent_death_kill(old_parent)
            os._exit(42)
        os.close(started_w)
        os.close(release_r)
        signal.pause()
        os._exit(127)
    os.close(started_w)
    os.close(release_r)
    try:
        child_text, original_parent_text = os.read(started_r, 64).split()
        child = int(child_text)
        if int(original_parent_text) != parent:
            raise RuntimeError('child did not observe launching parent')
        # Only the exact direct child created above is signaled.
        os.kill(parent, signal.SIGKILL)
        got, status = os.waitpid(parent, 0)
        if got != parent or not os.WIFSIGNALED(status) or os.WTERMSIG(status) != signal.SIGKILL:
            raise RuntimeError('launcher was not reaped after SIGKILL')
        os.write(release_w, b'R')
        got, status = os.waitpid(child, 0)
        if got != child or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 125:
            raise RuntimeError(f'pre-arm child did not refuse: wait status {status}')
        try:
            os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            print('PREARM_PARENT_LOSS_REFUSED_AND_REAPED')
            return 0
        raise RuntimeError('descendants remain')
    finally:
        os.close(started_r)
        os.close(release_w)


if __name__ == '__main__':
    sys.exit(main())
