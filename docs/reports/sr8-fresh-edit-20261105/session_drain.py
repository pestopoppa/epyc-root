#!/usr/bin/env python3
"""Linux captured-session cleanup for a future SR-6 launcher.

Only PIDs captured from the newly created session are signalled, via pidfds.
This does not establish cgroup containment: a child that changes session before
inspection can escape. A launcher must independently rule out that behavior and
prove grant, identity, deadline and residency before this is a runnable row.
"""
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import time


class DrainError(RuntimeError):
    pass


def _stat(pid):
    raw = Path(f'/proc/{pid}/stat').read_text()
    fields = raw[raw.rindex(')') + 2:].split()
    return fields[0], int(fields[3]), int(fields[19])  # state, session, starttime


def _session_members(session):
    result = {}
    try:
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():
                continue
            pid = int(path.name)
            try:
                state, sid, birth = _stat(pid)
            except FileNotFoundError:
                continue
            if sid == session and state != 'Z':
                result[pid] = birth
    except (OSError, IndexError, ValueError) as exc:
        raise DrainError('cannot inspect process session') from exc
    return result


def _signal_captured(pid, birth, session, sig):
    """Bind an inspected PID to a pidfd and revalidate before signalling."""
    fd = None
    try:
        fd = os.pidfd_open(pid)
        state, sid, actual_birth = _stat(pid)
        if state == 'Z':
            return
        if sid != session or actual_birth != birth:
            raise DrainError('captured process identity changed')
        signal.pidfd_send_signal(fd, sig)
    except ProcessLookupError:
        return
    except (OSError, IndexError, ValueError) as exc:
        raise DrainError('cannot signal captured session member') from exc
    finally:
        if fd is not None:
            os.close(fd)


def spawn_session(argv, *, stdout, stderr, env, cwd):
    """Spawn one owned child as a session leader; never use a shell."""
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(a, str) or not a for a in argv) or
            not isinstance(env, dict) or not isinstance(cwd, str)):
        raise ValueError('explicit argv, environment and cwd required')
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                            env=env, cwd=cwd, start_new_session=True, close_fds=True)


def drain_session(process, grace_seconds=10):
    """TERM then KILL captured session members, and refuse an undrained session.

    process must be the actual Popen from spawn_session, with PID equal to its
    session ID. This scoped proof does not cover processes that escaped session.
    """
    if not isinstance(process, subprocess.Popen) or type(process.pid) is not int or process.pid <= 0:
        raise DrainError('captured child handle required')
    if type(grace_seconds) not in (int, float) or not 0 < grace_seconds <= 60:
        raise DrainError('invalid cleanup timeout')
    session = process.pid
    for sig in (signal.SIGTERM, signal.SIGKILL):
        members = _session_members(session)
        for pid, birth in members.items():
            _signal_captured(pid, birth, session, sig)
        deadline = time.monotonic() + grace_seconds
        while True:
            process.poll()  # reap the owned leader when it exits
            if not _session_members(session):
                process.wait(timeout=0)
                return
            if time.monotonic() >= deadline:
                break
            # A bounded child wait avoids host-wide name-based signalling.
            try:
                process.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
            else:
                # A reaped leader may have live children; avoid a busy loop.
                select.select([], [], [], min(0.05, max(0, deadline - time.monotonic())))
    raise DrainError('session still contains live processes after KILL')


def _deny_fresh_file_writes():
    """Deny fresh write-open after cgroup entry, inherited by exec and forks.

    Landlock is mandatory: a session leader on this host can otherwise migrate
    itself out of its cgroup. stdout/stderr remain usable as inherited FDs.
    This deliberately denies *all* fresh file write-opens, not just cgroupfs.
    """
    import ctypes
    import platform
    if platform.machine() != 'x86_64':
        raise DrainError('Landlock syscall numbers require x86_64')
    libc = ctypes.CDLL(None, use_errno=True)
    class Ruleset(ctypes.Structure):
        _fields_ = [('handled_access_fs', ctypes.c_uint64)]
    attr = Ruleset(1 << 1)  # LANDLOCK_ACCESS_FS_WRITE_FILE
    fd = libc.syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'landlock_create_ruleset')
    try:
        if libc.prctl(38, 1, 0, 0, 0):  # PR_SET_NO_NEW_PRIVS
            raise OSError(ctypes.get_errno(), 'PR_SET_NO_NEW_PRIVS')
        if libc.syscall(446, fd, 0):  # landlock_restrict_self
            raise OSError(ctypes.get_errno(), 'landlock_restrict_self')
    finally:
        os.close(fd)


def _deny_clone3():
    """Prevent CLONE_INTO_CGROUP from bypassing Landlock's open controls.

    Return ENOSYS so libc may use legacy clone. This is an inherited seccomp
    filter on x86_64 and its x32 syscall-number encoding, not a general sandbox.
    """
    import ctypes
    import errno
    import platform
    if platform.machine() != 'x86_64':
        raise DrainError('seccomp syscall numbers require x86_64')
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                    ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint32)]
    class Program(ctypes.Structure):
        _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]
    instructions = (Filter * 6)(
        Filter(0x20, 0, 0, 0),                 # load seccomp_data.nr
        Filter(0x15, 1, 0, 435),               # clone3 native -> reject
        Filter(0x15, 0, 1, 0x40000000 | 435),  # clone3 x32 -> reject
        Filter(0x06, 0, 0, 0x00050000 | errno.ENOSYS),
        Filter(0x06, 0, 0, 0x7fff0000),        # allow
        Filter(0x06, 0, 0, 0x7fff0000),
    )
    program = Program(len(instructions), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    # _deny_fresh_file_writes has already set PR_SET_NO_NEW_PRIVS.
    if libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), 'PR_SET_SECCOMP')


def _filesystem_type(fd):
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux statfs begins with a signed long f_type. Oversize the buffer so
    # the kernel can fill its complete platform struct safely.
    buf = ctypes.create_string_buffer(256)
    if libc.fstatfs(fd, ctypes.byref(buf)) != 0:
        raise OSError(ctypes.get_errno(), 'fstatfs')
    return ctypes.c_long.from_buffer(buf).value


def spawn_contained_session(argv, *, stdout, stderr, env, cwd, cgroup_root=Path('/sys/fs/cgroup')):
    """Spawn into a fresh cgroup before exec, then impose Landlock on child.

    Requires writable delegated cgroup v2 and Linux x86_64 Landlock. All child
    descendants inherit membership and the Landlock restriction. Output FDs
    must be regular files on a filesystem other than cgroup v2.
    """
    import uuid
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(a, str) or not a or '\0' in a for a in argv) or
            not isinstance(env, dict) or not isinstance(cwd, str) or
            not isinstance(cgroup_root, Path) or cgroup_root.is_symlink() or
            not (cgroup_root / 'cgroup.controllers').is_file()):
        raise DrainError('invalid arguments or missing cgroup v2 delegation')
    try:
        if cgroup_root.resolve(strict=True) != cgroup_root:
            raise DrainError('cgroup root must be canonical')
        root_fd = os.open(cgroup_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if _filesystem_type(root_fd) != 0x63677270:
                raise DrainError('cgroup root is not cgroup v2')
        finally:
            os.close(root_fd)
    except OSError as exc:
        raise DrainError('cannot verify cgroup filesystem') from exc
    for stream in (stdout, stderr):
        try:
            fd = stream.fileno()
            if not stat.S_ISREG(os.fstat(fd).st_mode) or _filesystem_type(fd) == 0x63677270:
                raise DrainError('output descriptor must be a regular file')
            target = os.readlink('/proc/self/fd/' + str(fd))
        except (OSError, ValueError, AttributeError) as exc:
            raise DrainError('unverifiable output descriptor') from exc
        if target.startswith(str(cgroup_root) + '/'):
            raise DrainError('cgroup output descriptor forbidden')
    group = cgroup_root / ('sr6-' + uuid.uuid4().hex)
    try:
        group.mkdir(mode=0o700)
        identity = group.stat()
        def enter_and_restrict():
            with open(group / 'cgroup.procs', 'w', encoding='ascii') as f:
                f.write(str(os.getpid()))
            _deny_fresh_file_writes()
            _deny_clone3()
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout,
            stderr=stderr, env=env, cwd=cwd, start_new_session=True,
            close_fds=True, preexec_fn=enter_and_restrict)
        process._sr6_cgroup = group
        process._sr6_cgroup_identity = (identity.st_dev, identity.st_ino)
        return process
    except BaseException:
        try:
            group.rmdir()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise DrainError('failed spawn left nonempty cgroup') from exc
        raise


def _cgroup_members(group):
    try:
        members = {}
        for line in (group / 'cgroup.procs').read_text().splitlines():
            pid = int(line)
            try:
                state, _, birth = _stat(pid)
            except FileNotFoundError:
                continue
            if state != 'Z':
                members[pid] = birth
        return members
    except (OSError, ValueError, IndexError) as exc:
        raise DrainError('cannot inspect owned cgroup') from exc


def _signal_cgroup_member(group, pid, birth, sig):
    fd = None
    try:
        fd = os.pidfd_open(pid)
        state, _, actual_birth = _stat(pid)
        if state == 'Z':
            return
        if actual_birth != birth or pid not in _cgroup_members(group):
            raise DrainError('cgroup member identity changed')
        signal.pidfd_send_signal(fd, sig)
    except ProcessLookupError:
        return
    except (OSError, IndexError, ValueError) as exc:
        raise DrainError('cannot signal captured cgroup member') from exc
    finally:
        if fd is not None:
            os.close(fd)


def drain_contained_session(process, grace_seconds=10):
    """Drain only PIDs captured from the fresh cgroup, then prove it empty."""
    if (not isinstance(process, subprocess.Popen) or
            not isinstance(getattr(process, '_sr6_cgroup', None), Path) or
            type(grace_seconds) not in (int, float) or not 0 < grace_seconds <= 60):
        raise DrainError('contained child and bounded timeout required')
    group = process._sr6_cgroup
    def verify_group():
        try:
            info = group.lstat()
            if (not stat.S_ISDIR(info.st_mode) or
                    (info.st_dev, info.st_ino) != process._sr6_cgroup_identity):
                raise DrainError('owned cgroup identity changed')
        except (OSError, AttributeError) as exc:
            raise DrainError('cannot verify cgroup identity') from exc
    for sig in (signal.SIGTERM, signal.SIGKILL):
        deadline = time.monotonic() + grace_seconds
        while True:
            process.poll()
            verify_group()
            members = _cgroup_members(group)
            if not members:
                try:
                    process.wait(timeout=0)
                    group.rmdir()  # also refuses if any child cgroup exists
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise DrainError('cannot prove cgroup drained') from exc
                return
            for pid, birth in members.items():
                verify_group()
                _signal_cgroup_member(group, pid, birth, sig)
            if time.monotonic() >= deadline:
                break
            select.select([], [], [], min(0.05, max(0, deadline - time.monotonic())))
    raise DrainError('cgroup still contains live processes after KILL')
