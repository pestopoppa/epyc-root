#!/usr/bin/env python3
"""Offline plan validation for future source-bound build; never executes commands."""
import argparse
import json
import re
from pathlib import PurePosixPath

SHA = re.compile(r'^[0-9a-f]{64}$')
COMMIT = 'a0d0ae238e714aaab04e973ef4b5a4b7c9917744'
TREE = '507ee1a6b1c5f09d56a337232f99eb82c1aeea55'
PATCH = '4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235'


def absolute(value, name):
    if not isinstance(value, str) or not value.startswith('/') or '..' in PurePosixPath(value).parts:
        raise ValueError(f'{name}: absolute normalized path required')
    return value


def sha(value, name):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError(f'{name}: SHA-256 required')
    return value


def make_plan(record, dryrun):
    if record.get('commit') != COMMIT or record.get('tree') != TREE or record.get('patch_sha256') != PATCH:
        raise ValueError('source identity mismatch')
    if dryrun not in (True, False):
        raise ValueError('mode must be explicit')
    cmake = absolute(record.get('cmake'), 'cmake')
    sha(record.get('cmake_sha256'), 'cmake_sha256')
    compiler = absolute(record.get('hip_compiler'), 'hip_compiler')
    sha(record.get('hip_compiler_sha256'), 'hip_compiler_sha256')
    root = PurePosixPath(absolute(record.get('scratch_root'), 'scratch_root'))
    if not root.is_relative_to('/mnt/raid0/llm/tmp') or root == PurePosixPath('/mnt/raid0/llm/tmp') or root.is_relative_to('/mnt/raid0/llm/tmp/compute-flags'):
        raise ValueError('scratch root outside permitted isolated job directory')
    threads = record.get('parallel')
    if type(threads) is not int or not 1 <= threads <= 96:
        raise ValueError('invalid parallel count')
    # Prospective short control has its own independent trivial source and output;
    # it must never configure or mutate the target source/build paths.
    if dryrun:
        src = str(root / 'qualification' / 'source')
        build = str(root / 'qualification' / 'build')
        return {'mode': 'qualification', 'event': str(root / 'qualification' / 'events.jsonl'),
                'commands': [[cmake, '-G', 'Ninja', '-S', src, '-B', build], [cmake, '--build', build, '--parallel', str(threads)]]}
    commands = []
    for arm in ('baseline', 'candidate'):
        sha(record.get(f'{arm}_source_manifest_sha256'), f'{arm}_source_manifest_sha256')
        src, build = str(root / 'sources' / arm), str(root / 'builds' / arm)
        commands.extend([[cmake, '-G', 'Ninja', '-S', src, '-B', build,
                          '-DCMAKE_BUILD_TYPE=Release', '-DGGML_HIP=ON', '-DAMDGPU_TARGETS=gfx90a',
                          '-DGGML_HIP_ROCWMMA_FATTN=ON', '-DCMAKE_HIP_COMPILER=' + compiler],
                         [cmake, '--build', build, '--parallel', str(threads)]])
    return {'mode': 'target', 'event': str(root / 'target' / 'events.jsonl'), 'commands': commands}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('record')
    parser.add_argument('--mode', required=True, choices=('qualification', 'target'))
    args = parser.parse_args()
    with open(args.record) as f:
        record = json.load(f)
    print(json.dumps(make_plan(record, args.mode == 'qualification'), indent=2))


if __name__ == '__main__':
    main()
