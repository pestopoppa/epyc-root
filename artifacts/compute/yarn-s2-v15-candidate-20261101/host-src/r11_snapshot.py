"""Task-local bounded read of observational R11 queue/grant snapshots."""
import os
import stat
import time
from pathlib import Path

class SnapshotChanged(RuntimeError):
    pass

def identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns

def read_regular(path, limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:
            raise RuntimeError('unsafe snapshot file: '+str(path))
        raw=os.read(fd,before.st_size+1)
        after=os.fstat(fd);named=path.lstat()
        if identity(before)!=identity(after) or identity(after)!=identity(named) or len(raw)!=before.st_size:
            raise SnapshotChanged('file changed during snapshot')
        return raw,identity(after)
    finally:
        os.close(fd)

def snapshot(flags):
    """No caller-required grant is relaxed: this snapshots other live grants only.

    A vanished enumerated grant requires a new complete enumeration. Missing
    queue paths, symlinks, malformed stable records and all admission conflicts
    remain errors. At most three attempts and forty ms of retry delay.
    """
    flags=Path(flags);reason=None
    for attempt in range(3):
        try:
            grants=flags/'grants'
            if grants.is_symlink() or not grants.is_dir():
                raise RuntimeError('missing or unsafe grants directory')
            queue,qid=read_regular(flags/'FILLERS.md',16*1024**2)
            if not queue:
                raise SnapshotChanged('existing queue temporarily empty')
            names=sorted((flags/'grants').glob('*.grant'))
            records=[]
            for path in names:
                try:
                    raw,gid=read_regular(path,4096)
                except FileNotFoundError as exc:
                    raise SnapshotChanged('enumerated grant changed') from exc
                if not raw:
                    raise SnapshotChanged('existing grant temporarily empty')
                records.append((path,raw,gid))
            if names!=sorted((flags/'grants').glob('*.grant')) or identity((flags/'FILLERS.md').lstat())!=qid:
                raise SnapshotChanged('snapshot publication changed')
            try:
                if any(identity(p.lstat())!=gid for p,raw,gid in records):
                    raise SnapshotChanged('grant changed after read')
            except FileNotFoundError as exc:
                raise SnapshotChanged('enumerated grant changed after read') from exc
            if grants.is_symlink() or not grants.is_dir():
                raise RuntimeError('missing or unsafe grants directory')
            return queue.decode('utf-8'),[(p,raw.decode('ascii')) for p,raw,gid in records]
        except SnapshotChanged as exc:
            reason=str(exc)
            if attempt<2:time.sleep(.02)
    raise RuntimeError('no stable R11 snapshot after three reads: '+str(reason))
