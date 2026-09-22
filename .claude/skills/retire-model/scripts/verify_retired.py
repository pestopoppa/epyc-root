#!/usr/bin/env python3
"""PHASE 9 of retire-model: verify the retirement is what it claims to be.

    verify_retired.py <model-row-id> --stage deprecate [--graveyard-was N] [--scratch DIR]
    verify_retired.py <model-row-id> --stage delete    --graveyard-was N

Exit 0 pass, 2 fail, 1 usage. Every check is a RECOMPUTE from the master
registry, never a comparison of one copy against another.

deprecate asserts the three-key marker is complete and honest, the weights are
still on disk (a deprecation is a MARK, not a reclamation), the graveyard did
NOT grow, and nothing live resolves to the row any more.

delete asserts the graveyard grew by exactly one, that row carries `deleted:`
and `path_was:`, and the file really is gone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import artifacts_of, live_roles, load_sources, server_for_role  # noqa: E402

MODELS_ROOT = "/mnt/raid0/llm/models"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_id")
    ap.add_argument("--stage", choices=("deprecate", "delete"), required=True)
    ap.add_argument("--graveyard-was", type=int,
                    help="deprecated_models length recorded BEFORE the edit (required for --stage delete)")
    ap.add_argument("--scratch")
    args = ap.parse_args()

    src = load_sources(args.scratch)
    roles = src["roles"]
    mid = args.model_id
    row = roles.get(mid)
    fails: list[str] = []
    notes: list[str] = []

    if not isinstance(row, dict):
        print(f"ERROR: no `roles.{mid}` row; nothing to verify.", file=sys.stderr)
        return 1

    arts = artifacts_of(row)
    paths = {p if p.startswith("/") else os.path.join(MODELS_ROOT, p) for p in arts if "/" in p}
    on_disk = sorted(p for p in paths if os.path.exists(p))

    # --- the three-key marker, complete and parseable ----------------------
    for key in ("deprecated", "deprecated_date", "deprecated_reason"):
        if key not in row:
            fails.append(f"roles.{mid}.{key} is MISSING. The marker is three keys; a partial "
                         "marker reads as deprecated to a human and as live to the compiler.")
    if row.get("deprecated") is not True:
        fails.append(f"roles.{mid}.deprecated is {row.get('deprecated')!r}, not True")
    date = row.get("deprecated_date")
    if date is not None and not isinstance(date, (dt.date, dt.datetime)):
        fails.append(f"roles.{mid}.deprecated_date is {date!r}, not a YAML date")
    reason = str(row.get("deprecated_reason") or "")
    if len(reason.strip()) < 20:
        fails.append(f"roles.{mid}.deprecated_reason is empty or a stub. The reason is the only "
                     "place the retirement's measured record survives the row.")

    # --- nothing live still resolves to it ---------------------------------
    for role in sorted(live_roles(src)):
        server_role, cfg, binding = server_for_role(src, role)
        if cfg is None:
            continue
        if cfg.get("model_role") == mid or (artifacts_of(cfg) & arts):
            fails.append(f"live role {role!r} still resolves to {mid} via {binding} "
                         f"(server_mode.{server_role})")

    # --- graveyard: MARK, not delete ---------------------------------------
    grave = src["deprecated_models"]
    grave_names = [str(g.get("model")) for g in grave if isinstance(g, dict)]

    if args.stage == "deprecate":
        if args.graveyard_was is not None and len(grave) != args.graveyard_was:
            fails.append(f"deprecated_models went {args.graveyard_was} -> {len(grave)}. A "
                         "deprecation MARKS a row; it does not move it to the graveyard. "
                         "live -> deprecated -> deleted, and the middle state keeps the weights.")
        if paths and not on_disk:
            fails.append(f"none of {sorted(paths)} is on disk, but this stage asserts the GGUF "
                         "STAYS. Either the weights were deleted (that is --stage delete, and a "
                         "separate operator action) or the path in the row is wrong.")
        else:
            notes.append(f"weights retained on disk: {on_disk}")
    else:
        if args.graveyard_was is None:
            print("ERROR: --graveyard-was is required for --stage delete", file=sys.stderr)
            return 1
        if len(grave) != args.graveyard_was + 1:
            fails.append(f"deprecated_models went {args.graveyard_was} -> {len(grave)}; "
                         "exactly one graveyard row is expected.")
        match = [g for g in grave if isinstance(g, dict)
                 and (mid in str(g.get("model")) or any(a in str(g.get("path_was") or "") for a in arts))]
        if not match:
            fails.append(f"no deprecated_models row names {mid} or its artifact "
                         "(schema: model / path_was / size_gb / reason / deleted)")
        for g in match:
            for key in ("deleted", "path_was"):
                if not g.get(key):
                    fails.append(f"graveyard row {g.get('model')!r} is missing `{key}:`")
        if on_disk:
            fails.append(f"the weights are STILL PRESENT at {on_disk}. A `deleted:` row for a file "
                         "that exists is a false ledger entry -- and this skill never deletes "
                         "weights, so the operator has not done their half yet.")

    notes.append(f"graveyard rows: {len(grave)} (last: {grave_names[-1] if grave_names else '-'})")

    for n in notes:
        print(f"note  {n}")
    for f in fails:
        print(f"FAIL  {f}")
    if fails:
        print(f"\nVERIFY FAILED: {len(fails)} problem(s) for {mid} at stage={args.stage}.", file=sys.stderr)
        return 2
    print(f"\nVERIFY PASS: {mid} stage={args.stage}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
