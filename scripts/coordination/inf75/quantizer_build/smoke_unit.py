#!/usr/bin/env python3
"""Compile one archived source unit for a publishing smoke; never certify a build."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def validate_output(out, dryrun_dir):
    native = (Path(dryrun_dir).resolve() / 'native-attempts')
    if (out.exists() or out.is_symlink() or out.parent.is_symlink() or
            out.parent.parent.resolve() != native or not out.parent.name.startswith('attempt-')):
        raise ValueError('diagnostic output must be a fresh native attempt')


def main():
    if os.environ.get('FILLER_DRYRUN') != '1' or os.environ.get('FILLER_SMOKE') != '1':
        raise SystemExit('diagnostic unit requires dryrun smoke')
    out, run = map(Path, sys.argv[1:3])
    try:
        validate_output(out, os.environ['FILLER_DRYRUN_DIR'])
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    source = run / 'src/ggml/src/ggml-alloc.c'
    obj = run / 'output/diagnostic-ggml-alloc.o'
    cc = Path('/usr/bin/gcc').resolve(strict=True)
    compiler_lines = (run / 'output/compiler.sha256').read_text().splitlines()
    if not compiler_lines or compiler_lines[0] != f"{hashlib.sha256(cc.read_bytes()).hexdigest()}  {cc}":
        raise SystemExit('compiler differs from prepared invocation')
    argv = [str(cc), '-DGGML_BUILD', '-DGGML_SHARED', '-DGGML_USE_OPENMP',
            '-D_GNU_SOURCE', '-D_XOPEN_SOURCE=600',
            '-I' + str(run / 'src/ggml/src'), '-I' + str(run / 'src/ggml/include'),
            '-O3', '-DNDEBUG', '-std=gnu11', '-fPIC', '-fopenmp',
            '-c', str(source), '-o', str(obj)]
    remaining = int(os.environ['FILLER_DEADLINE']) - time.time() - 10
    if remaining <= 0 or Path(os.environ['FILLER_STOPFILE']).exists():
        raise SystemExit(75)
    with (run / 'output/smoke-compile.log').open('wb') as log:
        subprocess.run(argv, cwd=run / 'build', stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=min(180, remaining))
    subprocess.run(['sha256sum', '--check', str(run / 'output/compiler.sha256')], check=True,
                   stdout=subprocess.DEVNULL)
    if not obj.is_file() or obj.stat().st_size == 0:
        raise SystemExit('compile did not produce an object')
    if Path(os.environ['FILLER_STOPFILE']).exists() or time.time() >= int(os.environ['FILLER_DEADLINE']):
        raise SystemExit(75)
    files = [run / n for n in ('output/compiler.sha256', 'output/configure.log',
             'build/CMakeCache.txt', 'build/compile_commands.json', 'output/smoke-compile.log')]
    files += [obj]
    from prepare import ARCHIVE_SHA, MANIFEST_SHA
    receipt = dict(schema='epyc.inf75.quantizer_smoke.v1', status='diagnostic-unit',
                   source_commit=sys.argv[3], source_archive_sha256=ARCHIVE_SHA,
                   source_manifest_sha256=MANIFEST_SHA, run_dir=str(run), command=argv,
                   unit='ggml/src/ggml-alloc.c',
                   scope='controlled diagnostic flags; one compile unit only; no linked quantizer, linkage, model quantization or P1c replay',
                   files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.smoke-', dir=out.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(receipt, f, sort_keys=True)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == '__main__':
    main()
