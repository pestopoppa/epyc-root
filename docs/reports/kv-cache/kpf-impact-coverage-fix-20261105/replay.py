#!/usr/bin/env python3
"""replay.py JOB_PY OUT_DIR [extra-stderr-line]: run JOB_PY's verified_coverage() offline against OUT_DIR's analyze logs.
Copies logs into a fresh scratch dir (coverage.json is written there, never into OUT_DIR)."""
import ast, sys, shutil, tempfile, json
from pathlib import Path
job, out = Path(sys.argv[1]), Path(sys.argv[2])
extra = sys.argv[3] if len(sys.argv) > 3 else None
tree = ast.parse(job.read_text())
keep = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom)) or
        (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets))]
keep = [n for n in keep if not (isinstance(n, ast.ImportFrom) and n.module in ('source_integrity', 'tool_seal'))]
scratch = Path(tempfile.mkdtemp(dir=str(Path(__file__).resolve().parent / 'replays')))
(scratch/'out').mkdir()
for n in ('analyze.stdout', 'analyze.stderr'): shutil.copy(out/n, scratch/'out'/n)
if extra:
    with (scratch/'out/analyze.stderr').open('a') as f: f.write(extra + '\n')
g = {'__file__': str(scratch/'job.py')}
exec(compile(ast.Module(body=keep, type_ignores=[]), str(job), 'exec'), g)
g['D'] = scratch
try:
    r = g['verified_coverage']('replay-status', [])
    print('PASS', json.dumps(r.get('scope_extract_skips', r.get('scope_skipped')))[:400])
except AssertionError as e:
    print('FAIL', repr(e)[:400])
