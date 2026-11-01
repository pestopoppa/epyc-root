#!/usr/bin/env python3
"""Prepare two source snapshots; does not build, launch, or publish."""
import argparse
import ctypes
import errno
import stat
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

COMMIT = 'a0d0ae238e714aaab04e973ef4b5a4b7c9917744'
TREE = '507ee1a6b1c5f09d56a337232f99eb82c1aeea55'
PATCH_SHA = '4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235'
BASE_SHA = '878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844'
CAND_SHA = '3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82'
TILE = 'ggml/src/ggml-cuda/fattn-tile.cuh'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validated_patch(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('patch hash mismatch')
    return data


def apply_validated_patch(target, data):
    # Feed exactly the validated bytes; never reopen a caller-controlled path.
    subprocess.run(['patch', '--batch', '--forward', '-p1'], cwd=target, input=data, check=True)


def open_private_parent(scratch, output):
    """Open each parent without following symlinks; require private owned custody."""
    if not output.is_absolute() or '..' in output.parts:
        raise ValueError('output must be an absolute normalized path')
    relative = output.relative_to(scratch)
    if len(relative.parts) < 2 or relative.parts[0] == 'compute-flags':
        raise ValueError('output needs a private parent under scratch')
    fd = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for name in relative.parts[:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            if st.st_uid != os.geteuid() or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise PermissionError('every scratch parent must be owned and not group/world writable')
        return fd, relative.parts[-1]
    except BaseException:
        os.close(fd)
        raise


def rename_noreplace(src_fd, source, dst_fd, destination):
    """Linux renameat2 exclusively publishes the pair; never replace any path."""
    libc = ctypes.CDLL(None, use_errno=True)
    fn = getattr(libc, 'renameat2', None)
    if fn is None:
        raise OSError(errno.ENOSYS, 'renameat2 unavailable; refusing publication')
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(src_fd, os.fsencode(source), dst_fd, os.fsencode(destination), 1) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--git-dir', type=Path, required=True, help='repository containing the pinned commit')
    ap.add_argument('--patch', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True, help='new directory under an isolated job scratch root')
    args = ap.parse_args()
    output = args.output
    scratch = Path('/mnt/raid0/llm/tmp')
    try:
        parent_fd, output_name = open_private_parent(scratch, output)
    except (OSError, ValueError) as exc:
        raise SystemExit(f'unsafe output parent: {exc}') from exc
    # Keep the directory handle open throughout staging and publication. No caller
    # path is followed after this point; a parent must already exist privately.
    parent_path = f'/proc/self/fd/{parent_fd}'
    try:
        patch_bytes = validated_patch(args.patch, PATCH_SHA)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    cmd = ['git', '--git-dir', str(args.git_dir)]
    tree = subprocess.check_output(cmd + ['rev-parse', COMMIT + '^{tree}'], text=True).strip()
    if tree != TREE:
        raise SystemExit('source tree mismatch')
    # stage in a unique sibling; publish only a complete pair using an atomic rename.
    with tempfile.TemporaryDirectory(prefix='.kvu19-sources-', dir=parent_path) as tmp:
        staging = Path(tmp) / 'pair'
        staging.mkdir()
        for arm in ('baseline', 'candidate'):
            target = staging / arm
            target.mkdir()
            with tempfile.TemporaryFile() as archive:
                subprocess.run(cmd + ['archive', '--format=tar', COMMIT], stdout=archive, check=True)
                archive.seek(0)
                with tarfile.open(fileobj=archive, mode='r:') as tar:
                    tar.extractall(target, filter='data')
            tile = target / TILE
            if digest(tile) != BASE_SHA:
                raise SystemExit('base tile hash mismatch')
            if arm == 'candidate':
                apply_validated_patch(target, patch_bytes)
                if digest(tile) != CAND_SHA:
                    raise SystemExit('candidate tile hash mismatch')
        manifest = {'schema':'kvu19.source-pair.v1', 'commit':COMMIT, 'git_tree':TREE,
                    'patch_sha256':PATCH_SHA, 'baseline_tile_sha256':BASE_SHA,
                    'candidate_tile_sha256':CAND_SHA,
                    'scope':'source preparation only; no build or binary evidence'}
        (staging/'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        stage_fd = os.open(tmp, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            rename_noreplace(stage_fd, 'pair', parent_fd, output_name)
        finally:
            os.close(stage_fd)
    os.close(parent_fd)
    print(output/'source-manifest.json')


if __name__ == '__main__':
    main()
