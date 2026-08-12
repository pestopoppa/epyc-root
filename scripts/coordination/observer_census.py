#!/usr/bin/env python3
"""Static half of the OBSERVATION CONTRACT — the part cheap enough to run on every commit.

ONE implementation, TWO consumers, so they cannot drift:

  * ``tests/test_observer_contract.py`` imports these checks (each as its own named,
    collected test) and adds the runtime battery on top.
  * ``scripts/hooks/observer_census_precommit.sh`` runs ``main()`` on every commit.

Deliberately dependency-free — stdlib and ``git`` only. A gate that needs pytest, jq
or a particular venv acquires a third state of its own ("the checker could not run"),
and a checker for *this* defect class arriving with *this* defect class would be a
poor joke. The one external call is ``git ls-files``, and its failure is raised, not
swallowed.

WHAT IT ENFORCES
----------------
  1. The registry is well formed; no duplicate rows.
  2. No row points at a file that no longer exists.
  3. RULE A — any file under the discovery roots that identifies a process by
     name/argv is registered (as adopted, deferred, or explicitly exempt-with-reason).
  4. RULE B — any file that sources ``observer_guard.sh`` is registered as adopted,
     so it cannot quietly drop out of the runtime battery.
  5. Every deferred row is bound to a REAL, currently-UNCHECKED ``- [ ]`` task in a
     real handoff. Deferring is fine. Deferring silently is what cost the hours.

Rules 3 and 4 are what make this survive its author: the subjects are discovered from
the tree, not listed by hand, so a new watchdog enrolls itself.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO / "scripts" / "coordination" / "observer_registry.json"

VALID_CONTRACTS = ("v1", "unadopted", "exempt")


def load_registry(path: Path | None = None) -> dict:
    return json.loads((path or REGISTRY_PATH).read_text())


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

def _git(*args: str) -> list[str]:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()


def source_files(reg: dict) -> list[str]:
    """Candidate files: tracked AND untracked-but-not-ignored.

    Untracked files are included on purpose. ``git ls-files`` alone lists only the
    index, so a brand-new watchdog sitting in the working tree would be invisible —
    and "invisible until somebody remembers to ``git add``" is the exact shape of
    gap this whole contract exists to close.
    """
    disc = reg["discovery"]
    listed = _git("ls-files", *disc["roots"])
    untracked = _git("ls-files", "--others", "--exclude-standard", *disc["roots"])
    out = []
    for rel in [*listed, *untracked]:
        if not any(rel.endswith(e) for e in disc["extensions"]):
            continue
        if any(s in "/" + rel for s in disc["skip_path_substrings"]):
            continue
        out.append(rel)
    return out


def matching(reg: dict, pattern: str) -> set[str]:
    rx = re.compile(pattern)
    hits = set()
    for rel in source_files(reg):
        try:
            text = (REPO / rel).read_text(errors="replace")
        except OSError:
            continue
        if rx.search(text):
            hits.add(rel)
    return hits


# --------------------------------------------------------------------------- #
# The checks. Each returns a list of human-readable violations.
# --------------------------------------------------------------------------- #

def check_registry_well_formed(reg: dict) -> list[str]:
    bad, seen = [], set()
    for row in reg["observers"]:
        rid = row.get("id", "<no id>")
        if row.get("contract") not in VALID_CONTRACTS:
            bad.append(f"{rid}: contract must be one of {VALID_CONTRACTS}, got {row.get('contract')!r}")
        if row.get("script") in seen:
            bad.append(f"{rid}: duplicate row for {row.get('script')}")
        seen.add(row.get("script"))
        if row.get("contract") == "unadopted":
            if not row.get("owning_handoff"):
                bad.append(f"{rid}: deferred without an owning handoff")
            if not row.get("task_marker"):
                bad.append(f"{rid}: deferred without a task marker")
        if row.get("contract") == "exempt" and not row.get("reason"):
            bad.append(f"{rid}: exempt without a recorded reason")
    return bad


def check_no_stale_rows(reg: dict) -> list[str]:
    return [
        f"{r['id']}: registry row points at {r['script']}, which does not exist"
        for r in reg["observers"] if not (REPO / r["script"]).exists()
    ]


def check_rule_a(reg: dict) -> list[str]:
    found = matching(reg, reg["discovery"]["identity_probe_pattern"])
    found -= set(reg["discovery"].get("self_exclude", []))
    registered = {r["script"] for r in reg["observers"]}
    missing = sorted(found - registered)
    if not missing:
        return []
    return [
        "These files identify a process by name/argv but are absent from "
        f"{REGISTRY_PATH.relative_to(REPO)}:\n    " + "\n    ".join(missing) +
        "\n  Add a row: contract 'v1' if it adopts observer_guard.sh, 'unadopted' with "
        "an owning handoff + task marker if it is a known gap, 'exempt' with a reason "
        "if it is genuinely out of scope. Silence is the one option removed."
    ]


def check_rule_b(reg: dict) -> list[str]:
    found = matching(reg, reg["discovery"]["adoption_pattern"])
    found -= set(reg["discovery"].get("self_exclude", []))
    found = {f for f in found if not f.endswith("observer_guard.sh")}
    by_script = {r["script"]: r for r in reg["observers"]}
    out = []
    for rel in sorted(found):
        row = by_script.get(rel)
        if row is None:
            out.append(f"{rel}: sources observer_guard.sh but has no registry row")
        elif row["contract"] != "v1":
            out.append(f"{rel}: sources observer_guard.sh but is registered '{row['contract']}' "
                       "(adoption means contract 'v1', which is what enrols it in the battery)")
    return out


def check_deferrals_are_live(reg: dict) -> list[str]:
    out = []
    for row in reg["observers"]:
        if row.get("contract") != "unadopted":
            continue
        handoff = REPO / row["owning_handoff"]
        if not handoff.exists():
            out.append(f"{row['id']}: owning handoff {row['owning_handoff']} does not exist")
            continue
        marker = row["task_marker"]
        open_lines = [
            ln for ln in handoff.read_text(errors="replace").splitlines()
            if marker in ln and re.search(r"-\s*\[\s\]", ln)
        ]
        if not open_lines:
            out.append(
                f"{row['id']}: no OPEN '- [ ]' task carrying marker '{marker}' in "
                f"{row['owning_handoff']}. Either the migration landed (flip the registry "
                "row to contract 'v1') or the deferral was silently lost."
            )
    return out


CHECKS = {
    "registry-well-formed": check_registry_well_formed,
    "no-stale-rows": check_no_stale_rows,
    "rule-a-process-pattern-observers-registered": check_rule_a,
    "rule-b-guard-adopters-registered": check_rule_b,
    "deferrals-bound-to-open-tasks": check_deferrals_are_live,
}


def run_all(reg: dict | None = None) -> dict[str, list[str]]:
    reg = reg if reg is not None else load_registry()
    return {name: fn(reg) for name, fn in CHECKS.items()}


def main(argv: list[str] | None = None) -> int:
    results = run_all()
    failed = {k: v for k, v in results.items() if v}
    if not failed:
        print(f"observer census: OK ({len(load_registry()['observers'])} observers registered)")
        return 0
    print("\nOBSERVER CONTRACT VIOLATION\n", file=sys.stderr)
    for name, problems in failed.items():
        print(f"  [{name}]", file=sys.stderr)
        for p in problems:
            print(f"    - {p}", file=sys.stderr)
    print(
        "\n  Context: a watchdog that cannot observe its target must say so. On 2026-08-12 one\n"
        "  identified a healthy daemon by an argv pattern that had drifted, called it dead\n"
        "  forever, and relaunch-looped for hours in silence. Registry:\n"
        f"  {REGISTRY_PATH.relative_to(REPO)}   Contract: scripts/coordination/observer_guard.sh\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
