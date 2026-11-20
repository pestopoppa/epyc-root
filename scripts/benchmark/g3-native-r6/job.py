#!/usr/bin/env python3
"""Scheduled six-process G3 diagnostic; no performance claim."""
import json
import os
from pathlib import Path
import sys
import tempfile

SOURCE = Path('/mnt/raid0/llm/views/epyc-root-main/docs/reports/g3-mi210-verify-instrumentation')
sys.path.insert(0, str(SOURCE))
from native_protocol import execute

D = Path(__file__).resolve().parent


def main():
    runs = D / 'runs'
    runs.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='attempt-', dir=runs))
    result = Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH') or D / 'RESULT.json')
    if result.exists():
        raise RuntimeError('refuse to overwrite native result')
    base = json.loads((D / 'base.json').read_text())
    execute(base, attempt / 'capture')
    endpoint = attempt / 'capture/endpoint.json'
    # Includes partial UNKNOWN on a stopped/failed child, with captured drain.
    result.write_bytes(endpoint.read_bytes())
    record = json.loads(result.read_text())
    return 0 if len(record['cells']) == 6 and all(
        c['rc'] == 0 for c in record['cells'].values()) else 1


if __name__ == '__main__':
    sys.exit(main())
