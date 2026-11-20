"""Configure only a newly created target-precision leaf in a delegated cgroup.

Never enables a parent's controllers, moves a process, or changes shared limits.
A failed new leaf is retained for inspection; existing leaves are never reused.
"""
import argparse
import json
import os
from pathlib import Path
import re

from preparation import check_cgroup, positive


def _mounted_cgroup2(path):
    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        raw = left.split()[4]
        mount = Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), raw))
        if path == mount or mount in path.parents:
            mounts.append((len(mount.parts), right.split()[0]))
    if not mounts or max(mounts)[1] != 'cgroup2':
        raise ValueError('delegated parent must be on cgroup2')


def _new_leaf(path):
    path.mkdir()  # no exist_ok: never adopt a preexisting/shared leaf


def _write_control(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        data = (str(value)+'\n').encode()
        if os.write(fd, data) != len(data):
            raise OSError('short cgroup control write')
    finally:
        os.close(fd)


def provision(parent, name, memory_max_bytes):
    positive(memory_max_bytes, 'memory cap')
    parent = Path(parent)
    if not parent.is_absolute() or '..' in parent.parts:
        raise ValueError('absolute canonical delegated parent required')
    for ancestor in [parent, *parent.parents]:
        if ancestor.is_symlink():
            raise ValueError('symlink delegated parent')
    if not parent.is_dir() or parent.resolve() != parent:
        raise ValueError('canonical delegated parent required')
    if not isinstance(name, str) or not re.fullmatch(r'df2-tp-[a-z0-9][a-z0-9-]{0,63}', name):
        raise ValueError('task-owned df2-tp leaf name required')
    _mounted_cgroup2(parent)
    # Require an already delegated domain. Do not mutate subtree_control.
    for control in ['cgroup.type', 'cgroup.subtree_control', 'cgroup.procs']:
        if (parent/control).is_symlink():
            raise ValueError('symlink parent control')
    if (parent/'cgroup.type').read_text().strip() != 'domain':
        raise ValueError('domain parent required')
    if 'memory' not in (parent/'cgroup.subtree_control').read_text().split():
        raise ValueError('parent memory controller must already be delegated')
    if (parent/'cgroup.procs').read_text().strip():
        raise ValueError('delegated parent must be empty')
    leaf = parent/name
    _new_leaf(leaf)
    for control, value in [('memory.max', memory_max_bytes),
                           ('memory.swap.max', 0), ('memory.oom.group', 1)]:
        _write_control(leaf/control, value)
    check_cgroup(leaf, memory_max_bytes)
    if list(leaf.glob('*/cgroup.procs')):
        raise ValueError('new leaf unexpectedly has descendants')
    return dict(schema='epyc.target-precision.cgroup-leaf.v1', status='CONFIGURED',
                path=str(leaf), device=leaf.stat().st_dev, inode=leaf.stat().st_ino,
                memory_max_bytes=memory_max_bytes, swap_max_bytes=0, oom_group=1,
                processes_moved=False, execution_admitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--memory-max-bytes', required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(provision(args.parent, args.name, args.memory_max_bytes), sort_keys=True))
