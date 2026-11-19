"""Bounded cleanup for one explicitly owned capture worker process.

The worker must open and own all perf FDs itself and must not create children.
No process name matching or process group signalling is used. A kill success
is reported only after Popen.wait has reaped the exact captured child.
"""
import math
import os
import signal
import subprocess


class WorkerGuard:
    def __init__(self, process, *, grace_s=2.0, kill_s=2.0):
        if not isinstance(process, subprocess.Popen) or type(process.pid) is not int or process.pid <= 0:
            raise ValueError('owned Popen child required')
        for value in (grace_s, kill_s):
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 < value <= 10:
                raise ValueError('cleanup deadline out of bounds')
        self.process, self.pid, self.grace_s, self.kill_s = process, process.pid, float(grace_s), float(kill_s)
        self.finished = False

    @classmethod
    def spawn(cls, argv, *, env, cwd, pass_fds=(), popen=subprocess.Popen, grace_s=2.0, kill_s=2.0):
        if (not isinstance(argv, (list, tuple)) or not argv or
                any(not isinstance(x, str) or not x or '\x00' in x for x in argv)):
            raise ValueError('invalid worker argv')
        if not isinstance(env, dict) or not os.path.isabs(cwd): raise ValueError('explicit env and absolute cwd required')
        if (not isinstance(pass_fds, (tuple, list)) or
                any(type(fd) is not int or fd < 3 for fd in pass_fds) or
                len(pass_fds) != len(set(pass_fds))):
            raise ValueError('unique explicit nonstandard FDs required')
        for fd in pass_fds:
            os.fstat(fd)  # reject closed descriptors before spawning
        # No shell; only explicitly passed IPC descriptors are inherited.
        process = popen(list(argv), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        close_fds=True, pass_fds=tuple(pass_fds), start_new_session=False)
        try:
            return cls(process, grace_s=grace_s, kill_s=kill_s)
        except BaseException:
            # The returned handle is ours even if guard setup failed.
            process.kill()
            process.wait(timeout=2.0)
            raise

    def stop(self):
        if self.finished: raise ValueError('worker already reaped')
        p = self.process
        if p.pid != self.pid: raise ValueError('worker identity changed')
        stage = 'already-exited'
        if p.poll() is None:
            stage = 'sigterm'
            try: p.send_signal(signal.SIGTERM)
            except ProcessLookupError: pass  # exit race; wait must still reap
        try:
            rc = p.wait(timeout=self.grace_s)
        except subprocess.TimeoutExpired:
            stage = 'sigkill'
            try: p.send_signal(signal.SIGKILL)
            except ProcessLookupError: pass
            try:
                rc = p.wait(timeout=self.kill_s)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('owned worker remains unconfirmed after SIGKILL') from exc
        self.finished = True
        return {'pid': self.pid, 'stage': stage, 'returncode': rc,
                'reaped': True, 'measurement_admission': 'none'}
