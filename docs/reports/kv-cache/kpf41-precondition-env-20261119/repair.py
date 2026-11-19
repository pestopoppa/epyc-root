"""Bind the launcher precondition environment before engine job exports exist."""
import hashlib
from pathlib import Path

BASE = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119')
OLD_SHA = '113eabc430477071175f5d720c84357129f835748c21003e971ecf830db83603'
ROW = 'kpf41-backend-gpu-qualification-r2-20261119'


def repaired(raw):
    if hashlib.sha256(raw).hexdigest() != OLD_SHA:
        raise ValueError('launcher source identity mismatch')
    old = b"&& python3 '$D/job.py' --check\""
    new = b"&& env FILLER_ID=" + ROW.encode() + b" python3 '$D/job.py' --check\""
    if raw.count(old) != 1:
        raise ValueError('ambiguous precondition entry')
    return raw.replace(old, new)


if __name__ == '__main__':
    path = BASE / 'launch.sh'
    if path.is_symlink() or not path.is_file():raise ValueError('regular launcher required')
    raw = repaired(path.read_bytes())
    temporary = path.with_suffix('.repair-tmp')
    with temporary.open('xb') as stream:stream.write(raw)
    temporary.chmod(path.stat().st_mode)
    temporary.replace(path)
    print(hashlib.sha256(raw).hexdigest())
