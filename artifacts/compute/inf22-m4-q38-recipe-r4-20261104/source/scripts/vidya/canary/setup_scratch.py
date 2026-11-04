#!/usr/bin/env python3
"""Create fresh isolated canary state; never modify the source ledger."""
from pathlib import Path
import hashlib
import shutil
import os

parent = Path("/mnt/raid0/llm/tmp")
base = Path(os.environ["CANARY_SCRATCH"]).resolve()
if not base.is_relative_to(parent) or base == parent:
    raise SystemExit("CANARY_SCRATCH must be a new directory under /mnt/raid0/llm/tmp")
base.mkdir(mode=0o700, parents=False, exist_ok=False)
source = Path("/mnt/raid0/llm/state/vidya")
for name in ("A", "B-autopilot"):
    dest = base / "state" / name
    dest.mkdir(parents=True)
    for file in ("ledger.jsonl", "ledger.jsonl.sync.json"):
        shutil.copy2(source / file, dest / file)
    for directory in ("loop-memo", "loop-known-good"):
        shutil.copytree(source / directory, dest / directory)
(base / "alarm").mkdir()
(base / "alarm" / "alarm_config.yaml").write_text(
    "schema_version: alarm_channel.config.v1\nenabled: false\nbackend: ntfy\n"
    "advisory_mirror: false\nntfy:\n  url: https://ntfy.sh/REPLACE-ME-canary-disabled\n"
    "  timeout_s: 1\nemail:\n  to: REPLACE-ME@example.invalid\nfile:\n"
    f"  path: {base / 'alarm/alarms.jsonl'}\n")
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
src_hash = digest(source / "ledger.jsonl")
if any(digest(base / "state" / n / "ledger.jsonl") != src_hash for n in ("A", "B-autopilot")):
    raise SystemExit("source ledger changed during copy; discard scratch")
print("CANARY_SCRATCH=" + str(base))
print("source ledger SHA-256=" + src_hash)
