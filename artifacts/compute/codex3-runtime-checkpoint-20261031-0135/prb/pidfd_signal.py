#!/usr/bin/python3
"""Fail-closed signal delivery to a previously captured process identity."""
from __future__ import annotations

import os
from pathlib import Path
import select
import signal
import sys
import time


class Refused(RuntimeError):
    pass


def read_identity(pid: int):
    """Return (start_ticks, uid, sid, pgid, state), or None if gone."""
    root = Path("/proc") / str(pid)
    try:
        fields = (root / "stat").read_text(encoding="ascii").rsplit(") ", 1)[1].split()
        status = (root / "status").read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, ProcessLookupError):
        return None
    except (PermissionError, OSError) as exc:
        raise Refused(f"cannot read process identity pid={pid}: {exc}") from exc
    if len(fields) < 20:
        raise Refused(f"short /proc stat for pid={pid}")
    uid_rows = [line.split() for line in status if line.startswith("Uid:")]
    if len(uid_rows) != 1 or len(uid_rows[0]) != 5:
        raise Refused(f"unparseable Uid row for pid={pid}")
    uid_values = tuple(int(value) for value in uid_rows[0][1:])
    if len(set(uid_values)) != 1:
        raise Refused(f"process uid fields disagree for pid={pid}")
    try:
        state = fields[0]
        pgid = int(fields[2])
        sid = int(fields[3])
        start = int(fields[19])
    except ValueError as exc:
        raise Refused(f"invalid /proc stat identity for pid={pid}") from exc
    return (start, uid_values[0], sid, pgid, state)


def signal_captured(pid: int, expected: tuple[int, int, int, int], sig: int,
                    *, opener=None, identity_reader=None, sender=None, closer=None) -> str:
    """Open pidfd first, then validate /proc identity and signal only that fd."""
    if opener is None and not hasattr(os, "pidfd_open"):
        raise Refused("pidfd_open unavailable; numeric-signal fallback is forbidden")
    if sender is None and not hasattr(signal, "pidfd_send_signal"):
        raise Refused("pidfd_send_signal unavailable; numeric-signal fallback is forbidden")
    # Avoid truthiness-based fallback: a caller may inject deliberately failing
    # test doubles, and production must never silently select another signal
    # mechanism.
    if opener is None:
        opener = os.pidfd_open
    if identity_reader is None:
        identity_reader = read_identity
    if sender is None:
        sender = signal.pidfd_send_signal
    if closer is None:
        closer = os.close
    try:
        pidfd = opener(pid, 0)
    except ProcessLookupError:
        return "gone"
    except OSError as exc:
        raise Refused(f"pidfd_open failed for captured pid={pid}: {exc}") from exc
    try:
        current = identity_reader(pid)
        if current is None:
            return "gone"
        if tuple(current[:4]) != tuple(expected):
            raise Refused(f"captured identity mismatch pid={pid} expected={expected} current={current[:4]}")
        try:
            sender(pidfd, sig, None, 0)
        except ProcessLookupError:
            return "gone"
        except OSError as exc:
            raise Refused(f"pidfd_send_signal failed for captured pid={pid}: {exc}") from exc
        return "signalled"
    finally:
        closer(pidfd)


def _pidfd_exited(pidfd: int) -> bool:
    poller = select.poll()
    poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
    return bool(poller.poll(0))


def pidfd_is_exited(pidfd: int) -> bool:
    """Return whether a retained pidfd is readable for process exit."""
    return _pidfd_exited(pidfd)


def signal_pidfd(pidfd: int, sig: int) -> str:
    """Signal an already captured pidfd; never resolve or signal a numeric PID."""
    if not hasattr(signal, "pidfd_send_signal"):
        raise Refused("pidfd_send_signal unavailable; numeric-signal fallback is forbidden")
    try:
        signal.pidfd_send_signal(pidfd, sig, None, 0)
    except ProcessLookupError:
        return "gone"
    except OSError as exc:
        raise Refused(f"pidfd_send_signal failed: {exc}") from exc
    return "signalled"


def _group_candidates(session_id: int, process_group_id: int):
    """Yield PIDs observed in the real captured session (any process group)."""
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="ascii").rsplit(") ", 1)[1].split()
            sid, pgid = int(fields[3]), int(fields[2])
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (OSError, IndexError, ValueError) as exc:
            raise Refused(f"cannot parse process-group candidate pid={entry.name}: {exc}") from exc
        if sid == session_id:
            yield int(entry.name)


def signal_captured_group(anchor_pid: int, expected: tuple[int, int, int, int], sig: int,
                          *, opener=None, identity_reader=None, sender=None,
                          closer=None, exited=None, verify_cleanup=False,
                          grace_seconds=2.0, monotonic=None, sleeper=None) -> int:
    """Census one anchored process group and signal only pidfds pinned in-census.

    The leader pidfd is opened and validated first. Every matching member pidfd
    is then opened and validated while that anchor is live. After census, the
    anchor pidfd and real `/proc` tuple are checked again before any signal.
    A leader exit/reuse during census refuses without sending to any member.
    Tests inject the in-memory candidate enumerator and identity/signal
    functions; production enumeration always reads the fixed real `/proc`.
    """
    if opener is None and not hasattr(os, "pidfd_open"):
        raise Refused("pidfd_open unavailable; numeric-signal fallback is forbidden")
    if sender is None and not hasattr(signal, "pidfd_send_signal"):
        raise Refused("pidfd_send_signal unavailable; numeric-signal fallback is forbidden")
    opener = os.pidfd_open if opener is None else opener
    identity_reader = read_identity if identity_reader is None else identity_reader
    sender = signal.pidfd_send_signal if sender is None else sender
    closer = os.close if closer is None else closer
    exited = _pidfd_exited if exited is None else exited
    monotonic = time.monotonic if monotonic is None else monotonic
    sleeper = time.sleep if sleeper is None else sleeper

    anchor_fd = None
    member_fds: list[tuple[int, int, tuple[int, int, int, int, str]]] = []
    try:
        try:
            anchor_fd = opener(anchor_pid, 0)
        except ProcessLookupError:
            raise Refused("captured group leader disappeared before census")
        except OSError as exc:
            raise Refused(f"cannot pin captured group leader pid={anchor_pid}: {exc}") from exc
        anchor_now = identity_reader(anchor_pid)
        if anchor_now is None or tuple(anchor_now[:4]) != tuple(expected):
            raise Refused("captured group leader identity mismatch before census")
        if exited(anchor_fd):
            raise Refused("captured group leader exited before census")

        helper_pid = os.getpid()
        for pid in _group_candidates(expected[2], expected[3]):
            # This helper is launched inside the captured session to perform
            # cleanup. Never include or signal its own process.
            if pid == helper_pid:
                continue
            try:
                member_fd = opener(pid, 0)
            except ProcessLookupError:
                continue
            except OSError as exc:
                raise Refused(f"cannot pin group member pid={pid}: {exc}") from exc
            keep = False
            try:
                member_now = identity_reader(pid)
                if member_now is None:
                    continue
                if member_now[1] != expected[1]:
                    raise Refused(f"group member UID mismatch pid={pid}")
                if member_now[2] != expected[2]:
                    # It left the target group between the stat read and pidfd
                    # validation. The pinned process is not signaled.
                    continue
                member_fds.append((pid, member_fd, tuple(member_now)))
                keep = True
            finally:
                if not keep:
                    closer(member_fd)

        anchor_final = identity_reader(anchor_pid)
        if exited(anchor_fd) or anchor_final is None or tuple(anchor_final[:4]) != tuple(expected):
            raise Refused("captured group leader exited or changed during census")

        # Keep the session leader alive as the ownership anchor through the
        # first member signals; signal it last when it is part of the group.
        member_fds.sort(key=lambda item: item[0] == anchor_pid)
        sent = 0
        for _pid, member_fd, _identity in member_fds:
            if exited(anchor_fd):
                raise Refused("captured group leader exited before census-bound signals completed")
            try:
                sender(member_fd, sig, None, 0)
                sent += 1
            except ProcessLookupError:
                continue
            except OSError as exc:
                raise Refused(f"pidfd group signal refused: {exc}") from exc
        if verify_cleanup:
            def wait_members() -> bool:
                deadline = monotonic() + grace_seconds
                while monotonic() < deadline:
                    if all(exited(fd) for _pid, fd, _ident in member_fds) and exited(anchor_fd):
                        return True
                    sleeper(min(0.05, max(0.0, deadline - monotonic())))
                return all(exited(fd) for _pid, fd, _ident in member_fds) and exited(anchor_fd)

            if not wait_members():
                # These descriptors were pinned while the live leader anchored
                # the complete session census. Escalation targets only those
                # same processes, even if the leader exited after TERM.
                for _pid, member_fd, _identity in member_fds:
                    if not exited(member_fd):
                        try:
                            sender(member_fd, signal.SIGKILL, None, 0)
                        except ProcessLookupError:
                            continue
                        except OSError as exc:
                            raise Refused(f"pidfd group KILL refused: {exc}") from exc
                if not wait_members():
                    raise Refused("captured session members survived TERM/KILL cleanup")
        return sent
    finally:
        for _pid, member_fd, _identity in member_fds:
            closer(member_fd)
        if anchor_fd is not None:
            closer(anchor_fd)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--group":
        if len(args) != 7:
            print("usage: pidfd_signal.py --group PID START_TICKS UID SID PGID TERM|KILL", file=sys.stderr)
            return 64
        try:
            pid, start, uid, sid, pgid = (int(value) for value in args[1:6])
            if pid <= 0 or min(start, uid, sid, pgid) < 0:
                raise ValueError("negative identity field")
            sig = {"TERM": signal.SIGTERM, "KILL": signal.SIGKILL}[args[6]]
            sent = signal_captured_group(pid, (start, uid, sid, pgid), sig)
        except (ValueError, KeyError, Refused) as exc:
            print(f"PIDFD_GROUP_SIGNAL_REFUSED {exc}", file=sys.stderr)
            return 2
        print(f"PIDFD_GROUP_SIGNAL sent={sent} anchor_pid={pid} signal={args[6]}")
        return 0
    if len(args) != 6:
        print("usage: pidfd_signal.py PID START_TICKS UID SID PGID TERM|KILL", file=sys.stderr)
        return 64
    try:
        pid, start, uid, sid, pgid = (int(value) for value in args[:5])
        if pid <= 0 or min(start, uid, sid, pgid) < 0:
            raise ValueError("negative identity field")
        sig = {"TERM": signal.SIGTERM, "KILL": signal.SIGKILL}[args[5]]
        result = signal_captured(pid, (start, uid, sid, pgid), sig)
    except (ValueError, KeyError, Refused) as exc:
        print(f"PIDFD_SIGNAL_REFUSED {exc}", file=sys.stderr)
        return 2
    print(f"PIDFD_SIGNAL {result} pid={pid} signal={args[5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
