#!/usr/bin/env python3
"""STACKCHG-DFLASH2-20261003: DECLARED WITHDRAWAL of worker_vision from the contention matrix stamp.

worker_vision moves GPU_HOST_LANE 184-191/-t 8 -> NUMA_HALF_A 0-47,96-143/-t 48 (cold CPU). Its
three measured pairs describe a placement that no longer exists, and because the top-level
`topology_hash` is computed over the pairwise-stamped role set (contention.matrix_stamped_roles),
leaving them makes the WHOLE matrix read STALE — contention_gate then QUEUEs every BACKGROUND
request and DEGRADED_ALLOWs every foreground one, stack-wide, until a re-bench.

contention_matrix.py has no withdraw subcommand, so this tool does the one honest thing
available without re-measuring (same shape as ARCHSWAP-20260927's declared relabel):

  * removes ONLY the `pairs`/`unknown_pairs` entries that name the withdrawn role, keeping
    them verbatim as a commented audit block (no measured number is altered or invented);
  * asserts every REMAINING stamped role's numa_config block is byte-for-byte (as parsed YAML)
    identical in the base and candidate topology — refuses otherwise (a placement change for
    a remaining role needs a re-measurement, not a restamp);
  * asserts the OLD stamp recomputes from the BASE tree (so the restamp is provably a subset
    of the same inputs);
  * restamps `topology_hash` with the repo's own topology_fingerprint_for_matrix().

After this, worker_vision is an UNKNOWN pair: contention.pair_policy -> QUEUE for background,
ALLOW-with-warning for foreground — correct for an unmeasured cold role. The rest of the stack
stays certified. Re-bench its pairs (contention_matrix.py) if/when it becomes a hot role again.

usage: withdraw_contention_role.py <base-orch-tree> <candidate-orch-tree> [--write]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROLE = "worker_vision"
MARK = "STACKCHG-DFLASH2-20261003 DECLARED WITHDRAWAL"

_FP = r"""
import sys, json
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1] + "/scripts/server")
from stack_numa import NUMA_CONFIG
from src.scheduling import contention
from pathlib import Path; m = contention.load_contention_matrix(Path(sys.argv[2]))
print(json.dumps({"hash": contention.topology_fingerprint_for_matrix(NUMA_CONFIG, m),
                  "stamped": sorted(contention.matrix_stamped_roles(m))}))
"""


def _fingerprint(tree: Path, matrix_path: Path) -> dict:
    out = subprocess.run([sys.executable, "-c", _FP, str(tree), str(matrix_path)],
                         cwd=tree, capture_output=True, text=True, check=False,
                         env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    if out.returncode != 0:
        raise SystemExit(f"REFUSING: fingerprint in {tree} failed:\n{out.stderr[-1500:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 1
    base, cand = (Path(a).resolve() for a in args)
    write = "--write" in sys.argv[1:]
    path = cand / "orchestration" / "contention_matrix.yaml"
    text = path.read_text()
    if MARK in text:
        print(f"REFUSING: {path} already carries the withdrawal")
        return 2
    old_hash = re.search(r'^topology_hash: "([0-9a-f]+)"', text, re.M).group(1)

    # 1. the OLD stamp must recompute from the BASE tree (proves we restamp the same inputs)
    base_fp = _fingerprint(base, base / "orchestration" / "contention_matrix.yaml")
    if base_fp["hash"] != old_hash:
        print(f"REFUSING: base tree recomputes {base_fp['hash']}, matrix says {old_hash}")
        return 2

    # 2. cut the withdrawn role's entries out of pairs/unknown_pairs, verbatim
    lines = text.split("\n")
    start = lines.index("pairs:")
    end = lines.index("unknown_pairs:") + 1
    while end < len(lines) and (lines[end].startswith(" ") or lines[end] == ""):
        end += 1
    kept, withdrawn, block = [], [], []

    def flush() -> None:
        if block:
            (withdrawn if re.search(rf"roles: \[.*'{ROLE}'.*\]", block[0]) else kept).extend(block)
            block.clear()

    for line in lines[start:end]:
        if line.startswith("  - roles:") or not line.startswith("  "):
            flush()
        (block if line.startswith("  ") else kept).append(line)
    flush()
    if not withdrawn:
        print(f"REFUSING: no stamped entry names {ROLE}")
        return 2
    # Every withdrawn pair is re-DECLARED as an unknown pair (never silently missing:
    # tests/unit/test_scheduling_contention.py::test_load_real_matrix requires every
    # cross-role pair of the lineup to be measured OR declared unknown). An unknown
    # pair gates as background QUEUE / foreground ALLOW-with-warning.
    reason = ("placement_withdrawn (STACKCHG-DFLASH2-20261003): worker_vision moved "
              "GPU_HOST_LANE 184-191/-t8 -> NUMA_HALF_A 0-47,96-143/-t48 as a COLD (warm-tier) "
              "CPU role; the measured pair described the old placement and was withdrawn. "
              "Re-bench with contention_matrix.py before worker_vision becomes a hot role")
    declared = []
    for line in withdrawn:
        if line.startswith("  - roles:"):
            declared += [line, f'    reason: "{reason}"']
    last = max(i for i, line in enumerate(kept) if line.strip())
    kept = kept[: last + 1] + declared + kept[last + 1:]
    new_text = "\n".join(lines[:start] + kept + lines[end:])

    # 3. every OTHER stamped role keeps an identical placement
    tmp = path.with_suffix(".withdraw.tmp.yaml")
    tmp.write_text(new_text)
    try:
        cand_fp = _fingerprint(cand, tmp)
    finally:
        tmp.unlink()
    remaining = set(cand_fp["stamped"]) - {ROLE}
    if ROLE not in set(cand_fp["stamped"]):
        print(f"REFUSING: {ROLE} should be stamped through its declared unknown pairs")
        return 2
    topo = lambda t: (yaml.safe_load((t / "orchestration" / "stack_topology.yaml").read_text())
                      .get("numa_config") or {})
    tb, tc = topo(base), topo(cand)
    moved = sorted(r for r in remaining if tb.get(r) != tc.get(r))
    if moved:
        print(f"REFUSING: remaining stamped role(s) {moved} changed placement — RE-MEASURE")
        return 2

    new_hash = cand_fp["hash"]
    new_text = new_text.replace(f'topology_hash: "{old_hash}"', f'topology_hash: "{new_hash}"', 1)
    note = (
        f"# {MARK} (tools/withdraw_contention_role.py, epyc-root\n"
        "# artifacts/operator/stack-change-dflash2-20261003). worker_vision moved GPU_HOST_LANE\n"
        "# 184-191/-t8 -> NUMA_HALF_A 0-47,96-143/-t48 as a COLD (warm-tier) CPU role, so its\n"
        f"# {len([l for l in withdrawn if l.startswith('  - roles:')])} measured pair(s) no longer "
        "describe any placement: WITHDRAWN from `pairs` (kept verbatim\n"
        "# below, commented) and re-declared under `unknown_pairs`. The other stamped roles "
        f"{sorted(remaining)}\n"
        "# were asserted to have IDENTICAL numa_config in base and candidate; no measured value,\n"
        "# date or provenance changed. The stamp now covers worker_vision's DECLARED new placement.\n"
        f"# topology_hash restamped {old_hash} -> {new_hash}. worker_vision pairs gate as UNKNOWN\n"
        "# (background QUEUE / foreground ALLOW). Re-bench with contention_matrix.py if it goes hot.\n"
        "# Withdrawn entries:\n"
        + "".join(f"#   {l}\n" for l in withdrawn if l.strip())
    )
    i = new_text.index("topology_hash:")
    new_text = new_text[:i] + note + new_text[i:]
    print(f"withdrawn pairs: {[l.strip() for l in withdrawn if l.startswith('  - roles:')]}")
    print(f"remaining stamped roles (placement identical): {sorted(remaining)}")
    print(f"topology_hash {old_hash} -> {new_hash}")
    if write:
        path.write_text(new_text)
        print(f"wrote {path}")
    else:
        print("dry run (pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
