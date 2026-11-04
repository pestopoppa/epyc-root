"""Read-only, fail-closed context for prospective KPF-50 cgroup admission.

This diagnostic never admits a run: mount and capability snapshots cannot
exclude writable alternate groups, namespace races, or later privilege change.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os
import stat
import sys


@dataclass(frozen=True)
class Assessment:
    admitted: bool
    reasons: list[str]
    pid: int
    mount_id: int | None
    mount_point: str | None
    mount_options: tuple[str, ...]
    cap_eff: int | None
    target_writable: bool | None


def parse_mountinfo(raw: str) -> list[tuple[int, str, tuple[str, ...]]]:
    found = []
    for line in raw.splitlines():
        fields = line.split()
        if '-' not in fields:
            raise ValueError('missing mountinfo separator')
        pos = fields.index('-')
        if pos < 6 or len(fields) <= pos + 3:
            raise ValueError('malformed mountinfo entry')
        if fields[pos + 1] != 'cgroup2':
            continue
        # Reject escaped names: this diagnostic never guesses path semantics.
        if '\\' in fields[4]:
            raise ValueError('escaped cgroup2 mount path')
        found.append((int(fields[0]), fields[4], tuple(fields[5].split(','))))
    return found


def parse_cap_eff(raw: str) -> int:
    values = [line.split(':', 1)[1].strip() for line in raw.splitlines()
              if line.startswith('CapEff:')]
    if len(values) != 1 or not values[0] or any(c not in '0123456789abcdefABCDEF' for c in values[0]):
        raise ValueError('missing or ambiguous effective capabilities')
    return int(values[0], 16)


def inspect(parent: Path, *, mountinfo: str, status: str, pid: int | None = None) -> Assessment:
    """Collect bounded facts and always refuse; this is not an admission grant."""
    reasons = []
    mount_id = None
    mount_point = None
    options: tuple[str, ...] = ()
    caps = None
    writable = None
    parent = Path(parent)
    try:
        if not parent.is_absolute() or '..' in parent.parts or parent.resolve(strict=True) != parent:
            raise ValueError('path is not canonical or includes a symlink')
        procs = parent / 'cgroup.procs'
        if not stat.S_ISREG(procs.lstat().st_mode):
            raise ValueError('cgroup.procs is not regular')
        matches = [(mid, point, opt) for mid, point, opt in parse_mountinfo(mountinfo)
                   if parent == Path(point) or Path(point) in parent.parents]
        if len(matches) != 1:
            raise ValueError('cgroup2 mount is missing or ambiguous')
        mount_id, mount_point, options = matches[0]
        caps = parse_cap_eff(status)
        writable = os.access(procs, os.W_OK, effective_ids=True, follow_symlinks=False)
        if writable:
            reasons.append('effective identity can write target cgroup.procs')
        if caps:
            reasons.append('effective capabilities are nonzero and require independent review')
    except (OSError, ValueError, NotImplementedError) as exc:
        reasons.append('context unavailable: ' + str(exc))
    reasons.append('alternate groups, namespace, ACL and subsequent changes remain unproven')
    return Assessment(False, reasons, os.getpid() if pid is None else pid,
                      mount_id, mount_point, options, caps, writable)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: context.py /absolute/cgroup-parent')
    try:
        result = inspect(Path(sys.argv[1]), mountinfo=Path('/proc/self/mountinfo').read_text(),
                         status=Path('/proc/self/status').read_text())
    except OSError as exc:
        print(json.dumps({'admitted': False, 'reasons': ['proc context unavailable: ' + str(exc)]}))
        raise SystemExit(1)
    print(json.dumps(asdict(result), sort_keys=True))
    raise SystemExit(1)
