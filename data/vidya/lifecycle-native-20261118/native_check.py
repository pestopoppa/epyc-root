#!/usr/bin/python3
"""Run the strict lifecycle source adapter once against a sealed observation."""
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parent / "sources/root"
sealed = Path(sys.argv[1]).resolve(strict=True)
ledger = sealed.parent / "output" / f"native-check-{uuid4().hex}.jsonl"
cmd = [sys.executable, "-I", "-B", str(root / "scripts/vidya/cli.py"), "--json", "ingest",
       "kernel-promotion-lifecycle", "--path", str(sealed), "--dry-run", "--ledger", str(ledger),
       "--as-of", datetime.now(UTC).isoformat()]
result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
report = json.loads(result.stdout)
if (report["units_matched"] != 1 or report["refused"] or report["missing"]
        or (report["units_projected"], report["frames_emitted"], len(report["declined"]))
        not in ((1, 3, 0), (0, 0, 1))):
    raise ValueError(f"native adapter refused or returned an unexpected disposition: {report}")
print(json.dumps(report, sort_keys=True))
