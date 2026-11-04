"""Compact, bounded archive of observed perf ring windows; no coverage warrant.

Only bytes between the captured tail and head are retained. Unused ring bytes
are intentionally not retained. Each JSONL frame is chained and independently
replayable; caller must maintain source FD custody and kernel loss counters.
"""
import base64
import hashlib
import json
import os
import stat
from pathlib import Path
from perf_ring import decode

# Session permits up to 1024 data pages; reject untrusted larger rings before allocation.
MAX_RING_BYTES = 1024 * os.sysconf("SC_PAGE_SIZE")


def _window(snapshot, head, tail):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_RING_BYTES:
        raise ValueError('ring exceeds supported mapping size')
    parsed = decode(snapshot, head=head, tail=tail)
    if parsed.get('errors') or parsed.get('new_tail') != head:
        raise ValueError('invalid, lossy or incomplete ring')
    n = head - tail
    start = tail & (len(snapshot) - 1)
    first = min(n, len(snapshot) - start)
    return snapshot[start:start + first] + snapshot[:n-first]


def _rebuild(size, head, tail, data):
    if type(size) is not int or size < 1 or size > MAX_RING_BYTES or size & (size - 1):
        raise ValueError('invalid ring size')
    if type(head) is not int or type(tail) is not int or tail < 0 or head < tail or head-tail > size or len(data) != head-tail:
        raise ValueError('invalid ring interval')
    ring = bytearray(size)
    start = tail & (size - 1)
    first = min(len(data), size - start)
    ring[start:start+first] = data[:first]
    ring[:len(data)-first] = data[first:]
    return bytes(ring)


class RingArchive:
    def __init__(self, path, *, max_bytes):
        if type(max_bytes) is not int or max_bytes < 256:
            raise ValueError('invalid archive quota')
        self.path = Path(path)
        if not self.path.is_absolute(): raise ValueError('absolute archive path required')
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self.quota=max_bytes; self.bytes=0; self.count=0; self.previous='0'*64
        self.tails={}; self.closed=False

    def append(self, source, snapshot, *, head, tail):
        try:
            return self._append(source, snapshot, head=head, tail=tail)
        except BaseException:
            self.abort()
            raise

    def _append(self, source, snapshot, *, head, tail):
        if self.closed or type(source) is not int or source <= 0:
            raise ValueError('invalid event ID or closed archive')
        if source in self.tails and self.tails[source] != tail:
            raise ValueError('source position discontinuity')
        data=_window(snapshot, head, tail)
        frame={'source':source, 'size':len(snapshot), 'head':head, 'tail':tail,
               'data':base64.b64encode(data).decode('ascii'), 'previous':self.previous}
        raw=json.dumps(frame,sort_keys=True,separators=(',',':')).encode()
        digest=hashlib.sha256(raw).hexdigest()
        line=json.dumps({'frame':frame,'sha256':digest},sort_keys=True,separators=(',',':')).encode()+b'\n'
        if self.bytes + len(line) > self.quota:
            self.abort(); raise ValueError('archive quota exceeded')
        offset=0
        try:
            while offset < len(line):
                written=os.write(self.fd,line[offset:])
                if written <= 0: raise OSError('archive write made no progress')
                offset += written
        except BaseException:
            self.abort(); raise
        self.previous=digest; self.tails[source]=head; self.count+=1; self.bytes+=len(line)

    def finish(self):
        if self.closed: raise ValueError('archive already closed')
        try:
            os.fsync(self.fd)
            os.close(self.fd); self.closed=True
        except BaseException:
            self.abort(); raise
        return {'count':self.count, 'bytes':self.bytes, 'last_sha256':self.previous}

    def abort(self):
        if self.closed: return
        try:
            os.close(self.fd)
        finally:
            self.closed=True
            try: self.path.unlink()
            except FileNotFoundError: pass


def verify(path, expected, *, max_bytes):
    if type(max_bytes) is not int or max_bytes < 256: raise ValueError('invalid quota')
    fd=os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > max_bytes: raise ValueError('invalid archive file or quota exceeded')
        identity=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns,x.st_nlink)
        if identity(os.lstat(path)) != identity(st): raise ValueError('archive path identity mismatch')
        with os.fdopen(fd, 'rb') as f:
            fd=None; last='0'*64; tails={}; count=0; total=0
            for line in f:
                total+=len(line)
                if total > max_bytes or not line.endswith(b'\n'): raise ValueError('truncated or oversized archive')
                doc=json.loads(line); frame=doc['frame']
                raw=json.dumps(frame,sort_keys=True,separators=(',',':')).encode()
                digest=hashlib.sha256(raw).hexdigest()
                if set(doc) != {'frame','sha256'} or set(frame) != {'source','size','head','tail','data','previous'} or doc['sha256'] != digest or frame['previous'] != last:
                    raise ValueError('archive chain mismatch')
                source=frame['source']; head=frame['head']; tail=frame['tail']
                if type(source) is not int or source <= 0 or (source in tails and tails[source]!=tail): raise ValueError('source discontinuity')
                data=base64.b64decode(frame['data'],validate=True)
                ring=_rebuild(frame['size'],head,tail,data)
                if _window(ring,head,tail) != data: raise ValueError('ring replay mismatch')
                tails[source]=head; last=digest; count+=1
            if identity(os.fstat(f.fileno())) != identity(st) or identity(os.lstat(path)) != identity(st):
                raise ValueError('archive changed during replay')
            observed={'count':count,'bytes':total,'last_sha256':last}
            if observed != expected: raise ValueError('archive receipt mismatch')
            return observed
    finally:
        if fd is not None: os.close(fd)
