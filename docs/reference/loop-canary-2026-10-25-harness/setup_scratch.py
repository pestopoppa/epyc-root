#!/usr/bin/env python3
"""Copy the canonical Vidya ledger state into per-canary scratch dirs (read-only on the source).

Every loop_beliefs prepare in this canary runs against a COPY, so its incremental ingest
(sync.sync / scoped_ingest), read log, known-good snapshot and loop-memo land in scratch,
never in /mnt/raid0/llm/state/vidya.
"""
import hashlib
import shutil
import subprocess
from pathlib import Path

BASE = Path("/mnt/raid0/llm/tmp/ws58-canary-20261025")
SRC = Path("/mnt/raid0/llm/state/vidya")
NAMES = ("A1-default", "A2-views", "B-autopilot")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    (BASE / "alarm").mkdir(parents=True, exist_ok=True)
    (BASE / "index").mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        dst = BASE / "state" / name
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("ledger.jsonl", "ledger.jsonl.sync.json"):
            shutil.copy2(SRC / f, dst / f)
        for d in ("loop-memo", "loop-known-good"):
            if (dst / d).exists():
                shutil.rmtree(dst / d)
            shutil.copytree(SRC / d, dst / d)
        print(name, "ledger sha256", sha(dst / "ledger.jsonl"))
    print("source ledger sha256", sha(SRC / "ledger.jsonl"))
    idx = subprocess.run(["git", "-C", "/workspace", "show", "origin/main:research/intake_index.yaml"],
                         capture_output=True, check=True).stdout
    head = subprocess.run(["git", "-C", "/workspace", "rev-parse", "origin/main"],
                          capture_output=True, text=True, check=True).stdout.strip()
    out = BASE / "index" / f"intake_index.origin-main-{head[:9]}.yaml"
    out.write_bytes(idx)
    print("index", out, hashlib.sha256(idx).hexdigest())
    # Alarm config: delivery disabled, placeholder URL, record file in scratch.
    (BASE / "alarm" / "alarm_config.yaml").write_text(
        "schema_version: alarm_channel.config.v1\n"
        "enabled: false\n"
        "backend: ntfy\n"
        "advisory_mirror: false\n"
        "ntfy:\n"
        "  url: https://ntfy.sh/REPLACE-ME-canary-disabled\n"
        "  timeout_s: 1\n"
        "email:\n"
        "  to: REPLACE-ME@example.invalid\n"
        "file:\n"
        f"  path: {BASE / 'alarm' / 'alarms.jsonl'}\n")
    print("alarm config written")


if __name__ == "__main__":
    main()
