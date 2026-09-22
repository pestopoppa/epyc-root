#!/usr/bin/env python3
"""PHASE 1 of retire-model: enumerate EVERY reference to a model, then assert.

This script does not advise. It classifies every reference it finds and exits
non-zero when any of them forbids the transition you asked for.

    enumerate_refs.py <model-row-id> [--stage deprecate|delete] [--scratch DIR] [--json]

Exit codes
    0  the transition is permitted; MUST-EDIT rows are the change set
    2  a BLOCK class reference exists -- the transition is refused
    1  usage / missing source

Why it exists: on 2026-09-22 a one-file retirement patch was applied and the
remaining eight surfaces were discovered one pipeline run at a time, with the
stack down. Enumeration is cheap; discovery by error message is not.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    AUTOKERNEL,
    LAUNCH_MANIFEST,
    MODELS_PY,
    PROCEDURES,
    ROLES_PY,
    SERVING_RECIPES,
    STACK_TEMPLATES,
    artifacts_of,
    is_deprecated,
    live_roles,
    load_sources,
    scan_files,
    server_for_role,
)

BLOCK, MUST_EDIT, ADVISORY = "BLOCK", "MUST-EDIT", "ADVISORY"

# Language that marks a row as somebody's way back. Grepped, not remembered:
# `roles.qwen35_122b_q4km` carries "ROLLBACK ANCHOR: this row is RETAINED
# UNMODIFIED ... so the 122B remains restorable if the cutover fails".
ANCHOR_WORDS = ("ROLLBACK ANCHOR", "rollback anchor", "REMAIN ON DISK", "retained precisely")


class Report:
    def __init__(self) -> None:
        self.refs: list[dict] = []

    def add(self, klass: str, surface: str, locator: str, detail: str) -> None:
        self.refs.append(
            {"class": klass, "surface": surface, "locator": locator, "detail": detail}
        )

    def blocks(self) -> list[dict]:
        return [r for r in self.refs if r["class"] == BLOCK]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_id", help="the `roles.<id>` row key of the model being retired")
    ap.add_argument("--stage", choices=("deprecate", "delete"), default="deprecate")
    ap.add_argument("--scratch", help="re-root both repos at DIR (stack-change phases 2-5)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src = load_sources(args.scratch)
    roles, sm = src["roles"], src["server_mode"]
    mid = args.model_id
    rep = Report()

    row = roles.get(mid)
    if not isinstance(row, dict):
        print(f"ERROR: no `roles.{mid}` row in the master registry.", file=sys.stderr)
        print("       The row key is the identity here, not the GGUF filename.", file=sys.stderr)
        return 1

    arts = artifacts_of(row)
    paths = {a for a in arts if "/" in a}
    basenames = {os.path.basename(a) for a in arts if a.endswith(".gguf")}
    needles = paths | basenames | {mid}
    already = is_deprecated(row)

    # --- S1 current state -------------------------------------------------
    rep.add(
        ADVISORY,
        "roles.<id>",
        f"roles.{mid}",
        f"deprecated={already}"
        + (f" date={row.get('deprecated_date')}" if already else "")
        + f"; artifacts={sorted(paths) or sorted(basenames)}",
    )

    # --- S2 rollback-anchor language -------------------------------------
    blob = json.dumps(row, default=str)
    for word in ANCHOR_WORDS:
        if word in blob:
            klass = BLOCK if (args.stage == "delete" or not already) else ADVISORY
            rep.add(
                klass,
                "rollback anchor",
                f"roles.{mid}",
                f"the row declares itself a rollback path ({word!r}). A model that is "
                "somebody's way back is not retirable in the same change that depends on it.",
            )
            break

    # --- S3 live roles that resolve to it ---------------------------------
    lr = live_roles(src)
    for role in sorted(lr):
        server_role, cfg, binding = server_for_role(src, role)
        if cfg is None:
            continue
        hit = cfg.get("model_role") == mid or bool(artifacts_of(cfg) & arts)
        role_row = roles.get(role)
        if not hit and isinstance(role_row, dict) and (artifacts_of(role_row) & arts):
            hit, binding = True, "roles.<role>.model.path"
        if hit:
            rep.add(
                BLOCK,
                "live role binding",
                f"{role} -> server_mode.{server_role} ({binding})",
                "a LIVE role still resolves to this model. Re-point the role FIRST "
                "(change-role), in the same package. 2026-09-22: marking qwen35_122b_q4km "
                "deprecated while architect_critic still bound to it made compile_stack_priors "
                "refuse the whole file with 'Missing live server binding'.",
            )

    # --- S4 server_mode rows naming it -------------------------------------
    for name, cfg in sm.items():
        if not isinstance(cfg, dict):
            continue
        why = []
        if name == mid:
            why.append("row key")
        if cfg.get("model_role") == mid:
            why.append("model_role")
        if artifacts_of(cfg) & arts:
            why.append("model/model_path")
        draft = cfg.get("draft_model")
        if draft and {str(draft), os.path.basename(str(draft))} & arts:
            self_draft = bool(artifacts_of(cfg) & {str(draft), os.path.basename(str(draft))})
            if self_draft:
                rep.add(
                    ADVISORY,
                    "drafter target",
                    f"server_mode.{name}.draft_model",
                    "SELF-DRAFT: the draft head is inside the same file, so no external "
                    "drafter is orphaned by this retirement.",
                )
            else:
                rep.add(
                    BLOCK if str(name) in lr else MUST_EDIT,
                    "drafter target",
                    f"server_mode.{name}.draft_model",
                    "a LIVE server drafts against this artifact. Retiring it orphans that "
                    "server's speculative path, and a target/drafter pair is only valid as a "
                    "pair (`draft-compat`).",
                )
        if why:
            klass = BLOCK if str(name) in lr and "row key" in why else MUST_EDIT
            rep.add(klass, "server_mode", f"server_mode.{name}", "matched via " + ", ".join(why))
        shared = cfg.get("shared_with") or []
        if (why or (artifacts_of(cfg) & arts)) and shared:
            rep.add(
                MUST_EDIT,
                "shared_with riders",
                f"server_mode.{name}.shared_with",
                f"{list(shared)} ride this process and must be re-pointed or retired with it",
            )

    # --- S5 other roles rows naming the same artifact ----------------------
    for name, r in roles.items():
        if name == mid or not isinstance(r, dict):
            continue
        if artifacts_of(r) & arts:
            rep.add(
                MUST_EDIT,
                "roles.* artifact reuse",
                f"roles.{name}.model",
                "names the SAME GGUF. Retiring the row does not retire the file; this "
                "row keeps it load-bearing.",
            )
        if mid in (r.get("compatible_targets") or []):
            rep.add(MUST_EDIT, "drafter compatibility", f"roles.{name}.compatible_targets", mid)

    # --- S6 candidate_roles claims -----------------------------------------
    claims = [c for c in (row.get("candidate_roles") or []) if c in lr]
    if claims:
        rep.add(
            ADVISORY,
            "candidate_roles",
            f"roles.{mid}.candidate_roles",
            f"still claims live role(s) {claims}. Not itself a binding, but it is what keeps "
            "a retired row looking employable; clear it in the same change.",
        )

    # --- S7..S11 file surfaces ---------------------------------------------
    affected = {mid} | {
        str(n) for n, c in sm.items() if isinstance(c, dict) and (n == mid or c.get("model_role") == mid)
    }
    # TWO patterns, deliberately. Role names are generic English words -- scanning
    # AutoKernel for `\bworker\b` returned 900+ "references" on this script's own
    # first run, none of them a pin. So: ARTIFACT identity (paths, GGUF basenames,
    # the row id) scans the wide surfaces; ROLE names scan only the two small,
    # role-keyed surfaces where the name IS the datum.
    artifact_re = re.compile(
        "|".join(
            sorted(
                {re.escape(p) for p in paths}
                | {rf"\b{re.escape(n)}\b" for n in (basenames | {mid})},
                key=len,
                reverse=True,
            )
        )
    )
    role_re = re.compile("|".join(sorted({rf"\b{re.escape(r)}\b" for r in affected}, key=len, reverse=True)))

    manifest = src["manifest"]
    for key in ("port_map", "role_launch_meta"):
        for rname in (manifest.get(key) or {}):
            if rname in affected:
                rep.add(MUST_EDIT, "launch_manifest", f"{LAUNCH_MANIFEST}:{key}.{rname}",
                        "launcher surface for a retiring role")
    for rname in (src["topology"].get("numa_config") or {}):
        if rname in affected:
            rep.add(MUST_EDIT, "stack_topology", f"numa_config.{rname}",
                    "a role with no process must carry no NUMA wiring")

    file_surfaces = [
        ("procedure enums", [PROCEDURES], {".yaml", ".json"}, role_re),
        ("stack template", [STACK_TEMPLATES], {".yaml"}, role_re),
        ("canonical recipe", [SERVING_RECIPES], {".json", ".yaml"}, artifact_re),
        ("autokernel pin", [AUTOKERNEL], {".py", ".json", ".yaml"}, artifact_re),
        ("code delegation", [MODELS_PY, ROLES_PY], {".py"}, role_re),
    ]
    for surface, roots, exts, pattern in file_surfaces:
        for path, lineno, line, needle in scan_files(roots, pattern, exts):
            rep.add(MUST_EDIT, surface, f"{path}:{lineno}", f"[{needle}] {line}")

    # --- S12 disk state / deletion stage -----------------------------------
    # Registry rows carry both absolute and models/-relative paths; resolve both or
    # the disk check answers "absent" for a file that is present.
    MODELS_ROOT = "/mnt/raid0/llm/models"
    resolved = {p if p.startswith("/") else os.path.join(MODELS_ROOT, p) for p in paths}
    on_disk = [p for p in sorted(resolved) if os.path.exists(p)]
    rep.add(ADVISORY, "disk", ", ".join(on_disk) or "(none resolved)",
            "present" if on_disk else "not present on this host")

    if args.stage == "delete":
        if not already:
            rep.add(BLOCK, "stage order", f"roles.{mid}",
                    "the row is not deprecated yet. live -> deprecated -> deleted; "
                    "there is no shortcut.")
        if on_disk:
            rep.add(BLOCK, "stage order", ", ".join(on_disk),
                    "the GGUF is STILL ON DISK. This skill never deletes weights -- that is a "
                    "separate operator action. Writing a `deleted:`/`path_was:` graveyard row "
                    "for a file that still exists makes the ledger lie.")

    rep.add(ADVISORY, "evidence durability",
            "epyc-inference-research/scripts/validate/check_evidence_durability.py",
            "run it after the edit: a retired row's citations must still RESOLVE, or the "
            "hashes behind ratified claims degrade into assertions (2026-08-02: 157 cited "
            "paths lived in /mnt/raid0/llm/tmp).")

    # --- output -------------------------------------------------------------
    if args.json:
        print(json.dumps({"model": mid, "stage": args.stage, "refs": rep.refs}, indent=2))
    else:
        order = {BLOCK: 0, MUST_EDIT: 1, ADVISORY: 2}
        for r in sorted(rep.refs, key=lambda r: (order[r["class"]], r["surface"])):
            print(f"{r['class']:<9} {r['surface']:<24} {r['locator']}")
            print(f"{'':<9} {'':<24} {r['detail']}")
        counts = {k: sum(1 for r in rep.refs if r["class"] == k) for k in (BLOCK, MUST_EDIT, ADVISORY)}
        print(f"\n-- {mid} stage={args.stage}: "
              f"{counts[BLOCK]} BLOCK, {counts[MUST_EDIT]} MUST-EDIT, {counts[ADVISORY]} ADVISORY --")

    if rep.blocks():
        print(f"REFUSED: {len(rep.blocks())} blocking reference(s); "
              f"{args.stage} of {mid} is not permitted.", file=sys.stderr)
        return 2
    print(f"PERMITTED: {args.stage} of {mid}. The MUST-EDIT rows above ARE the change set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
