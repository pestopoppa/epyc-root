#!/usr/bin/env python3
"""Owner-only append; give expected current SHA256 for each file, then --apply."""
import hashlib, pathlib, sys
h = pathlib.Path('handoffs/active/yarn-context-extension-research.md')
p = pathlib.Path('progress/2026-11/2026-11-01.md')
if len(sys.argv) != 4 or sys.argv[3] != '--apply':
    raise SystemExit('usage: python3 owner-append.py HANDOFF_SHA256 PROGRESS_SHA256 --apply')
marker = 'S0 v35 admission failure — 2026-11-01'
for path, expected in ((h, sys.argv[1]), (p, sys.argv[2])):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected or marker.encode() in raw:
        raise SystemExit(f'refused: changed file or already filed: {path}')
entry = ('\n### ' + marker + '\n\n'
    '- 2026-11-01: S0 v35 failed admission rc=70: dry run reported malformed claimed_cpus and in-claim RLIMIT/affinity/cgroup proof refused. No new matching pairs; retained prior A0 and unknowns unchanged. Diagnose and requalify the CPU claim and proof before continuation; the original diagnostic rule and denominators remain in force. [Evidence](../../artifacts/compute/results-filing-yarn-s0-v35-20261101/README.md). [belief: cc]\n')
for path in (h, p):
    with path.open('a', encoding='utf-8') as f: f.write(entry)
