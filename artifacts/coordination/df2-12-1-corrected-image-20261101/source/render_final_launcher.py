#!/usr/bin/env python3
"""Stage fixed role wrapper/job; the wrapper reads a fully bound manifest."""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shlex

from df2_launcher import ROLES

ROOT = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', choices=('cpu', 'gpu'), required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    out = pathlib.Path(args.out_dir).resolve()
    if not out.is_relative_to(ROOT):
        raise SystemExit('draft output must stay inside NI scratch')
    out.mkdir(parents=True, exist_ok=False)
    (ROOT / 'stop').mkdir(exist_ok=True)
    spec = ROLES[args.role]
    shape = spec['shape']
    port = spec['port']
    binary = ROOT / 'frontend-instrument-corrected' / args.role / 'bin/llama-server'
    manifest = ROOT / 'PROMPTS.json'
    proof = ROOT / 'corrected-proof'
    science = ROOT / 'science' / shape
    job = out / ('job-' + shape + '.sh')
    launcher = out / ('launcher-' + shape + '.sh')
    q = shlex.quote
    job.write_text('#!/bin/bash\nset -euo pipefail\n'
        '# The canonical v14 engine supplies the same environment and same job in normal/cutoff.\n'
        f'if [[ "${{WS58_QUAL:-0}}" == 1 ]]; then OUT={q(str(ROOT / "qualification-work" / shape))}; '
        f'else OUT={q(str(science))}; fi\n'
        f'exec /usr/bin/python3 {q(str(ROOT / "run_role.py"))} --shape {shape} '
        f'--binary {q(str(binary))} --port {port} --manifest {q(str(manifest))} '
        f'--manifest-sha {sha(manifest)} --proof-dir {q(str(proof))} --out "$OUT"\n')
    launcher.write_text('#!/bin/bash\nset -euo pipefail\n'
        '# Fail closed until native token proof, calibrated rate, source closure, engine allowlist and manifest exist.\n'
        'exec /usr/bin/python3 ' + q(str(ROOT / 'df2_launcher.py')) +
        ' --role ' + args.role + ' --manifest ' +
        q(str(out / 'FINAL-MANIFEST.json')) + '\n')
    os.chmod(job, 0o755)
    os.chmod(launcher, 0o755)
    print(f'{shape} job {job} sha256={sha(job)}')
    print(f'{shape} launcher {launcher} sha256={sha(launcher)}')


if __name__ == '__main__':
    main()
