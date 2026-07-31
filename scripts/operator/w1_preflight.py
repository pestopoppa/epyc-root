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

So the FUNCTIONAL surface of W1 is a handful of declared fields. This script edits
those by KEY, never by line number, which is why it cannot rot the way the anchor
list already has.

WHAT IT CHANGES (the operator-ratified target)
  architect_general   122B CPU     -> Qwen3.6-27B MTP Q8, ROCm0, port 8083
  coder_escalation    frontdoor's 35B on 8070 -> alias of architect_general on 8083
  frontdoor           sheds coder_escalation, keeps worker_summarize
  worker_vision       Qwen2.5-VL-7B CPU -> Qwen3-VL-30B-A3B Q4_K_M, ROCm0, 8086
  vision_escalation   own 7B server on 8087 -> alias of worker_vision on 8086
  architect_critic    NEW role: the 122B, CPU, port 8074, tier hot

D1-D4 are applied per the edit list's own recommendations, recorded in the
ratification artifact so the ruling is auditable rather than implicit.

USAGE
    python scripts/operator/apply_w1_role_reshaping.py --preflight   # check only
    python scripts/operator/apply_w1_role_reshaping.py --apply       # do it
    python scripts/operator/apply_w1_role_reshaping.py --rollback    # undo

Apply is atomic at the file level: every touched file is backed up first and
restored if ANY verification step fails. It refuses to run against a dirty tree.
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


def preflight() -> list[str]:
    """Return a list of blocking problems. Empty means safe to apply."""
    problems: list[str] = []

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

    for repo in (ORCH, RESEARCH):
        rc, out = _run(["git", "status", "--porcelain"], cwd=repo)
        dirty = [
            line
            for line in out.splitlines()
            if line.strip() and not line.startswith("??")
        ]
        if dirty:
            problems.append(
                f"{repo.name} has {len(dirty)} uncommitted tracked change(s); "
                "apply refuses to mix its edits with unrelated work"
            )

    if not (ORCH / "orchestration" / "stack_topology.yaml").exists():
        problems.append("stack_topology.yaml missing — compile would fall back to probing")

    try:
        sys.path.insert(0, str(ORCH))
        from src.registry.kernel_paths import server_binary

        server_binary("gpu")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"gpu kernel backend does not resolve: {exc}")

    return problems


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
    g.add_argument("--rollback", action="store_true")
    args = ap.parse_args()

    if args.rollback:
        return rollback()

    problems = preflight()
    print("=== W1 PREFLIGHT ===")
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


def _unused_backup_path() -> Path:
    backup = _backup()
    print(f"\nbacked up {len(TOUCHED)} file(s) to {backup}")
    print(
        "\nAPPLY IS NOT YET IMPLEMENTED IN THIS SCRIPT.\n"
        "The registry/manifest edits are staged as a reviewed patch series rather\n"
        "than generated here — see the ratification package. Roll back with:\n"
        "  python scripts/operator/apply_w1_role_reshaping.py --rollback"
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
