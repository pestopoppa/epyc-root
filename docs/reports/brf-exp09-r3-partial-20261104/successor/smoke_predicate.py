#!/usr/bin/env python3
"""Qualify smoke only on a fresh R4 dry-run verified-quote cell."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
try:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
raise SystemExit(0 if any(
    row.get("kind") == "cell" and row.get("arm") == "verified_quote" and row.get("dryrun") is True
    for row in rows
) else 1)
