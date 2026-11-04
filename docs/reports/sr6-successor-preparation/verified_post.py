#!/usr/bin/env python3
"""Fail-closed request guard for the SR-6 controller (not grant admission).

The caller must supply a real grant checker and exclusive server/port ownership.
Linux /proc checks bind a listener to the captured PID and its start time at the
moment of inspection. They do not eliminate a close/rebind race, prove residency,
or replace kernel-level admission, source seals, STOP handling, or tree drain.
"""
import math
import os
from pathlib import Path
import time

from loopback_transport import LoopbackCompletion
from server_lifecycle import ReadyServer


def process_starttime(pid):
    """Return Linux /proc starttime (clock ticks), rejecting inaccessible PIDs."""
    if type(pid) is not int or pid <= 0:
        raise ValueError('invalid pid')
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        tail = raw[raw.rindex(')') + 2:].split()
        value = int(tail[19])  # field 22; tail starts at field 3
        if value <= 0:
            raise ValueError('invalid start time')
        return value
    except (OSError, ValueError, IndexError) as exc:
        raise ValueError('process identity unavailable') from exc


def verify_owned_loopback_listener(pid, birth, port):
    """Require a unique IPv4 127.0.0.1 listener in the captured process's fd set."""
    if type(birth) is not int or birth <= 0 or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid listener identity')
    if process_starttime(pid) != birth:
        raise ValueError('process identity changed')
    try:
        owned = set()
        for fd in Path(f'/proc/{pid}/fd').iterdir():
            try:
                target = os.readlink(fd)
            except FileNotFoundError:
                continue
            if target.startswith('socket:[') and target.endswith(']'):
                owned.add(target[8:-1])
        lines = Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]
        matches = []
        for line in lines:
            fields = line.split()
            local = fields[1].split(':')
            if fields[3] == '0A' and int(local[1], 16) == port:
                matches.append((local[0], fields[9]))
        if len(matches) != 1 or matches[0][0] != '0100007F' or matches[0][1] not in owned:
            raise ValueError('listener ownership not established')
        if process_starttime(pid) != birth:
            raise ValueError('process identity changed')
    except (OSError, IndexError) as exc:
        raise ValueError('listener inspection failed') from exc
    return True


class VerifiedPost:
    """Compose controller transport with repeated external admission and PID checks."""
    def __init__(self, *, port, timeout_s, max_response_bytes, deadline, stop_file, admission_check):
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or not isinstance(stop_file, Path) or not callable(admission_check)):
            raise ValueError('deadline, stop path and grant checker required')
        self.deadline, self.stop_file, self.admission_check = deadline, stop_file, admission_check
        self.timeout_s = timeout_s
        self._next_admission_check = 0.0
        self._admission_ok = False
        self.transport = LoopbackCompletion(port, timeout_s, max_response_bytes,
            continue_check=self._continue_request)

    def _continue_request(self):
        # STOP/deadline are checked on every transport poll. A full ownership
        # audit is expensive, so it runs at most once per second in flight.
        if os.path.lexists(self.stop_file) or time.time() >= self.deadline:
            return False
        now = time.monotonic()
        if now >= self._next_admission_check:
            try:
                self._admission_ok = self.admission_check() is True
            except Exception:
                self._admission_ok = False
            self._next_admission_check = now + 1.0
        return self._admission_ok

    def __call__(self, server, payload):
        if not isinstance(server, ReadyServer) or not isinstance(server.evidence, dict):
            raise ValueError('verified server evidence required')
        if self.admission_check() is not True or os.path.lexists(self.stop_file):
            raise ValueError('admission revoked or stop requested')
        if time.time() + self.timeout_s >= self.deadline:
            raise ValueError('insufficient request time remaining')
        verify_owned_loopback_listener(server.pid, server.evidence.get('starttime_ticks'), self.transport.port)
        if self.admission_check() is not True or os.path.lexists(self.stop_file):
            raise ValueError('admission revoked or stop requested')
        self._next_admission_check = 0.0
        return self.transport(server, payload)
