"""Prepare detached source worktrees and validate their pinned file inventories."""
import hashlib
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def inventory(source):
    source = Path(source)
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.rglob('*')) if p.is_file() and p != source / '.git'}


def verify(source, expected, repository):
    source = Path(source).resolve()
    repository = Path(repository).resolve()
    if not (source / '.git').is_file():
        raise ValueError('source must be a prepared git worktree: ' + str(source))
    if Path(git(source, 'rev-parse', '--show-toplevel')).resolve() != source:
        raise ValueError('source worktree root mismatch')
    def common(repo):
        path = Path(git(repo, 'rev-parse', '--git-common-dir'))
        return (path if path.is_absolute() else repo / path).resolve()
    if common(source) != common(repository):
        raise ValueError('source belongs to another repository')
    if git(source, 'rev-parse', 'HEAD') != expected['commit']:
        raise ValueError('source commit mismatch')
    if subprocess.run(['git', '-C', str(source), 'symbolic-ref', '-q', 'HEAD'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 1:
        raise ValueError('source must have detached HEAD')
    if git(source, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('source worktree is dirty')
    if any(line[:1] != 'H' for line in git(source, 'ls-files', '-v').splitlines()):
        raise ValueError('source has hidden index flags')
    if inventory(source) != expected['files']:
        raise ValueError('source file inventory changed')


def prepare(repository, source, expected):
    source = Path(source)
    if source.exists():
        raise FileExistsError('refusing to overwrite source: ' + str(source))
    subprocess.run(['git', '-C', str(repository), 'worktree', 'add', '--detach',
                    str(source), expected['commit']], check=True)
    try:
        verify(source, expected, repository)
    except BaseException:
        # This path was created by this invocation; remove via git, never copy it.
        subprocess.run(['git', '-C', str(repository), 'worktree', 'remove', '--force',
                        str(source)], check=True)
        raise
