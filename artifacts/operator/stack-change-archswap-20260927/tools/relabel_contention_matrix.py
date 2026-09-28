#!/usr/bin/env python3
"""ARCHSWAP-20260927: DECLARED RELABEL of the contention matrix's stamped sections.

The swap moves the role LABELS architect_general <-> architect_critic between two processes
whose placement tuples (cpu_list, port, threads) do NOT change: :8074 stays 0-95/96t and :8083
stays 184-191/8t. topology_fingerprint() hashes the role NAME with those tuples, so the stamp
goes stale although no physical fact moved. contention_matrix.py has no relabel subcommand, so
this tool does the one honest thing available without re-measuring:

  * swaps the two names ONLY inside the pairwise-stamped sections (`pairs`, `unknown_pairs`),
    the input the top-level `topology_hash` is computed over (contention.matrix_stamped_roles);
  * asserts every relabeled instance still carries the SAME (cpu_list, port, threads) as the
    lane's realized NUMA_CONFIG for its NEW role name — refuses otherwise (i.e. refuses if the
    placement changed, which would require re-measurement, not relabeling);
  * restamps `topology_hash` with the repo's own topology_fingerprint_for_matrix();
  * leaves every measured number, measured_at and provenance untouched, and prepends a
    comment block recording the relabel.

Sections outside the stamp (same_role, n_way, nway_heavy_roles, ...) are NOT edited: they
carry their own provenance and predate the lineup. (nway_heavy_roles naming architect_general
as the whole-machine role becomes accurate again after the swap.)

usage: relabel_contention_matrix.py <orchestrator-tree> [--write]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

A, B = "architect_general", "architect_critic"
MARK = "ARCHSWAP-20260927 DECLARED RELABEL"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    tree = Path(sys.argv[1]).resolve()
    write = "--write" in sys.argv[2:]
    path = tree / "orchestration" / "contention_matrix.yaml"
    text = path.read_text()
    if MARK in text:
        print(f"REFUSING: {path} already relabeled")
        return 2

    lines = text.split("\n")
    try:
        start = lines.index("pairs:")
    except ValueError:
        print("REFUSING: no top-level `pairs:` section")
        return 2
    try:
        unk = lines.index("unknown_pairs:")
    except ValueError:
        unk = start
    end = unk + 1
    while end < len(lines) and (lines[end].startswith(" ") or lines[end] == ""):
        end += 1

    tmp = "\x00SWAP\x00"
    region = "\n".join(lines[start:end])
    region = region.replace(A, tmp).replace(B, A).replace(tmp, B)
    new_lines = lines[:start] + region.split("\n") + lines[end:]
    new_text = "\n".join(new_lines)

    sys.path.insert(0, str(tree))
    sys.path.insert(0, str(tree / "scripts" / "server"))
    from stack_numa import NUMA_CONFIG  # noqa: E402
    import yaml  # noqa: E402
    from src.scheduling import contention  # noqa: E402

    doc = yaml.safe_load(new_text)
    for section in ("pairs", "unknown_pairs"):
        for entry in doc.get(section) or []:
            for key in ("instance_a", "instance_b"):
                inst = entry.get(key)
                if not isinstance(inst, dict) or inst.get("role") not in (A, B):
                    continue
                cfg = NUMA_CONFIG.get(inst["role"]) or {}
                tuples = {(str(i[0]), int(i[1]), int(i[2])) for i in cfg.get("instances", [])}
                got = (str(inst["cpu_list"]), int(inst["port"]), int(inst["threads"]))
                if got not in tuples:
                    print(f"REFUSING: relabeled {section} {inst['role']} instance {got} is not in the "
                          f"lane NUMA_CONFIG {sorted(tuples)} — placement changed; RE-MEASURE, do not relabel")
                    return 2

    old_hash = re.search(r'^topology_hash: "([0-9a-f]+)"', new_text, re.M).group(1)
    tmp_path = path.with_suffix(".relabel.tmp.yaml")
    tmp_path.write_text(new_text)
    try:
        matrix = contention.load_contention_matrix(tmp_path)
        new_hash = contention.topology_fingerprint_for_matrix(NUMA_CONFIG, matrix)
    finally:
        tmp_path.unlink()
    new_text = new_text.replace(f'topology_hash: "{old_hash}"', f'topology_hash: "{new_hash}"', 1)
    note = (
        f"# {MARK} (tools/relabel_contention_matrix.py, epyc-root\n"
        "# artifacts/operator/stack-change-archswap-20260927). The role labels architect_general <->\n"
        "# architect_critic were swapped inside `pairs`/`unknown_pairs` ONLY; the (cpu_list, port,\n"
        "# threads) of every relabeled instance was asserted equal to the post-swap NUMA_CONFIG, and no\n"
        "# measured value, date or provenance changed. topology_hash restamped "
        f"{old_hash} -> {new_hash}.\n"
        "# A relabel is not a re-measurement: re-run contention_matrix.py when placement next changes.\n"
    )
    anchor = "topology_hash:"
    i = new_text.index(anchor)
    new_text = new_text[:i] + note + new_text[i:]
    print(f"topology_hash {old_hash} -> {new_hash}")
    if write:
        path.write_text(new_text)
        print(f"wrote {path}")
    else:
        print("dry run (pass --write to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
