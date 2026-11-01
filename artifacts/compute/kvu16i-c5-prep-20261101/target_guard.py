#!/usr/bin/env python3
"""Durable exclusive request-exposure receipt; no reset or redraw method."""
import json
import os
from pathlib import Path
import time

def mark_once(path, plan_sha256, grant_sha256):
    path=Path(path)
    for value in (plan_sha256, grant_sha256):
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('plan and grant SHA-256 must be explicit')
    payload={'schema':'kvu16i.target-exposure.v1','plan_sha256':plan_sha256,
             'grant_sha256':grant_sha256,'epoch':time.time()}
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(payload,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    # Persist the directory entry as well as its contents before sending target traffic.
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
