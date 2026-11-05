"""Fail-closed, point-in-time mapped DSO identity checks; not a custody observer."""
import hashlib
import os
import re
import stat


class Invalid(ValueError):
    pass


def relevant_maps(lines):
    mappings = {}
    for line in lines:
        fields = line.rstrip('\n').split(None, 5)
        if len(fields) < 6:
            continue
        path = fields[5]
        if not re.search(r'/(?:libllama|libggml)[^/]*\.so(?:\.[^/]*)?(?: \(deleted\))?$', path):
            continue
        if path.endswith(' (deleted)') or not path.startswith('/'):
            raise Invalid('deleted or nonabsolute mapping')
        try:
            major, minor = (int(x, 16) for x in fields[3].split(':'))
            inode = int(fields[4])
        except (ValueError, TypeError):
            raise Invalid('malformed device/inode') from None
        if inode <= 0:
            raise Invalid('invalid inode')
        identity = (major, minor, inode)
        if path in mappings and mappings[path] != identity:
            raise Invalid('conflicting map identities')
        mappings[path] = identity
    if not mappings or not any(os.path.basename(p).startswith('libllama.so') for p in mappings):
        raise Invalid('missing mapped libllama')
    return mappings


def verify_snapshot(lines, pins):
    """pins maps exact mapped paths to SHA-256; only these mappings are examined."""
    mappings = relevant_maps(lines)
    for path, (major, minor, inode) in mappings.items():
        digest = pins.get(path)
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise Invalid('missing or malformed pin')
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'rb') as f:
                before = os.fstat(f.fileno())
                if not stat.S_ISREG(before.st_mode) or (os.major(before.st_dev), os.minor(before.st_dev), before.st_ino) != (major, minor, inode):
                    raise Invalid('mapped file identity mismatch')
                h = hashlib.sha256()
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
                after = os.fstat(f.fileno())
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise Invalid('file changed while hashing')
                if h.hexdigest() != digest:
                    raise Invalid('digest mismatch')
        except OSError as exc:
            raise Invalid('cannot open mapped file') from exc
    return mappings
