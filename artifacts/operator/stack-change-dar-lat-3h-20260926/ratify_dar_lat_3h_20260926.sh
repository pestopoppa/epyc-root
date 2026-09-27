#!/bin/bash
# Operator signature for the DAR-LAT-3h stack-change package (v2): reconcile the :8074
# architect_critic's thread count and GGML env with its codified recipe. See
# PACKAGE.md in this directory.
#
# What it does: verifies PACKAGE.md, the patches and the G1 prompt set against the
# sha256 values pinned below, verifies every lane commit exists on its origin lane,
# and writes ONE receipt recording the signature, the pre-registered G1 rule and the
# outcome -> merge-prefix table.
#
# What it does NOT do: run G1, apply a patch, merge a branch, compile, start, stop or
# reload anything. Phases 7-8 (PACKAGE.md section 6) are run afterwards by the session
# that owns the inference, and they begin by checking this receipt.
#
# No path under the measurement trust boundary is touched by this package, so there
# is no consolidated section-5 bundle to emit; the receipt below is the signature.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926"
# Resolved from this script's own location, so it runs from the epyc-root main clone
# or from the lane worktree alike; the receipt lands in that same tree.
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
PYTHON="/usr/bin/python3"

# repo|lane|commits (every commit must be an ancestor of origin/<lane>). v2 (2026-09-27):
# the v1 lanes are superseded, and the env fix 7c426412 lands separately (it is the base
# of the orchestrator v2 lanes).
LANES=(
  "$ORCH|lane/strip-preserve-v2-20260927|7c426412"
  "$ORCH|lane/dar-lat-3h-v2-20260927|7c426412 f98d210b 565a7c15 ee21ed4e 4a4bbd8f 2e5e5544"
  "$ORCH|lane/dar-lat-3h-v2-t48-20260927|ee21ed4e 379dca64"
  "$RESEARCH|lane/dar-lat-3h-v2-20260927|cbaeee2d"
  "$RESEARCH|lane/dar-lat-3h-v2-t48n-20260927|cbaeee2d af4f5675"
  "$RESEARCH|lane/dar-lat-3h-v2-t96-20260927|cbaeee2d a969d2f9"
  "$RESEARCH|lane/dar-lat-3h-v2-t96n-20260927|cbaeee2d 48f7ebf6"
)

# Pinned content. A package edited after preparation must be re-pinned by its
# preparer, not signed as-is.
PINS=(
  "9ece6bd409a09f20bc4c048e678df0bc3a3e40d2590a948a346dd5842f597eba PACKAGE.md"
  "ea154096eb110850ab5be5e4f574e995e5dbf17540dcbb9461b8cc38c0855783 gate/prompts-24mix.json"
  "5b302df2c8eac8b2e2656c54f927f1976456acb6561c63fc816ba3a4b15ed5e2 patches/orchestrator-t48/0004-topology-architect_critic-NUMA_FULL_T48-t-48-complet.patch"
  "204bb488fe692a0dd7a8b51e32bad01bedd0d95155d04c703c80dd8e94385d4f patches/orchestrator/0001-stack_numa-NUMA_FULL_T48-shape-split-thread-invarian.patch"
  "ad995bb9124c4fe496914d83cbc687cf36d74c10191c232ac35b48730e3aa9d0 patches/orchestrator/0002-server-critic_thread_gate.py-the-DAR-LAT-3h-gate-G1-.patch"
  "dc0954861ea603dd9b130e63fa390ceef9891e599f2206e34ac560adb3c42235 patches/orchestrator/0003-stack_env-architect_critic-serving-env-GGML_FUSED_DE.patch"
  "452e532a5bb42476c393e0c844585dd30b1cfed0a9d20f7c6a37f5721964dd60 patches/orchestrator/0004-stack_env-architect_critic-GGML_NOHUGEPAGE_PROCESS-1.patch"
  "a90ce52727c171ffbeb84a89b252a2273694d438f633a185479342e849a21faa patches/orchestrator/0005-topology-architect_critic-NUMA_FULL_T48-t-48-complet.patch"
  "3cc1b64a1d6914bbbba45607d545e3c09973c38ad797d1672f55afc07b85acd5 patches/research-t48n/0002-registry-architect_critic-serving-shape-for-DAR-LAT-.patch"
  "3932ac4ebe21abbbb22c2f9c580a92c880df870a93c2a845133184d7ff1069ae patches/research-t96/0002-registry-architect_critic-serving-shape-for-DAR-LAT-.patch"
  "c6997496b363da349fd1ca3d8b8ed47680fc73ba398fc1b9956adde3e8a72802 patches/research-t96n/0002-registry-architect_critic-serving-shape-for-DAR-LAT-.patch"
  "508f92dc73d9745663b79af2a445181757602af6ac650ac7be641b6ff25e3075 patches/research/0001-registry-recipe-correct-the-Flash-Next-t-48-served-o.patch"
)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() { printf 'usage: %s --validate-only\n       %s --attest %s\n' "$0" "$0" "$TOKEN" >&2; }

MODE=""
case "${1:-}" in
  --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
  --attest) [[ $# == 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest" ;;
  *) usage; exit 2 ;;
esac

[[ -x "$PYTHON" ]] || fail "trusted interpreter unavailable"
[[ "$MODE" != "attest" || ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"

cd "$PKG"
for pin in "${PINS[@]}"; do
  want="${pin%% *}"; file="${pin#* }"
  [[ -f "$file" ]] || fail "missing package file: $file"
  got="$(sha256sum -- "$file" | cut -d' ' -f1)"
  [[ "$got" == "$want" ]] || fail "$file sha256 $got != pinned $want (package changed after preparation)"
  printf 'ok  %s\n' "$file"
done

for entry in "${LANES[@]}"; do
  IFS='|' read -r repo lane commits <<<"$entry"
  git -C "$repo" fetch -q origin "$lane" || fail "cannot fetch origin/$lane in $repo"
  for c in $commits; do
    git -C "$repo" merge-base --is-ancestor "$c" FETCH_HEAD \
      || fail "$c is not on origin/$lane in $repo"
    printf 'ok  %s %s on origin/%s\n' "$(basename "$repo")" "$c" "$lane"
  done
done

# The env fix is a precondition of APPLY (PACKAGE.md section 6 P0), not of signing. Say where it stands.
if git -C "$ORCH" fetch -q origin main && git -C "$ORCH" merge-base --is-ancestor 7c426412 FETCH_HEAD; then
  printf 'ok  env fix 7c426412 is on origin/main\n'
else
  printf 'NOTE: env fix 7c426412 is NOT yet on origin/main (its push was refused; see PACKAGE.md). Apply waits for it.\n'
fi

if [[ "$MODE" == "validate" ]]; then
  printf 'VALID: package, patches, prompt set and lane commits verified. Nothing written.\n'
  exit 0
fi

mkdir -p -- "$(dirname -- "$RECEIPT")"
"$PYTHON" - "$RECEIPT" "$TOKEN" "${PINS[@]}" <<'PY'
import json, os, sys
from datetime import UTC, datetime
receipt, token, *pins = sys.argv[1:]
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": token,
    "status": "ratified",
    "human_attestation": token,
    "signed_at": datetime.now(UTC).isoformat(),
    "signed_by_uid": os.getuid(),
    "package": "artifacts/operator/stack-change-dar-lat-3h-20260926/PACKAGE.md",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "package_version": "v2 (operator split after the GGML_* env audit, 2026-09-26)",
    "signed_gates": {
        "G1_threads_x_thp_shim": {
            "driver": "epyc-orchestrator scripts/server/critic_thread_gate.py @ 565a7c15",
            "arms": {"L": "-t 96, live env", "T96": "-t 96 + FUSED_DECODE_OFF",
                     "T96N": "-t 96 + FUSED_DECODE_OFF + NOHUGEPAGE_PROCESS",
                     "T48": "-t 48 + FUSED_DECODE_OFF", "T48N": "-t 48 + FUSED_DECODE_OFF + NOHUGEPAGE_PROCESS"},
            "unit": "launch", "launches_per_arm": 3, "min_clean_launches_per_arm": 3,
            "mechanism_check": "THP_enabled from /proc/<pid>/status: 0 on N arms, 1 otherwise, else the launch is re-queued",
            "primary": "mean per-launch median W1 request wall time (the critic's region-lock hold time)",
            "non_inferior": "wall <= 1.03x, TTFT <= 1.10x, coherent >= ref-1",
            "rule": "premise T96~L else INVALID-PREMISE; threads 48 iff T48~T96 AND T48N~T96N else 96; "
                    "shim iff TtN wall <= 0.98x Tt and TtN~Tt on TTFT/coherence; <3 clean launches -> INCONCLUSIVE",
        },
        "G2_serving_proof": "PACKAGE.md section 6 P4-P5: /proc argv, environ (no GGML_FA_SPLIT_KV), THP_enabled, per-task affinity, numa_maps, runtime_attestation + declared_env_attestation ok, coherent ~4k-token completion with MTP accepting",
        "G3_contention_recert": "T48/T48N only: contention_matrix.py run in the same window; check_contention_matrix_fresh.py OK",
    },
    "outcome_merge_pair": {
        "T48": {"epyc-orchestrator": "lane/dar-lat-3h-v2-t48-20260927 @ 379dca64",
                "epyc-inference-research": "lane/dar-lat-3h-v2-20260927 @ cbaeee2d", "reload": "architect_critic"},
        "T48N": {"epyc-orchestrator": "lane/dar-lat-3h-v2-20260927 @ 2e5e5544",
                 "epyc-inference-research": "lane/dar-lat-3h-v2-t48n-20260927 @ af4f5675", "reload": "architect_critic"},
        "T96": {"epyc-orchestrator": "lane/dar-lat-3h-v2-20260927 through ee21ed4e",
                "epyc-inference-research": "lane/dar-lat-3h-v2-t96-20260927 @ a969d2f9", "reload": "architect_critic"},
        "T96N": {"epyc-orchestrator": "lane/dar-lat-3h-v2-20260927 through 4a4bbd8f",
                 "epyc-inference-research": "lane/dar-lat-3h-v2-t96n-20260927 @ 48f7ebf6", "reload": "architect_critic"},
        "INVALID-PREMISE": "apply nothing; GGML_FUSED_DECODE_OFF was not inert",
        "INCONCLUSIVE": "apply nothing; re-run G1 in another window",
    },
    "apply_precondition": "epyc-orchestrator main contains 7c426412 (env fix + recurrence guard)",
    "superseded_lanes": ["lane/dar-lat-3h-20260926", "lane/dar-lat-3h-t96-20260926", "lane/dar-lat-3h-live-20260926"],
    "scope_excluded": ["GGML_FA_SPLIT_KV (task DAR-LAT-3i)", "n_ctx (lineup-change C4 stands)", "CPU speech co-tenancy (operator ruling 2026-09-24: no change)"],
    "applies_nothing": True,
}
tmp = receipt + ".tmp"
with open(tmp, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, receipt)
print(f"RATIFIED: {receipt}")
PY
