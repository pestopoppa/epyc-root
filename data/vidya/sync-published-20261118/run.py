#!/usr/bin/env python3
"""One-shot disposable native publication proof. Never touches production state."""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

source = Path(__file__).resolve().parent / 'bundle'
out = Path(__file__).resolve().parent
sandbox = Path(sys.argv[1]).resolve() / 'native-run'
if sandbox.exists():
    raise SystemExit('native-run already exists; preserve original receipts and use a fresh directory')
sandbox.mkdir()
env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
           GIT_AUTHOR_NAME='Native Test', GIT_AUTHOR_EMAIL='native@example.invalid',
           GIT_COMMITTER_NAME='Native Test', GIT_COMMITTER_EMAIL='native@example.invalid',
           GIT_TERMINAL_PROMPT='0', VIDYA_STATE_DIR=str(sandbox / 'state'))
for key in ('VIDYA_LEDGER', 'VIDYA_SCRATCH', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
    env.pop(key, None)
def run(name, argv, cwd=None, ok=True):
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    (sandbox / (name + '.stdout')).write_text(p.stdout)
    (sandbox / (name + '.stderr')).write_text(p.stderr)
    (sandbox / (name + '.json')).write_text(json.dumps({'argv': list(map(str, argv)), 'cwd': str(cwd), 'exit': p.returncode}, indent=2) + '\n')
    if ok and p.returncode:
        raise RuntimeError(f'{name}: exit {p.returncode}; see receipt')
    return p

def git(name, cwd, *args): return run(name, ['git', *args], cwd)
origin = sandbox / 'origin.git'; wt = sandbox / 'primary'
git('init_origin', sandbox, 'init', '--bare', '-b', 'main', str(origin))
git('clone', sandbox, 'clone', str(origin), str(wt))
(wt / 'scripts').mkdir(); shutil.copytree(source / 'scripts/vidya', wt / 'scripts/vidya', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
(wt / 'research').mkdir()
index = (source / 'research/intake_index.yaml').read_text()
starts = [m.start() for m in re.finditer(r'^- id: intake-', index, re.M)]
assert len(starts) >= 4
(wt / 'research/intake_index.yaml').write_text(index[starts[0]:starts[2]])
git('seed_add', wt, 'add', 'scripts/vidya', 'research/intake_index.yaml')
git('seed_commit', wt, 'commit', '-m', 'seed')
git('seed_push', wt, 'push', '-u', 'origin', 'main')
hooks = wt / '.git/hooks'
git('configure_common_hooks', wt, 'config', 'core.hooksPath', str(hooks))
(hooks / 'post-commit').write_text('#!/bin/sh\nprintf original-hook-ran > "$(git rev-parse --git-dir)/original-hook-receipt"\n')
(hooks / 'post-commit').chmod(0o755)
(hooks / 'reference-transaction').write_text('#!/bin/sh\ncat >> "$(git rev-parse --git-dir)/reference-hook-receipt"\n')
(hooks / 'reference-transaction').chmod(0o755)
run('installer', ['bash', str(wt / 'scripts/vidya/install_sync_hook.sh')], wt)
run('installer_again', ['bash', str(wt / 'scripts/vidya/install_sync_hook.sh')], wt)
assert (sandbox / 'installer_again.stdout').read_text() == ''
(wt / 'research/intake_index.yaml').write_text(index[starts[0]:starts[3]])
git('intake_add', wt, 'add', 'research/intake_index.yaml')
git('intake_commit', wt, 'commit', '-m', 'native intake update')
assert (wt / '.git/original-hook-receipt').read_text() == 'original-hook-ran'
git('head_before_push', wt, 'rev-parse', 'HEAD')
git('remote_before_push', origin, 'rev-parse', 'refs/heads/main')
git('ordinary_push', wt, 'push', 'origin', 'main')
assert 'refs/remotes/origin/main' in (wt / '.git/reference-hook-receipt').read_text()
check = run('postpush_check', [sys.executable, str(wt / 'scripts/vidya/cli.py'), '--json', 'sync', '--check', '--no-fetch'], wt)
status = json.loads(check.stdout)
index_sha = hashlib.sha256((wt / 'research/intake_index.yaml').read_bytes()).hexdigest()
marker = sandbox / 'state/ledger.jsonl.sync.json'
marker_data = json.loads(marker.read_text())
assert status['fresh'] and status['lag_entries'] == 0 and status['index'] == 'origin/main'
assert status['index_sha256'] == index_sha and index_sha in marker_data['seen_sha256']
(sandbox / 'native-marker.json').write_bytes(marker.read_bytes())
git('remote_after_push', origin, 'rev-parse', 'refs/heads/main')
assert (sandbox / 'remote_after_push.stdout').read_text() == (sandbox / 'head_before_push.stdout').read_text()
assert (sandbox / 'remote_before_push.stdout').read_text() != (sandbox / 'head_before_push.stdout').read_text()
(sandbox / 'PASS.json').write_text(json.dumps({'scope': 'disposable native main commit, installer, ordinary push, reference transaction and automatic origin/main fold', 'manual_sync': False, 'production_acceptance': False, 'postpush_status': status}, indent=2) + '\n')
print(sandbox / 'PASS.json')
