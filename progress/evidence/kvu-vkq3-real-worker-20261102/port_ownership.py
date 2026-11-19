"""Verify a captured process holds the expected loopback TCP listener.

Point-in-time evidence only: keep the captured process alive and recheck before
use. This does not establish exclusive ownership, HTTP identity or custody.
"""
import os
from pathlib import Path
import re

_SOCKET = re.compile(r'socket:\[(\d+)\]\Z')


def process_birth(pid, proc_root='/proc'):
    raw = (Path(proc_root) / str(pid) / 'stat').read_text(encoding='ascii')
    try:
        # comm may contain spaces and parentheses; fields after the last ') '
        # start at field 3, so field 22 (starttime) is element 19.
        fields = raw.rsplit(') ', 1)[1].split()
        return int(fields[19])
    except (IndexError, ValueError) as exc:
        raise ValueError('malformed process stat') from exc


def owns_loopback_listener(pid, birth_ticks, port, proc_root='/proc'):
    """Return whether PID/birth holds an IPv4 127.0.0.1:port LISTEN socket.

    Errors inspecting /proc propagate: callers must refuse on exceptions.
    A positive result is point-in-time; another process may share the fd, and
    process/socket replacement after return remains possible.
    """
    if type(pid) is not int or pid <= 0 or type(birth_ticks) is not int or birth_ticks < 0:
        raise ValueError('invalid process identity')
    if type(port) is not int or not 0 < port < 65536:
        raise ValueError('invalid TCP port')
    proc = Path(proc_root) / str(pid)
    if process_birth(pid, proc_root) != birth_ticks:
        return False
    inodes = set()
    for fd in (proc / 'fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            # A descriptor may close during inspection; it cannot prove ownership.
            continue
        match = _SOCKET.fullmatch(target)
        if match:
            inodes.add(match.group(1))
    if not inodes:
        return False
    target_local = f'0100007F:{port:04X}'
    with (proc / 'net' / 'tcp').open(encoding='ascii') as stream:
        next(stream, None)
        found = False
        for line in stream:
            fields = line.split()
            if len(fields) < 10:
                raise ValueError('malformed TCP table')
            if fields[1].upper() == target_local and fields[3] == '0A' and fields[9] in inodes:
                found = True
                break
    return found and process_birth(pid, proc_root) == birth_ticks
