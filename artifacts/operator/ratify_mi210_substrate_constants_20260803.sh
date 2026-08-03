#!/bin/bash
# DP-1 ratification — MI210 substrate constants as first-class measured facts.
#
#   bash artifacts/operator/ratify_mi210_substrate_constants_20260803.sh --dry-run
#   bash artifacts/operator/ratify_mi210_substrate_constants_20260803.sh
#
# WHY THIS IS A SCRIPT AND NOT AN AGENT EDIT
#   MEASUREMENT.md sits behind the human-only trust boundary. An agent may prepare
#   the amendment and validate every precondition; only the operator executes it.
#   This script is idempotent and refuses on any precondition failure.
#
# WHAT IT RATIFIES — DP-1 option C, executable in ONE step because the measurements
# that option C was going to wait for have all landed:
#
#   peak fp16/bf16 matrix   172.2 TFLOPS  [M]   (181.0 [D] from spec)
#   achievable HBM BW       1433.3 GB/s   [M]   (1638   [D] datasheet)
#   PCIe H2D / D2H          28.89 / 28.20 GB/s [M]  (Gen4 x16, 31.5 theoretical)
#   ridge, measured basis   120.1 FLOP/byte [M]
#   ridge, spec basis       110.5 FLOP/byte [D]  (retained for cross-vendor use)
#   B* measured basis       Q4_K 34 · Q8_0 64 · bf16 120
#
# AND ONE USAGE RULE, which is the part that actually prevents error:
#   Use the MEASURED basis for headroom and campaign sizing. Use the SPEC basis for
#   cross-vendor comparison. Never mix them, and always state which was used. A
#   utilisation quoted without its denominator is not a number. Converting our
#   figures to a measured basis while a competitor's stay on spec makes a gap look
#   smaller without it being smaller -- and dividing a per-OAM FLOPS figure by a
#   per-GCD bandwidth is how AMD's own KB published a ridge point off by 2x.
#
# DP-2..DP-6 are NOT ratified here. They are independent decisions with their own
# options and tradeoffs; see artifacts/operator/measurement-decision-packages-20260803.md.

set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
RESEARCH=/mnt/raid0/llm/epyc-inference-research
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

REQUIRED_RECEIPTS=(
  "data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json"
  "data/mi210-h2d-d2h/20260803T131500Z/receipt.json"
  "data/mi210-mfma-peak/20260803T143200Z/receipt.json"
)

fail() { printf 'REFUSING: %s\n' "$1" >&2; exit 1; }

echo "== DP-1 preconditions =="

# 1. Every constant must trace to a committed receipt. An untracked receipt looks
#    identical to a committed one, which is exactly how evidence goes missing.
for r in "${REQUIRED_RECEIPTS[@]}"; do
  [[ -f "$RESEARCH/$r" ]] || fail "receipt missing: $r"
  git -C "$RESEARCH" ls-files --error-unmatch "$r" >/dev/null 2>&1 \
    || fail "receipt is UNTRACKED (not committed): $r"
  echo "  OK  tracked receipt: $r"
done

# 2. The measured values in this script must match the receipts, or the script has
#    drifted from its evidence.
check() {  # name jq-path expected tolerance
  local got; got=$(python3 -c "import json;d=json.load(open('$RESEARCH/$2'));print($3)")
  python3 -c "import sys;sys.exit(0 if abs($got-($4))<=($5) else 1)" \
    || fail "$1: receipt says $got, script asserts $4"
  echo "  OK  $1 = $got"
}
check "peak TFLOPS"   "data/mi210-mfma-peak/20260803T143200Z/receipt.json" \
      "d['measured_TFLOPS_fp16_matrix']" 172.2 0.5
check "achievable BW" "data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json" \
      "d['denominators']['measured_achievable_GBps']" 1433.3 1.0
check "H2D GB/s"      "data/mi210-h2d-d2h/20260803T131500Z/receipt.json" \
      "max(d['h2d_peak_GBps'].values())" 28.89 0.1

# 3. Idempotence.
if grep -q 'MI210-SUBSTRATE-CONSTANTS-1' "$ROOT/MEASUREMENT.md" 2>/dev/null; then
  echo; echo "Already ratified (MI210-SUBSTRATE-CONSTANTS-1 present). No files changed."
  exit 0
fi

echo; echo "== amendment text =="
AMEND=$(cat <<'AMENDMENT'

## MI210-SUBSTRATE-CONSTANTS-1 — measured substrate constants (RATIFIED 2026-08-03)

Every roofline denominator this project uses is measured, not assumed. Each traces to a
committed receipt under `epyc-inference-research/data/`.

| Constant | Measured `[M]` | Derived `[D]` | Receipt |
|---|---|---|---|
| Peak fp16/bf16 matrix | **172.2 TFLOPS** | 181.0 | `data/mi210-mfma-peak/20260803T143200Z/` |
| Achievable HBM bandwidth | **1433.3 GB/s** | 1638 (datasheet) | `data/mi210-achievable-bandwidth/20260803T124401Z/` |
| PCIe H2D / D2H | **28.89 / 28.20 GB/s** | 31.5 (Gen4 x16) | `data/mi210-h2d-d2h/20260803T131500Z/` |
| Ridge, measured basis | **120.1 FLOP/byte** | — | derived from the two above |
| Ridge, spec basis | — | 110.5 FLOP/byte | retained for cross-vendor comparison |

`B*` on the measured basis: Q4_K 34 · Q8_0 64 · bf16 120.

**Usage rule (binding).** Use the **measured** basis for headroom and campaign sizing; use the
**spec** basis for cross-vendor comparison; **never mix them, and always state which was used.**
A utilisation quoted without its denominator is not a number. Two failure modes this rule exists
to prevent, both observed in 2026-08: converting our own figures to a measured basis while a
competitor's remain on spec, which makes a gap look smaller without it being smaller; and
dividing a per-OAM FLOPS figure by a per-GCD bandwidth, which is how a vendor knowledge base
published a ridge point off by 2×.

**Grade.** These are substrate constants at OBSERVATION grade. They describe the machine, not a
candidate: they license no promotion, no era row, and no release claim.
AMENDMENT
)
printf '%s\n' "$AMEND"

if (( DRY_RUN )); then
  echo; echo "--dry-run: all preconditions pass, nothing written."
  exit 0
fi

printf '%s\n' "$AMEND" >> "$ROOT/MEASUREMENT.md"
printf -- '- 2026-08-03: MI210-SUBSTRATE-CONSTANTS-1 ratified — peak FLOPS, achievable HBM bandwidth and PCIe H2D/D2H measured; ridge stated on both bases with a binding no-mixing rule.\n' \
  >> "$ROOT/CHANGELOG.md"

echo
echo "Amended: MEASUREMENT.md, CHANGELOG.md"
echo "Review with:  git -C $ROOT diff"
echo "Then commit.  DP-2..DP-6 remain unratified and independent."
