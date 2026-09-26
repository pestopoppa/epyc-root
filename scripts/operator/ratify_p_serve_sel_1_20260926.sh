#!/bin/bash
# ratify_p_serve_sel_1_20260926.sh — P-SERVE-SEL-1: the text-LLM serving-selection load-sweep A/B
# protocol lands in Annex Q, with its section-2 registry row and CHANGELOG entry.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_p_serve_sel_1_20260926.sh
#   Apply + receipts + commit (ONE):    RATIFY_OPERATOR=<name> bash scripts/operator/ratify_p_serve_sel_1_20260926.sh --apply
#   Apply + receipts, no commit:        RATIFY_OPERATOR=<name> bash scripts/operator/ratify_p_serve_sel_1_20260926.sh --apply --no-commit
#   Verify the post-state (read-only):  bash scripts/operator/ratify_p_serve_sel_1_20260926.sh --verify
#
# Or run it all from an isolated worktree off origin/main, with a typed confirmation:
#   bash scripts/operator/run_p_serve_sel_1_ratify_20260926.sh --operator <name>
#
# OPERATOR DECISION OP-62. The operator RATIFIED P-SERVE-SEL-1 on 2026-09-26 in the orchestrator-design
# session. The decision is already made. This script only carries the text across the trust boundary,
# because no agent may write it. Tracked as OP-62 in handoffs/active/master-handoff-index.md; first
# consumer handoffs/active/decision-aware-routing.md DAR-LAT-3 (the Stage-3 plan's DAR-LAT-3a drafted
# the protocol: docs/research-intake/orch-prior-art-stage3-plan-20260926.md).
#
# WHY. No ratified text-LLM TTFT or serving-load protocol existed: section 2 listed only P-TTS-3 for
# first-audio latency. Without one, DAR-LAT-3's load-sweep A/B could only ever be observation-grade,
# and its result is meant to decide whether a latency/load term's routing weights leave 0.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/p-serve-sel-1-20260926.patch; additions only, 0 lines removed)
#   measurement/protocols/quality-eval.md   (Annex Q)
#     - appends section "P-SERVE-SEL-1 — Text-LLM serving-selection load-sweep A/B (RATIFIED 2026-09-26)":
#       arms (A0 incumbent category=OPTIMUM, candidates category=CANDIDATE, unit = arm), the six rigor
#       controls, floor F over 24 A/A block pairs at rho=1.25, the decision rule, PAIRED-CI-1 within a
#       window only (W1/W2 never pooled), BOUNDED-NULL-1 positive controls, preconditions, sizing and
#       stop rules, grammar. Byte-identical to artifacts/operator/staged/p-serve-sel-1-20260926.md.
#   MEASUREMENT.md
#     - section 2: one registry row appended at the end of the table (status ✅ 2026-09-26, annex Q)
#     - CHANGELOG: one 2026-09-26 entry prepended (required by section 5)
#   Both MEASUREMENT.md blocks are verbatim in artifacts/operator/staged/p-serve-sel-1-20260926.measurement-md.md,
#   which also records WHY Annex Q (the P-AB-1 family) and not a new annex or Annex G.
#
# WHAT IT DOES NOT DO. It takes no measurement, grants no window, flips no routing weight (that flip
# needs its own instrument-era row), changes no code, and touches no other protocol. It does not touch
# coordination/session-bus/human_only_paths.yaml. Nothing here starts a process, takes compute, or uses
# the network.
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml; invariant 15). An agent prepared this bundle
# (research-intake Stage 4, S4-F). Only the operator applies it.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                              f11f8ea20638199a65079de35f9734fd35009e5aff754a6cf335a360370b0b48
#   staged annex text                  034a9265ed7c1f0e8b63bd26dc874cd37d6a6d533de4811fabd20a536c50a8f6
#   staged MEASUREMENT.md snippets     f6c690ef3df5c851dd4388f8ffa9bd7757c28d9363a1777197e235aacfc8b0eb
#   MEASUREMENT.md         pre-state   abfd4f2c8a7dc70a6586a0090b1d233e1b87f18bc62bf5cf0d043abfa859409a
#   MEASUREMENT.md         post-state  73f09cacca8c1dcb8eaed5c57cebec860b0f35a757e3e9efc32827f20fd3cbc4
#   protocols/quality-eval pre-state   ec25a3ea2a483341bcac05ad956030148ebf5aa4567e64963388e4082dd1a644
#   protocols/quality-eval post-state  1d901b4bca7e4de4d5efd10bd029984ca1efec6c7c0781ed2560d08ee11bf934
# The pre-state pins match epyc-root origin/main b3e1bb00 (2026-09-26). A stale checkout is refused:
# fast-forward it first.
#
# COMMIT. --apply commits exactly the five paths below on ROOT's current branch, through a private
# index seeded from HEAD, after re-hashing the staged targets against the post-state pins. Nothing a
# peer has staged in a shared index rides along. Preflight also proves all five paths clean first.
# Pushing is left to you (scripts/coordination/serialized_push.py); the command is printed.
#
# IDEMPOTENT. When both targets sit at their post-state pins and the decision receipt and keyed index
# exist, a re-run prints ALREADY RATIFIED and exits 0 without writing. Every other partial state is
# refused and left for resolution by hand.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_p_serve_sel_1_20260926.sh"

PATCH_REL="artifacts/operator/p-serve-sel-1-20260926.patch"
STAGED_ANNEX_REL="artifacts/operator/staged/p-serve-sel-1-20260926.md"
STAGED_SNIPPET_REL="artifacts/operator/staged/p-serve-sel-1-20260926.measurement-md.md"
PATCH="$ROOT/$PATCH_REL"
MEAS_REL="MEASUREMENT.md"
Q_REL="measurement/protocols/quality-eval.md"
TARGETS=("$MEAS_REL" "$Q_REL")
GATE_ID="RATIFY-P-SERVE-SEL-1-20260926"
RECEIPT_REL="artifacts/operator/ratify_p_serve_sel_1_20260926.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
# Beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
CONSOLIDATED_REL="artifacts/operator/ratify_p_serve_sel_1_20260926.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$Q_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_SUBJECT="RATIFIED: P-SERVE-SEL-1 — text-LLM serving-selection load-sweep A/B protocol, Annex Q (OP-62, 2026-09-26)"
CHANGELOG_ANCHOR='- **2026-09-26 (v2.x)** — AMENDMENT (Annex Q, new protocol `P-SERVE-SEL-1`): text-LLM'
REGISTRY_ANCHOR='| P-SERVE-SEL-1 | Text-LLM serving-selection load-sweep A/B:'
ANNEX_HEADING='## P-SERVE-SEL-1 — Text-LLM serving-selection load-sweep A/B (RATIFIED 2026-09-26)'

PATCH_SHA256="f11f8ea20638199a65079de35f9734fd35009e5aff754a6cf335a360370b0b48"
STAGED_ANNEX_SHA256="034a9265ed7c1f0e8b63bd26dc874cd37d6a6d533de4811fabd20a536c50a8f6"
STAGED_SNIPPET_SHA256="f6c690ef3df5c851dd4388f8ffa9bd7757c28d9363a1777197e235aacfc8b0eb"
MEAS_PRE_SHA256="abfd4f2c8a7dc70a6586a0090b1d233e1b87f18bc62bf5cf0d043abfa859409a"
MEAS_POST_SHA256="73f09cacca8c1dcb8eaed5c57cebec860b0f35a757e3e9efc32827f20fd3cbc4"
Q_PRE_SHA256="ec25a3ea2a483341bcac05ad956030148ebf5aa4567e64963388e4082dd1a644"
Q_POST_SHA256="1d901b4bca7e4de4d5efd10bd029984ca1efec6c7c0781ed2560d08ee11bf934"

MODE="review"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --review|--dry-run) MODE="review" ;;
    --apply)            MODE="apply" ;;
    --verify)           MODE="verify" ;;
    --no-commit)        DO_COMMIT=0 ;;
    -h|--help)          sed -n '2,70p' "$SCRIPT_PATH"; exit 0 ;;
    *) echo "usage: $0 [--review | --apply [--no-commit] | --verify]   (default: --review, writes nothing)" >&2; exit 64 ;;
  esac
done
if [ "$DO_COMMIT" -eq 0 ] && [ "$MODE" != "apply" ]; then
  echo "usage: --no-commit only makes sense with --apply" >&2; exit 64
fi

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for t in "${TARGETS[@]}"; do [ -f "$ROOT/$t" ] || die "$t not found under ROOT=$ROOT"; done
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

# ---------------------------------------------------------------- bundle pins (what you review is what lands)
[ -f "$PATCH" ] || die "patch not found at $PATCH"
[ -f "$ROOT/$STAGED_ANNEX_REL" ]   || die "staged annex text not found at $ROOT/$STAGED_ANNEX_REL"
[ -f "$ROOT/$STAGED_SNIPPET_REL" ] || die "staged MEASUREMENT.md snippets not found at $ROOT/$STAGED_SNIPPET_REL"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."
got="$(sha "$ROOT/$STAGED_ANNEX_REL")"
[ "$got" = "$STAGED_ANNEX_SHA256" ] || die "staged annex hash mismatch: expected $STAGED_ANNEX_SHA256, found $got."
got="$(sha "$ROOT/$STAGED_SNIPPET_REL")"
[ "$got" = "$STAGED_SNIPPET_SHA256" ] || die "staged snippet hash mismatch: expected $STAGED_SNIPPET_SHA256, found $got."

# Structural tie between the reviewable staged text and the target files: the annex section is the
# staged file appended verbatim after one blank line, and each fenced MEASUREMENT.md block from the
# snippet file is present verbatim exactly once. Used by postflight and --verify.
check_landed() { # check_landed <MEASUREMENT.md> <quality-eval.md> <pre-quality-eval.md or ->
  python3 - "$1" "$2" "$3" "$ROOT/$STAGED_ANNEX_REL" "$ROOT/$STAGED_SNIPPET_REL" <<'PYEOF'
import re, sys
meas_p, q_p, q_pre_p, annex_p, snip_p = sys.argv[1:6]
meas = open(meas_p, encoding="utf-8").read()
q = open(q_p, encoding="utf-8").read()
annex = open(annex_p, encoding="utf-8").read()
snip = open(snip_p, encoding="utf-8").read()
ok = True
blocks = re.findall(r"```\n(.*?)```\n", snip, re.S)
if len(blocks) != 2:
    print(f"  FAIL  staged snippet file: expected 2 fenced blocks, found {len(blocks)}"); ok = False
for b in blocks:
    n = meas.count(b)
    if n != 1:
        print(f"  FAIL  MEASUREMENT.md: staged block present {n}x (want 1): {b.splitlines()[0][:70]!r}"); ok = False
if not q.endswith("\n" + annex):
    print("  FAIL  quality-eval.md does not end with the staged annex text verbatim"); ok = False
if q_pre_p != "-":
    q_pre = open(q_pre_p, encoding="utf-8").read()
    if q != q_pre + "\n" + annex:
        print("  FAIL  quality-eval.md post-state != pre-state + blank line + staged annex text"); ok = False
if q.count("## P-SERVE-SEL-1 ") != 1:
    print("  FAIL  quality-eval.md: P-SERVE-SEL-1 heading not present exactly once"); ok = False
row = [l for l in meas.split("\n") if l.startswith("| P-SERVE-SEL-1 |")]
if len(row) != 1 or not row[0].rstrip().endswith("| ✅ 2026-09-26 | Q |"):
    print(f"  FAIL  MEASUREMENT.md: registry row for P-SERVE-SEL-1 missing, duplicated or not '✅ 2026-09-26 | Q'"); ok = False
if ok:
    print("  ok    staged text landed verbatim (annex appended; registry row + CHANGELOG entry present once)")
sys.exit(0 if ok else 1)
PYEOF
}

meas_now="$(sha "$ROOT/$MEAS_REL")"
q_now="$(sha "$ROOT/$Q_REL")"
meas_post=0; [ "$meas_now" = "$MEAS_POST_SHA256" ] && meas_post=1
q_post=0;    [ "$q_now"    = "$Q_POST_SHA256"    ] && q_post=1

# ---------------------------------------------------------------- --verify (read-only)
if [ "$MODE" = "verify" ]; then
  say "== verify (ROOT=$ROOT, read-only) =="
  vf=0
  vpin() { if [ "$2" != "$3" ]; then printf '  FAIL  %-48s expected %s found %s\n' "$1" "$2" "$3"; vf=1
           else printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"; fi; }
  vpin "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$meas_now"
  vpin "quality-eval.md post-state hash" "$Q_POST_SHA256" "$q_now"
  check_landed "$ROOT/$MEAS_REL" "$ROOT/$Q_REL" - || vf=1
  for f in "$RECEIPT" "$INDEX" "$CONSOLIDATED"; do
    if [ -f "$f" ]; then printf '  ok    %-48s\n' "present: ${f#"$ROOT"/}"
    else printf '  FAIL  %-48s\n' "present: ${f#"$ROOT"/}"; vf=1; fi
  done
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ] && [ -f "$CONSOLIDATED" ]; then
    python3 - "$RECEIPT" "$INDEX" "$CONSOLIDATED" "$GATE_ID" "$RECEIPT_REL" "$PATCH_SHA256" \
      "$STAGED_ANNEX_SHA256" "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$Q_PRE_SHA256" "$Q_POST_SHA256" <<'PYEOF' || vf=1
import json, sys
(receipt_p, index_p, cons_p, gate, receipt_rel, patch_sha, annex_sha,
 mpre, mpost, qpre, qpost) = sys.argv[1:12]
ok = True
def bad(msg):
    global ok; ok = False; print(f"  FAIL  {msg}")
r = json.load(open(receipt_p, encoding="utf-8"))
i = json.load(open(index_p, encoding="utf-8"))
c = json.load(open(cons_p, encoding="utf-8"))
if r.get("status") != "ratified" or r.get("gate_id") != gate: bad("decision receipt: status/gate_id")
if r.get("protocol_id") != "P-SERVE-SEL-1": bad("decision receipt: protocol_id")
if r.get("ratification", {}).get("date") != "2026-09-26": bad("decision receipt: ratification date")
if r.get("patch", {}).get("sha256") != patch_sha: bad("decision receipt: patch sha256")
if r.get("staged_text", {}).get("annex", {}).get("sha256") != annex_sha: bad("decision receipt: staged annex sha256")
st = r.get("state", {})
if st.get("MEASUREMENT.md") != {"sha256_before": mpre, "sha256_after": mpost}: bad("decision receipt: MEASUREMENT.md hashes")
if st.get("measurement/protocols/quality-eval.md") != {"sha256_before": qpre, "sha256_after": qpost}: bad("decision receipt: quality-eval.md hashes")
if i.get("gate_id") != gate or i.get("status") != "ratified" or not str(i.get("receipt", "")).endswith(receipt_rel):
    bad("keyed index does not point at the decision receipt as ratified")
if c.get("verdict") != "RATIFIED" or c.get("protocol_id") != "P-SERVE-SEL-1" or c.get("ratification_id") != gate:
    bad(f"consolidated receipt: verdict={c.get('verdict')!r} protocol_id={c.get('protocol_id')!r}")
if ok: print("  ok    decision receipt, keyed index and section-5 consolidated receipt agree with the pins")
sys.exit(0 if ok else 1)
PYEOF
  fi
  dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
  if [ -n "$dirty" ]; then printf '  FAIL  %-48s\n%s\n' "five paths committed and clean at HEAD" "$dirty"; vf=1
  else printf '  ok    %-48s (%s)\n' "five paths committed and clean at HEAD" "$(git -C "$ROOT" rev-parse --short HEAD)"; fi
  if [ "$vf" -ne 0 ]; then
    say "VERIFY FAILED: P-SERVE-SEL-1 is not (fully) ratified in $ROOT."
    exit 1
  fi
  say "VERIFIED: P-SERVE-SEL-1 is ratified, receipted and committed in $ROOT."
  exit 0
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ "$meas_post" -eq 1 ] && [ "$q_post" -eq 1 ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    say "Check it with: ROOT=$ROOT bash $SCRIPT_PATH --verify"
    exit 0
  fi
  die "half-applied state: both targets are amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
if [ "$meas_post" -ne "$q_post" ]; then
  die "half-applied state: MEASUREMENT.md post=$meas_post, quality-eval.md post=$q_post. Resolve by hand."
fi
[ -f "$RECEIPT" ]      && die "$RECEIPT_REL already exists, but the targets are not amended. Resolve by hand."
[ -f "$INDEX" ]        && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
pin() { # pin <label> <expected> <found>
  if [ "$2" != "$3" ]; then
    printf '  FAIL  %-48s expected %s\n        %-48s found    %s\n' "$1" "$2" "" "$3"; fail=1
  else
    printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"
  fi
}
printf '  ok    %-48s (%s)\n' "patch hash" "${PATCH_SHA256:0:12}"
printf '  ok    %-48s (%s)\n' "staged annex text hash" "${STAGED_ANNEX_SHA256:0:12}"
printf '  ok    %-48s (%s)\n' "staged MEASUREMENT.md snippets hash" "${STAGED_SNIPPET_SHA256:0:12}"
pin "MEASUREMENT.md pre-state hash" "$MEAS_PRE_SHA256" "$meas_now"
pin "quality-eval.md pre-state hash" "$Q_PRE_SHA256" "$q_now"

if grep -qF 'P-SERVE-SEL-1' "$ROOT/$MEAS_REL" "$ROOT/$Q_REL"; then
  printf '  FAIL  %-48s\n' "P-SERVE-SEL-1 not yet in either target"; fail=1
else
  printf '  ok    %-48s\n' "P-SERVE-SEL-1 not yet in either target"
fi

# The five commit paths must carry no unrelated edits, staged or unstaged, or the commit would sweep
# a peer session's hunk into this amendment (shared-clone hazard).
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-48s\n%s\n' "commit paths clean in git" "$dirty"; fail=1
else printf '  ok    %-48s\n' "commit paths clean in git"; fi

if git -C "$ROOT" apply --check "$PATCH" 2>/dev/null; then
  printf '  ok    %-48s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-48s\n' "patch applies cleanly (no fuzz)"; fail=1
fi

if [ "$fail" -ne 0 ]; then
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main b3e1bb00). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "REVIEW ONLY: would apply the diff above to ${TARGETS[*]} (post-state pins ${MEAS_POST_SHA256:0:12} / ${Q_POST_SHA256:0:12}),"
  say "write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL, and commit those five paths. Nothing written."
  say "Apply with: RATIFY_OPERATOR=<your-name> ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
APPLIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR="${RATIFY_OPERATOR:-${USER:-unknown}}"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$MEAS_REL" "$TMPD/MEASUREMENT.md.bak"
cp "$ROOT/$Q_REL"    "$TMPD/quality-eval.md.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL"
  cp "$TMPD/quality-eval.md.bak" "$ROOT/$Q_REL"
  rm -f "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT"/scripts/operator/ratification_receipt.py capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --state "$Q_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"

# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$PATCH" || { restore; die "git apply failed; targets restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pin_pf() { if [ "$2" != "$3" ]; then printf '  FAIL  %-48s expected %s found %s\n' "$1" "$2" "$3"; pf=1
           else printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"; fi; }
pin_pf "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$(sha "$ROOT/$MEAS_REL")"
pin_pf "quality-eval.md post-state hash" "$Q_POST_SHA256" "$(sha "$ROOT/$Q_REL")"
check_landed "$ROOT/$MEAS_REL" "$ROOT/$Q_REL" "$TMPD/quality-eval.md.bak" || pf=1
# Append-or-version: not one ratified line may be removed or rewritten.
if python3 - "$TMPD/quality-eval.md.bak" "$ROOT/$Q_REL" "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL" <<'PYEOF'
import sys, difflib
ok = True
for a_path, b_path in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    a = open(a_path, encoding="utf-8").read().split("\n")
    b = open(b_path, encoding="utf-8").read().split("\n")
    removed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0)
               if l.startswith("-") and not l.startswith("---")]
    if removed:
        print(f"  FAIL  {b_path}: {len(removed)} line(s) removed or rewritten; additions only expected")
        for line in removed[:5]:
            print(f"        {line[:90]!r}")
        ok = False
if ok:
    print("  ok    additions only in both targets")
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi
if [ "$pf" -ne 0 ]; then
  restore
  die "postflight failed: targets restored from backup. Nothing changed."
fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
mkdir -p "$ROOT/artifacts/operator/receipts"
receipt_rc=0
python3 "$ROOT"/scripts/operator/ratification_receipt.py emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-SERVE-SEL-1 \
  --protocol-new \
  --anchor "$CHANGELOG_ANCHOR" \
  --anchor "$REGISTRY_ANCHOR" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$OPERATOR" \
  --no-evidence-reason "new protocol text, not a measured claim: no measurement has been taken under P-SERVE-SEL-1; its design is the approved research-intake Stage-3 plan item DAR-LAT-3 (docs/research-intake/orch-prior-art-stage3-plan-20260926.md) and it was ratified by the operator on 2026-09-26 in the orchestrator-design session (OP-62)" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $Q_REL $STAGED_ANNEX_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$APPLIED_AT" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" \
     "$OPERATOR" "$PATCH_SHA256" "$PATCH_REL" "$SCRIPT_REL" "$(sha "$SCRIPT_PATH")" \
     "$STAGED_ANNEX_REL" "$STAGED_ANNEX_SHA256" "$STAGED_SNIPPET_REL" "$STAGED_SNIPPET_SHA256" \
     "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$Q_PRE_SHA256" "$Q_POST_SHA256" <<'PYEOF'
import sys, json, os
(receipt, index, applied_at, gate, consolidated_rel, receipt_rel, operator, patch_sha, patch_rel,
 script_rel, script_sha, annex_rel, annex_sha, snip_rel, snip_sha,
 meas_pre, meas_post, q_pre, q_post) = sys.argv[1:20]
doc = {
  "schema": "epyc.measurement.protocol_amendment.v1",
  "decision": "CREATE-PROTOCOL-P-SERVE-SEL-1",
  "gate_id": gate,
  "operator_decision": "OP-62: ratify P-SERVE-SEL-1 (text-LLM serving-selection load-sweep protocol) before DAR-LAT-3 W1, so the A/B is decision-grade",
  "ratification": {
    "date": "2026-09-26",
    "by": "operator",
    "where": "orchestrator-design session",
    "note": "the decision was given in session on 2026-09-26; this receipt records its application across the human-only boundary",
  },
  "ratified_at": applied_at,
  "applied_at": applied_at,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-SERVE-SEL-1",
  "annex": "Q",
  "annex_path": "measurement/protocols/quality-eval.md",
  "amendment_class": "new protocol (append to the owning annex; no new annex)",
  "registry_status": "✅ 2026-09-26",
  "protocol_summary": {
    "scope": "selection-policy A/B on a single-instance tier that saturates under offered load, TTFT-bound, orchestrator in the loop; instrument_class=serving; specialises P-AB-1 for load",
    "primary_metric": "S = TTFT-SLO attainment per block (higher-better); budget = 2 x unloaded p50 TTFT per prompt-length bucket",
    "arms": "A0 incumbent category=OPTIMUM; candidates category=CANDIDATE; switched per block in one experiment API process, unit = arm",
    "load_points": "rho in {0.5, 0.8, 1.0, 1.25, 1.6, 2.0} x mu_hat; saturating rho >= 1.0; 40 open-loop seeded Poisson arrivals per block; ABBA",
    "floor": "95% upper bound of |dS| over 24 A/A block pairs of the reference candidate arm at rho=1.25, unit = arm, n and interval recorded (FLOOR-UNIT-1)",
    "decision_rule": "gap > F at >=2 saturating rho in W1, same sign and gap > F at rho=1.25 in W2 (>=24 h later, fresh seeds), quality non-inferior (>= -1 per-suite quantum), no rho<1 point worse by more than F; else BOUNDED-NULL-1",
    "intervals": "PAIRED-CI-1 with small-K correction, within a window only; W1 and W2 never pooled",
  },
  "first_consumer": "handoffs/active/decision-aware-routing.md DAR-LAT-3",
  "provenance": "research-intake 2026-09-26 orchestration prior art, Stage-3 plan item DAR-LAT-3/DAR-LAT-3a (docs/research-intake/orch-prior-art-stage3-plan-20260926.md); bundle prepared by Stage-4 agent S4-F",
  "not_granted": "no measurement, compute window or routing-weight flip; the default-weight flip needs its own operator-signed instrument-era row",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "staged_text": {
    "annex": {"path": annex_rel, "sha256": annex_sha},
    "measurement_md_snippets": {"path": snip_rel, "sha256": snip_sha},
  },
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/quality-eval.md": {"sha256_before": q_pre, "sha256_after": q_post},
  },
  "tracking": {"operator_queue": "handoffs/active/master-handoff-index.md OP-62",
               "handoff_task": "handoffs/active/decision-aware-routing.md DAR-LAT-3a"},
  "consolidated_receipt": consolidated_rel,
  "applied_by": {"path": script_rel, "sha256": script_sha},
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify",
               "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}")
print(f"  keyed index:      {index}")
PYEOF
then
  restore; rm -f "$CONSOLIDATED"
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these five paths:"
  say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
  say "    git -C $ROOT commit -m '$COMMIT_SUBJECT'     # only if nothing else is staged in this index"
  say "Then: ROOT=$ROOT bash $SCRIPT_PATH --verify"
  exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""
say "== commit on $BRANCH =="
# A PRIVATE index seeded from HEAD, holding only these five paths: nothing a peer has staged in the
# shared index rides along, and no pathspec commit re-reads the working tree. The staged blobs of
# both targets are re-hashed against the post-state pins before committing.
PIDX="$TMPD/private.index"
MSGF="$TMPD/commit_msg.txt"
cat > "$MSGF" <<EOF
$COMMIT_SUBJECT

Operator decision OP-62: P-SERVE-SEL-1 was ratified by the operator on
2026-09-26 in the orchestrator-design session, and is applied here through
scripts/operator/ratify_p_serve_sel_1_20260926.sh. All pins were verified and
the section-5 consolidated receipt returned RATIFIED.

Annex Q (measurement/protocols/quality-eval.md) gains P-SERVE-SEL-1, the
text-LLM serving-selection load-sweep A/B: selection-policy arms on a
single-instance saturating tier, TTFT-bound, orchestrator in the loop,
instrument_class=serving. The floor comes from 24 A/A block pairs at
unit = arm. The decision rule needs a gap above the floor at >=2 saturating
load points in W1 and a reproduction at rho=1.25 in a holdout window W2.
PAIRED-CI-1 applies within a window only; W1 and W2 are never pooled. A null
is a BOUNDED-NULL-1 statement. MEASUREMENT.md gains the section-2 registry
row (✅ 2026-09-26, Q) and a CHANGELOG entry. Additions only.

First consumer: handoffs/active/decision-aware-routing.md DAR-LAT-3.
Receipts: $RECEIPT_REL,
$CONSOLIDATED_REL, $INDEX_REL.

Operator-applied by $OPERATOR
EOF
commit_manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -F <message>"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD \
  || die "could not seed a private index from HEAD. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_meas="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$MEAS_REL" | sha256sum | awk '{print $1}')"
staged_q="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$Q_REL" | sha256sum | awk '{print $1}')"
if [ "$staged_meas" != "$MEAS_POST_SHA256" ] || [ "$staged_q" != "$Q_POST_SHA256" ]; then
  die "a staged target does not match its post-state pin (MEASUREMENT.md ${staged_meas:0:12}, quality-eval.md ${staged_q:0:12}): something edited it after postflight. NOT committed; the amendment and receipts are applied in the working tree. Inspect: git -C $ROOT diff -- ${TARGETS[*]}"
fi
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -F "$MSGF"; then
  # Bring the checkout's own index up to the new HEAD for OUR five paths only.
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <five paths>' failed; run it by hand so the index matches HEAD."
  sha_c="$(git -C "$ROOT" rev-parse --short HEAD)"
  say "  committed $sha_c on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Check, then publish:"
say "    ROOT=$ROOT bash $SCRIPT_PATH --verify"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
say ""
say "Then the owning session deletes the OP-62 row from handoffs/active/master-handoff-index.md and"
say "records P-SERVE-SEL-1 as landed on DAR-LAT-3a in handoffs/active/decision-aware-routing.md."
