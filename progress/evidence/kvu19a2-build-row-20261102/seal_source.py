#!/usr/bin/env python3
"""Reconstruct and seal the pinned KVU-19a-2 source pair before publication.

Run as root, before any row grant. Inputs are independently digest pinned;
never reuse an existing output. Build jobs only read the resulting tree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile

ARCHIVE_SHA = '87e3cdc13b1859a31dfd3ced43c596e6b9653e2194b1ebd0d5eb6772593c04c2'
PATCH_SHA = '4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235'
TILE = Path('ggml/src/ggml-cuda/fattn-tile.cuh')
TILES = {'base': '878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844',
         'candidate': '3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82'}
ALLOWED = Path('/mnt/raid0/llm/tmp/kvu19a2-build-row-20261102')


def digest_stream(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(chunk)
    return h.hexdigest()


def check_tree(root, owner=0):
    """Reject unowned, writable, unreadable or non-regular build inputs."""
    root = Path(root)
    def fail(error):
        raise error
    for path, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        for item in [Path(path), *(Path(path) / n for n in files)]:
            s = item.lstat()
            if not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
                raise ValueError('special or symlink source: ' + str(item))
            if s.st_uid != owner or s.st_mode & 0o222:
                raise ValueError('unowned or writable source: ' + str(item))
            if stat.S_ISDIR(s.st_mode):
                if s.st_mode & 0o555 != 0o555:
                    raise ValueError('directory not readable/traversable: ' + str(item))
            elif stat.S_ISREG(s.st_mode):
                if s.st_mode & 0o444 != 0o444 or s.st_nlink != 1:
                    raise ValueError('file unreadable or multiply linked: ' + str(item))
            else:
                raise ValueError('special or symlink source: ' + str(item))
        # os.walk would otherwise silently omit symlink directories.
        for name in dirs:
            if (Path(path) / name).is_symlink():
                raise ValueError('symlink directory in source')


def seal(archive, patch, output, receipt):
    if os.geteuid() != 0:
        raise PermissionError('sealing requires root')
    output,receipt=Path(output),Path(receipt)
    if output.parent != ALLOWED or receipt.parent != ALLOWED or output.name in ('.','..') or receipt.name in ('.','..'):
        raise ValueError('outputs must be directly beneath the build scratch root')
    rowfd=os.open(ALLOWED,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        st=os.fstat(rowfd)
        if st.st_uid!=0 or st.st_mode & 0o022:
            raise ValueError('build scratch root must be root-owned and protected')
        # Anchor every pathname under this held directory descriptor: the
        # shared tmp parent is writable and may rename the scratch directory.
        anchor=Path('/proc')/str(os.getpid())/'fd'/str(rowfd)
        _seal_anchored(archive,patch,anchor/output.name,anchor/receipt.name)
    finally:
        os.close(rowfd)
    return output


def _seal_anchored(archive,patch,output,receipt):
    patch_bytes = Path(patch).read_bytes()
    if hashlib.sha256(patch_bytes).hexdigest() != PATCH_SHA:
        raise ValueError('patch digest mismatch')
    output.mkdir(mode=0o700)
    # Pin the exact extracted bytes in a new root-owned directory; reopening
    # the original writable archive after hashing would introduce a race.
    copied_archive = output / '.source.tar'
    with Path(archive).open('rb') as source, copied_archive.open('xb') as copy:
        h = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
            copy.write(chunk)
        copy.flush()
        os.fsync(copy.fileno())
    if h.hexdigest() != ARCHIVE_SHA:
        raise ValueError('archive digest mismatch')
    with copied_archive.open('rb') as stream:
        patch_path = output / '.candidate.patch'
        patch_path.write_bytes(patch_bytes)
        for arm in ('base', 'candidate'):
            target = output / arm
            target.mkdir(mode=0o700)
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode='r:') as tar:
                members = tar.getmembers()
                if any(not (m.isfile() or m.isdir()) for m in members):
                    raise ValueError('archive contains links or special entries')
                tar.extractall(path=target, members=members, filter='data')
        subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch_path)],
                       cwd=output/'candidate', check=True)
        patch_path.unlink()
    copied_archive.unlink()
    for arm, expected in TILES.items():
        with (output / arm / TILE).open('rb') as stream:
            if digest_stream(stream) != expected:
                raise ValueError('tile identity mismatch: ' + arm)
    diff = subprocess.run(['diff','-rq',str(output/'base'),str(output/'candidate')],
                          capture_output=True,text=True)
    expected = f'Files {output / "base" / TILE} and {output / "candidate" / TILE} differ\n'
    if diff.returncode != 1 or diff.stdout != expected or diff.stderr:
        raise ValueError('unexpected source difference')
    for parent, dirs, files in os.walk(output, topdown=False, followlinks=False):
        for name in files:
            p = Path(parent) / name
            st = p.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise ValueError('special or multiply linked source')
            p.chmod(0o555 if st.st_mode & 0o111 else 0o444)
        for name in dirs:
            p = Path(parent) / name
            if not stat.S_ISDIR(p.lstat().st_mode):
                raise ValueError('special source directory')
            p.chmod(0o555)
    output.chmod(0o555)
    check_tree(output)
    entries=[]
    for parent, dirs, files in os.walk(output, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        for name in sorted(files):
            path=Path(parent)/name
            with path.open('rb') as stream:
                entries.append((str(path.relative_to(output)),digest_stream(stream),stat.S_IMODE(path.stat().st_mode)))
    entries.sort()
    tree_hash=hashlib.sha256(json.dumps(entries,separators=(',',':')).encode()).hexdigest()
    identities={}
    for name in ('.','base','candidate'):
        s=(output/name).stat()
        identities[name]={'dev':s.st_dev,'ino':s.st_ino,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid}
    record={'schema':'kvu19a2.sealed-source.v1','archive_sha256':ARCHIVE_SHA,'patch_sha256':PATCH_SHA,
            'files_sha256':tree_hash,'file_count':len(entries),'identities':identities}
    fd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
    with os.fdopen(fd,'w') as out:
        json.dump(record,out,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive'); parser.add_argument('patch'); parser.add_argument('output'); parser.add_argument('receipt')
    a = parser.parse_args()
    print(seal(a.archive, a.patch, a.output, a.receipt), flush=True)
