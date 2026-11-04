#!/usr/bin/env python3
"""Recognize a completed G3 native first cell from this publisher smoke.

A PASS is progress, not G3's scientific verdict. Verify a content-bound native
response and trace, and require explicit process-group drain.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def valid_progress(result_path, *, runs_root, smoke_t0):
    try:
        path = Path(result_path)
        if path.stat().st_mtime < smoke_t0:
            return False
        lines = path.read_text().splitlines()
        if len(lines) != 1:
            return False
        unit = json.loads(lines[0])
        if unit.get('cell') != 'q8_0-d1' or unit.get('status') != 'complete':
            return False
        root = Path(runs_root).resolve(strict=True)
        result = Path(unit['result']).resolve(strict=True)
        if not result.is_relative_to(root) or result.name != 'result.json':
            return False
        raw = result.read_bytes()
        if hashlib.sha256(raw).hexdigest() != unit['result_sha256']:
            return False
        native = json.loads(raw)
        if native.get('status') != 'complete' or native.get('process_group_drained') is not True:
            return False
        requests = native.get('requests')
        if not isinstance(requests, list) or len(requests) != 1 or not isinstance(requests[0], dict):
            return False
        response = requests[0]
        timings = response.get('timings')
        n = response.get('tokens_predicted')
        if n is None and isinstance(timings, dict):
            n = timings.get('predicted_n')
        if type(n) is not int or n <= 0:
            return False
        content = response.get('content')
        if not isinstance(content, str) or not content:
            return False
        log_path = Path(unit['server_log']).resolve(strict=True)
        if log_path != result.parent / 'server.log':
            return False
        text = log_path.read_text(errors='replace')
        if any(marker not in text for marker in ('G3_TARGET_BEGIN_V3', 'G3_TARGET_END_V3', 'G3_FATTN_DISPATCH_V3')):
            return False
        return True
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


def main():
    try:
        t0 = float(os.environ['FILLER_SMOKE_T0'])
        if not math.isfinite(t0):
            return 1
        path = os.environ['FILLER_DRYRUN_RESULT_PATH']
        root = Path(__file__).resolve().parent / 'runs'
        return 0 if valid_progress(path, runs_root=root, smoke_t0=t0) else 1
    except (OSError, ValueError, KeyError):
        return 1


if __name__ == '__main__':
    sys.exit(main())
