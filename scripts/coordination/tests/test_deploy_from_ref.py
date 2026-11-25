"""Deploy bootstrap and replay gate use one pinned ref, even from a stale tree."""
import os
from pathlib import Path
import shutil
import subprocess

DEPLOY = Path(__file__).resolve().parents[1] / 'rowflow/deploy_rowflow.sh'
REL = Path('scripts/coordination/rowflow/deploy_rowflow.sh')
HARNESS = Path('scripts/coordination/tests/replay/test_replay_gate.py')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c',
                           'user.email=test@example.com', *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_stale_invocation_runs_ref_script_and_harness(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    (repo / REL).parent.mkdir(parents=True)
    script = DEPLOY.read_text().replace('set -euo pipefail',
                                        'set -euo pipefail\necho REF_SCRIPT_MARKER', 1)
    (repo / REL).write_text(script)
    (repo / 'scripts/coordination/rowflow/rowflow.py').write_text('# fixture\n')
    (repo / 'scripts/coordination/INSTALL.manifest').write_text('')
    (repo / HARNESS).parent.mkdir(parents=True)
    (repo / HARNESS).write_text('REF_HARNESS_MARKER\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'ref')
    ref = git(repo, 'rev-parse', 'HEAD')
    (repo / HARNESS).write_text('STALE_HARNESS_MARKER\n')
    stale = tmp_path / 'stale/scripts/coordination/rowflow/deploy_rowflow.sh'
    stale.parent.mkdir(parents=True)
    stale.write_text(DEPLOY.read_text())
    stale_harness = stale.parent.parent / 'tests/replay/test_replay_gate.py'
    stale_harness.parent.mkdir(parents=True)
    stale_harness.write_text('STALE_HARNESS_MARKER\n')
    stub = tmp_path / 'stub'
    stub.mkdir()
    python = shutil.which('python3')
    (stub / 'python3').write_text(
        '#!/bin/bash\nif [ "${1:-}" = "-m" ] && [ "${2:-}" = "pytest" ]; then\n'
        '  for arg in "$@"; do case "$arg" in */test_replay_gate.py) cat "$arg";; esac; done\n'
        '  echo gate-pass; exit 0\nfi\n'
        f'exec "{python}" "$@"\n')
    (stub / 'python3').chmod(0o755)
    env = dict(os.environ, ROWFLOW_FLAGS=str(tmp_path / 'flags'),
               REPLAY_SCRATCH=str(tmp_path / 'scratch'), PATH=str(stub) + os.pathsep + os.environ['PATH'])
    env.pop('ROWFLOW_DEPLOY_PINNED_SHA', None)
    cmd = ['bash', str(stale), '--repo', str(repo), '--ref', ref,
           '--no-light-claim', '--check-only']
    refused = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
    assert refused.returncode == 65
    assert '--allow-stale-script' in refused.stderr
    assert not (tmp_path / 'flags').exists()
    result = subprocess.run(cmd + ['--allow-stale-script'], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'REF_SCRIPT_MARKER' in result.stdout
    assert 'gates PASS' in result.stdout
    replay_log = next((tmp_path / 'scratch').glob('*-replay.log')).read_text()
    assert 'REF_HARNESS_MARKER' in replay_log
    assert 'STALE_HARNESS_MARKER' not in replay_log
