"""Read-only membership capture for a private cgroup-v2 subtree.

This prototype never uses cgroup.kill and never claims exclusivity against a
same-UID process moving itself out of, or another process into, the cgroup.
"""
import os
from pathlib import Path


def birth(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def captured_members(group):
    path = Path(group)
    if path.parent != Path('/sys/fs/cgroup') or not path.name.startswith('kpf50-test-'):
        raise ValueError('not an explicitly created test cgroup')
    pids = [int(x) for x in (path / 'cgroup.procs').read_text().split()]
    captured = {}
    try:
        for pid in pids:
            ticks = birth(pid)
            fd = os.pidfd_open(pid)
            if birth(pid) != ticks:
                os.close(fd)
                raise RuntimeError('PID identity changed')
            captured[pid] = (ticks, fd)
        return captured
    except BaseException:
        for _, fd in captured.values():
            os.close(fd)
        raise
