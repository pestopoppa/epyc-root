#!/usr/bin/env python3
"""make_successor.py OLD_ID OLD_DIR NEW_ID NEW_DIR: copy a sealed impact-row job dir into a new successor dir
(originals untouched), apply patch_job.py, rewrite paths/ids, re-seal identity.json + seals.sha256, write spec."""
import hashlib, json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import patch_job
old_id, old_dir, new_id, new_dir = sys.argv[1:5]
O, N = Path(old_dir), Path(new_dir)
assert not N.exists(), N
N.mkdir()
SKIP = {'out', 'private-graph', '__pycache__', 'tool'}
for p in O.iterdir():
    if p.name in SKIP: continue
    if p.is_dir(): shutil.copytree(p, N/p.name, symlinks=True)
    else: shutil.copy2(p, N/p.name)
rx = re.compile("(" + re.escape(old_dir) + r")(?!-source|/tool[/'\"])|(" + re.escape(old_id) + r")(?!-source)")
sub = lambda m: new_dir if m.group(1) else new_id
for p in N.rglob('*'):
    if not p.is_file() or p.name in ('tool-manifest.json',): continue
    try: t = p.read_text()
    except UnicodeDecodeError: continue
    t2 = rx.sub(sub, t)
    if t2 != t: p.write_text(t2)
patch_job.main(str(N/'job.py'))
spec = json.loads((N/'spec.json').read_text())
assert spec['id'] == new_id and spec['scratch_root'] == new_dir, spec
spec.update(owner='operator-adhoc-takeover-20261105', supersedes=old_id,
            notes=f'Successor of {old_id} (sealed, untouched). Only change: verified_coverage() exempts [gitnexus-heap] '
                  'instrumentation from the unknown-skip scan and instead verifies sr-extract-end skipped=N as whitespace-only '
                  'tracked files outside the impact targets (recorded in coverage.json scope_extract_skips).')
(N/'spec.json').write_text(json.dumps(spec, indent=2) + '\n')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ident = json.loads((N/'identity.json').read_text())
ident['sha256'] = {k: sha(k) for k in ident['sha256']}
(N/'identity.json').write_text(json.dumps(ident, indent=2) + '\n')
lines = [f'{sha(k)}  {k}' for k in ident['sha256']] + [f"{sha(N/'identity.json')}  {N/'identity.json'}"]
(N/'seals.sha256').write_text('\n'.join(lines) + '\n')
print('made', N)
