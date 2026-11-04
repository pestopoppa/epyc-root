#!/usr/bin/env python3
"""Qualify only on this attempt's single dry-run verified-quote cell."""
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
cells = [row for row in rows if row.get("kind") == "cell"]
valid = (
    len(rows) == 1
    and len(cells) == 1
    and cells[0].get("arm") == "verified_quote"
    and cells[0].get("dryrun") is True
    and bool(cells[0].get("exec_id"))
)
raise SystemExit(0 if valid else 1)
