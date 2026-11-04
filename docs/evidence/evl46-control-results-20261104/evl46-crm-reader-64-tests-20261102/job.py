#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

D = pathlib.Path('/mnt/raid0/llm/tmp/evl46-crm-reader-64-row')
R = pathlib.Path('/mnt/raid0/llm/worktrees/codex-evl46-proof-aa41')
HEAD = '64a96b58b5054a54a2efae416ae25908d0f13dbe'
# Full source identity is validated by Git, not the directory name.
head = subprocess.check_output(['git', '-C', str(R), 'rev-parse', 'HEAD'], text=True).strip()
if head != HEAD:
    raise SystemExit('source commit mismatch')
dirty = subprocess.check_output(['git', '-C', str(R), 'status', '--porcelain', '--',
    'scripts/vidya/adapters/dtap_crm_pair.py', 'tests/vidya/test_dtap_crm_pair_refusal.py'], text=True)
if dirty:
    raise SystemExit('source under test modified')
prefix = 'dry-' if os.environ.get('FILLER_DRYRUN') == '1' else 'full-'
out = pathlib.Path(tempfile.mkdtemp(prefix=prefix, dir=D / 'results'))
cmd = ['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python', '-m', 'pytest', '-q',
       'tests/vidya/test_dtap_crm_pair_refusal.py']
started = time.time()
proc = subprocess.run(cmd, cwd=R, capture_output=True, text=True)
(out / 'pytest.log').write_text(proc.stdout + proc.stderr)
if proc.returncode:
    print(proc.stdout + proc.stderr, file=sys.stderr)
    raise SystemExit(proc.returncode)
sys.path.insert(0, str(R / 'scripts/vidya'))
from adapters.dtap_crm_pair import _source  # noqa: E402
source_path = pathlib.Path('/mnt/raid0/llm/tmp/evl46-qual-20261102/source.json')
source_raw = source_path.read_bytes()
source = json.loads(source_raw)
_source(source_raw, {'source_commit': source['source_commit'],
                      'source_tree_sha256': source['source_tree_sha256']},
        {'producer_path': str(pathlib.Path(source['repo_path']) /
         'scripts/autopilot/evals/dtap/harness/crm_pair_capture.py')})
record = {'schema': 'evl46.crm_reader.tests.v1', 'source_commit': head,
          'mode': 'dry' if prefix == 'dry-' else 'full', 'pytest_rc': 0,
          'started_utc_epoch': started, 'finished_utc_epoch': time.time(),
          'scope': 'synthetic reader/source/claim controls; no live measurement'}
with (out / 'unit.jsonl').open('x') as target:
    target.write(json.dumps(record, sort_keys=True) + '\n')
if prefix == 'full-':
    (D / 'full-pass.json').write_text(json.dumps(record, sort_keys=True) + '\n')
