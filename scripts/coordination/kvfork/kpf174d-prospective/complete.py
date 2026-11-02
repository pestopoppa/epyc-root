#!/usr/bin/env python3
"""Accept only the declared, completed single-cell witness."""
import json
import sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text())
    cells = data['cells']
    assert data['schema'] == 'kpf174d-prospective/v1'
    assert data['historical_verdict_unchanged'] is True and data['smoke'] is True
    assert data['rc'] == 0 and data['partial'] is False
    assert len(cells) == 1 and all(v['verdict'] == 'SMOKE_ONLY' for v in cells.values())
    assert data['cleanup']['verified_dead'] is True
except (OSError, ValueError, AssertionError, KeyError, TypeError, IndexError):
    sys.exit(1)
