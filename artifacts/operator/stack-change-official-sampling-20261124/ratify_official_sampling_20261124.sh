#!/bin/bash
# Operator signature for stack change OFFICIAL-SAMPLING-20261124 (vendor sampling on served roles). See PACKAGE.md.
# Verifies pinned package content and that both lane commits exist on origin, then writes ONE receipt.
# Applies, merges, compiles, reloads NOTHING.
set -euo pipefail
export PATH="/usr/bin:/bin"
TOKEN="RATIFY-OFFICIAL-SAMPLING-20261124"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
LANE="lane/sc-official-sampling-20261124"
R_COMMIT="fb4dca72e"
O_COMMIT="00ef9f47"
PINS=(
  "03cda2964d566f315eddec6e229d981ff3149e77a6952705d304f8dbb2dd8123 PACKAGE.md"
  "328ec2b86a5aa7e4ce8d71f6aac55d811ca79e85e0d384f7d821427ee5df87ae patches/research-01-official-sampling-generation-defaults.patch"
  "cb99fba1d9f2cdbc273d175a63c97ac93a4199128c3ab5d34db8961feac5f15d patches/orchestrator-01-sampler-wire.patch"
)
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
case "${1:-}" in
  --validate-only) MODE=validate ;;
  --attest) [[ "${2:-}" == "$TOKEN" ]] || fail "usage: $0 --attest $TOKEN"; MODE=attest ;;
  *) fail "usage: $0 --validate-only | --attest $TOKEN" ;;
esac
[[ "$MODE" != attest || ! -e "$RECEIPT" ]] || fail "token SPENT: $RECEIPT"
cd "$PKG"
for pin in "${PINS[@]}"; do
  want="${pin%% *}"; f="${pin#* }"
  got="$(sha256sum -- "$f" | cut -d' ' -f1)"
  [[ "$got" == "$want" ]] || fail "$f changed after preparation"
  echo "ok  $f"
done
for pair in "$RESEARCH $R_COMMIT" "$ORCH $O_COMMIT"; do
  repo="${pair% *}"; c="${pair#* }"
  git -C "$repo" fetch -q origin "$LANE" 2>/dev/null || fail "cannot fetch origin/$LANE in $repo"
  git -C "$repo" merge-base --is-ancestor "$c" FETCH_HEAD 2>/dev/null || fail "$c not on origin/$LANE in $repo"
  echo "ok  $repo $c on origin/$LANE"
done
[[ "$MODE" == validate ]] && { echo "VALID (no receipt written)"; exit 0; }
mkdir -p "$(dirname "$RECEIPT")"
printf '{"token":"%s","signed_at":"%s","package":"artifacts/operator/stack-change-official-sampling-20261124","research_commit":"%s","orchestrator_commit":"%s","roles":["frontdoor","worker_general","worker_summarize","toolrunner","worker_math","coder_escalation","architect_critic","ingest_long_context","architect_general","worker_vision"],"change":"roles.*.generation_defaults = vendor official sampling; backend sends top_p/top_k/min_p/presence_penalty/repeat_penalty from it"}\n' "$TOKEN" "$(date -u +%FT%TZ)" "$R_COMMIT" "$O_COMMIT" > "$RECEIPT"
echo "SIGNED: $RECEIPT"
