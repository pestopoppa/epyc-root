"""Fail-closed KPF-50 cgroup admission diagnostic, not a containment proof.

No cgroup or process is modified.  A negative writability check is insufficient:
capabilities, ACLs, alternate mounts, namespaces, and later permission changes
can all defeat it.  Consequently this diagnostic does not admit a native run.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import stat

@dataclass(frozen=True)
class Refusal:
    admitted: bool
    reason: str
    checked_path: str


def check_parent(parent: Path) -> Refusal:
    """Refuse admission; give a concrete writable-parent reason when observable."""
    parent = Path(parent)
    if not parent.is_absolute() or '..' in parent.parts or parent.is_symlink():
        return Refusal(False, 'parent path is not absolute and non-symlink', str(parent))
    try:
        resolved = parent.resolve(strict=True)
        if resolved != parent:
            return Refusal(False, 'parent path has a symlink component', str(parent))
        procs = resolved / 'cgroup.procs'
        st = procs.lstat()
        if not stat.S_ISREG(st.st_mode):
            return Refusal(False, 'parent cgroup.procs is not a regular file', str(procs))
        if os.access(procs, os.W_OK, effective_ids=True, follow_symlinks=False):
            return Refusal(False, 'effective identity can write parent cgroup.procs', str(procs))
    except (OSError, ValueError, NotImplementedError):
        return Refusal(False, 'parent access cannot be established', str(parent))
    return Refusal(False, 'unverified alternate groups, ACLs, capabilities, namespaces and races', str(procs))


if __name__ == '__main__':
    import json
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('usage: admission.py /absolute/cgroup-parent')
    result = check_parent(Path(sys.argv[1]))
    print(json.dumps(result.__dict__, sort_keys=True))
    raise SystemExit(0 if result.admitted else 1)
