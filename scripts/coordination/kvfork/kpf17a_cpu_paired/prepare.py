#!/usr/bin/env python3
"""Prepare a new paired-row scratch directory without changing a live row."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from source_worktrees import prepare as prepare_source

HERE = Path(__file__).resolve().parent
LIVE = Path('/mnt/raid0/llm/tmp/kvfork/kpf17a-cpu-paired')
OLD = Path('/mnt/raid0/llm/tmp/kvfork17a-cpu-successor')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, default=LIVE)
    parser.add_argument('--predecessor', type=Path, default=OLD)
    parser.add_argument('--source-repository', type=Path,
                        default=Path('/mnt/raid0/llm/llama.cpp-experimental'))
    args = parser.parse_args()
    d = args.destination.resolve()
    old = args.predecessor.resolve()
    # Never overwrite a published row, its binding, or any existing scratch.
    d.mkdir(parents=True, exist_ok=False)
    for name in ('input', 'sources', 'prior-receipts'):
        (d / name).mkdir()
    for path in (old / 'input').iterdir():
        shutil.copy2(path, d / 'input' / path.name)
    for name in ('filler_run15.sh', 'filler_lib.sh'):
        shutil.copy2(old / name, d / name)
    for path in (old / 'out').glob('original-???.json'):
        shutil.copy2(path, d / 'prior-receipts' / path.name)
    shutil.copy2(old / 'identity.json', d / 'prior-receipts' / 'identity.json')
    # The checked-in job is canonical.  Never regenerate it from mutable scratch.
    for name in ('job.py', 'source_worktrees.py'):
        shutil.copy2(HERE / name, d / name)
    launch = (HERE / 'launch.sh').read_text().replace(str(LIVE), str(d))
    (d / 'launch.sh').write_text(launch)
    identity = json.loads((old / 'identity.json').read_text())
    identity['source_repository'] = str(args.source_repository.resolve())
    created = []
    try:
        for arm, expected in identity['sources'].items():
            expected.pop('archive_sha256', None)
            prepare_source(args.source_repository, d / 'sources' / arm, expected)
            created.append(d / 'sources' / arm)
    except BaseException:
        for source in reversed(created):
            subprocess.run(['git', '-C', str(args.source_repository), 'worktree',
                            'remove', '--force', str(source)], check=True)
        raise
    identity['scope'] = ('CPU exactness successor: original and extended preservation '
                         'compared under identical grant and thread count; earlier '
                         'receipts retained separately')
    inputs = [*(d / 'input').iterdir(), d / 'source_worktrees.py',
              d / 'job.py', d / 'filler_run15.sh', d / 'filler_lib.sh',
              *(d / 'prior-receipts').iterdir()]
    identity['inputs'] = {str(path.relative_to(d)): sha(path) for path in inputs}
    (d / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    spec = json.loads((HERE / 'spec.json').read_text())
    spec.update(launcher=str(d / 'launch.sh'), scratch_root=str(d),
                result_path=str(d / 'out/results.jsonl'))
    (d / 'spec.json').write_text(json.dumps(spec, indent=2) + '\n')


if __name__ == '__main__':
    main()
