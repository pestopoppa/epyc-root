#!/usr/bin/env python3
"""Materialize the KVU-19a-2 baseline and tile-branch candidate in scratch.

This prepares source only. It neither builds a binary nor proves runtime behavior.
Existing output directories are never reused; incomplete attempts remain visible.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

COMMIT = 'a0d0ae238e714aaab04e973ef4b5a4b7c9917744'
TREE = '507ee1a6b1c5f09d56a337232f99eb82c1aeea55'
PATCH_SHA = '4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235'
TILE = Path('ggml/src/ggml-cuda/fattn-tile.cuh')
TILE_SHAS = {'base': '878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844',
             'candidate': '3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82'}
PATCH_GIT = 'artifacts/compute/kvu19a2-companion-20261101/store-to-candidate.patch'
KERNEL_REPO = '/mnt/raid0/llm/llama.cpp-experimental'
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu').resolve()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def prepare(output, repo):
    output = Path(output)
    if not output.is_absolute() or not output.parent.resolve().is_relative_to(SCRATCH):
        raise ValueError('output must be an absolute path beneath kvu scratch')
    observed = subprocess.check_output(['git', '-C', KERNEL_REPO, 'rev-parse', COMMIT + '^{tree}'], text=True).strip()
    if observed != TREE:
        raise ValueError('source commit tree mismatch')
    patch = subprocess.check_output(['git', '-C', str(repo), 'show', 'HEAD:' + PATCH_GIT])
    if hashlib.sha256(patch).hexdigest() != PATCH_SHA:
        raise ValueError('recorded candidate patch mismatch')
    output.mkdir(mode=0o700)
    patchfile = output / 'candidate.patch'
    patchfile.write_bytes(patch)
    archive = output / 'source.tar'
    with archive.open('xb') as stream:
        subprocess.run(['git', '-C', KERNEL_REPO, 'archive', '--format=tar', COMMIT], stdout=stream, check=True)
    for arm in ('base', 'candidate'):
        target = output / arm
        target.mkdir(mode=0o700)
        subprocess.run(['tar', '-xf', str(archive), '-C', str(target)], check=True)
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patchfile)], cwd=output/'candidate', check=True)
    for arm, expected in TILE_SHAS.items():
        if digest(output / arm / TILE) != expected:
            raise ValueError(f'{arm} tile digest mismatch')
    comparison = subprocess.run(['diff', '-rq', str(output/'base'), str(output/'candidate')],
                                capture_output=True, text=True)
    expected_diff = f'Files {output / "base" / TILE} and {output / "candidate" / TILE} differ\n'
    if comparison.returncode != 1 or comparison.stdout != expected_diff or comparison.stderr:
        raise ValueError('source pair differs beyond the single expected tile')
    record = {'schema': 'kvu19a2.source-pair.v1', 'source_commit': COMMIT, 'git_tree': TREE,
              'source_archive_sha256': digest(archive), 'patch_sha256': PATCH_SHA,
              'tile_sha256': TILE_SHAS, 'differing_path': str(TILE),
              'scope': 'source materialization only; no historical binary, build or runtime claim'}
    with (output/'source-pair.json').open('x') as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    parser.add_argument('--repo', default='/mnt/raid0/llm/worktrees/mains/h-kvu')
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, Path(args.repo)), sort_keys=True))
