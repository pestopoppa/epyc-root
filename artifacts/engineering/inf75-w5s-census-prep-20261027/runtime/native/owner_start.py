"""Create-only permanent metadata before the native diagnostic's model work."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time


def write(path, *, job_pid, grant, manifest, job):
    start = (Path('/proc')/str(job_pid)/'stat').read_text().rpartition(') ')[2].split()[19]
    raw = Path(grant).read_bytes()
    row = {'owner':'codex-ni preparation; ROOT review; WS58 calendar',
           'job_pid':job_pid,'job_start_ticks':int(start),'recorded_utc_ns':time.time_ns(),
           'grant_literal':raw.decode(),'grant_sha256':hashlib.sha256(raw).hexdigest(),
           'source_manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),
           'job_path':str(job),'job_sha256':hashlib.sha256(Path(job).read_bytes()).hexdigest(),
           'scope':'native C5 ABI canary only; no P0d completion'}
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(json.dumps(row,sort_keys=True).encode()+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return row


if __name__ == '__main__':
    write(Path(sys.argv[1]),job_pid=int(sys.argv[2]),grant=Path(sys.argv[3]),
          manifest=Path(sys.argv[4]),job=Path(sys.argv[5]))
