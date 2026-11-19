#!/usr/bin/env python3
"""Seal finalized KPF-50 rocprof CSVs; structural custody, not a profile verdict."""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import uuid
from pathlib import Path

ORDER = {'full-a', 'mask-a', 'mask-b', 'full-b'}
SAFE = re.compile(r'[A-Za-z0-9_.-]{1,160}\Z')
LIMIT = 10 * 1024 * 1024  # existing receipt consumer's per-file ceiling

def read_regular(dfd, name):
    if not isinstance(name, str) or not SAFE.fullmatch(name) or name in ('.', '..'):
        raise ValueError('unsafe file name')
    fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=dfd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= LIMIT:
            raise ValueError('trace missing, empty or too large')
        chunks = []
        while True:
            chunk = os.read(fd, 1048576)
            if not chunk: break
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('file changed while reading')
        return b''.join(chunks)
    finally:
        os.close(fd)

def validate_csv(raw):
    rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    if not rows.fieldnames or len(rows.fieldnames) != len(set(rows.fieldnames)) or not {'KernelName', 'BeginNs', 'EndNs'} <= set(rows.fieldnames):
        raise ValueError('missing or ambiguous rocprof event columns')
    count = 0
    for row in rows:
        if None in row or not row.get('KernelName', '').strip():
            raise ValueError('malformed profiler kernel event')
        try:
            begin, end = int(row['BeginNs']), int(row['EndNs'])
        except (ValueError, TypeError):
            raise ValueError('invalid profiler timestamp') from None
        if begin < 0 or begin >= end:
            raise ValueError('invalid profiler event interval')
        count += 1
    if not count: raise ValueError('no profiler kernel events')
    return count

def publish(directory, window, run_id, filenames):
    if window not in ORDER or not isinstance(run_id, str) or not SAFE.fullmatch(run_id) or run_id in ('.','..'):
        raise ValueError('invalid window or run identity')
    if not filenames or len(filenames) != len(set(filenames)):
        raise ValueError('missing or duplicate traces')
    dfd = os.open(Path(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    stage = '.trace-' + uuid.uuid4().hex
    created = False
    try:
        start = json.loads(read_regular(dfd, window + '.start.json'))
        if start != {'schema':'kpf50.window-start.v1', 'window':window, 'run_id':run_id}:
            raise ValueError('start identity mismatch')
        entries=[]
        for name in filenames:
            if not name.startswith(window + '.' + run_id + '.') or not name.endswith('.csv'):
                raise ValueError('trace filename is not window/run bound rocprof CSV')
            raw = read_regular(dfd, name)
            validate_csv(raw)
            entries.append({'file':name, 'sha256':hashlib.sha256(raw).hexdigest()})
        result = {'schema':'kpf50.trace-manifest.v1','window':window,'run_id':run_id,'complete':True,'files':entries}
        raw=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
        fd=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600,dir_fd=dfd);created=True
        try:
            view=memoryview(raw)
            while view:
                n=os.write(fd,view)
                if n<=0:raise OSError('short manifest write')
                view=view[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.link(stage,window+'.trace.json',src_dir_fd=dfd,dst_dir_fd=dfd,follow_symlinks=False)
        os.fsync(dfd)
        return result
    finally:
        if created:
            try: os.unlink(stage,dir_fd=dfd)
            except FileNotFoundError: pass
        os.close(dfd)

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--window',required=True);p.add_argument('--run-id',required=True);p.add_argument('files',nargs='+');a=p.parse_args()
    try: publish(a.directory,a.window,a.run_id,a.files)
    except (ValueError,OSError,UnicodeError,json.JSONDecodeError) as exc: p.exit(2,f'trace manifest refused: {exc}\n')
if __name__=='__main__': main()
