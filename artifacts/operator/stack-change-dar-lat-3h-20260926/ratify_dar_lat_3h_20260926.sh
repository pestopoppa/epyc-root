#!/bin/bash
# Operator signature for the DAR-LAT-3h stack-change package: reconcile the :8074
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

# repo|lane|commits (every commit must be an ancestor of origin/<lane>)
LANES=(
  "$ORCH|lane/dar-lat-3h-20260926|c43d10fb aa2c2c2a 27008a15 071d8ff9 20c7d902"
  "$RESEARCH|lane/dar-lat-3h-20260926|cf2476b0"
  "$RESEARCH|lane/dar-lat-3h-t96-20260926|cf2476b0 2a4613f7"
  "$RESEARCH|lane/dar-lat-3h-live-20260926|cf2476b0 cc8dd98e"
)

# Pinned content. A package edited after preparation must be re-pinned by its
# preparer, not signed as-is.
PINS=(
  "e665f8fe870aa4894b5827f860eb0fd7a52ad445076cdfbea5480fa3c2ec7382 PACKAGE.md"
  "ea154096eb110850ab5be5e4f574e995e5dbf17540dcbb9461b8cc38c0855783 gate/prompts-24mix.json"
  "204bb488fe692a0dd7a8b51e32bad01bedd0d95155d04c703c80dd8e94385d4f patches/orchestrator/0001-stack_numa-NUMA_FULL_T48-shape-split-thread-invarian.patch"
  "813fa6848c94be1f6521506ca206fb2d0ae079f8cf00ea3209046f97a242a265 patches/orchestrator/0002-server-critic_thread_gate.py-the-DAR-LAT-3h-gate-G1-.patch"
  "d82d0d1d717313912241fe886b0ad3033ff101bdedd3337670dd29b8bef42aa3 patches/orchestrator/0003-launcher-the-binary-override-GGML-strip-keeps-the-ro.patch"
  "99244196526143d2d054fc3ef867476e8bd41326627dba3ea336ad53784478de patches/orchestrator/0004-stack_env-architect_critic-carries-its-codified-reci.patch"
  "e1356253f56932ea4bce3881710bd357cc42f98929875caf5fe6878418784ae3 patches/orchestrator/0005-topology-architect_critic-NUMA_FULL_T48-t-48-complet.patch"
  "022c6ca69c1ec986516c0acaf4971a8aa680f237d061c10fe7e6585b2bb4a1f2 patches/research-fallback-L/0002-registry-architect_critic-serving-stays-t-96-canonic.patch"
  "bd7357deba45d0c82b73ea86fd8ea608683aad4ecd14ff482519dcbf4914c9b3 patches/research-fallback-R96/0002-registry-architect_critic-serving-t-96-recipe-env-DA.patch"
  "6375e31159910049f68f20c5a0f02c794f2208eb7a7b4022847a3db535bfc283 patches/research/0001-registry-recipe-correct-the-Flash-Next-t-48-served-o.patch"
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
    "signed_gates": {
        "G1_thread_env_aba": {
            "driver": "epyc-orchestrator scripts/server/critic_thread_gate.py @ aa2c2c2a",
            "arms": {"L": "-t 96, live env", "R96": "-t 96 + recipe GGML env", "R48": "-t 48 + recipe GGML env"},
            "unit": "launch", "launches_per_arm": 4, "min_clean_launches_per_arm": 3,
            "primary": "mean per-launch median W1 request wall time (the critic's region-lock hold time)",
            "rule": "R48 if wall <= 1.03x and TTFT <= 1.10x vs BOTH R96 and L and coherent >= ref-1; "
                    "else R96 if the same vs L; else L; <3 clean launches in any arm -> INCONCLUSIVE",
        },
        "G2_serving_proof": "PACKAGE.md section 6 P4-P5 (/proc argv, environ, per-task affinity, numa_maps, runtime_attestation ok, coherent ~4k-token completion with MTP accepting)",
        "G3_contention_recert": "R48 only: contention_matrix.py run in the same window; check_contention_matrix_fresh.py OK",
    },
    "outcome_merge_prefix": {
        "R48": {"epyc-orchestrator": "lane/dar-lat-3h-20260926 through 20c7d902",
                "epyc-inference-research": "lane/dar-lat-3h-20260926 (cf2476b0)", "reload": "architect_critic"},
        "R96": {"epyc-orchestrator": "lane/dar-lat-3h-20260926 through 071d8ff9",
                "epyc-inference-research": "lane/dar-lat-3h-t96-20260926 (2a4613f7)", "reload": "architect_critic"},
        "L": {"epyc-orchestrator": "lane/dar-lat-3h-20260926 through 27008a15",
              "epyc-inference-research": "lane/dar-lat-3h-live-20260926 (cc8dd98e)", "reload": "none"},
        "INCONCLUSIVE": "apply nothing; re-run G1 in another window",
    },
    "scope_excluded": ["n_ctx (lineup-change C4 stands)", "CPU speech co-tenancy (operator ruling 2026-09-24: no change)"],
    "applies_nothing": True,
}
tmp = receipt + ".tmp"
with open(tmp, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, receipt)
print(f"RATIFIED: {receipt}")
PY
