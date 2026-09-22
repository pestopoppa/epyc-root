#!/bin/bash
# STEP 1: DERIVE the promotion scope. Never quote a prose count.
#
# The scope is "which models must show no regression before this kernel may serve", and
# it is a function of the compiled priors: the models whose roles resolve to backend B.
# This wraps kernel_freeze_scope.py and asserts the three things that made the derived
# answer WRONG rather than absent on 2026-09-21/22:
#
#   * an EMPTY backend scope. The tool used to classify backend by `"build-hip" in path`.
#     The moment production/gpu pointed at a versioned store dir the marker vanished,
#     `--backend gpu` reported "0 role(s)" and cpu went 8 -> 12. An empty gate is not a
#     pass; a promotion derived from it would have skipped the entire GPU half, which is
#     the only path that catches a -30% MoE regression.
#   * a scope whose binary_path does NOT resolve to the CURRENT store target. The priors
#     pin the RESOLVED build dir, so between a repoint and the step-9 regeneration they
#     name the OUTGOING kernel. Derive BEFORE the repoint or AFTER the regen -- never in
#     between, and never trust a scope taken there.
#   * a model file that no longer exists. A role pointing at a deleted GGUF derives a
#     gate nothing can run.
#
# usage: scope.sh [--backend cpu|gpu|stt|tts] [--json <out>]
set -euo pipefail
ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
BACKEND=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --backend) BACKEND="$2"; shift 2 ;;
    --json) OUT="$2"; shift 2 ;;
    *) echo "usage: scope.sh [--backend cpu|gpu|stt|tts] [--json <out>]"; exit 2 ;;
  esac
done
cd "$ORCH"
ARGS=(--json)
[ -n "$BACKEND" ] && ARGS+=(--backend "$BACKEND")
TMP=$(mktemp -t kernel-scope.XXXXXX.json)
trap 'rm -f "$TMP"' EXIT
uv run python scripts/validate/kernel_freeze_scope.py "${ARGS[@]}" > "$TMP"
[ -n "$OUT" ] && cp "$TMP" "$OUT"

SCOPE_JSON="$TMP" WANT="$BACKEND" uv run python - <<'PY'
import json, os, sys
from pathlib import Path

scope = json.loads(Path(os.environ["SCOPE_JSON"]).read_text())
want = os.environ.get("WANT") or ""
store = Path("/mnt/raid0/llm/kernels/production")
problems = []

for backend, rows in sorted(scope.items()):
    link = store / backend
    target = link.resolve() if link.is_symlink() else None
    print(f"== {backend}: {len(rows)} role(s) must show no regression")
    if not rows:
        problems.append(
            f"{backend}: EMPTY scope. Zero roles resolve to this backend. Either no role "
            "uses it, or the backend classifier failed to resolve a store path -- and an "
            "empty gate silently skips that half of the promotion. Prove which."
        )
    models = {}
    for row in rows:
        models.setdefault(row["model_path"], []).append(row["role"])
        bindir = Path(row["binary_path"]).parent
        if target is not None and bindir != target:
            problems.append(
                f"{backend}/{row['role']}: priors pin {bindir} but "
                f"kernels/production/{backend} resolves to {target}. The scope is STALE "
                "relative to the store: regenerate the derived layer "
                "(stack_change_pipeline.py update --numa-mode <declared>) and derive again."
            )
        if not Path(row["model_path"]).exists():
            problems.append(f"{backend}/{row['role']}: model does not exist: {row['model_path']}")
    for path, roles in sorted(models.items()):
        spec = {r["spec_type"] for r in rows if r["model_path"] == path} - {None}
        print(f"   {Path(path).name:<62} {','.join(sorted(roles))}"
              + (f"  [{'/'.join(sorted(spec))}]" if spec else ""))

if want and want not in scope:
    problems.append(f"requested backend {want!r} is absent from the derived scope")

if problems:
    print(f"\nSCOPE FAIL: {len(problems)} problem(s)")
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("\nSCOPE DERIVED")
PY
