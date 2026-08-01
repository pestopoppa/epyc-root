#!/usr/bin/env python3
"""W1 role reshaping PREFLIGHT — verify it is safe to apply, and back up / roll back.

This is a GATE, not an applier. It deliberately does not edit the registry.

WHY THIS IS A SCRIPT AND NOT 76 HAND-EDITS
------------------------------------------
The recovered edit list (wf_7d5f6816-a67) carries 76 line-anchored edits against
master at 96aa90f6. Master has moved, so every anchor needs re-deriving — and most
of those 76 are prose, annotations and historical records, not behaviour.

Since 2026-07-31 the compiler DERIVES what used to be restated by hand:
  * binary_path      <- role's declared device, via the stable kernel layer
  * numa lineup      <- declared stack_topology.yaml, not a live probe
  * launch flags     <- compiled from master + role assignments + topology

So the FUNCTIONAL surface of W1 is a handful of declared fields, and the bulk of
the 76 anchors are prose the compiler no longer reads.

The anchors were re-derived on 2026-08-01 by exact-text resolution rather than by
line arithmetic (`/mnt/raid0/llm/tmp/w1-26b5f442/w1_resolve.py`): master had moved
96aa90f6 -> 596a1e24 by exactly one hunk, and every edit was required to match its
CURRENT text uniquely or be reported. This script remains the GATE over that work.

WHAT W1 CHANGES (the operator-ratified target)
  architect_general   122B CPU     -> Qwen3.6-27B MTP Q8, ROCm0, port 8083
  coder_escalation    frontdoor's 35B on 8070 -> alias of architect_general on 8083
  frontdoor           sheds coder_escalation, keeps worker_summarize
  worker_vision       Qwen2.5-VL-7B CPU -> Qwen3-VL-30B-A3B Q4_K_M, ROCm0, 8086
  vision_escalation   own 7B server on 8087 -> alias of worker_vision on 8086
  architect_critic    NEW role: the 122B, CPU, port 8074, tier hot

D1-D4 were ruled by the operator on 2026-08-01 and recorded in the ratification
artifact so each ruling is auditable rather than implicit:
  D1 architect_critic tier          -> HOT
  D2 reasoning-chain triggers       -> NARROW (explicit_request only)
  D3 frontdoor keeps `coder`?       -> NO, removed
  D4 duplicate B3-code hint         -> delete the unreachable one, keep one above

USAGE
    python scripts/operator/w1_preflight.py --preflight   # check only
    python scripts/operator/w1_preflight.py --backup      # snapshot before applying
    python scripts/operator/w1_preflight.py --rollback    # restore that snapshot

This tool never edits the registry.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
MASTER = RESEARCH / "orchestration" / "model_registry.yaml"
BACKUP_ROOT = Path("/mnt/raid0/llm/tmp/w1-backups")

ARCHITECT_MODEL = "/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf"
VISION_MODEL = (
    "/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/"
    "Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf"
)
VISION_MMPROJ = (
    "/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/"
    "mmproj-Qwen3-VL-30B-A3B-Instruct-F16.gguf"
)
CRITIC_MODEL = (
    "/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/"
    "Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf"
)

TOUCHED = [
    MASTER,
    ORCH / "scripts/server/stack_manifest.py",
    ORCH / "scripts/server/stack_numa.py",
    ORCH / "src/roles.py",
    ORCH / "src/config/models.py",
    ORCH / "src/api/routes/health.py",
    ORCH / "scripts/server/stack_env.py",
]


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def preflight() -> tuple[list[str], list[str]]:
    """Return (blocking problems, advisory notes). No problems means safe to apply."""
    problems: list[str] = []
    notes: list[str] = []

    for path, label in (
        (ARCHITECT_MODEL, "architect 27B weights"),
        (VISION_MODEL, "vision 30B weights"),
        (VISION_MMPROJ, "vision mmproj"),
        (CRITIC_MODEL, "critic 122B weights"),
    ):
        if not Path(path).exists():
            problems.append(f"MISSING {label}: {path}")

    # GPU headroom: 27B Q8 (~29 GiB) + VL-30B Q4 (~18 GiB) must fit in HBM.
    rc, out = _run(["rocm-smi", "--showmeminfo", "vram"])
    if rc == 0:
        try:
            total = used = None
            for line in out.splitlines():
                if "Total Memory" in line:
                    total = int(line.split(":")[-1].strip())
                elif "Total Used Memory" in line:
                    used = int(line.split(":")[-1].strip())
            if total and used is not None:
                free_gib = (total - used) / 2**30
                if free_gib < 50:
                    problems.append(
                        f"GPU free {free_gib:.1f} GiB < 50 GiB needed for 27B Q8 + VL-30B Q4"
                    )
        except Exception as exc:  # noqa: BLE001
            problems.append(f"could not parse rocm-smi output: {exc}")
    else:
        problems.append("rocm-smi unavailable — cannot verify GPU headroom")

    # Working-tree check, scoped to the files W1 actually touches.
    #
    # This deliberately does NOT demand a globally clean repo. These are SHARED
    # clones (/workspace/repos/<name> -> /mnt/raid0/llm/<name>); parallel sessions
    # routinely leave unrelated work in the tree, and the documented idiom here is
    # a pathspec-limited commit (`git commit -- <paths>`), not a clean tree. A gate
    # that blocks on unrelated dirt forbids the compliant path and trains people to
    # bypass it -- so it blocks only on collisions with W1's OWN targets, and
    # reports the rest.
    touched_by_repo = {ORCH: [], RESEARCH: []}
    for path in TOUCHED:
        repo = RESEARCH if str(path).startswith(str(RESEARCH)) else ORCH
        touched_by_repo[repo].append(str(path.relative_to(repo)))

    for repo, owned in touched_by_repo.items():
        rc, out = _run(["git", "status", "--porcelain"], cwd=repo)
        dirty = [
            line[3:].strip()
            for line in out.splitlines()
            if line.strip() and not line.startswith("??")
        ]
        collisions = sorted(set(dirty) & set(owned))
        unrelated = sorted(set(dirty) - set(owned))
        if collisions:
            problems.append(
                f"{repo.name}: W1 target file(s) already modified by someone else — "
                f"applying would mix edits: {', '.join(collisions)}"
            )
        if unrelated:
            notes.append(
                f"{repo.name}: {len(unrelated)} unrelated tracked change(s) in the shared "
                f"clone, untouched by W1. Commit W1 with an explicit pathspec so they do "
                f"not ride along: git commit -- {' '.join(owned[:2])} ..."
            )

    if not (ORCH / "orchestration" / "stack_topology.yaml").exists():
        problems.append("stack_topology.yaml missing — compile would fall back to probing")

    try:
        sys.path.insert(0, str(ORCH))
        from src.registry.kernel_paths import server_binary

        server_binary("gpu")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"gpu kernel backend does not resolve: {exc}")

    return problems, notes


def _backup() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = BACKUP_ROOT / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for path in TOUCHED:
        if path.exists():
            target = dest / path.name
            shutil.copy2(path, target)
    (dest / "MANIFEST.json").write_text(
        json.dumps({"files": [str(p) for p in TOUCHED], "created": stamp}, indent=2)
    )
    return dest


def _latest_backup() -> Path | None:
    if not BACKUP_ROOT.exists():
        return None
    candidates = sorted(p for p in BACKUP_ROOT.iterdir() if p.is_dir())
    return candidates[-1] if candidates else None


def rollback() -> int:
    backup = _latest_backup()
    if backup is None:
        print("no backup found; nothing to roll back")
        return 1
    for path in TOUCHED:
        src = backup / path.name
        if src.exists():
            shutil.copy2(src, path)
            print(f"  restored {path}")
    print(f"rolled back from {backup}")
    print("re-run the compile to regenerate derived artifacts:")
    print("  python scripts/registry/stack_change_pipeline.py update")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--backup", action="store_true")
    g.add_argument("--rollback", action="store_true")
    args = ap.parse_args()

    if args.rollback:
        return rollback()

    if args.backup:
        backup = _backup()
        print(f"backed up {len(TOUCHED)} file(s) to {backup}")
        print("roll back with: python scripts/operator/w1_preflight.py --rollback")
        return 0

    problems, notes = preflight()
    print("=== W1 PREFLIGHT ===")
    for n in notes:
        print(f"  NOTE   {n}")
    if problems:
        for p in problems:
            print(f"  BLOCK  {p}")
        print(f"\n{len(problems)} blocker(s). Not safe to apply.")
        return 2
    print("  all preconditions satisfied")
    print(f"    architect  -> {ARCHITECT_MODEL}")
    print(f"    vision     -> {VISION_MODEL}")
    print(f"    critic     -> {CRITIC_MODEL}")

    print("\npreflight only; nothing changed. This tool never edits the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
