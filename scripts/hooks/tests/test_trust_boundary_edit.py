#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/hooks/check_trust_boundary_edit.sh (rider R7).

The hook has two layers with deliberately different strictness, and the tests
mirror that split:

  Layer 1 — the gate list and its pin. Unconditional, needs no parsing, must
            never degrade.
  Layer 2 — the paths the gate list names. Needs the list parsed; ALLOWS with a
            warning if it cannot be read, because failing closed on an
            unreadable config would block every edit in the repo.

Usage: scripts/hooks/tests/test_trust_boundary_edit.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # tests -> hooks -> scripts -> repo root
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_trust_boundary_edit.sh"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")


def run(tool: str, path: str, env: dict | None = None) -> int:
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": tool, "tool_input": {"file_path": path}}),
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={**os.environ, **(env or {})},
    ).returncode


CASES: list[tuple[str, str, int, str]] = [
    # layer 1 — containment
    ("Edit",  "coordination/session-bus/human_only_paths.yaml",   2, "gate list (relative)"),
    ("Edit",  str(REPO_ROOT / "coordination/session-bus/human_only_paths.yaml"), 2, "gate list (absolute)"),
    ("Write", str(REPO_ROOT / "coordination/session-bus/human_only_paths.sha256"), 2, "the pin itself"),
    # layer 2 — the named boundary paths
    ("Edit",  str(REPO_ROOT / "MEASUREMENT.md"), 2, "MEASUREMENT.md"),
    ("Edit",  str(REPO_ROOT / "agents/shared/MEASUREMENT_POLICY.md"), 2, "MEASUREMENT_POLICY.md"),
    ("Edit",  str(ORCH / "orchestration/instrument_eras.yaml"), 2, "era registry rows"),
    ("Edit",  str(ORCH / "orchestration/autopilot_baseline.yaml"), 2, "autopilot baseline"),
    # layer 2 — WILDCARD gate-list entries. Until 2026-08-03 the matcher quoted
    # its right-hand side, making the comparison literal, so `measurement/
    # protocols/*.md` matched nothing and Annexes B/Q/G were agent-writable
    # while the guard reported success. Every case above is a LITERAL entry and
    # passed throughout, which is why the defect survived this suite. These are
    # the cases that were missing; do not remove them.
    ("Edit",  str(REPO_ROOT / "measurement/protocols/bench-cpu.md"), 2, "Annex B (wildcard entry)"),
    ("Edit",  str(REPO_ROOT / "measurement/protocols/quality-eval.md"), 2, "Annex Q (wildcard entry)"),
    ("Write", str(REPO_ROOT / "measurement/protocols/gpu-cross-device.md"), 2, "Annex G (wildcard entry)"),
    ("Edit",  "measurement/protocols/bench-cpu.md", 2, "Annex B (wildcard, relative path)"),
    # must allow — ordinary work
    ("Edit",  str(REPO_ROOT / "coordination/session-bus/config.yaml"), 0, "bus config (agent-editable)"),
    ("Edit",  str(REPO_ROOT / "CLAUDE.md"), 0, "CLAUDE.md"),
    ("Edit",  str(REPO_ROOT / "handoffs/active/session-bus-thin-dispatcher.md"), 0, "a handoff"),
    ("Write", str(REPO_ROOT / "scripts/coordination/session_bus.py"), 0, "a source file"),
    ("Edit",  str(REPO_ROOT / "MEASUREMENT_NOTES.md"), 0, "similarly-named non-boundary file"),
    ("Edit",  str(ORCH / "orchestration/model_registry.yaml"), 0, "a non-boundary orchestrator file"),
    # The compliant-path counterpart to the wildcard cases above: the pattern
    # must not over-block. A non-.md file inside the protected directory, and a
    # .md file outside it, both stay writable.
    ("Edit",  str(REPO_ROOT / "measurement/protocols/README.txt"), 0, "non-.md inside a protected dir"),
    ("Edit",  str(REPO_ROOT / "measurement/policy-notes.md"), 0, ".md outside the protected dir"),
]


def main() -> int:
    failures: list[str] = []
    for tool, path, expect, why in CASES:
        rc = run(tool, path)
        ok = rc == expect
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want={expect}  {why}")
        if not ok:
            failures.append(why)

    rc = run("Edit", str(REPO_ROOT / "MEASUREMENT.md"), {"EPYC_ALLOW_TRUST_BOUNDARY_EDIT": "1"})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  explicit operator override")
    if not ok:
        failures.append("override")

    # Layer 2 degrades open when the gate list is unreadable; layer 1 must not.
    with tempfile.TemporaryDirectory() as empty:
        rc = run("Edit", str(REPO_ROOT / "MEASUREMENT.md"), {"CLAUDE_PROJECT_DIR": empty})
        ok = rc == 0
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  layer 2 degrades open (list unreadable)")
        if not ok:
            failures.append("layer 2 should degrade open")
        rc = run("Edit", str(Path(empty) / "coordination/session-bus/human_only_paths.yaml"),
                 {"CLAUDE_PROJECT_DIR": empty})
        ok = rc == 2
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=2  layer 1 holds even then")
        if not ok:
            failures.append("layer 1 must not degrade")

    print(f"\n{'FAILED: ' + '; '.join(failures) if failures else 'all checks passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
