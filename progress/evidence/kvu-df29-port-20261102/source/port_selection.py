"""Select a currently bindable private IPv4 loopback port; never reserves it."""
from __future__ import annotations

import argparse
import socket
import sys


def select_port(port: str = 'auto', *, first: int = 18093, last: int = 18192) -> int:
    if not 1024 <= first <= last <= 65535 or last - first >= 1024:
        raise ValueError('port range must contain 1..1024 unprivileged ports')
    if port == 'auto':
        candidates = range(first, last + 1)
    else:
        try:
            explicit = int(port)
        except ValueError as exc:
            raise ValueError('port must be auto or an integer') from exc
        if not 1024 <= explicit <= 65535:
            raise ValueError('explicit port must be unprivileged and <=65535')
        candidates = [explicit]
    for candidate in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(('127.0.0.1', candidate))
            except OSError:
                continue
        return candidate
    raise RuntimeError('no bindable port in requested selection')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='auto')
    parser.add_argument('--first', type=int, default=18093)
    parser.add_argument('--last', type=int, default=18192)
    args = parser.parse_args()
    try:
        chosen = select_port(args.port, first=args.first, last=args.last)
    except (ValueError, RuntimeError) as exc:
        print(f'DF29 port selection refused: {exc}', file=sys.stderr)
        return 2
    print(chosen)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
