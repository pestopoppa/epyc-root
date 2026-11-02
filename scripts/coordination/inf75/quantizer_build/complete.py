#!/usr/bin/env python3
"""Check custody of the exact quantizer build's recorded artifacts."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path('/mnt/raid0/llm/tmp/inf75-quantizer-7cdd7c97-20261102')
COMMIT = '7cdd7c97bed538a85c3b75331b6cdb369e5b2adc'
REQUIRED = ('source.tar', 'compiler.sha256', 'gcc-version.txt', 'gxx-version.txt',
            'cmake-version.txt', 'configure.log', 'build.log', 'linkage.log',
            'build/CMakeCache.txt', 'build/compile_commands.json', 'build/bin/llama-quantize')


def valid(record, root=ROOT):
    try:
        if (record['schema'] != 'epyc.inf75.quantizer_build.v1' or
                record['status'] != 'built' or record['source_commit'] != COMMIT or
                record['linkage_rc'] != 0):
            return False
        run = Path(record['run_dir']).resolve(strict=True)
        if run.parent != (root / 'runs').resolve(strict=True):
            return False
        files = record['files']
        if not isinstance(files, dict) or not all(str(run / name) in files for name in REQUIRED):
            return False
        if not any(Path(p).parent == run / 'build/bin' and 'ggml' in Path(p).name and '.so' in Path(p).name for p in files):
            return False
        for name, expected in files.items():
            path = Path(name)
            if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                return False
            if not path.is_absolute() or path.is_symlink() or not path.resolve(strict=True).is_relative_to(run):
                return False
            h = hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            if h.hexdigest() != expected:
                return False
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def main():
    path = os.environ.get('FILLER_DRYRUN_RESULT_PATH') if os.environ.get('FILLER_DRYRUN') == '1' else str(ROOT / 'RESULT.json')
    try:
        return 0 if valid(json.loads(Path(path).read_text())) else 1
    except (OSError, ValueError, TypeError):
        return 1


if __name__ == '__main__':
    sys.exit(main())
