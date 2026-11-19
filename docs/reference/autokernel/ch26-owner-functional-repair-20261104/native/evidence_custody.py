"""Read bounded evidence on a pinned FD; recheck at each use, no producer attestation."""
import hashlib
import os
import stat
MAX_BYTES = 512 * 1024 * 1024

def _identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def read_receipt(path, expected_sha256=None):
    if not os.path.isabs(path): raise ValueError('absolute evidence path required')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError('evidence must be bounded single-link regular file')
        chunks, size, digest = [], 0, hashlib.sha256()
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_BYTES + 1 - size))
            if not chunk: break
            size += len(chunk)
            if size > MAX_BYTES: raise ValueError('evidence exceeds bound')
            chunks.append(chunk); digest.update(chunk)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named) or size != before.st_size:
            raise ValueError('evidence changed or path replaced during read')
        actual = digest.hexdigest()
        if expected_sha256 is not None and (not isinstance(expected_sha256, str) or actual != expected_sha256):
            raise ValueError('evidence digest mismatch')
        return b''.join(chunks), actual
    finally:
        os.close(fd)
