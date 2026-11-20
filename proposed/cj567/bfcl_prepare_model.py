"""Offline BFCL weight identity preparation. Never import/run in a compute grant."""
import hashlib
import os
from pathlib import Path

from bfcl_residency import fingerprint


def prepare_model(path):
    """Offline preparation only; hash the exact open inode and refuse mutation."""
    path = Path(path).resolve(strict=True)
    with path.open('rb') as source:
        before = fingerprint(os.fstat(source.fileno()))
        sha = hashlib.file_digest(source, 'sha256').hexdigest()
        if before != fingerprint(os.fstat(source.fileno())):
            raise ValueError('model changed during preparation')
    if before != fingerprint(path.stat()):
        raise ValueError('model replaced during preparation')
    return {'path': str(path), 'sha256': sha, 'stat': before}

