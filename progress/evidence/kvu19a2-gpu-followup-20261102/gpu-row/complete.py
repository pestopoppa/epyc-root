#!/usr/bin/env python3
"""Status-aware rowflow completion; controls and failures never complete a row."""
import json
from pathlib import Path
import sys

ROW_ID = 'handoff-kvu-kvu19a2-repeatability-20261104'

def complete(path, mode):
    try:
        path = Path(path)
        if path.is_symlink() or not path.is_file(): return False
        result = json.loads(path.read_text())
        if result.get('row_id') != ROW_ID or result.get('mode') != mode: return False
        allowed = {'qualification': {'qualified_gpu_smoke'}, 'full': {'completed_sample', 'observed_mismatch'}}
        return result.get('status') in allowed.get(mode, set())
    except (OSError, ValueError, TypeError): return False

if __name__ == '__main__':
    sys.exit(0 if len(sys.argv) == 3 and complete(sys.argv[1], sys.argv[2]) else 1)
