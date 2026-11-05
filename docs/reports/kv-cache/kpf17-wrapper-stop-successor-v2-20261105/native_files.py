"""Validate oracle native evidence bindings without trusting file labels.

This is an isolated review candidate; it does not prove measurement validity,
race freedom, or wrapper stop precedence.
"""
import re
import stat
from pathlib import Path

NAMES = frozenset(('test.log', 'config.json', 'witness.json'))
ATTEMPT = re.compile(r'attempt-[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def validate(files, out_root, digest):
    if not isinstance(files, dict) or len(files) != 3:
        raise ValueError('native evidence must contain exactly three files')
    root = Path(out_root)
    if not root.is_absolute() or root.is_symlink():
        raise ValueError('output root must be an absolute non-symlink directory')
    if not root.is_dir():
        raise ValueError('output root missing')
    seen = set()
    attempt = None
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str) or not SHA.fullmatch(expected):
            raise ValueError('invalid file binding')
        path = Path(name)
        if not path.is_absolute():
            raise ValueError('nonabsolute evidence path')
        try:
            parts = path.relative_to(root).parts
        except ValueError as exc:
            raise ValueError('evidence outside output root') from exc
        if len(parts) != 2 or not ATTEMPT.fullmatch(parts[0]) or parts[1] not in NAMES:
            raise ValueError('invalid attempt or native file name')
        if attempt is not None and attempt != parts[0]:
            raise ValueError('native files belong to different attempts')
        attempt = parts[0]
        if parts[1] in seen:
            raise ValueError('duplicate native file')
        seen.add(parts[1])
        parent = root / parts[0]
        if parent.is_symlink() or not parent.is_dir() or path.is_symlink():
            raise ValueError('symlink or missing attempt')
        if not stat.S_ISREG(path.lstat().st_mode) or digest(path) != expected:
            raise ValueError('missing, nonregular or changed native file')
    if seen != NAMES:
        raise ValueError('incomplete native evidence')
