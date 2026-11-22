#!/usr/bin/env python3
"""repo_monitor.py — zero-token upstream repo monitor for intake entries converted to knowledge_only + monitor.

Reads research/repo_monitors.json, runs `git ls-remote <repo> HEAD` per entry and prints CHANGED / UNCHANGED /
ERROR against the recorded baseline_head. Exit 0 = all unchanged, 1 = at least one CHANGED, 2 = an ERROR.
Re-baseline by editing baseline_head after the owner has read the change."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def head(repo: str, timeout: int) -> str:
    out = subprocess.run(["git", "ls-remote", repo, "HEAD"], capture_output=True, text=True, timeout=timeout, check=True)
    return out.stdout.split()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(ROOT / "research" / "repo_monitors.json"))
    ap.add_argument("--timeout", type=int, default=30)
    a = ap.parse_args()
    rc = 0
    for m in json.loads(Path(a.config).read_text())["monitors"]:
        try:
            h = head(m["repo"], a.timeout)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {m['repo']} {e}")
            rc = 2
            continue
        if h == m["baseline_head"]:
            print(f"UNCHANGED {m['repo']} {h[:12]} ({m['intake']})")
        else:
            print(f"CHANGED {m['repo']} {m['baseline_head'][:12]} -> {h[:12]} ({m['intake']}): {m['on_change']}")
            rc = max(rc, 1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
