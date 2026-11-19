"""cgroup v2 helpers for the M4 watcher: birth stamps and a `cgroup.kill` drain.

There is no external guardian process. The watcher drains its own private
cgroup with `cgroup.kill`; the CPU-region lease is the caller's `region-lock run`.
"""
from __future__ import annotations

from pathlib import Path
import time

CGROUP_ROOT = Path('/sys/fs/cgroup')


def birth(pid: int) -> int:
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19])


def _empty(path: Path) -> bool:
    if not path.exists():
        return True
    fields = dict(line.split() for line in (path / 'cgroup.events').read_text().splitlines())
    if fields.get('populated') not in ('0', '1'):
        raise RuntimeError('unreadable cgroup population')
    return fields['populated'] == '0'


def drain(path: Path, deadline_s: float = 10) -> None:
    if not path.exists():
        return
    (path / 'cgroup.kill').write_text('1')
    deadline = time.monotonic() + deadline_s
    while not _empty(path):
        if time.monotonic() >= deadline:
            raise RuntimeError('owned cgroup failed to drain')
        time.sleep(0.02)
