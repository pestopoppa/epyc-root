#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
TREE = Path('/mnt/raid0/llm/worktrees/kv-prefix-fork-p3-20261102')
GUARD = Path('/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency/scripts/gitnexus-guard.py')
IDENTITY = json.loads((D / 'identity.json').read_text())
from scan_policy import analysis_env, impact_args, validate_impact

def run(args, log=None):
    p = subprocess.run(args, cwd=TREE, env=analysis_env(os.environ), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if log:
        (D / 'out' / (log + '.stdout')).write_text(p.stdout)
        (D / 'out' / (log + '.stderr')).write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f'{args!r} returned {p.returncode}: {p.stderr[-1500:]}')
    return p.stdout

def check():
    assert run(['git', 'rev-parse', 'HEAD']).strip() == IDENTITY['head'], 'P3 HEAD changed'
    assert not run(['git', 'diff', '--name-only', 'HEAD']).strip(), 'P3 tracked files changed'
    for name, digest in IDENTITY['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, f'input changed: {name}'

check()
if '--check' in sys.argv:
    print('P3 head, tracked cleanliness, wrapper and guard input hashes verified; no GitNexus compute')
    raise SystemExit(0)
(D / 'out').mkdir(exist_ok=True)
# Source references are an independent, genuine preliminary unit. They are
# marked partial; only the guarded native impacts below satisfy the decision.
references = {}
for symbol in ('find_slot', 'apply_ubatch', 'llama_kv_cells'):
    raw = run(['git', 'grep', '-n', '-w', symbol, IDENTITY['head'], '--', 'src'])
    references[symbol] = raw.splitlines()
    assert references[symbol], f'no committed reference for {symbol}'
record = {'type': 'source_reference_scan', 'status': 'partial', 'head': IDENTITY['head'],
          'references': references, 'counts': {k: len(v) for k, v in references.items()}}
if os.environ.get('FILLER_SMOKE') == '1':
    out = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record) + '\n')
    raise SystemExit(75)
with (D / 'out/results.jsonl').open('a') as f:
    f.write(json.dumps(record) + '\n')
    f.flush(); os.fsync(f.fileno())
# Admission must precede the P3 historical wrapper and every analysis/query.
run(['/usr/bin/python3', '-I', str(GUARD), '--repo', 'app'], 'guard')
run(['bash', str(TREE / 'scripts/gitnexus-analyze.sh'), '--skip-agents-md', '--skip-skills', '--workers', '1', '--force'], 'analyze')
run(['gitnexus', 'status'], 'status')
for symbol, source in [('find_slot', 'src/llama-kv-cache.cpp'), ('apply_ubatch', 'src/llama-kv-cache.cpp'), ('llama_kv_cells', 'src/llama-kv-cells.h')]:
    run(['/usr/bin/python3', '-I', str(GUARD), '--repo', 'app'])
    raw = run(impact_args(TREE, symbol, source), symbol)
    data = json.loads(raw)
    validate_impact(symbol, data)
    record = {'symbol': symbol, 'source': source, 'head': IDENTITY['head'], 'impact': data}
    with (D / 'out/results.jsonl').open('a') as f:
        f.write(json.dumps(record) + '\n')
check()
with (D / 'out/results.jsonl').open('a') as f:
    f.write(json.dumps({'type': 'scan_complete', 'head': IDENTITY['head'], 'impact_count': 3, 'partial': False}) + '\n')
    f.flush(); os.fsync(f.fileno())
(D / 'out/COMPLETE').write_text('All three native impact outputs captured; review risk before source edits.\n')
