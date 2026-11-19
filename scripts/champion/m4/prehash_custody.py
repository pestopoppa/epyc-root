#!/usr/bin/env python3
"""Create a pre-admission content-hash custody receipt; never loads a model."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def identity(st):
    return {'device':st.st_dev, 'inode':st.st_ino, 'size':st.st_size,
            'mtime_ns':st.st_mtime_ns, 'ctime_ns':st.st_ctime_ns}


def receipt(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('canonical absolute source path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('regular file required')
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
        after = os.fstat(stream.fileno())
        path_after = path.stat()
    if identity(before) != identity(after) or identity(after) != identity(path_after):
        raise ValueError('file changed during hashing')
    return {'schema':'epyc.m4.file-custody.v1','path':str(path),'sha256':digest,'identity':identity(after)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();value=receipt(args.source)
    with args.output.open('x') as stream:
        json.dump(value,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    return 0

if __name__=='__main__':
    raise SystemExit(main())
