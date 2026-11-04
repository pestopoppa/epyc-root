#!/usr/bin/env python3
"""Check preflight receipt and cheap model metadata; does not hash weights."""
import hashlib,json,os,sys
from pathlib import Path

def stat_record(path):
    s=os.stat(path,follow_symlinks=False)
    return {'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}

def verify(path,digest):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('preflight receipt mismatch')
    receipt=json.loads(data)
    for entry in receipt['models']:
        if stat_record(entry['path'])!=entry['stat']:raise ValueError('model metadata changed')
if __name__=='__main__':
    try:verify(sys.argv[1],sys.argv[2])
    except Exception as e:print(f'identity refusal: {e}',file=sys.stderr);sys.exit(65)
