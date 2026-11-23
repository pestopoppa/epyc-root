#!/bin/bash
# Operator signature for stack change A3B-PMIN05 (frontdoor --draft-p-min 0.5). See PACKAGE.md.
# Verifies pinned package content and that the research lane commit exists on origin,
# then writes ONE receipt. Applies, merges, compiles, reloads NOTHING.
set -euo pipefail
export PATH="/usr/bin:/bin"
TOKEN="RATIFY-A3B-PMIN05-20261123"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
LANE="lane/sc-a3b-pmin05-20261123"
COMMIT="ed7796375"
PINS=(
  "5f9f94b745424631ad0162c12eb0828ae846ebcc0e8ab25cd678ac3cc19c19dd PACKAGE.md"
  "b067be226334329e94d8ec48a7cfe4501218e8c206b065e080ac40100c86d075 patches/research-01-frontdoor-draft-p-min-0.5.patch"
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
git -C "$RESEARCH" fetch -q origin "$LANE" 2>/dev/null || fail "cannot fetch origin/$LANE"
git -C "$RESEARCH" merge-base --is-ancestor "$COMMIT" FETCH_HEAD 2>/dev/null || fail "$COMMIT not on origin/$LANE"
echo "ok  research $COMMIT on origin/$LANE"
[[ "$MODE" == validate ]] && { echo "VALID (no receipt written)"; exit 0; }
mkdir -p "$(dirname "$RECEIPT")"
printf '{"token":"%s","signed_at":"%s","package":"artifacts/operator/stack-change-a3b-pmin05-20261123","research_commit":"%s","roles":["frontdoor","worker_summarize","worker_general","worker_explore","worker_math","toolrunner","worker"],"change":"server_mode.frontdoor.acceleration.draft_p_min=0.5"}\n' "$TOKEN" "$(date -u +%FT%TZ)" "$COMMIT" > "$RECEIPT"
echo "SIGNED: $RECEIPT"
