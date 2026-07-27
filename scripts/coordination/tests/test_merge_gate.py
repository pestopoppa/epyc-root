#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/coordination/merge_gate.py (rider R6).

Classification is tested as a unit (no git needed) so the cases are explicit and
host-independent; the fail-closed path is tested end-to-end, because that is the
behaviour that matters most — a gate list which cannot be verified must refuse,
not default to permitting.

Usage: scripts/coordination/tests/test_merge_gate.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.merge_gate import classify, load_gate_list  # noqa: E402

GATE_SCRIPT = REPO_ROOT / "scripts" / "coordination" / "merge_gate.py"

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def main() -> int:
    gate = load_gate_list()
    print("== gate list loads and matches its pin ==")
    check(bool(gate.get("paths")), f"{len(gate.get('paths') or [])} path rule(s) loaded")
    check(bool(gate.get("branches")), f"{len(gate.get('branches') or [])} branch rule(s) loaded")
    check(bool(gate.get("conceptual")), "conceptual (unenforceable) entries present and separate")

    print("\n== path rules ==")
    r = classify("epyc-root", ["MEASUREMENT.md"], "main", gate)
    check(r["verdict"] == "gated", "MEASUREMENT.md in epyc-root -> gated")

    r = classify("epyc-root", ["agents/shared/MEASUREMENT_POLICY.md"], "main", gate)
    check(r["verdict"] == "gated", "MEASUREMENT_POLICY.md -> gated")

    r = classify("epyc-orchestrator", ["orchestration/instrument_eras.yaml"], "main", gate)
    check(r["verdict"] == "gated", "instrument_eras.yaml in epyc-orchestrator -> gated")

    r = classify("epyc-orchestrator", ["orchestration/autopilot_baseline.yaml"], "main", gate)
    check(r["verdict"] == "gated", "autopilot_baseline.yaml -> gated")

    print("\n== rules are REPO-SCOPED (a path only gates in its own repo) ==")
    r = classify("epyc-orchestrator", ["MEASUREMENT.md"], "main", gate)
    check(r["verdict"] == "autonomous",
          "MEASUREMENT.md under epyc-orchestrator does NOT trip the epyc-root rule")

    print("\n== ordinary work is autonomous ==")
    for paths, why in [
        (["handoffs/active/session-bus-thin-dispatcher.md"], "a handoff"),
        (["scripts/coordination/session_bus.py"], "a source file"),
        (["coordination/session-bus/config.yaml"], "bus config"),
        (["MEASUREMENT_NOTES.md"], "similarly-named non-boundary file"),
        (["progress/2026-07/2026-07-27.md", "CLAUDE.md"], "progress + CLAUDE.md together"),
    ]:
        r = classify("epyc-root", paths, "main", gate)
        check(r["verdict"] == "autonomous", f"{why} -> autonomous")

    print("\n== branch rule + extra requirement ==")
    r = classify("epyc-llama", ["ggml/src/ggml.c"], "production-consolidated-v8", gate)
    check(r["verdict"] == "gated", "frozen production branch -> gated")
    check(any("four-step" in e for e in r["extra_requirements"]),
          "carries the four-step promotion requirement")
    r = classify("epyc-llama", ["ggml/src/ggml.c"], "experimental-v9-refresh", gate)
    check(r["verdict"] == "autonomous", "an experimental branch is autonomous")

    print("\n== a gated result carries an actionable token block ==")
    r = classify("epyc-root", ["MEASUREMENT.md"], "main", gate)
    from scripts.coordination.merge_gate import token_block
    block = token_block(r, "epyc-root")
    check(block.lstrip().startswith("###"), "block is a token-queue section")
    check("- [ ]" in block, "block carries an UNGRANTED checkbox for the operator")
    check("agent defect" in block, "block states that a failing command is an agent defect")

    print("\n== mixed change: one gated path among many clean ones still gates ==")
    r = classify("epyc-root", ["README.md", "scripts/x.py", "MEASUREMENT.md", "docs/y.md"],
                 "main", gate)
    check(r["verdict"] == "gated", "one human-only path among four gates the whole merge")
    check(r["changed"] == 4, "reports the full changed count, not just the hits")

    print("\n== fail-closed when the gate list is unusable (end-to-end) ==")
    pin = REPO_ROOT / "coordination" / "session-bus" / "human_only_paths.sha256"
    original = pin.read_text()
    try:
        pin.write_text("0" * 64 + "\n")           # simulate drift
        out = subprocess.run([str(GATE_SCRIPT), "check"], capture_output=True, text=True)
        check(out.returncode == 3, f"drifted pin -> rc 3 (got {out.returncode})")
        check("DRIFTED" in out.stderr, "says the gate list drifted")
        check("cannot authorise" in out.stderr, "states that it cannot authorise a merge")
    finally:
        pin.write_text(original)
    out = subprocess.run([str(GATE_SCRIPT), "check"], capture_output=True, text=True)
    check(out.returncode == 0, f"pin restored -> rc 0 again (got {out.returncode})")

    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
