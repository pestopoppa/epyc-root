#!/bin/bash
# Operator signature for the UFH-12 Phase-0 stack-change package (embedder
# placement + -c 2048, and stale stack-config text). See PACKAGE.md in this
# directory.
#
# What it does: verifies PACKAGE.md and the three patches against the sha256
# values pinned below, verifies the three lane commits exist on origin, and
# writes ONE receipt recording the signature and the signed G1 thresholds.
#
# What it does NOT do: apply a patch, merge a branch, compile, start, stop or
# reload anything. Phases 7-8 (PACKAGE.md section 9) are run afterwards by the
# session that owns the inference, and they begin by checking this receipt.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-UFH12-PHASE0-EMBEDDER-PLACEMENT-20260926"
# Resolved from this script's own location, so it runs from the epyc-root main
# clone or from the lane worktree alike; the receipt lands in that same tree.
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
LANE="lane/ufh11-phase0-20260926"
ORCH_COMMITS="845950b4 05048a66"
RESEARCH_COMMITS="7640269b"
PYTHON="/usr/bin/python3"

# Pinned content. A package edited after preparation must be re-pinned by its
# preparer, not signed as-is.
PINS=(
  "f35b90905d2ba610241ab2d09e3575eb4449213a4b5653bca25734419ec9c73c PACKAGE.md"
  "4b3f81f32eb3561c9ef28defe145f8e6b34b62c0c0f5c795345c8f95319d7860 patches/orchestrator-01-embedder-placement-ctx2048-stale-text.patch"
  "5eca1899153f7813f143fe9272ffd1513c9c47f15dbddbfd1dc2c2a72c8efa04 patches/orchestrator-02-measurement-gate-driver.patch"
  "d5f0b07c64854b584bc49772aa526c26f3e81d756b6446a08fd9de81e72b2839 patches/research-01-stale-role-descriptions.patch"
)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'usage: %s --validate-only\n       %s --attest %s [--g1-pass X] [--g1-rollback Y]\n' "$0" "$0" "$TOKEN" >&2
}

MODE=""; G1_PASS="0.95"; G1_ROLLBACK="0.90"
case "${1:-}" in
  --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
  --attest)
    [[ $# -ge 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }
    MODE="attest"; shift 2
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --g1-pass) G1_PASS="${2:?}"; shift 2 ;;
        --g1-rollback) G1_ROLLBACK="${2:?}"; shift 2 ;;
        *) usage; exit 2 ;;
      esac
    done ;;
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

for repo_commits in "$ORCH:$ORCH_COMMITS" "$RESEARCH:$RESEARCH_COMMITS"; do
  repo="${repo_commits%%:*}"; commits="${repo_commits#*:}"
  git -C "$repo" fetch -q origin "$LANE" || fail "cannot fetch origin/$LANE in $repo"
  for c in $commits; do
    git -C "$repo" merge-base --is-ancestor "$c" FETCH_HEAD \
      || fail "$c is not on origin/$LANE in $repo"
    printf 'ok  %s %s on origin/%s\n' "$(basename "$repo")" "$c" "$LANE"
  done
done

"$PYTHON" - "$G1_PASS" "$G1_ROLLBACK" <<'PY'
import sys
p, r = float(sys.argv[1]), float(sys.argv[2])
if not (0 < r < p <= 1):
    raise SystemExit(f"G1 thresholds must satisfy 0 < rollback < pass <= 1, got pass={p} rollback={r}")
PY

if [[ "$MODE" == "validate" ]]; then
  printf 'VALID: package, patches and lane commits verified. Nothing written.\n'
  exit 0
fi

mkdir -p -- "$(dirname -- "$RECEIPT")"
"$PYTHON" - "$RECEIPT" "$TOKEN" "$G1_PASS" "$G1_ROLLBACK" "${PINS[@]}" <<'PY'
import json, os, sys
from datetime import UTC, datetime
receipt, token, g1p, g1r, *pins = sys.argv[1:]
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": token,
    "status": "ratified",
    "human_attestation": token,
    "signed_at": datetime.now(UTC).isoformat(),
    "signed_by_uid": os.getuid(),
    "package": "artifacts/operator/stack-change-ufh12-phase0-20260926/PACKAGE.md",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "lane_branch": "lane/ufh11-phase0-20260926",
    "lane_commits": {"epyc-orchestrator": ["845950b4", "05048a66"], "epyc-inference-research": ["7640269b"]},
    "signed_gates": {
        "G0_idle_cost": "post Q within the larger A/A floor of pre/post, per port",
        "G1_frontdoor_decode_s_over_q": {"pass": float(g1p), "rollback_below": float(g1r),
                                           "also": "not below pre S/Q by more than the A/A floor"},
        "G2_pool_scaling": {"pass": 4.0, "rollback_below": 2.0},
        "G3_speech": {"stt_rtf_max": 0.40, "tts_first_packet_ms_max": 500},
    },
    "scope_excluded": ["GPU embedder (separate package, PACKAGE.md N-4)", "D1 scheduler code (REPL-EMB-1.1)"],
    "applies_nothing": True,
}
tmp = receipt + ".tmp"
with open(tmp, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, receipt)
print(f"RATIFIED: {receipt}")
PY
