"""SR-7 prelaunch seal checks and direct-child launch; not grant authority.

The caller must establish actual held region claims, model identity, dynamic
linkage, listener ownership, in-flight STOP handling and descendant drain.
The approved predeclared seal and its provenance must be authenticated outside
this helper; a digest supplied by the caller is not approval.
"""
import hashlib
import os
from pathlib import Path
import re

from owned_server import launch_owned

HEX = re.compile(r'[0-9a-f]{64}\Z')


def _digest(path):
    h = hashlib.sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def launch_sealed(*, seal, argv, env, trace_path, admission):
    """Verify predeclared executable and non-weight files before one launch.

    Hashes are checked outside the model workload. This function refuses GGUF
    files: weight hashing is a separate, once-only preparation outside grants.
    Verification is not a proof of dynamic linker resolution or a race-free
    binding of bytes to execution. Check actual loaded libraries independently.
    """
    if not isinstance(seal, dict) or set(seal) != {'server', 'library_dir', 'files'}:
        raise ValueError('invalid runtime seal')
    server, libdir, files = seal['server'], seal['library_dir'], seal['files']
    if (not isinstance(server, str) or not os.path.isabs(server) or
            not isinstance(libdir, str) or not os.path.isabs(libdir) or
            not isinstance(files, dict) or server not in files or len(files) < 2):
        raise ValueError('server and libraries must be sealed')
    if not isinstance(argv, list) or not argv or argv[0] != server:
        raise ValueError('argv does not match seal')
    if not isinstance(env, dict) or env.get('LD_LIBRARY_PATH') != libdir:
        raise ValueError('library path does not match seal')
    if not Path(libdir).is_dir() or not callable(admission) or admission() is not True:
        raise ValueError('admission or library directory invalid')
    libraries = 0
    for name, expected in files.items():
        if (not isinstance(name, str) or not os.path.isabs(name) or
                not isinstance(expected, str) or not HEX.fullmatch(expected) or
                (name != server and '.so' not in Path(name).name)):
            raise ValueError('invalid sealed input')
        path = Path(name)
        if path.resolve().name.lower().endswith('.gguf'):
            raise ValueError('weight files are not runtime libraries')
        if not path.is_file() or _digest(path) != expected:
            raise ValueError('runtime digest mismatch')
        if path.resolve().parent == Path(libdir).resolve() and '.so' in path.name:
            libraries += 1
    if not libraries or not os.access(server, os.X_OK):
        raise ValueError('executable or sealed library missing')
    if admission() is not True:
        raise ValueError('admission revoked')
    return launch_owned(argv, env, trace_path)
