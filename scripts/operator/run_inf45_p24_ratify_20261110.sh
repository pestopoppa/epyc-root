#!/bin/bash
# run_inf45_p24_ratify_20261110.sh -- ONE operator signature (RATIFY-INF45-P24-20261110) amending
# P-BENCH-PLACEMENT-1 in measurement/protocols/bench-cpu.md (INF-45 P2-4 + the four-amendment fold box).
# Operator decision 2026-11-10 (coordinator decision tool): P2-4 "Required depth=<n> (Recommended)".
#
# WHAT YOU ARE SIGNING
#   1. Claim grammar gains a REQUIRED context-depth field: `depth=<n>` (resident context tokens at the
#      measured decode, read from the server's `n_tokens`, never from the first `prompt eval time` line).
#      Old grammar line is replaced in place; a claim without depth= is non-conforming.
#   2. Four P-BENCH-PLACEMENT-1 amendments, added as a block before "**Claim grammar.**":
#      A1 no repeated-prompt replication for context-reading drafters; A2 a non-context control arm is
#      mandatory; A3 report n/min/max, never a bare median; A4 `accept=1.000` is a bug report, not a result.
#   NOT included: INTERLEAVE_TOLERANCE (+/-25% relative) -- already ratified as TBD 2 under
#   RATIFY-INF45-P23-20261109; TBDs 3,4,5,7,8,9,10,13,14 stay open.
#   Placement note: the amendments go into the P-BENCH-PLACEMENT-1 annex (where the protocol lives), not
#   into MEASUREMENT.md's body; MEASUREMENT.md is unchanged.
#
#   Review / dry run (DEFAULT, writes nothing):
#     bash scripts/operator/run_inf45_p24_ratify_20261110.sh
#   Sign (operator, from a terminal, in an epyc-root checkout that has this script):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/run_inf45_p24_ratify_20261110.sh --apply --attest RATIFY-INF45-P24-20261110
#
# ratify-targets: measurement/protocols/bench-cpu.md
#
# Idempotent: marker present with identical content = ALREADY RATIFIED, exit 0; different = REFUSE.
# Does NOT commit or push and touches no process; commit the changed files yourself (pathspec commit).
# ROLLBACK: git checkout -- measurement/protocols/bench-cpu.md ; rm the receipt file it printed.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TARGET="measurement/protocols/bench-cpu.md"
GATE_ID="RATIFY-INF45-P24-20261110"
RECEIPT_REL="artifacts/operator/ratify_inf45_p24_20261110.receipt.json"
MODE=review; ATTEST=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply) MODE=apply ;;
    --dry-run|--review) MODE=review ;;
    --attest) shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--apply --attest $GATE_ID]" >&2; exit 64 ;;
  esac; shift
done
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
[ -f "$ROOT/$TARGET" ] || die "$ROOT/$TARGET missing"

NEW="$(mktemp)"
trap 'rm -f "$NEW"' EXIT
rc=0
python3 -I - "$GATE_ID" "$ROOT/$TARGET" "$NEW" <<'PYEOF' || rc=$?
import sys, difflib
gid, target, new = sys.argv[1:4]
begin = f"<!-- {gid} BEGIN -->"; end = f"<!-- {gid} END -->"
old_g = "`<value> tok/s <per-stream|aggregate(T=n)>, spec-dec <on|off>, arm <A0..A4> [P-BENCH-PLACEMENT-1, n=<reps>, <date>, attest <ref>]`"
new_g = "`<value> tok/s <per-stream|aggregate(T=n)>, spec-dec <on|off>, arm <A0..A4>, depth=<n> [P-BENCH-PLACEMENT-1, n=<reps>, <date>, attest <ref>]`"
block = "\n".join([
  begin,
  f"**Amendments ({gid}).** Binding on every conforming run from ratification on; earlier claims are not retro-certified.",
  "",
  "- **A1 — no repeated-prompt replication for context-reading drafters.** Replicates of an arm whose drafter reads the context (ngram, lookup, MTP over context) must use distinct prompts; re-sending one prompt measures cache reuse, not decode.",
  "- **A2 — mandatory non-context control arm.** Every placement comparison carries one arm whose decode does not depend on prompt content (spec-dec off or a non-context drafter), so placement and drafter effects separate.",
  "- **A3 — report n/min/max, never a bare median.** Every quoted central value carries its sample count, minimum and maximum.",
  "- **A4 — `accept=1.000` is a bug report.** A perfect draft-acceptance rate is treated as an instrumentation defect (replayed prompt, cache hit, mis-parsed counter) and the arm is REJECTED until explained.",
  "- **A5 — context depth is a required claim field (P2-4).** The claim grammar below carries `depth=<n>`: resident context tokens at the measured decode, read from the server's `n_tokens` (`stop processing: n_tokens`), never from the first `prompt eval time` line. Same model, recipe and placement span 40.22 tok/s at 28 tokens to 17.23 at 35k, so a claim without depth is non-conforming.",
  end, ""]) + "\n"
txt = open(target, encoding="utf-8").read()
if begin in txt:
    cur = txt[txt.index(begin): txt.index(end) + len(end) + 1]
    if cur.rstrip("\n") == block.strip("\n") and new_g in txt and old_g not in txt:
        print("ALREADY RATIFIED: identical block and grammar present"); sys.exit(10)
    print("block with this gate id exists but differs"); sys.exit(65)
sec = txt.find("## P-BENCH-PLACEMENT-1")
anchor = "**Claim grammar.**\n"
pos = txt.find(anchor, sec)
nxt = txt.find("\n## ", sec + 5)
if sec < 0 or pos < 0 or (nxt != -1 and nxt < pos):
    print("anchor not inside the P-BENCH-PLACEMENT-1 section; re-derive"); sys.exit(65)
if txt.count(old_g) != 1 or txt.find(old_g) < pos or (nxt != -1 and txt.find(old_g) > nxt):
    print("claim-grammar line not found exactly once in the section; re-derive"); sys.exit(65)
out = txt[:pos] + block + "\n" + txt[pos:]
out = out.replace(old_g, new_g, 1)
open(new, "w", encoding="utf-8").write(out)
for l in difflib.unified_diff(txt.splitlines(), out.splitlines(), target, target + " (after)", lineterm="", n=1): print(l)
PYEOF
[ "$rc" -eq 10 ] && exit 0
[ "$rc" -eq 0 ] || die "preflight failed (rc=$rc); nothing written"

if [ "$MODE" = review ]; then
  echo; echo "DRY RUN: nothing written. Re-run with --apply --attest $GATE_ID to sign."; exit 0
fi
[ "$ATTEST" = "$GATE_ID" ] || die "--apply needs --attest $GATE_ID"
# shellcheck source=/dev/null
source "$ROOT/scripts/operator/lib/ratify_operator.sh"
ratify_require_operator
PRE="$(mktemp)"; BAK="$(mktemp)"; cp "$ROOT/$TARGET" "$BAK"
restore() { cp "$BAK" "$ROOT/$TARGET"; rm -f "$PRE" "$BAK" "$ROOT/$RECEIPT_REL"; }
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" --state "$TARGET" --out "$PRE" || { restore; die "capture failed"; }
cp "$NEW" "$ROOT/$TARGET"
BEGIN_MARK="<!-- $GATE_ID BEGIN -->"
[ "$(grep -cF "$BEGIN_MARK" "$ROOT/$TARGET")" = 1 ] || { restore; die "post-state marker count != 1; restored"; }
grep -qF 'depth=<n> [P-BENCH-PLACEMENT-1' "$ROOT/$TARGET" || { restore; die "grammar replacement missing; restored"; }
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit --repo-root "$ROOT" --pre "$PRE" \
  --protocol-id P-BENCH-PLACEMENT-1 --anchor "$BEGIN_MARK" --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" --operator "$RATIFY_OPERATOR" \
  --no-evidence-reason "protocol-text amendment; depth spread cited inline (INF-45 P2-4), amendments A1-A4 from the INF-45 fold box" \
  --validation "grep -cF '$BEGIN_MARK' $TARGET" \
  --out "$ROOT/$RECEIPT_REL" || { restore; die "receipt refused; target restored"; }
rm -f "$PRE" "$BAK"
echo "RATIFIED $GATE_ID by $RATIFY_OPERATOR. Changed: $TARGET, $RECEIPT_REL. Commit them (pathspec commit); nothing was committed or pushed."
