#!/usr/bin/env python3
"""Prepare source once, outside a grant, using registered detached worktrees."""
import argparse
import json
from pathlib import Path
import subprocess

PRESETS = {
    'kpf174d': ('/mnt/raid0/llm/llama.cpp-experimental', '6ec877068936588b6d63dbba5842bbd540b92031', '/mnt/raid0/llm/tmp/kvfork/kpf174d-build/v3/source'),
    'kpf20-v3': ('/mnt/raid0/llm/epyc-orchestrator', '488b31c96c6c148768508b3dcaefcb6c4c297664', '/mnt/raid0/llm/tmp/kvfork/kpf20-v3/source'),
    'kpf20': ('/mnt/raid0/llm/epyc-orchestrator', '488b31c96c6c148768508b3dcaefcb6c4c297664', '/mnt/raid0/llm/tmp/kvfork/kpf20-orchestrator'),
}

def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo), *args], check=check, text=True, capture_output=True)

def validate(repo, dest, commit):
    repo, dest = Path(repo).resolve(), Path(dest).resolve()
    if not (dest / '.git').is_file() or (dest / '.git').is_symlink():
        raise ValueError('source must be a registered worktree, never a checkout copy')
    if Path(git(dest, 'rev-parse', '--show-toplevel').stdout.strip()).resolve() != dest:
        raise ValueError('unexpected source worktree root')
    expected_common = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()).resolve()
    actual_common = Path(git(dest, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()).resolve()
    if expected_common != actual_common:
        raise ValueError('source belongs to another repository')
    registered = [line[9:] for line in git(repo, 'worktree', 'list', '--porcelain').stdout.splitlines() if line.startswith('worktree ')]
    if str(dest) not in registered:
        raise ValueError('source is not registered at this destination')
    if git(dest, 'rev-parse', 'HEAD').stdout.strip() != commit:
        raise ValueError('source commit changed')
    if git(dest, 'symbolic-ref', '-q', 'HEAD', check=False).returncode != 1:
        raise ValueError('source must remain detached')
    if git(dest, 'status', '--porcelain', '--untracked-files=all').stdout.strip():
        raise ValueError('source worktree is dirty')
    if any(line[:1] != 'H' for line in git(dest, 'ls-files', '-v').stdout.splitlines()):
        raise ValueError('source has hidden index flags')
    return {'schema': 'epyc.detached-source.v1', 'source_commit': commit, 'source': str(dest), 'git_common_dir': str(actual_common)}

def prepare(repo, ref, dest):
    repo, dest = Path(repo).resolve(), Path(dest).resolve()
    commit = git(repo, 'rev-parse', '--verify', ref + '^{commit}').stdout.strip()
    if dest.exists() or dest.is_symlink():
        return validate(repo, dest, commit)
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(repo, 'worktree', 'add', '--detach', str(dest), commit)
    return validate(repo, dest, commit)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preset', choices=PRESETS)
    p.add_argument('--repo'); p.add_argument('--ref'); p.add_argument('--destination')
    args = p.parse_args()
    if args.preset:
        if any((args.repo, args.ref, args.destination)):
            p.error('use a preset or an explicit repository/ref/destination')
        values = PRESETS[args.preset]
    else:
        if not all((args.repo, args.ref, args.destination)):
            p.error('explicit preparation requires repository, ref and destination')
        values = (args.repo, args.ref, args.destination)
    print(json.dumps(prepare(*values), sort_keys=True))

if __name__ == '__main__':
    main()
