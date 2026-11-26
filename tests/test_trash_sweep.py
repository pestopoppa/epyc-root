import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/safety/trash-sweep.sh'


def run_sweep(tmp_path, *args, **extra):
    trash = tmp_path / 'trash'
    env = dict(os.environ, TRASH_ROOT=str(trash), SAFETY_AUDIT_LOG=str(tmp_path / 'audit'), **extra)
    return subprocess.run(['bash', str(SCRIPT), *args], env=env, text=True, capture_output=True)


def test_retry_skip_and_continue(tmp_path):
    trash = tmp_path / 'trash'
    trash.mkdir()
    readonly = trash / '20200101-000000-readonly'
    readonly.mkdir()
    (readonly / 'file').write_text('data')
    readonly.chmod(0o555)
    stuck = trash / '20200101-000000-stuck'
    stuck.write_text('stuck')
    normal = trash / '20200101-000000-normal'
    normal.write_text('normal')
    tools = tmp_path / 'bin'
    tools.mkdir()
    wrapper = tools / 'rm'
    wrapper.write_text('#!/bin/bash\nfor arg in "$@"; do\n  case "$arg" in *-stuck) echo "simulated immutable" >&2; exit 1;; esac\ndone\nexec /bin/rm "$@"\n')
    wrapper.chmod(0o755)
    result = run_sweep(tmp_path, '--older-than', 'now', PATH=f'{tools}:{os.environ["PATH"]}')
    assert result.returncode == 0, result.stderr
    assert not readonly.exists() and not normal.exists() and stuck.exists()
    assert r'simulated\ immutable' in result.stdout and str(stuck) in result.stdout
    assert 'owner=' in result.stdout and 'skipped entries: 1' in result.stdout


def test_outside_links_are_refused(tmp_path):
    trash = tmp_path / 'trash'
    trash.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'keep').write_text('safe')
    (trash / '20200101-000000-link').symlink_to(outside, target_is_directory=True)
    nested = trash / '20200101-000000-nested'
    nested.mkdir()
    (nested / 'link').symlink_to(outside, target_is_directory=True)
    result = run_sweep(tmp_path, '--older-than', 'now')
    assert result.returncode == 0, result.stderr
    assert (outside / 'keep').read_text() == 'safe'
    assert nested.exists() and (trash / '20200101-000000-link').is_symlink()
    assert 'skipped entries: 2' in result.stdout


def test_age_and_dry_run(tmp_path):
    trash = tmp_path / 'trash'
    trash.mkdir()
    old = trash / '20200101-000000-old'
    old.touch()
    future = trash / '20990101-000000-future'
    future.touch()
    result = run_sweep(tmp_path, '--older-than', '24h', '--dry-run')
    assert result.returncode == 0 and '[dry-run] would remove ' + str(old) in result.stdout
    assert str(future) not in result.stdout and old.exists()
    result = run_sweep(tmp_path, '--older-than', '1')
    assert result.returncode == 0 and not old.exists() and future.exists()


@pytest.mark.parametrize('args', [[], ['--older-than'], ['--older-than', '0'], ['--bad']])
def test_bad_args(tmp_path, args):
    (tmp_path / 'trash').mkdir()
    assert run_sweep(tmp_path, *args).returncode != 0


def test_missing_root(tmp_path):
    assert run_sweep(tmp_path, '--older-than', 'now').returncode != 0
