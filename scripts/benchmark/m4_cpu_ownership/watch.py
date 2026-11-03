"""Run one M4 workload under STOP / HOLD / grant / deadline polling with cleanup.

Containment: when `M4_DELEGATED_CGROUP_PARENT` names a usable cgroup v2 directory,
the workload runs in a fresh private child cgroup and cleanup is `cgroup.kill`.
Otherwise (a bare run) the workload is its own session (setsid); cleanup signals
that session and every birth-verified PID in the server registry. Either way the
run starts: an unset `M4_OWNED_CGROUP` is never an error. The CPU-region lease is
held by the caller (`region-lock run`); the kernel releases it when that exits.
"""
import hashlib, json, os, select, signal, time, uuid
from pathlib import Path
import owned
import m4_cgroup_guard


def _private_cgroup(parent):
    if not parent:
        return None, 'no delegated cgroup parent'
    try:
        parent = Path(parent).resolve(strict=True)
        parent.relative_to(Path('/sys/fs/cgroup').resolve(strict=True))
        cg = parent/('m4-private-'+uuid.uuid4().hex); cg.mkdir(mode=0o700)
    except (OSError, ValueError) as exc:
        return None, f'cgroup unavailable: {exc}'
    if not (cg/'cgroup.kill').is_file():
        cg.rmdir(); return None, 'cgroup.kill unavailable'
    return cg, None


def _killpg(pgid, sig):
    try: os.killpg(pgid, sig)
    except ProcessLookupError: pass


def _stop_session(proc, fd):
    # Signal the group only while its leader is unreaped (its PGID cannot be reused).
    _killpg(proc.pid, signal.SIGTERM)
    if not select.select([fd], [], [], 10)[0]:
        try: signal.pidfd_send_signal(fd, signal.SIGKILL)
        except ProcessLookupError: pass
        select.select([fd], [], [], 10)
    _killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10)


def _registry_live(registry):
    live = []
    for line in registry.read_text().splitlines():
        try: pid, stamp = (int(x) for x in line.split())
        except ValueError: continue
        try: fd = os.pidfd_open(pid)
        except ProcessLookupError: continue
        try:
            if not owned.exited(fd) and owned.birth(pid) == stamp: live.append(fd); continue
        except (OSError, IndexError, ValueError): pass
        os.close(fd)
    return live


def _session_members(sid):
    found = []
    for name in os.listdir('/proc'):
        if name.isdigit():
            try:
                if os.getsid(int(name)) == sid: found.append(int(name))
            except OSError: pass
    return found


def _drain_session(sid, registry, deadline_s=10):
    """Kill detached servers recorded (pid + birth) by owned.spawn; report emptiness."""
    for fd in _registry_live(registry):
        try: signal.pidfd_send_signal(fd, signal.SIGKILL)
        except ProcessLookupError: pass
        finally: os.close(fd)
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        live = _registry_live(registry)
        for fd in live: os.close(fd)
        if not live and not _session_members(sid): return True
        time.sleep(.05)
    return False


def run(cmd, grant, stop, hold, deadline, out, env=None):
    out = Path(out); grant = Path(grant); stop = Path(stop); hold = Path(hold)
    registry = out/'server-pids.txt'; registry.touch(exist_ok=False)
    original = hashlib.sha256(grant.read_bytes()).digest()
    signals = []; prior = {}; proc = None; fd = None; cg = None; result = {'status': 'error'}
    e = dict(os.environ if env is None else env)
    def guard():
        if signals: return 'SIGNAL_'+str(signals[0])
        if stop.exists(): return 'STOP'
        if list(hold.glob('HOLD_*')): return 'HOLD'
        try:
            if hashlib.sha256(grant.read_bytes()).digest() != original: return 'GRANT_CHANGED'
        except OSError: return 'GRANT_MISSING'
        if time.time() >= deadline: return 'DEADLINE'
        return None
    try:
        reason = guard()
        if reason: result.update(reason=reason, rc=124); return 124
        cg, note = _private_cgroup(e.get('M4_DELEGATED_CGROUP_PARENT'))
        result['containment'] = 'cgroup' if cg else 'session'
        (out/'containment.json').write_text(json.dumps(
            {'mode': result['containment'], 'path': str(cg) if cg else None, 'note': note})+'\n')
        if cg: e['M4_OWNED_CGROUP'] = str(cg)
        else: e.pop('M4_OWNED_CGROUP', None)
        e['M4_SERVER_PID_REGISTRY'] = str(registry)
        e.pop('FILLER_PIDFILE', None)
        for sig in (signal.SIGTERM, signal.SIGINT):
            prior[sig] = signal.signal(sig, lambda number, frame: signals.append(number))
        proc, fd, stamp = owned.spawn(cmd, env=e, attach=cg)
        # Pidfile: the session leader's identity (its PID is also the session/group id).
        (out/'supervisor.json').write_text(json.dumps({'pid': proc.pid, 'birth': stamp})+'\n')
        while not owned.exited(fd):
            reason = guard()
            if reason: break
            time.sleep(.1)
        reason = reason or guard()
        if cg is None: _stop_session(proc, fd)
        elif reason: owned.stop(proc, fd, stamp)
        else: proc.wait(timeout=10)
        result.update(reason=reason or 'none', rc=proc.returncode)
        return 124 if reason else proc.returncode
    finally:
        try:
            if cg is not None:
                # Includes detached servers and descendants even after a supervisor SIGKILL.
                m4_cgroup_guard.drain(cg)
                result['containment_empty'] = True
                cg.rmdir()
                if proc is not None and proc.returncode is None: proc.wait(timeout=10)
            elif proc is not None:
                if proc.returncode is None: _stop_session(proc, fd)
                result['containment_empty'] = _drain_session(proc.pid, registry)
                if not result['containment_empty']: raise RuntimeError('session or registry not drained')
            result['status'] = 'closed'
        except BaseException as exc:
            result['cleanup_error'] = repr(exc)
            raise  # a failed drain overrides a successful/STOP return
        finally:
            if fd is not None: os.close(fd)
            for sig, handler in prior.items(): signal.signal(sig, handler)
            (out/'watch-result.json').write_text(json.dumps(result, sort_keys=True)+'\n')
