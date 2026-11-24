#!/bin/bash
# Operator signature for stack change OFFICIAL-SAMPLING-VISION-ESC-20261124 (vision_escalation vendor sampling). See PACKAGE.md.
# Verifies pinned package content and that the lane commit exists on origin, then writes ONE receipt.
# Applies, merges, compiles, reloads NOTHING.
set -euo pipefail
export PATH="/usr/bin:/bin"
TOKEN="RATIFY-OFFICIAL-SAMPLING-VISION-ESC-20261124"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
LANE="lane/sc-official-sampling-vision-esc-20261124"
R_COMMIT="6522e7c0b"
PINS=(
  "848d15014a6739952621e900fa63aa00597528703709f76e9403c6f69b04d61d PACKAGE.md"
  "ed62a27699c31b637521ee175011a2a0e485adc2ef3482145e04fa798d706b61 patches/research-01-vision-escalation-generation-defaults.patch"
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
git -C "$RESEARCH" fetch -q origin "$LANE" 2>/dev/null || fail "cannot fetch origin/$LANE in $RESEARCH"
git -C "$RESEARCH" merge-base --is-ancestor "$R_COMMIT" FETCH_HEAD 2>/dev/null || fail "$R_COMMIT not on origin/$LANE in $RESEARCH"
echo "ok  $RESEARCH $R_COMMIT on origin/$LANE"
[[ "$MODE" == validate ]] && { echo "VALID (no receipt written)"; exit 0; }
mkdir -p "$(dirname "$RECEIPT")"
printf '{"token":"%s","signed_at":"%s","package":"artifacts/operator/stack-change-official-sampling-vision-esc-20261124","research_commit":"%s","roles":["vision_escalation"],"change":"roles.vision_escalation.generation_defaults = Qwen3-VL official sampling (same as worker_vision)"}\n' "$TOKEN" "$(date -u +%FT%TZ)" "$R_COMMIT" > "$RECEIPT"
echo "SIGNED: $RECEIPT"
