"""Metadata-only grant-time model identity check; never opens weight bytes."""
from pathlib import Path
import os

_FIELDS=('dev','ino','size','mtime_ns','ctime_ns')

def snapshot(path):
    p=Path(path)
    if not p.is_absolute(): raise ValueError('model path must be absolute')
    resolved=p.resolve(strict=True)
    s=resolved.stat()
    if not resolved.is_file(): raise ValueError('model is not a regular file')
    return {'path':str(resolved), **{k:getattr(s,'st_'+k) for k in _FIELDS}}

def validate(record):
    if set(record)!={'path',*_FIELDS}: raise ValueError('invalid identity schema')
    if snapshot(record['path'])!=record: raise ValueError('model metadata changed')
    return True
