#!/usr/bin/env python3
"""Completion predicate: require exactly the full production cohort, never dry-run units."""
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent
cohort = json.loads((ROOT / 'dataset/cohort.json').read_text())
expected = {row['id'] for row in cohort}
result = ROOT / 'attempts/production/results.jsonl'
manifest = ROOT / 'attempts/production/run.json'
if len(expected) != 60 or not result.is_file() or not manifest.is_file():
    raise SystemExit(1)
run = json.loads(manifest.read_text())
rows = [json.loads(line) for line in result.read_text().splitlines() if line.strip()]
ids = [row.get('id') for row in rows]
def positive_finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

if run.get('exit_code') != 0 or run.get('rows_written') != 60 or len(ids) != 60 or set(ids) != expected or len(set(ids)) != 60:
    raise SystemExit(1)
if any(not positive_finite(row.get('decode_tok_s')) or
       not isinstance(row.get('decode_tokens'), int) or isinstance(row.get('decode_tokens'), bool) or row['decode_tokens'] <= 0
       for row in rows):
    raise SystemExit(1)
