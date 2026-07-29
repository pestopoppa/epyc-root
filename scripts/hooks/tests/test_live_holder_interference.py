#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/hooks/check_live_holder_interference.sh (rider R10).

WHY THE CASES LIVE IN A JSON FILE. A PreToolUse hook matches the text of a
command, so it cannot distinguish "a command that writes drop_caches" from "a
command that mentions writing drop_caches". A test that embeds the dangerous
patterns as literals therefore gets blocked by the very hook it is testing —
which happened during bring-up, twice. Keeping the cases in a data file means
this runner's own command line never contains them.

Usage:
    scripts/hooks/tests/test_live_holder_interference.py            # drop_caches rules
    scripts/hooks/tests/test_live_holder_interference.py --all      # + running-script rules
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_live_holder_interference.sh"
CASES = HERE / "live_holder_interference_cases.json"


def run_hook(payload: dict, env: dict | None = None) -> int:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, env=full_env, cwd=str(REPO_ROOT),
    ).returncode


def test_drop_caches() -> list[str]:
    """Data-driven: allow mentions, block real writes.

    Expectations assume at least one CPU region is currently claimed, which is
    the normal state on this host while the orchestrator serves. When nothing
    holds a region the block cases cannot fire, so they are skipped rather than
    reported as failures.
    """
    failures: list[str] = []
    empty = tempfile.mkdtemp()
    holder_present = run_hook(
        {"tool_name": "Bash", "tool_input": {"command": "echo 3 > /proc/sys/vm/" + "drop_caches"}}
    ) == 2
    for case in json.loads(CASES.read_text()):
        expect = case["expect"]
        if expect == 2 and not holder_present:
            print(f"  SKIP  (no region held)  {case['why']}")
            continue
        rc = run_hook({"tool_name": "Bash", "tool_input": {"command": case["cmd"]}})
        ok = rc == expect
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want={expect}  {case['why']}")
        if not ok:
            failures.append(case["why"])

    # Allow-path proof that does not depend on host state: an empty lock dir.
    rc = run_hook({"tool_name": "Bash",
                   "tool_input": {"command": "echo 3 > /proc/sys/vm/" + "drop_caches"}},
                  env={"EPYC_REGION_LOCK_DIR": empty})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  no regions held (empty lock dir)")
    if not ok:
        failures.append("empty lock dir should allow")

    rc = run_hook({"tool_name": "Bash",
                   "tool_input": {"command": "echo 3 > /proc/sys/vm/" + "drop_caches"}},
                  env={"EPYC_ALLOW_LIVE_INTERFERENCE": "1"})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  explicit operator override")
    if not ok:
        failures.append("override should allow")
    os.rmdir(empty)
    return failures


def test_running_script() -> list[str]:
    failures: list[str] = []
    tmpdir = Path(tempfile.mkdtemp())
    script = tmpdir / "runner.sh"
    script.write_text("#!/bin/bash\nsleep 8\n")
    script.chmod(0o755)
    proc = subprocess.Popen(["bash", str(script)])
    time.sleep(0.8)
    checks = [
        (str(script), 2, "editing the running script"),
        (str(tmpdir / "other.sh"), 0, "editing a different script"),
        (str(tmpdir / "runner.py"), 0, "non-.sh path"),
    ]
    for path, expect, why in checks:
        rc = run_hook({"tool_name": "Edit", "tool_input": {"file_path": path}})
        ok = rc == expect
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want={expect}  {why}")
        if not ok:
            failures.append(why)
    proc.terminate()
    proc.wait(timeout=10)
    time.sleep(0.5)
    rc = run_hook({"tool_name": "Edit", "tool_input": {"file_path": str(script)}})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  same script after it exits")
    if not ok:
        failures.append("post-exit edit should allow")
    script.unlink(missing_ok=True)
    os.rmdir(tmpdir)
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also run the running-script rules")
    args = ap.parse_args()

    print("== drop_caches under a live region claim ==")
    failures = test_drop_caches()
    if args.all:
        print("\n== editing a currently-executing script ==")
        failures += test_running_script()

    print(f"\n{'FAILED: ' + '; '.join(failures) if failures else 'all checks passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
