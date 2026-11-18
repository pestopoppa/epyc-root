#!/usr/bin/env python3
"""Own-port proof without `ss` (the keeper's job environment has no iproute2: 'ss: command not found').

  own_port_proof.py listening PORT    rc 0 if ANY process listens on loopback/any PORT (tcp, v4 or v6), else 1
  own_port_proof.py owner PORT PID    rc 0 only if the LISTEN socket on PORT belongs to PID's open fds, else 1

Reads /proc/net/tcp{,6} (LISTEN = state 0A) and /proc/<pid>/fd socket inodes. Read-only, no process is signalled."""
import os
import sys


def listen_inodes(port: int) -> set[str]:
    out = set()
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = open(f).read().splitlines()[1:]
        except OSError:
            continue
        for ln in lines:
            p = ln.split()
            if len(p) > 9 and p[3] == "0A" and int(p[1].rsplit(":", 1)[1], 16) == port:
                out.add(p[9])
    return out


def pid_socket_inodes(pid: int) -> set[str]:
    out = set()
    try:
        for fd in os.listdir(f"/proc/{pid}/fd"):
            try:
                t = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if t.startswith("socket:["):
                out.add(t[8:-1])
    except OSError:
        pass
    return out


def main(argv) -> int:
    if len(argv) == 3 and argv[1] == "listening":
        return 0 if listen_inodes(int(argv[2])) else 1
    if len(argv) == 4 and argv[1] == "owner":
        li = listen_inodes(int(argv[2]))
        return 0 if li and li & pid_socket_inodes(int(argv[3])) else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
