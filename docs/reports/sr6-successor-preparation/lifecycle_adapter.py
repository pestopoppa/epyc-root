#!/usr/bin/env python3
"""Bind contained SR-6 session spawn, readiness and captured-PID drain."""
from pathlib import Path
import time
import uuid

from native_worker import ARMS
from ready_server import verify_ready_server
from session_drain import spawn_contained_session, drain_contained_session


class LifecycleAdapters:
    def __init__(self, *, argv_by_arm, env, cwd, library_dir, build_root, port,
                 admission_check, evidence_dir, startup_timeout_s=300):
        if (not isinstance(argv_by_arm, dict) or set(argv_by_arm) != set(ARMS)
                or any(not isinstance(v, (list, tuple)) or not v or
                       any(not isinstance(x, str) or not x or '\0' in x for x in v)
                       for v in argv_by_arm.values())
                or not isinstance(env, dict) or env.get('LD_LIBRARY_PATH') != library_dir
                or not isinstance(cwd, str) or not Path(cwd).is_absolute()
                or not isinstance(library_dir, str) or not Path(library_dir).is_absolute()
                or not isinstance(build_root, Path) or not build_root.is_absolute()
                or type(port) is not int or not 1 <= port <= 65535
                or not callable(admission_check) or not isinstance(evidence_dir, Path)
                or evidence_dir.is_symlink() or not evidence_dir.is_dir()
                or type(startup_timeout_s) not in (int, float) or not 0 < startup_timeout_s <= 1800):
            raise ValueError('invalid lifecycle configuration')
        self.argv = {arm: tuple(argv) for arm, argv in argv_by_arm.items()}
        self.server_argv = {
            arm: argv[2:] if argv[:2] == ('/usr/bin/numactl', '--interleave=all') else argv
            for arm, argv in self.argv.items()
        }
        if any(not argv for argv in self.server_argv.values()):
            raise ValueError('numactl requires an executable')
        self.env = dict(env)
        self.cwd, self.library_dir, self.build_root = cwd, library_dir, build_root
        self.port, self.admission_check = port, admission_check
        self.evidence_dir, self.startup_timeout_s = evidence_dir, startup_timeout_s
        self.pending = {}
        self.owned = set()

    def spawn(self, arm):
        if arm not in self.argv or self.admission_check() is not True:
            raise ValueError('arm or admission invalid')
        token = uuid.uuid4().hex
        with (self.evidence_dir / (token + '.stdout')).open('xb') as stdout, \
             (self.evidence_dir / (token + '.stderr')).open('xb') as stderr:
            process = spawn_contained_session(list(self.argv[arm]), stdout=stdout, stderr=stderr,
                                    env=self.env, cwd=self.cwd)
        self.pending[process] = (arm, token)
        self.owned.add(process)
        return process

    def drain(self, process, grace_seconds):
        if process not in self.owned:
            raise ValueError('unknown process')
        drain_contained_session(process, grace_seconds)
        self.pending.pop(process, None)
        self.owned.remove(process)

    def verify_ready_and_identity(self, process, arm):
        if process not in self.pending or self.pending[process][0] != arm:
            raise ValueError('unknown process or arm')
        _, token = self.pending.pop(process)
        deadline = time.monotonic() + self.startup_timeout_s
        last_error = None
        while time.monotonic() < deadline:
            if process.poll() is not None or self.admission_check() is not True:
                raise ValueError('server exited or admission revoked')
            try:
                return verify_ready_server(process=process, arm=arm,
                    expected_argv=list(self.server_argv[arm]), library_dir=self.library_dir,
                    build_root=self.build_root, port=self.port,
                    admission_check=self.admission_check,
                    record_path=self.evidence_dir / (token + '.ready.json'))
            except ValueError as exc:
                last_error = exc
                time.sleep(min(0.2, max(0, deadline - time.monotonic())))
        raise ValueError('server readiness deadline expired') from last_error
