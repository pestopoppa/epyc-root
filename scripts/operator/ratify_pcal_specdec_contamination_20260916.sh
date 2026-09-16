#!/bin/bash
# ratify_pcal_specdec_contamination_20260916.sh — P-CAL (Annex Q) calibration baselines are
# contaminated by speculative decoding, so their decision uses are suspended pending EV-CONF-2.
#
#   Review (default, writes nothing):  bash scripts/operator/ratify_pcal_specdec_contamination_20260916.sh
#   Apply + receipts (no commit):      bash scripts/operator/ratify_pcal_specdec_contamination_20260916.sh --apply
#   Commit:                            printed by --apply
#
# OPERATOR DECISION 2026-09-16, OPTION (a): caveat the E7c and EV-4c calibration numbers in P-CAL
# now, rather than wait for the EV-CONF-2 GPU probe.
#
# THE DEFECT. All four P-CAL baselines were captured on `draft-mtp` servers. For every
# draft-accepted token, llama.cpp (v7 and v9) reports prob=1.0 with an empty top-k. The
# completion-probability geomean that P-CAL uses as "confidence" therefore averages placeholders,
# not model probabilities, over an unmeasured share of every answer.
#   E7c math   (worker_general / worker_math, gemma-4-26B-A4B MTP draft_max=2)
#              ECE 0.2114/0.2199, AUROC 0.4013/0.4114. SATURATED: 1528/1684 and 1485/1628 rows
#              have confidence >= 0.999999, so the numbers are INVALID as calibration.
#   EV-4c code (frontdoor Qwen3.6-35B-A3B-MTP draft_max=4, worker_general gemma MTP)
#              ECE 0.2532/0.3216, AUROC 0.6337/0.5751. Not saturated (0/820, 2/817), so the
#              contamination is real but its size is unmeasured.
# P-CAL grants two decision uses on the EV-4c numbers: (a) rlvr_tiers RLVR code-reward
# calibration, and (b) EV-5/EV-7 verifier promotion. Both are gating on a contaminated instrument.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/pcal-specdec-contamination-20260916.patch)
#   measurement/protocols/quality-eval.md
#     - P-CAL heading gains "decision uses SUSPENDED 2026-09-16"
#     - a new first bullet in P-CAL:
#       - marks each baseline CONTAMINATED: E7c INVALID; EV-4c demoted-to-prior, size unmeasured
#       - suspends both decision uses, plus the math cross-arm ECE check, until EV-CONF-2 reports
#       - states the standing re-baseline rule: confidence metrics are admissible only from
#         spec-off runs, or with placeholder tokens excluded and the excluded share reported
#       - states the lift condition, which is a further human amendment
#       - cites the evidence
#       - notes that P-PAIRED is unaffected
#   MEASUREMENT.md
#     - the section-2 P-CAL status cell gains the suspension marker
#     - a 2026-09-16 CHANGELOG entry (required by section 5)
#
# WHAT IT DOES NOT DO. It deletes and edits no historical number: the Baselines bullet is
# byte-identical afterwards. It changes no code, no threshold and no other protocol. It does not
# touch coordination/session-bus/human_only_paths.yaml, so that file's .sha256 pin needs no update.
# Nothing here starts a process, takes compute or touches the network.
#
# EVIDENCE
#   epyc-orchestrator b98dee18  per-token trace; placeholder tokens stored as a sentinel and counted
#   epyc-orchestrator f2e9ee07  EV-CONF-2 probe driver; the spec-off arm fails closed on a draft
#   Both were unmerged review branches (sub/evconf2-20260916, sub/evconf2-probe-20260916) when
#   this was prepared.
#   Sidecars, which carry the saturation counts:
#     epyc-orchestrator orchestration/reports/eval_tower_math_rebaseline_E7c/question_results.ev11-*.jsonl
#     epyc-orchestrator orchestration/reports/eval_tower_calibration_baseline_HE-R+/*_ev4c/question_results.*.jsonl
#   Probe spec: the EV-CONF-2 box in handoffs/active/autopilot-decision-plane-audit-2026-07-22.md
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml). An agent prepared this bundle. Only the
# operator applies it.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or
# fuzz it.
#   patch                                   2fb3402ea2bf62e7d788b8f795dd6acc2589a9a19dee7f66331b04024791a294
#   MEASUREMENT.md             pre-state    45c7e3a31ccc7c453d66b00124011a5bbbf9f44eaa90510d4cb3f75a1ae49dec
#   MEASUREMENT.md             post-state   9659d8c3bf66a06a215f7c2c5e5d6fd8eefe5e3f2c15d9656f0c8648bb720c4a
#   protocols/quality-eval.md  pre-state    94a2726f1e5327c20854b574e22be4834d47866ca7a3350865873ed3b365ebff
#   protocols/quality-eval.md  post-state   dac23d84aa0ed801d543af807a8cf9f019e2aa14356a530d58749c49989fe566
# The pre-state pins are origin/main 8abf6984b. A stale checkout (the shared clone lagged
# origin/main by 388 commits on 2026-09-16) is refused for the same reason: fast-forward or merge
# first.
#
# IDEMPOTENT. When both targets sit at their post-state pins and the decision receipt exists, a
# re-run prints ALREADY RATIFIED and exits 0 without writing. Every other partial state is refused
# and left for resolution by hand.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"

PATCH_REL="artifacts/operator/pcal-specdec-contamination-20260916.patch"
PATCH="${PATCH:-$ROOT/$PATCH_REL}"
MEAS_REL="MEASUREMENT.md"
QE_REL="measurement/protocols/quality-eval.md"
TARGETS=("$MEAS_REL" "$QE_REL")
GATE_ID="RATIFY-P-CAL-SPECDEC-20260916"
RECEIPT_REL="artifacts/operator/ratify_pcal_specdec_contamination_20260916.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_pcal_specdec_contamination_20260916.receipt.json"
# Kept beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"

PATCH_SHA256="2fb3402ea2bf62e7d788b8f795dd6acc2589a9a19dee7f66331b04024791a294"
MEAS_PRE_SHA256="45c7e3a31ccc7c453d66b00124011a5bbbf9f44eaa90510d4cb3f75a1ae49dec"
MEAS_POST_SHA256="9659d8c3bf66a06a215f7c2c5e5d6fd8eefe5e3f2c15d9656f0c8648bb720c4a"
QE_PRE_SHA256="94a2726f1e5327c20854b574e22be4834d47866ca7a3350865873ed3b365ebff"
QE_POST_SHA256="dac23d84aa0ed801d543af807a8cf9f019e2aa14356a530d58749c49989fe566"

ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
EVIDENCE_FILES=(
  "$ORCH/orchestration/reports/eval_tower_math_rebaseline_E7c/question_results.ev11-worker_general.jsonl"
  "$ORCH/orchestration/reports/eval_tower_math_rebaseline_E7c/question_results.ev11-worker_math.jsonl"
  "$ORCH/orchestration/reports/eval_tower_calibration_baseline_HE-R+/frontdoor_ev4c/question_results.cal-frontdoor.jsonl"
  "$ORCH/orchestration/reports/eval_tower_calibration_baseline_HE-R+/worker_general_ev4c/question_results.cal-worker_general.jsonl"
)

MODE="dry-run"
case "${1:-}" in
  ""|--dry-run) MODE="dry-run" ;;
  --apply)      MODE="apply" ;;
  *) echo "usage: $0 [--dry-run | --apply]   (default: --dry-run, writes nothing)" >&2; exit 64 ;;
esac
[ $# -le 1 ] || { echo "usage: $0 [--dry-run | --apply]" >&2; exit 64; }

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for t in "${TARGETS[@]}"; do [ -f "$ROOT/$t" ] || die "$t not found under ROOT=$ROOT"; done
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

# ---------------------------------------------------------------- patch pin
[ -f "$PATCH" ] || die "patch not found at $PATCH"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."

# ---------------------------------------------------------------- idempotence / partial states
meas_now="$(sha "$ROOT/$MEAS_REL")"
qe_now="$(sha "$ROOT/$QE_REL")"
meas_post=0; [ "$meas_now" = "$MEAS_POST_SHA256" ] && meas_post=1
qe_post=0;   [ "$qe_now"   = "$QE_POST_SHA256"   ] && qe_post=1
if [ "$meas_post" -eq 1 ] && [ "$qe_post" -eq 1 ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: both targets are amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
if [ "$meas_post" -ne "$qe_post" ]; then
  die "half-applied state: MEASUREMENT.md post=$meas_post, quality-eval.md post=$qe_post. Resolve by hand."
fi
[ -f "$RECEIPT" ]      && die "$RECEIPT_REL already exists, but the targets are not amended. Resolve by hand."
[ -f "$INDEX" ]        && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE) =="
fail=0
pin() { # pin <label> <expected> <found>
  if [ "$2" != "$3" ]; then
    printf '  FAIL  %-44s expected %s\n        %-44s found    %s\n' "$1" "$2" "" "$3"; fail=1
  else
    printf '  ok    %-44s (%s)\n' "$1" "${3:0:12}"
  fi
}
printf '  ok    %-44s (%s)\n' "patch hash" "${PATCH_SHA256:0:12}"
pin "MEASUREMENT.md pre-state hash" "$MEAS_PRE_SHA256" "$meas_now"
pin "quality-eval.md pre-state hash" "$QE_PRE_SHA256" "$qe_now"

# The targets must carry no unrelated edits, or a commit would sweep a peer session's hunk into
# this amendment (shared-clone hazard).
dirty="$(git -C "$ROOT" status --porcelain -- "${TARGETS[@]}" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-44s\n%s\n' "targets clean in git" "$dirty"; fail=1
else printf '  ok    %-44s\n' "targets clean in git"; fi

if git -C "$ROOT" apply --check "$PATCH" 2>/dev/null; then
  printf '  ok    %-44s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-44s\n' "patch applies cleanly (no fuzz)"; fail=1
fi

ev_missing=0
for f in "${EVIDENCE_FILES[@]}"; do [ -f "$f" ] || { printf '  FAIL  evidence missing: %s\n' "$f"; ev_missing=1; }; done
if [ "$ev_missing" -eq 0 ]; then printf '  ok    %-44s (%d files)\n' "evidence sidecars present" "${#EVIDENCE_FILES[@]}"; else fail=1; fi
for c in b98dee18 f2e9ee07; do
  if git -C "$ORCH" cat-file -e "$c^{commit}" 2>/dev/null; then printf '  ok    %-44s\n' "orchestrator commit $c resolvable"
  else printf '  FAIL  %-44s\n' "orchestrator commit $c resolvable"; fail=1; fi
done

if [ "$fail" -ne 0 ]; then
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (origin/main 8abf6984b). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "DRY RUN: would apply the diff above to ${TARGETS[*]} (post-state pins ${MEAS_POST_SHA256:0:12} / ${QE_POST_SHA256:0:12}),"
  say "then write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL. Nothing written."
  say "Apply with: ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$MEAS_REL" "$TMPD/MEASUREMENT.md.bak"
cp "$ROOT/$QE_REL"   "$TMPD/quality-eval.md.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL"
  cp "$TMPD/quality-eval.md.bak" "$ROOT/$QE_REL"
  rm -f "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --state "$QE_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"

# Working tree only, never --index. Staging is done by hand, after reading the diff.
git -C "$ROOT" apply "$PATCH" || { restore; die "git apply failed; targets restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pin_pf() { if [ "$2" != "$3" ]; then printf '  FAIL  %-44s expected %s found %s\n' "$1" "$2" "$3"; pf=1
           else printf '  ok    %-44s (%s)\n' "$1" "${3:0:12}"; fi; }
pin_pf "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$(sha "$ROOT/$MEAS_REL")"
pin_pf "quality-eval.md post-state hash" "$QE_POST_SHA256" "$(sha "$ROOT/$QE_REL")"
# No historical number may be deleted: the original P-CAL Baselines bullet must survive verbatim.
if python3 - "$TMPD/quality-eval.md.bak" "$ROOT/$QE_REL" "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL" <<'PYEOF'
import sys, difflib
ok = True
allowed = {
    "## P-CAL — Verifier/answer calibration (ECE / AUROC) [added 2026-07-23]",
    "| P-CAL | Verifier/answer calibration | ECE (↓) / AUROC (↑) | ✅ 2026-07-23 | Q |",
}
for a_path, b_path in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    a = open(a_path, encoding="utf-8").read().split("\n")
    b = open(b_path, encoding="utf-8").read().split("\n")
    removed = [l[1:] for l in difflib.unified_diff(a, b, lineterm="", n=0)
               if l.startswith("-") and not l.startswith("---")]
    for line in removed:
        if line not in allowed:
            print(f"  FAIL  unexpected removed line: {line[:90]!r}"); ok = False
    if len(removed) > 1:
        print(f"  FAIL  {b_path}: {len(removed)} lines rewritten, at most 1 expected"); ok = False
qe = open(sys.argv[2], encoding="utf-8").read()
for needle in ("code ECE 0.2532/0.3216, AUROC 0.6337/0.5751 (frontdoor/",
               "math ECE 0.2114/0.2199, AUROC 0.4013/0.4114 observation-only"):
    if qe.count(needle) != 1:
        print(f"  FAIL  historical baseline text not preserved: {needle!r}"); ok = False
if ok:
    print("  ok    additions only; one status line rewritten per file; baselines preserved")
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
ev_args=()
for f in "${EVIDENCE_FILES[@]}"; do ev_args+=(--evidence "$f"); done
receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-CAL \
  --anchor '| P-CAL | Verifier/answer calibration | ECE (↓) / AUROC (↑) | ✅ 2026-07-23 · ⚠️ decision uses SUSPENDED 2026-09-16' \
  --anchor '- **2026-09-16 (v2.x)** — AMENDMENT (Annex Q, `P-CAL`): all four calibration baselines are marked' \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  "${ev_args[@]}" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $QE_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#$ROOT/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$PATCH_SHA256" \
     "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$QE_PRE_SHA256" "$QE_POST_SHA256" <<'PYEOF'
import sys, json, os
(receipt, index, ts, gate, consolidated_rel, receipt_rel, operator, patch_sha,
 meas_pre, meas_post, qe_pre, qe_post) = sys.argv[1:13]
doc = {
  "schema": "epyc.measurement.protocol_amendment.v1",
  "decision": "PCAL-SPECDEC-CONTAMINATION-SUSPEND",
  "gate_id": gate,
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-CAL",
  "annex": "Q",
  "operator_decision": "2026-09-16 option (a): caveat now, do not wait for the EV-CONF-2 GPU probe",
  "patch": {"path": "artifacts/operator/pcal-specdec-contamination-20260916.patch", "sha256": patch_sha},
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/quality-eval.md": {"sha256_before": qe_pre, "sha256_after": qe_post},
  },
  "values": [
    {"run": "E7c", "domain": "math", "arms": "worker_general/worker_math",
     "ece": [0.2114, 0.2199], "auroc": [0.4013, 0.4114],
     "saturated_rows": ["1528/1684", "1485/1628"], "verdict": "CONTAMINATED-INVALID"},
    {"run": "EV-4c", "domain": "code", "arms": "frontdoor/worker_general",
     "ece": [0.2532, 0.3216], "auroc": [0.6337, 0.5751],
     "saturated_rows": ["0/820", "2/817"], "verdict": "CONTAMINATED-UNMEASURED-DEMOTED-TO-PRIOR"},
  ],
  "suspended_uses": ["rlvr_tiers RLVR code-reward calibration/discrimination",
                     "EV-5/EV-7 verifier promotion gate",
                     "math cross-arm ECE stability check"],
  "rebaseline_rule": "confidence metrics admissible only from spec-off runs, or with draft-accepted placeholder tokens excluded and the excluded share reported",
  "lift_condition": "EV-CONF-2 (spec-off GPU probe) reports; lifting is a further human amendment",
  "historical_numbers": "preserved verbatim; nothing deleted or edited",
  "evidence": {
    "mechanism": "llama.cpp v7/v9 reports prob=1.0 with empty top-k for draft-accepted tokens",
    "orchestrator_commits": {"b98dee18": "token_confidence per-token trace + placeholder sentinel (branch sub/evconf2-20260916)",
                             "f2e9ee07": "EV-CONF-2 probe driver, spec-off fail-closed (branch sub/evconf2-probe-20260916)"},
    "probe_spec": "handoffs/active/autopilot-decision-plane-audit-2026-07-22.md (EV-CONF-2 box)",
  },
  "consolidated_receipt": consolidated_rel,
  "applied_by": "scripts/operator/ratify_pcal_specdec_contamination_20260916.sh",
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2); fh.write("\n")
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

COMMIT_PATHS=("$MEAS_REL" "$QE_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
say ""
say "APPLIED, NOT STAGED, NOT COMMITTED. Review, then commit exactly these five paths"
say "(preflight verified they were clean, so adding them whole takes no peer hunk):"
say ""
say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
say "    git -C $ROOT diff --cached --stat"
say "    git -C $ROOT commit -m 'RATIFIED: P-CAL calibration baselines contaminated by speculative decoding; decision uses suspended pending EV-CONF-2 (2026-09-16, option a)' -- ${COMMIT_PATHS[*]}"
say ""
say "Then tick VB-EVCONF2-CAVEAT (handoffs/active/vidya-belief-substrate-program.md) and note the"
say "suspension on the EV-CONF-2 box in handoffs/active/autopilot-decision-plane-audit-2026-07-22.md."
