#!/usr/bin/env python3
"""SR-6 lifecycle seam; NOT a runnable launcher or admission proof.

All adapters are supplied by a future, reviewed launcher. It must bind admission
and identity checks to actual native evidence and prove process-tree ownership,
resource limits, deadline, signal handling, and residency. No default adapter
launches a process. A single captured process handle is used for all cleanup;
this scaffold alone cannot prove descendant-tree drain or authorize a row.
"""
from dataclasses import dataclass
import subprocess


class LifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReadyServer:
    """Scoped handle, valid only inside with_server's callback."""
    pid: int
    arm: str
    evidence: object


def with_server(*, arm, admission_check, spawn, verify_ready_and_identity,
                run, grace_seconds=10, drain=None):
    """Run callback once with a fresh handle, then terminate and reap it.

    `admission_check` must return the literal True before `spawn` is called.
    `spawn` returns the uniquely owned, already captured child handle and must
    never spawn then raise without cleaning it. The verifier receives the handle
    and arm and must return a nonempty evidence dict only after independently
    verifying readiness and identity; an empty or invalid result refuses work.
    Runtime admission and all callback semantics are untrusted until integrated.
    """
    if not isinstance(arm, str) or arm not in ('composed3', 'composed4', 'mtp3', 'mtp4', 'mtp4_repeat'):
        raise LifecycleError('unknown arm')
    if not all(callable(f) for f in (admission_check, spawn, verify_ready_and_identity, run)):
        raise LifecycleError('missing adapter')
    if drain is not None and not callable(drain):
        raise LifecycleError('invalid drain adapter')
    if type(grace_seconds) not in (int, float) or not (0 < grace_seconds <= 60):
        raise LifecycleError('invalid cleanup timeout')
    if admission_check() is not True:
        raise LifecycleError('admission not verified')
    process = spawn(arm)
    if process is None:
        raise LifecycleError('spawn returned no owned handle')
    try:
        pid = getattr(process, 'pid', None)
        if type(pid) is not int or pid <= 0:
            raise LifecycleError('invalid captured child PID')
        if process.poll() is not None:
            raise LifecycleError('server exited before verification')
        evidence = verify_ready_and_identity(process, arm)
        if not isinstance(evidence, dict) or not evidence:
            raise LifecycleError('server readiness and identity unverified')
        if process.poll() is not None:
            raise LifecycleError('server exited after verification')
        return run(ReadyServer(pid=pid, arm=arm, evidence=evidence))
    finally:
        (drain or drain_owned_child)(process, grace_seconds)


def drain_owned_child(process, grace_seconds):
    """Reap only the captured child; escalate TERM to KILL, then verify exit.

    Does not signal a process group or infer ownership of descendants. A live
    tree after child exit is not ruled out; integration must prove that separately.
    """
    try:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=grace_seconds)
        if process.poll() is None:
            raise LifecycleError('captured server not confirmed dead')
    except (AttributeError, OSError, subprocess.TimeoutExpired) as exc:
        raise LifecycleError('captured server drain unverified') from exc
