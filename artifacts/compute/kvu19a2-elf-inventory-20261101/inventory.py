#!/usr/bin/env python3
"""Inventory ELF bytes under a completed build root; no launch or linkage claim."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('build root must be an existing real directory')
    records = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        parent = Path(directory)
        for name in dirs:
            if (parent / name).is_symlink():
                raise ValueError('symlinked directory refused')
        for name in files:
            path = parent / name
            # Build trees commonly have shared-library symlinks. Record their target;
            # never follow them for a digest and reject escapes or dangling links.
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not target.is_relative_to(root.resolve(strict=True)) or not target.is_file():
                    raise ValueError('escaping or invalid library symlink')
                continue
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('non-regular build entry')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('non-regular build entry')
                magic = os.read(fd, 4)
                if magic != b'\x7fELF':
                    continue
                h = hashlib.sha256(magic)
                while chunk := os.read(fd, 1024 * 1024):
                    h.update(chunk)
                after = os.fstat(fd)
                ident = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if ident(before) != ident(after):
                    raise ValueError('ELF changed while being read')
                records[path.relative_to(root).as_posix()] = {'sha256': h.hexdigest(), 'bytes': after.st_size}
            finally:
                os.close(fd)
    if not records:
        raise ValueError('no ELF files found')
    return {'schema': 'kvu19.elf-inventory.v1', 'files': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.build_root), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
