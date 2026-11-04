"""SR-7 contained server and cancellable capture lifecycle.

Uses the SR-6 keeper and cgroup containment primitives. A deployment must bind
its approved grant, guard digest, runtime seal, model and readiness verifier;
this module does not turn caller-supplied values into authorization.
"""
import os
import math
from pathlib import Path
import sys
import time

_SR6 = str(Path(__file__).resolve().parents[1] / 'sr6-successor-preparation')
if _SR6 not in sys.path:
    sys.path.insert(0, _SR6)
from keeper_admission import KeeperAdmission
from session_drain import spawn_contained_session, drain_contained_session
from verified_post import process_starttime, verify_owned_loopback_listener
from loopback_transport import LoopbackCompletion
from server_lifecycle import ReadyServer
from capture_once import capture_once, _write_once, _json


class SmokeAdmission:
    """Non-science local dry-run, limited to the current <=4 CPU affinity."""
    def __init__(self, *, stop_path, deadline):
        if (os.environ.get('FILLER_DRYRUN') != '1' or
                not isinstance(stop_path, Path) or not stop_path.is_absolute() or
                type(deadline) not in (int, float) or not math.isfinite(deadline) or
                not time.time() < deadline <= time.time() + 1800 or
                not 1 <= len(os.sched_getaffinity(0)) <= 4):
            raise ValueError('bounded four-CPU dry-run required')
        self.stop_path, self.deadline = stop_path, deadline

    def __call__(self):
        return (os.environ.get('FILLER_DRYRUN') == '1' and
                1 <= len(os.sched_getaffinity(0)) <= 4 and
                not os.path.lexists(self.stop_path) and time.time() < self.deadline)


def capture_contained(*, root, request_id, payload, expected_names, port, timeout_s,
                      admission, argv, env, cwd, verify, trace_path,
                      grace_s=5, max_response_bytes=8 * 1024 * 1024):
    """Capture once, monitoring admission through request and draining descendants.

    `verify(process, port)` must independently verify executable, loaded library,
    model, command, readiness and placement, returning nonempty evidence. The
    predeclared launch and grant context must be authenticated by the caller.
    A failed or cancelled exposed request must never be retried. A delegated
    writable cgroup v2 and supported Landlock/seccomp are required; absence is
    a hard failure. Trace output is opened exclusively before spawning.
    """
    if (not isinstance(admission, (KeeperAdmission, SmokeAdmission)) or not callable(verify)
            or not isinstance(argv, list) or not argv or not os.path.isabs(argv[0])
            or any(not isinstance(x, str) or not x or '\0' in x for x in argv)
            or not isinstance(env, dict) or not env.get('LD_LIBRARY_PATH')
            or not isinstance(cwd, str) or not os.path.isabs(cwd)
            or not isinstance(trace_path, Path) or not trace_path.is_absolute()
            or type(grace_s) not in (int, float) or not 0 < grace_s <= 60):
        raise ValueError('invalid contained lifecycle configuration')
    if isinstance(admission, SmokeAdmission):
        from startup_identity import StartupIdentity
        if not isinstance(verify, StartupIdentity) or verify.smoke is not True or verify.cpus != os.sched_getaffinity(0):
            raise ValueError('smoke requires pinned smoke model and four-CPU verifier')
    if (not isinstance(payload, dict) or not isinstance(payload.get('prompt'), str)
            or not payload['prompt'] or payload.get('cache_prompt') is not False
            or payload.get('stream') is not False or type(payload.get('n_predict')) is not int
            or payload['n_predict'] <= 0):
        raise ValueError('uncached non-streaming completion payload required')
    holder = {}
    def launch():
        if admission() is not True:
            raise ValueError('admission revoked')
        fd = os.open(trace_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as trace:
            st = os.fstat(trace.fileno())
            holder['trace_identity'] = (st.st_dev, st.st_ino)
            process = spawn_contained_session(argv, stdout=trace, stderr=trace, env=env, cwd=cwd)
        holder['process'] = process
        return process

    def verify_owned(process, requested_port):
        if process is not holder.get('process') or admission() is not True:
            raise ValueError('unowned process or revoked admission')
        evidence = verify(process, requested_port)
        if not isinstance(evidence, dict) or not evidence or process.poll() is not None:
            raise ValueError('server identity unverified')
        birth = process_starttime(process.pid)
        verify_owned_loopback_listener(process.pid, birth, requested_port)
        if admission() is not True:
            raise ValueError('admission revoked')
        holder['birth'] = birth
        return dict(evidence, pid=process.pid, starttime_ticks=birth)

    def post(requested_port, request, request_timeout):
        process = holder['process']
        if (requested_port != port or request_timeout != timeout_s or process.poll() is not None
                or admission() is not True or time.time() + timeout_s >= admission.deadline):
            raise ValueError('admission or request deadline invalid')
        verify_owned_loopback_listener(process.pid, holder['birth'], port)
        last = [0.0, False]
        def continuing():
            if os.path.lexists(admission.stop_path) or time.time() >= admission.deadline or process.poll() is not None:
                return False
            now = time.monotonic()
            if now >= last[0]:
                last[:] = [now + 1.0, admission() is True]
            return last[1]
        transport = LoopbackCompletion(port, timeout_s, max_response_bytes, continue_check=continuing)
        return transport(ReadyServer(process.pid, 'sr7', {}), request)

    def stop(process):
        if process is not holder.get('process'):
            raise ValueError('unknown child')
        drain_contained_session(process, grace_s)
        holder['drained'] = True

    def read_trace(process):
        if process is not holder.get('process') or holder.get('drained') is not True:
            raise ValueError('contained process not drained')
        fd = os.open(trace_path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as trace:
            st = os.fstat(trace.fileno())
            if (st.st_dev, st.st_ino) != holder['trace_identity']:
                raise ValueError('trace identity changed')
            raw = trace.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('trace too large')
        return raw

    capture = _smoke_once if isinstance(admission, SmokeAdmission) else capture_once
    return capture(root=root, request_id=request_id, payload=payload,
        expected_names=expected_names, port=port, timeout_s=timeout_s, admit=admission,
        launch=launch, verify=verify_owned, stop=stop, read_trace=read_trace, post=post)


def _smoke_once(*, root, request_id, payload, expected_names, port, timeout_s,
                admit, launch, verify, stop, read_trace, post):
    """One native smoke completion, preserving identity, response and trace."""
    import json
    if expected_names != [] or request_id != 'smoke' or admit() is not True:
        raise ValueError('invalid smoke capture')
    prefix = root / request_id
    _write_once(prefix.with_suffix('.start.json'), _json({'science': False, 'request': payload}))
    process = launch()
    try:
        evidence = verify(process, port)
        _write_once(prefix.with_suffix('.exposure.json'), _json({'science': False, 'server': evidence}))
        status, raw = post(port, payload, timeout_s)
        _write_once(prefix.with_suffix('.response.bin'), raw)
        if status != 200 or not isinstance(json.loads(raw), dict):
            raise ValueError('smoke completion failed')
    finally:
        stop(process)
    _write_once(prefix.with_suffix('.trace.bin'), read_trace(process))
    return {'schema':'sr7.smoke.v1', 'state':'COMPLETE', 'science':False, 'verdict':None}
