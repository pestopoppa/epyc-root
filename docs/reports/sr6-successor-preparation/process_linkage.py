#!/usr/bin/env python3
"""Fail-closed snapshot of a captured SR-6 process's mapped kernel libraries.

Call only after an independently approved runtime manifest has been checked.
This is a momentary Linux /proc identity check, not a model, grant, residency,
or future-library-load proof; independently guard those invariants during work.
"""
import os
from pathlib import Path

from runtime_manifest import REQUIRED
from verified_post import process_starttime

_LIBS = frozenset(name for name in REQUIRED if name.startswith('bin/lib'))
_PREFIXES = ('libggml', 'libllama', 'libmtmd')


def inspect_maps(maps, build_root):
    """Check named mapped libraries and their actual filesystem device/inode."""
    if not isinstance(maps, str) or not isinstance(build_root, Path) or not build_root.is_absolute():
        raise ValueError('maps and absolute build root required')
    root = build_root.resolve(strict=True)
    expected = {str(root / name): name for name in _LIBS}
    seen = set()
    for line in maps.splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) < 5:
            raise ValueError('malformed maps entry')
        if len(parts) != 6:
            continue
        path = parts[5]
        if path.endswith(' (deleted)'):
            if Path(path[:-10]).name.startswith(_PREFIXES):
                raise ValueError('deleted kernel mapping')
            continue
        if not Path(path).name.startswith(_PREFIXES):
            continue
        if path not in expected:
            raise ValueError('unexpected kernel mapping: ' + path)
        try:
            major, minor = (int(x, 16) for x in parts[3].split(':'))
            inode = int(parts[4])
            st = os.stat(path, follow_symlinks=False)
        except (OSError, ValueError) as exc:
            raise ValueError('kernel mapping identity unavailable') from exc
        if not inode or (major, minor, inode) != (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino):
            raise ValueError('kernel mapping identity changed')
        seen.add(expected[path])
    if seen != _LIBS:
        raise ValueError('required kernel mappings missing')
    return sorted(seen)


def verify_process_linkage(pid, starttime, build_root):
    """Check captured process identity, executable and loaded library mappings."""
    if not isinstance(build_root, Path) or not build_root.is_absolute():
        raise ValueError('absolute build root required')
    if type(starttime) is not int or starttime <= 0 or process_starttime(pid) != starttime:
        raise ValueError('process identity changed')
    try:
        executable = (build_root.resolve(strict=True) / 'bin/llama-server').stat()
        actual = Path(f'/proc/{pid}/exe').stat()
        if (executable.st_dev, executable.st_ino) != (actual.st_dev, actual.st_ino):
            raise ValueError('server executable identity mismatch')
        maps = Path(f'/proc/{pid}/maps').read_text()
        checked = inspect_maps(maps, build_root)
        if process_starttime(pid) != starttime:
            raise ValueError('process identity changed')
        return {'pid': pid, 'starttime_ticks': starttime, 'mapped_kernel_artifacts': checked,
                'limitations': ['snapshot only', 'manifest approval and content seal external',
                                'future library loads, model, grant and placement unverified']}
    except OSError as exc:
        raise ValueError('process linkage unavailable') from exc
