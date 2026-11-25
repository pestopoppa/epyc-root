#!/bin/bash
# Operator signature for STACKCHG-27B-UB2048-20261125. See PACKAGE.md.
# Verifies pinned package content and that both lane commits exist on origin, then writes ONE receipt.
# Applies, merges, reloads NOTHING. Apply steps: PACKAGE.md section 5.
set -euo pipefail
export PATH="/usr/bin:/bin"
TOKEN="RATIFY-27B-UB2048-20261125"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
LANE="lane/sc-27b-ub2048-20261125"
RES="/mnt/raid0/llm/epyc-inference-research"; RES_C="0dfde6c0e386009b87938f2314d46945bee5c3b6"
ORCH="/mnt/raid0/llm/epyc-orchestrator";       ORCH_C="70fd48d950ffdb937f7f0bb207579edd29bbcbf4"
PINS=(
  "dce33852ddf3323da249a66ce45a666e3f7ee25e87b044c6c3625126f2385f81 PACKAGE.md"
  "d128fa500255730192d1a9bc42e381c951e5151e4355472af9fe202ef5b3183b patches/research-01-architect-critic-ub2048.patch"
  "fc8ea7b22deb8fdc1e8330b0c9ae89b58ea525ad67364e81678f437933f5da3f patches/orchestrator-01-architect-critic-ub2048.patch"
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
  [[ "$(sha256sum -- "$f" | cut -d' ' -f1)" == "$want" ]] || fail "$f changed after preparation"
  echo "ok  $f"
done
for pair in "$RES $RES_C" "$ORCH $ORCH_C"; do
  r="${pair% *}"; c="${pair#* }"
  git -C "$r" fetch -q origin "$LANE" || fail "cannot fetch origin/$LANE in $r"
  git -C "$r" merge-base --is-ancestor "$c" FETCH_HEAD || fail "$c not on origin/$LANE in $r"
  echo "ok  $r $c on origin/$LANE"
done
[[ "$MODE" == validate ]] && { echo "VALID (no receipt written)"; exit 0; }
mkdir -p "$(dirname "$RECEIPT")"
printf '{"token":"%s","signed_at":"%s","package":"artifacts/operator/stack-change-27b-ub2048-20261125","research_commit":"%s","orchestrator_commit":"%s","evidence_row":"ak-27b-served-ub-arrival-sweep-gpu-20261125-r2"}\n' "$TOKEN" "$(date -u +%FT%TZ)" "$RES_C" "$ORCH_C" > "$RECEIPT"
echo "SIGNED: $RECEIPT  -- now run PACKAGE.md section 5 steps 1-4"
