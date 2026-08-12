#!/usr/bin/env python3
"""Derive the LIVE topology fingerprint that gates every inference-batch entry.

WHY THIS EXISTS
---------------
Three different topology-hash values were simultaneously in circulation on
2026-08-12 (``8c8cfcbb13d2611d`` pinned in the entries, ``df373c79cc4af06f`` in
the kernel-op2 entries, ``bc28e15d`` recorded on 2026-07-30) while the live
value was ``171f86f9188211e9``. Every one of them entered circulation the same
way: somebody *recorded a number* instead of *recording how to get the number*.

So this script deliberately hard-codes NO hash. It derives the value through the
exact code path the two enforcing consumers use, and can therefore never go
stale:

  consumer 1 (fail-closed, exact match)
      epyc-orchestrator/scripts/server/preflight_gate.py
          check_topology_hashes(expected_topology_hash=...)
            -> _live_topology_hash()
            -> src.scheduling.contention.topology_fingerprint_for_matrix(
                   scripts.server.stack_numa.NUMA_CONFIG, <contention matrix>)

  consumer 2 (attestation-mediated)
      epyc-inference-research/scripts/benchmark/run_batch_entry.py::topology_gate
          compares the entry's required_topology_hash against the topology_hash
          recorded in a B4 attestation JSON.

The fingerprint is sha256 over the sorted ``(role, [(cpu_list, port, threads)])``
tuples of NUMA_CONFIG, truncated to 16 hex chars, restricted to the role subset
the contention matrix stamped. See contention.py::topology_fingerprint.

USAGE
-----
    python3 scripts/coordination/derive_topology_hash.py            # print the hash
    python3 scripts/coordination/derive_topology_hash.py --json     # full derivation record
    python3 scripts/coordination/derive_topology_hash.py --check-entries
        exit 0 if every inference-batch entry pins the live hash, 1 otherwise

Read-only. Starts no server, runs no benchmark, touches no host state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
ORCH_PY = ORCH / ".venv/bin/python"
REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRIES_DIR = REPO_ROOT / "coordination" / "inference-batch" / "entries"
MANIFEST = REPO_ROOT / "coordination" / "inference-batch" / "manifest.yaml"

_DERIVE_SNIPPET = r"""
import json, sys
sys.path.insert(0, '.')
from scripts.server.preflight_gate import _live_topology_hash, CONTENTION_MATRIX
from scripts.server.stack_numa import NUMA_CONFIG
from src.scheduling.contention import (
    load_contention_matrix, matrix_stamped_roles,
    topology_fingerprint, topology_fingerprint_for_matrix,
)
matrix = load_contention_matrix(CONTENTION_MATRIX)
roles = sorted(matrix_stamped_roles(matrix) or [])
out = {
    "live_topology_hash": _live_topology_hash(),
    "contention_matrix_path": str(CONTENTION_MATRIX),
    "matrix_stamped_roles": roles,
    "numa_config_roles": sorted(NUMA_CONFIG.keys()),
    "fingerprint_for_matrix": topology_fingerprint_for_matrix(NUMA_CONFIG, matrix),
    "fingerprint_full_numa_config": topology_fingerprint(NUMA_CONFIG),
    "numa_config_instances": {
        r: [list(i) for i in (NUMA_CONFIG.get(r) or {}).get("instances", [])]
        for r in roles if r in NUMA_CONFIG
    },
}
print(json.dumps(out))
"""


def derive() -> dict:
    """Return the full derivation record, or exit non-zero on failure (fail closed)."""
    if not ORCH_PY.exists():
        sys.exit(f"FATAL: orchestrator venv interpreter missing: {ORCH_PY}")
    res = subprocess.run(
        [str(ORCH_PY), "-c", _DERIVE_SNIPPET],
        cwd=str(ORCH), capture_output=True, text=True, timeout=180,
    )
    if res.returncode != 0:
        sys.exit(f"FATAL: derivation failed (exit {res.returncode}):\n{res.stderr}")
    try:
        rec = json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        sys.exit(f"FATAL: derivation produced unparseable output:\n{res.stdout}\n{res.stderr}")

    live = rec.get("live_topology_hash")
    if not isinstance(live, str) or len(live) != 16:
        sys.exit(f"FATAL: not a 16-char fingerprint: {live!r} (fail closed, do NOT pin this)")
    # Cross-check: the two derivation routes must agree, else the matrix role
    # subset is not what the consumers think it is.
    if live != rec.get("fingerprint_for_matrix"):
        sys.exit(
            "FATAL: _live_topology_hash() disagrees with topology_fingerprint_for_matrix "
            f"({live} vs {rec.get('fingerprint_for_matrix')}) — derivation is not trustworthy"
        )
    rec["derived_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec["derivation"] = (
        "preflight_gate._live_topology_hash() -> "
        "contention.topology_fingerprint_for_matrix(stack_numa.NUMA_CONFIG, contention_matrix)"
    )
    return rec


def check_entries(live: str) -> int:
    """Exit 0 only if every pinned required_topology_hash equals the live value."""
    try:
        import yaml
    except ImportError:
        sys.exit("FATAL: pyyaml missing; run with the orchestrator venv interpreter")

    bad: list[tuple[str, str, str]] = []
    seen = 0
    sources = sorted(ENTRIES_DIR.glob("*.yaml"))
    if MANIFEST.exists():
        sources.append(MANIFEST)
    for path in sources:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and isinstance(doc.get("entries"), list):
            items = doc["entries"]
        elif isinstance(doc, list):
            items = doc
        else:
            items = [doc]
        for item in items:
            if not isinstance(item, dict):
                continue
            topo = (item.get("preconditions") or {}).get("topology")
            pinned = topo.get("required_topology_hash") if isinstance(topo, dict) else None
            pinned = pinned or item.get("required_topology_hash")
            if pinned is None:
                continue
            seen += 1
            if pinned != live:
                bad.append((path.name, str(item.get("task_id")), pinned))

    print(f"live topology hash: {live}")
    print(f"pinned entries checked: {seen}")
    if seen == 0:
        # An empty check is a vacuous pass — refuse it.
        print("FAIL: no pinned entries found; the check inspected nothing (vacuous)")
        return 1
    if bad:
        print(f"FAIL: {len(bad)} entr(y/ies) pin a stale topology hash:")
        for fname, task_id, pinned in bad:
            print(f"  {fname}: {task_id} pins {pinned}")
        return 1
    print("OK: every pinned entry matches the live topology hash")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="print the full derivation record")
    ap.add_argument("--check-entries", action="store_true",
                    help="exit 1 if any inference-batch entry pins a non-live hash")
    args = ap.parse_args()

    rec = derive()
    if args.check_entries:
        return check_entries(rec["live_topology_hash"])
    if args.json:
        print(json.dumps(rec, indent=2))
    else:
        print(rec["live_topology_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
