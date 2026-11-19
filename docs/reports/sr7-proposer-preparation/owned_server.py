"""Owned direct-child lifecycle for an SR-7 capture adapter, not a launcher.

The caller must prove admission, executable and library provenance, listener
ownership, deadline and descendant-tree drain. This module starts no server at
import and never signals a process other than the captured direct child.
"""
import math
import os
from pathlib import Path
import subprocess


class OwnedServer:
    def __init__(self, process, trace_path, trace_identity):
        self.process = process
        self.trace_path = trace_path
        self.trace_identity = trace_identity
        self.stopped = False

    @property
    def pid(self):
        return self.process.pid

    def stop(self, grace_s=5):
        """Terminate and reap this exact child; fail if it cannot be reaped."""
        if type(grace_s) not in (int, float) or not math.isfinite(grace_s) or not 0 < grace_s <= 60:
            raise ValueError('invalid grace period')
        if self.stopped:
            raise ValueError('child already reaped')
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=grace_s)
        if self.process.poll() is None:
            raise RuntimeError('child exit unverified')
        self.stopped = True

    def read_trace(self, max_bytes=16 * 1024 * 1024):
        if not self.stopped:
            raise ValueError('child must be reaped before reading trace')
        if type(max_bytes) is not int or not 0 < max_bytes <= 64 * 1024 * 1024:
            raise ValueError('invalid trace limit')
        fd = os.open(self.trace_path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as source:
            stat = os.fstat(source.fileno())
            if (stat.st_dev, stat.st_ino) != self.trace_identity:
                raise ValueError('trace identity changed')
            raw = source.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError('trace exceeds limit')
        return raw


def launch_owned(argv, env, trace_path):
    """Spawn an absolute executable with an explicit environment and new log.

    Trace creation is exclusive. The returned handle owns only the direct
    child, not arbitrary processes listening on the same port or descendants.
    """
    if (not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv)
            or not os.path.isabs(argv[0])):
        raise ValueError('absolute executable and nonempty arguments required')
    if (not isinstance(env, dict) or not env.get('LD_LIBRARY_PATH')
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items())):
        raise ValueError('explicit environment and library path required')
    if not isinstance(trace_path, Path) or trace_path.is_symlink():
        raise ValueError('new trace path required')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(trace_path, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as trace:
            stat = os.fstat(trace.fileno())
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=trace,
                                       stderr=subprocess.STDOUT, env=env, close_fds=True)
    except BaseException:
        trace_path.unlink(missing_ok=True)
        raise
    return OwnedServer(process, trace_path, (stat.st_dev, stat.st_ino))
