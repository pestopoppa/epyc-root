"""Read-only Linux listener ownership check for the exact captured exec-chain PID."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


class OwnershipError(RuntimeError):
    pass


def start_time(pid: int, *, proc: Path = Path('/proc')) -> str:
    raw = (proc / str(pid) / 'stat').read_text()
    return raw[raw.rfind(')') + 2:].split()[19]


def listener_owned(pid: int, port: int, birth: str, *, proc: Path = Path('/proc')) -> bool:
    """False means no listener yet; foreign/unknown/recycled identity raises."""
    if not birth or start_time(pid, proc=proc) != birth:
        raise OwnershipError('captured server process identity changed')
    owned = set()
    for fd in (proc / str(pid) / 'fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue  # descriptor churn, not loss of the process
        if target.startswith('socket:['):
            owned.add(target[8:-1])
    listeners = set()
    # The server is launched with --host 127.0.0.1. Include wildcard listeners
    # because those can also answer the IPv4 health request.
    for name, addresses in [('tcp', {'0100007F', '00000000'}), ('tcp6', {'0' * 32})]:
        table = proc / str(pid) / 'net' / name
        for line in table.read_text().splitlines()[1:]:
            fields = line.split()
            address, number = fields[1].split(':')
            if fields[3] == '0A' and int(number, 16) == port and address in addresses:
                listeners.add(fields[9])
    if start_time(pid, proc=proc) != birth:
        raise OwnershipError('captured process changed during socket inspection')
    if listeners and not listeners <= owned:
        raise OwnershipError('listener is not owned by captured server PID')
    return bool(listeners)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--port', type=int)
    parser.add_argument('--birth')
    args = parser.parse_args()
    try:
        if args.port is None:
            print(start_time(args.pid))
            return 0
        if not 1 <= args.port <= 65535:
            raise OwnershipError('invalid port')
        return 0 if listener_owned(args.pid, args.port, args.birth or '') else 1
    except (OSError, ValueError, IndexError, OwnershipError) as exc:
        print(f'DF29 listener ownership refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
