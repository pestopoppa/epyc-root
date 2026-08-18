#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/hooks/check_live_holder_interference.sh (rider R10).

WHY THE CASES LIVE IN A JSON FILE. A test that embeds the dangerous patterns as
literals gets blocked by the very hook it is testing — which happened during
bring-up, twice. Keeping the cases in a data file means this runner's own command
line never contains them.

  (The original reason given here was that the hook "cannot distinguish a command
  that writes drop_caches from one that mentions writing drop_caches". As of
  2026-08-18 it can: drop_caches_write_scan.py strips heredoc bodies, quoted runs
  and comments before matching. The data file is still the right shape — a test
  runner should not have to rely on a guard being correct in order to test it —
  but the claim it rested on is no longer true.)

Usage:
    scripts/hooks/tests/test_live_holder_interference.py            # drop_caches rules
    scripts/hooks/tests/test_live_holder_interference.py --all      # + running-script rules
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
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


@contextlib.contextmanager
def synthetic_region():
    """Hold a GLOBAL region lock in an ISOLATED dir, so block cases always run.

    The block half of this suite used to depend on the host happening to have a region
    claimed — "the normal state on this host while the orchestrator serves". When nothing
    held one, every `expect: 2` case SKIPPED and the suite still printed "all checks
    passed", so the enforcement half could rot unnoticed while the permissive half stayed
    green. Measured 2026-08-18: with no holder, 5 of 5 block cases skipped.

    A real flock in a temp dir removes the dependency. The dir is isolated on purpose —
    creating a `cpu_region.GLOBAL.*` file in the SHARED lock dir would make every other
    session's region check see a claim that does not exist.
    """
    d = tempfile.mkdtemp()
    lock = Path(d) / "cpu_region.GLOBAL.pytest-synthetic.lock"
    lock.touch()
    fh = lock.open("w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield d
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def test_drop_caches() -> list[str]:
    """Data-driven: allow mentions, block real writes.

    Allow cases run against the live host. Block cases run under a SYNTHETIC held region
    (see synthetic_region) so they are deterministic and never silently skipped.
    """
    failures: list[str] = []
    empty = tempfile.mkdtemp()
    cases = json.loads(CASES.read_text())
    with synthetic_region() as held:
        for case in cases:
            expect = case["expect"]
            env = {"EPYC_REGION_LOCK_DIR": held} if expect == 2 else None
            rc = run_hook({"tool_name": "Bash", "tool_input": {"command": case["cmd"]}}, env=env)
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
