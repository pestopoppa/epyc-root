#!/usr/bin/env python3
"""Accept only the publisher's separate, real partial source-reference record."""
import json, os, sys
from pathlib import Path
try:
    path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    full = Path(__file__).resolve().parent / 'out/full-results.jsonl'
    if not path.is_absolute() or path.resolve() == full.resolve():
        raise ValueError('smoke output not isolated')
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    row = rows[-1]
    if not (row.get('type') == 'source_reference_scan' and row.get('partial') is True
            and row.get('graph_computed') is False
            and row.get('head') == '4f4f1443dba949c9d83d98cd37fe31210b6fb087'
            and row.get('symbol') == 'audit_coverage'
            and row.get('source') == 'scripts/benchmark/kpf64_replay/cohort_audit.py'
            and isinstance(row.get('references'), list) and len(row['references']) > 0
            and all(isinstance(ref, str) and ref for ref in row['references'])):
        raise ValueError('incomplete source references')
except (KeyError, OSError, ValueError, IndexError, TypeError, json.JSONDecodeError):
    sys.exit(1)
