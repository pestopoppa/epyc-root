#!/usr/bin/env python3
"""PROPOSED common publication lease, owner cutover only. No production activation.

Region claims remain mandatory independently. This lease only serializes canonical
row/HOLD/grant mutations, never claims compute capacity. Every producing process
must cut over; partial deployment never enables pool admission.
"""
import argparse
import fcntl
import os
from pathlib import Path
import tempfile
import time
from gap_runtime_v1 import Refuse
import gap_policy

PROTOCOL = 'gap-publication-v1'
ALL_PRODUCERS_BOUND = False
class PublicationLease:
    def __init__(self, flags, *, timeout=30, deadline_epoch=None):
        self.flags = Path(flags)
        self.path = self.flags / '.gap-publication-v1.lock'
        self.timeout = timeout
        self.deadline_epoch = deadline_epoch
        self.fd = None
    def __enter__(self):
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        remaining = self.timeout if self.deadline_epoch is None else min(self.timeout, self.deadline_epoch-time.time())
        if remaining <= 0:
            os.close(self.fd); self.fd=None
            raise Refuse("publication-admission-deadline-expired")
        deadline = time.monotonic() + remaining
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if self.deadline_epoch is not None and time.time() >= self.deadline_epoch:
                    fcntl.flock(self.fd,fcntl.LOCK_UN);os.close(self.fd);self.fd=None
                    raise Refuse("publication-admission-deadline-expired")
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(self.fd); self.fd = None
                    raise Refuse('publication-lease-timeout')
                time.sleep(.01)
    def assert_held(self):
        if self.deadline_epoch is not None and time.time() >= self.deadline_epoch:
            raise Refuse("publication-admission-deadline-expired")
        if self.fd is None:
            raise Refuse('publication-lease-not-held')
        opened, current = os.fstat(self.fd), self.path.stat()
        if (opened.st_dev,opened.st_ino) != (current.st_dev,current.st_ino):
            raise Refuse('publication-lock-replaced')
    def __exit__(self, *_):
        if self.fd is not None:
            fcntl.flock(self.fd,fcntl.LOCK_UN); os.close(self.fd); self.fd=None

def replace_bytes(lease, path, data):
    lease.assert_held()
    path=Path(path)
    if path.parent != lease.flags and path.parent != lease.flags/'grants':
        raise Refuse('publication-path-outside-flags')
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        lease.assert_held(); os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.lexists(name): os.unlink(name)

def hold_write(lease,name,data,quiet_not_before=None):
    if not name.startswith('HOLD_') or '/' in name:
        raise Refuse('invalid-hold-name')
    if any(line.startswith(b'quiet_not_before=') for line in data.splitlines()):
        raise Refuse('caller-cannot-smuggle-quiet-metadata')
    if quiet_not_before is not None:
        gap_policy.epoch(quiet_not_before)
        data=data.rstrip(b'\n')+b'\nquiet_not_before='+quiet_not_before.encode()+b'\n'
    # Legacy HOLDs intentionally remain legacy and refuse pool admission.
    replace_bytes(lease,lease.flags/name,data)

def hold_remove(lease,name):
    if not name.startswith('HOLD_') or '/' in name:
        raise Refuse('invalid-hold-name')
    lease.assert_held()
    try: os.unlink(lease.flags/name)
    except FileNotFoundError: pass

# A shell HOLD writer can call this exact version for every create/update/delete.
# No quiet timestamp is inferred from old HOLD content, mtime, or wall-clock ETA.
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--flags',required=True); p.add_argument('--name',required=True)
    p.add_argument('--remove',action='store_true'); p.add_argument('--text')
    p.add_argument('--quiet-not-before')
    p.add_argument("--if-missing",action="store_true")
    a=p.parse_args()
    if not ALL_PRODUCERS_BOUND:
        raise Refuse('owner-producer-cutover-not-adopted')
    with PublicationLease(a.flags) as lease:
        if a.if_missing and os.path.lexists(Path(a.flags)/a.name): return
        if a.remove: hold_remove(lease,a.name)
        elif a.text is not None: hold_write(lease,a.name,a.text.encode(),a.quiet_not_before)
        else: raise Refuse('missing-hold-content')
if __name__=='__main__':
    try: main()
    except (Refuse,OSError,ValueError) as error:
        raise SystemExit('refuse: '+str(error))
