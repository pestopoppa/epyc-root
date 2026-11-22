#!/bin/bash
# Operator signature for stack change V5I-27B-Q8MF. See PACKAGE.md.
# Verifies pinned package content and that the orchestrator lane commit exists on origin,
# then writes ONE receipt. Applies, merges, builds, reloads NOTHING.
set -euo pipefail
export PATH="/usr/bin:/bin"
TOKEN="RATIFY-V5I-27B-Q8MF-20261122"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
LANE="lane/sc-v5i-27b-q8mf-20261122"
COMMIT="8fd386d0"
PINS=(
  "038cd38ac77bf66b93db787fa8f8802a3eb9141875476b79be2717a505dcf9ee PACKAGE.md"
  "11a0dcdff8b17efe98317bb2e817739c9ed5d90674b94d0a31e0a02bd5959f4b patches/orchestrator-01-stack-env-v5i-architect-critic.patch"
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
git -C "$ORCH" fetch -q origin "$LANE" || fail "cannot fetch origin/$LANE"
git -C "$ORCH" merge-base --is-ancestor "$COMMIT" FETCH_HEAD || fail "$COMMIT not on origin/$LANE"
echo "ok  orchestrator $COMMIT on origin/$LANE"
[[ "$MODE" == validate ]] && { echo "VALID (no receipt written)"; exit 0; }
mkdir -p "$(dirname "$RECEIPT")"
printf '{"token":"%s","signed_at":"%s","package":"artifacts/operator/stack-change-v5i-27b-q8mf-20261122","orchestrator_commit":"%s","apply_condition":"bundle with C18->v11 promotion; inert on v10"}\n'   "$TOKEN" "$(date -u +%FT%TZ)" "$COMMIT" > "$RECEIPT"
echo "SIGNED: $RECEIPT"
