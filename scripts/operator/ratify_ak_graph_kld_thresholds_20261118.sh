#!/bin/bash
# ratify_ak_graph_kld_thresholds_20261118.sh -- ONE operator signature for the AK-FUSE-GRAPH-KLD-1 thresholds.
#
# WHAT YOU ARE SIGNING (operator ruling 2026-11-18, "today's 27B-anchored gate"):
#   GPU: correctness is decided by Qwen3.8-27B Q8_0: mean KLD <= 0.003 and |dPPL| <= 0.5% for the same change.
#        Q38FN (Qwen3.8-Flash-Next UD-IQ4_XS) KLD / PPL are reported only, BUT (operator decision 2026-11-19) the
#        keep is also REFUSED if Q38FN same-top < 93.0%. Q38FN is not served on GPU, so the GPU gate runs it hybrid
#        (-ngl 999 --n-cpu-moe 48, the H13b keep-run recipe) as the test vehicle. Reason: the known-bad H13b replay is
#        clean on the 27B and caught only by Q38FN.
#   CPU: the same 27B clause, plus Q38FN |dPPL| <= 0.5% and top-1 (same-top) >= 93%.
#   |dPPL| = |PPL(cand)/PPL(champion) - 1|, read from llama-perplexity's Mean ln(PPL(Q)/PPL(base)).
#   Corpus wikitext-2 (/mnt/raid0/llm/data/wiki.test.raw), -c 4096 --chunks 16, f16 KV, base logits saved once per champion.
#
#   1. research: writes scripts/kernel_rnd/autokernel/loop/graph_kld_policy.json (the ONLY input that sets these values;
#      without it every graph-fusion keep is refused threshold_unset). The keep-path wiring already landed
#      (gates.graph_kld_keep_check, called from loop/run.py). Runs test_graph_kld_gate.py on the staged tree first.
#   2. root: appends section P-AK-SEARCH-1-A5a to measurement/protocols/kernel-research.md (additions only), with the
#      MEASUREMENT.md section-5 consolidated receipt, the decision receipt and the keyed index.
#
#   Review / dry run (default; full trial in throwaway worktrees, pushes nothing, keeps nothing):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh
#   Sign, commit and push both repos (the OPERATOR runs this):
#     RATIFY_OPERATOR='<your name>' bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh --apply --attest RATIFY-AK-GRAPH-KLD-THRESHOLDS-20261118
#   Same, but commit only (keep both stage worktrees, push nothing):  ... --apply --attest ... --no-push
#   Verify origin/main of both repos (read-only):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh --verify
#
# ratify-targets: measurement/protocols/kernel-research.md
#
# Idempotent: an item already on origin/main is skipped. Research is committed first so the root receipt names it.
# Touches no process and no checkout. ROLLBACK: git revert the printed commits on fresh origin/main worktrees,
# pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root   # run from a copy outside the repo
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"
SCRIPT_REL="scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-ak-graph-kld-thresholds"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-GRAPH-KLD-THRESHOLDS-20261118"
TARGET="measurement/protocols/kernel-research.md"
# Pre-state = kernel-research.md AFTER the P-SERVE-1 Annex K ratification (ratify_p_serve_1_20261119.sh K_POST_SHA256).
# Re-pinned 2026-11-19 (operator: "Re-pin, keep RATIFY prompt"): both amendments append to this file, so this one
# applies second. The original pre-state (before P-SERVE-1) is OLD_PRE_SHA.
OLD_PRE_SHA="c086e4ee9f7bffd3e25f6f88636a780ca0aa1827589bc115a5ddafe749559315"
PRE_SHA="c5bd00d760bb70e1f300930268913b0cb002c6d05fe3712937ae320d5175dc4e"
ANCHOR="## P-AK-SEARCH-1-A5a"
PROTOCOL_ID="P-AK-SEARCH-1-A5a"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_graph_kld_thresholds_20261118.json"
CONSOLIDATED_REL="artifacts/operator/ratify_ak_graph_kld_thresholds_20261118.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
POLICY_REL="scripts/kernel_rnd/autokernel/loop/graph_kld_policy.json"
GATES_REL="scripts/kernel_rnd/autokernel/loop/gates.py"
WIRING_MARK="GRAPH_KLD_POLICY_SCHEMA"

MODE="review"; ATTEST=""; DO_PUSH=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)   MODE="apply" ;;
    --verify)  MODE="verify" ;;
    --no-push) DO_PUSH=0 ;;
    --attest)  shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --attest $GATE_ID [--no-push]]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
ok()  { printf '  ok    %s\n' "$*"; }
g()   { git -c safe.directory='*' -C "$@"; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
for tool in git sha256sum awk diff "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "ROOT=$ROOT is not an epyc-root checkout"
g "$RES" rev-parse --git-dir >/dev/null 2>&1 || die "RES=$RES is not a git checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"

if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply needs the typed confirmation --attest $GATE_ID. Nothing written."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  say "signer: $RATIFY_OPERATOR"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
g "$RES" fetch -q origin main || die "cannot fetch origin main in $RES"
ROOT_BASE="$(g "$ROOT" rev-parse origin/main)"
RES_BASE="$(g "$RES" rev-parse origin/main)"
say "== root origin/main $ROOT_BASE =="
say "== research origin/main $RES_BASE =="

item1_state() { g "$RES" cat-file -e "origin/main:$POLICY_REL" 2>/dev/null && echo already || true; }
item2_state() { g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && echo already || true; }

if [ "$MODE" = "verify" ]; then
  rc=0
  [ "$(item1_state)" = "already" ] && ok "research $POLICY_REL on origin/main" || { say "  FAIL  $POLICY_REL not on research origin/main"; rc=1; }
  if [ "$(item2_state)" = "already" ] && [ "$(g "$ROOT" show "origin/main:$TARGET" | grep -cF -- "$ANCHOR" || true)" -ge 1 ]; then ok "root $TARGET amended + receipts"
  else say "  FAIL  root amendment/receipts not on origin/main"; rc=1; fi
  exit "$rc"
fi

ITEM1="$(item1_state)"; ITEM2="$(item2_state)"
if [ "$ITEM1$ITEM2" = "alreadyalready" ]; then say "ALREADY RATIFIED: both items are on origin/main. Nothing to do."; exit 0; fi
[ "$(g "$RES" show "origin/main:$GATES_REL" | grep -cF -- "$WIRING_MARK" || true)" -ge 1 ] \
  || die "research origin/main lacks the keep-path wiring ($WIRING_MARK in $GATES_REL); the policy file would be read by nothing"

# ---- stage: two detached worktrees
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-graph-kld.XXXXXX")"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$KEEP_STAGE" -eq 0 ]; then
    [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove --force "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
    [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
    rm -f "$STAGE"/pre.json "$STAGE"/before.md
    rmdir "$STAGE" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"; RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"; WT_ADDED=1
ok "staged throwaway worktrees under $STAGE"

# ---- preflight
say "== preflight (mode=$MODE) =="
if [ "$ITEM2" != "already" ]; then
  [ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL exists without the index (half state); not touching it"
  ! grep -qF -- "$ANCHOR" "$WT/$TARGET" || die "$ANCHOR already present without a receipt; reconcile by hand"
  [ "$(sha "$WT/$TARGET")" != "$OLD_PRE_SHA" ] || die "P-SERVE-1 (Annex K) is not on origin/main yet: apply run_p_serve_1_ratify_20261119.sh first (this amendment applies second)"
  [ "$(sha "$WT/$TARGET")" = "$PRE_SHA" ] || die "$TARGET changed since this script was prepared; re-derive, do not overwrite"
  ok "$TARGET at pre-state ${PRE_SHA:0:12}"
  "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 && ok "receipt checker exits 0 before the amendment" \
    || die "receipt checker does not exit 0 before the amendment"
fi

# ---- item 1: research policy file
if [ "$ITEM1" != "already" ]; then
  say "== item 1: research $POLICY_REL =="
  [ ! -e "$RWT/$POLICY_REL" ] || die "$POLICY_REL exists on the stage"
  GATE_ID="$GATE_ID" "$SYS_PY" - "$RWT/$POLICY_REL" <<'PYEOF' || die "could not write the policy file"
import json, os, sys
doc = {
    "schema": "epyc.autokernel.graph_kld_policy.v1",
    "ratification": os.environ["GATE_ID"],
    "ruling": "operator 2026-11-18, amended 2026-11-19: 27B-anchored gate. GPU: 27B Q8_0 KLD <= 0.003 and |dPPL| <= 0.5% decide; Q38FN (run hybrid --n-cpu-moe 48 as the GPU test vehicle) KLD/dPPL reported only but same-top >= 93.0% refuses. CPU: same 27B clause plus Q38FN |dPPL| <= 0.5% and top-1 >= 93%.",
    "protocol": "measurement/protocols/kernel-research.md P-AK-SEARCH-1-A5 / A5a",
    "corpus": "/mnt/raid0/llm/data/wiki.test.raw",
    "chunks": 16,
    "models": {
        "q38_27b": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
        "q38fn": "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
    },
    "backends": {
        "gpu": [
            {"model": "q38_27b", "decisive": True, "max_mean_kld": 0.003, "max_abs_dppl_pct": 0.5},
            {"model": "q38fn", "decisive": True, "min_same_top_pct": 93.0, "n_cpu_moe": 48},
        ],
        "cpu": [
            {"model": "q38_27b", "decisive": True, "max_mean_kld": 0.003, "max_abs_dppl_pct": 0.5},
            {"model": "q38fn", "decisive": True, "max_abs_dppl_pct": 0.5, "min_same_top_pct": 93.0},
        ],
    },
}
with open(sys.argv[1], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2); fh.write("\n")
PYEOF
  cat "$RWT/$POLICY_REL"
  ( cd "$RWT/scripts/kernel_rnd" && "$SYS_PY" -m pytest -q -p no:cacheprovider autokernel/loop/test_graph_kld_gate.py ) \
    || die "test_graph_kld_gate.py fails with the policy file staged. Nothing committed."
  ok "test_graph_kld_gate.py passes with the ratified values (test_shipped_policy_matches_ruling_when_present)"
fi

# ---- item 2: root amendment + consolidated receipt
if [ "$ITEM2" != "already" ]; then
  say "== item 2: exact change to $TARGET =="
  cp "$WT/$TARGET" "$STAGE/before.md"
  "$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" --state "$TARGET" --out "$STAGE/pre.json" \
    || die "could not snapshot the pre-amendment state"
  cat >>"$WT/$TARGET" <<'AMENDEOF'

## P-AK-SEARCH-1-A5a — graph-level KLD thresholds, 27B-anchored (AK-FUSE-GRAPH-KLD-1, RATIFIED 2026-11-18; GPU Q38FN top-1 clause 2026-11-19)

Operator ruling 2026-11-18 (amended 2026-11-19: GPU Q38FN-hybrid top-1 clause) sets the values A5 left unset. A keep candidate that touches graph-fusion,
ggml-alloc or graph-matcher files (`gates.touches_graph_fusion`) passes the graph-level gate only if:

- **GPU:** Qwen3.8-27B Q8_0 decides: mean KLD <= 0.003 and |dPPL| <= 0.5% for the same change.
  Q38FN (Qwen3.8-Flash-Next UD-IQ4_XS) KLD and PPL are reported only; **amended by operator decision
  2026-11-19:** the keep is also refused if Q38FN top-1 (same-top) < 93.0%. Q38FN is not served on GPU, so
  the GPU gate runs it hybrid (`-ngl 999 --n-cpu-moe 48`, the H13b keep-run recipe) as the test vehicle.
  Reason: the known-bad H13b replay is clean on the 27B and caught only by Q38FN. The 27B still decides
  KLD and dPPL.
- **CPU:** the same 27B clause, plus Q38FN |dPPL| <= 0.5% and top-1 (same-top) >= 93%.

|dPPL| is |PPL(candidate)/PPL(champion) - 1|, from llama-perplexity's mean ln(PPL(Q)/PPL(base)). The
measurement is the A5 one: wikitext-2, `-c 4096 --chunks 16`, f16 KV, the champion's base logits saved once
per champion commit, each binary on its own build's libraries.

The values live in research `scripts/kernel_rnd/autokernel/loop/graph_kld_policy.json`, written by this
ratification; that file is their only input, and changing it needs a new operator amendment. A missing or
malformed policy, an unparsed decisive metric, or a decisive clause without a limit refuses the keep
(`threshold_unset` / `kld_unparsed`); a failed run is `oracle_unavailable`. Neither is a pass. The known-bad
C7/H13b Q38FN replay (KLD 0.1865, same-top 88.6%) fails the Q38FN top-1 clause on both CPU and GPU.

Enforcement: `gates.graph_kld_keep_check` is called from the correctness gate in `loop/run.py` for every
graph-fusion candidate on both legs, and every promoted champion builds `llama-perplexity`. This supersedes
A5's "Enforcement state at ratification" paragraph.
AMENDEOF
  diff -u --label "a/$TARGET" --label "b/$TARGET" "$STAGE/before.md" "$WT/$TARGET" || true
  removed="$(diff "$STAGE/before.md" "$WT/$TARGET" | grep -c '^<' || true)"
  [ "$removed" -eq 0 ] || die "postflight: $removed lines removed; additions only expected"
  [ "$(grep -cF -- "$ANCHOR" "$WT/$TARGET")" -eq 1 ] || die "postflight: the amendment heading must occur exactly once"
  ok "additions only (0 lines removed); heading once"
  say "== MEASUREMENT.md section-5 consolidated receipt =="
  "$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
    --repo-root "$WT" --pre "$STAGE/pre.json" \
    --protocol-id "$PROTOCOL_ID" --anchor "$ANCHOR" \
    --ratification-id "$GATE_ID" --script "$SCRIPT_PATH" \
    --operator "${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
    --no-evidence-reason "operator-chosen thresholds (ruling 2026-11-18, amended 2026-11-19), not a measured claim; the gate's own runs are the evidence per keep" \
    --validation "grep -qF 'P-AK-SEARCH-1-A5a' $TARGET" \
    --out "$WT/$CONSOLIDATED_REL" || die "consolidated receipt refused. Nothing committed."
  ok "consolidated receipt: $CONSOLIDATED_REL"
fi

COMMIT_PATHS=("$TARGET" "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")
if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: all checks passed in throwaway worktrees. Nothing committed, pushed or kept."
  say "  item 1 (research policy): ${ITEM1:-would apply}"
  say "  item 2 (root amendment):  ${ITEM2:-would apply}"
  say "Sign with ONE command:"
  say "  RATIFY_OPERATOR='<your name>' bash $SCRIPT_PATH --apply --attest $GATE_ID"
  exit 0
fi

push_main() {  # repo-for-lock worktree  (retrying, rebasing, never forced: lib/push_retry.sh)
  local lib; lib="$(dirname "$SCRIPT_PATH")/lib/push_retry.sh"; [ -f "$lib" ] || lib="$ROOT/scripts/operator/lib/push_retry.sh"
  # shellcheck source=/dev/null
  source "$lib"
  ratify_push_main_retry "$1" "$2" "$LOCK_AGENT" "$PUSHER" "$STAGE" \
    || die "push of $2 refused or failed after retries (see above). Nothing forced; re-run, applied items are skipped."
}

# ---- research commit (+ push)
RES_COMMIT="$RES_BASE"
if [ "$ITEM1" != "already" ]; then
  g "$RWT" add -- "$POLICY_REL"
  [ "$(g "$RWT" diff --cached --name-only HEAD)" = "$POLICY_REL" ] || die "research index holds an unexpected path set"
  g "$RWT" commit -q -m "autokernel: graph_kld_policy.json, $GATE_ID (signed by $RATIFY_OPERATOR)" \
    -m "AK-FUSE-GRAPH-KLD-1 thresholds per operator ruling 2026-11-18: GPU 27B Q8_0 KLD <= 0.003 and |dPPL| <= 0.5% decide, Q38FN KLD/dPPL report-only but Q38FN hybrid same-top >= 93.0% refuses (2026-11-19); CPU adds Q38FN |dPPL| <= 0.5% and top-1 >= 93%." \
    -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
  RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
  if [ "$DO_PUSH" -eq 1 ]; then
    say "== push research main =="
    push_main "$RES" "$RWT"; RES_COMMIT="$RATIFY_PUSHED_SHA"
    g "$RES" fetch -q origin main
    g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
    ok "research main $RES_COMMIT"
  fi
fi

# ---- root receipts + commit (+ push)
ROOT_COMMIT=""
if [ "$ITEM2" != "already" ]; then
  RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" \
  TARGET="$TARGET" PRE="$PRE_SHA" POST="$(sha "$WT/$TARGET")" OPERATOR="$RATIFY_OPERATOR" TS="$RATIFIED_AT" BASE="$ROOT_BASE" \
  RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" POLICY_REL="$POLICY_REL" \
  "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Root not committed; re-run."
import json, os
e = os.environ
doc = {
    "schema": "epyc.operator_ratification.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {
        "1": "2026-11-18 AK-FUSE-GRAPH-KLD-1: today's 27B-anchored gate as the thresholds (GPU: 27B Q8_0 KLD <= 0.003, |dPPL| <= 0.5%; Q38FN KLD/dPPL report-only. CPU: same plus Q38FN |dPPL| <= 0.5%, top-1 >= 93%)",
        "2": "2026-11-19 amendment: GPU additionally refuses if Q38FN (hybrid --n-cpu-moe 48 test vehicle) same-top < 93.0%; the known-bad H13b replay is clean on the 27B and caught only by Q38FN",
    },
    "items": {
        "1": f"research {e['POLICY_REL']} (the only threshold input of gates.graph_kld_keep_check)",
        "2": "measurement/protocols/kernel-research.md section P-AK-SEARCH-1-A5a (additions only)",
    },
    "base_origin_main": e["BASE"],
    "research_commit": e["RES_COMMIT"],
    "consolidated_receipt": e["CONSOLIDATED_REL"],
    "state": {e["TARGET"]: {"sha256_before": e["PRE"], "sha256_after": e["POST"]}},
    "applied_by": e["SCRIPT_REL"],
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "processes_touched": [],
}
wt = e["WT"]
with open(os.path.join(wt, e["RECEIPT_REL"]), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(wt, e["INDEX_REL"])), exist_ok=True)
with open(os.path.join(wt, e["INDEX_REL"]), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "ratify", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n")
PYEOF
  "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 || die "receipt checker fails after the amendment. Root not committed."
  ok "receipt checker exits 0 after the amendment"
  g "$WT" add -- "${COMMIT_PATHS[@]}"
  staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
  want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
  [ "$staged" = "$want" ] || die "root index holds an unexpected path set; not committed: $(echo $staged)"
  g "$WT" commit -q -m "RATIFIED $GATE_ID: AK-FUSE-GRAPH-KLD-1 27B-anchored thresholds, P-AK-SEARCH-1-A5a (signed by $RATIFY_OPERATOR)" \
    -m "Research commit: $RES_COMMIT ($POLICY_REL). Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
    -m "Operator-Ratified: yes" || die "root commit failed (hook?); re-run."
  ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"; ok "root committed ${ROOT_COMMIT:0:12}"
  if [ "$DO_PUSH" -eq 1 ]; then
    say "== push root main =="
    push_main "$ROOT" "$WT"; ROOT_COMMIT="$RATIFY_PUSHED_SHA"
    g "$ROOT" fetch -q origin main
    g "$ROOT" merge-base --is-ancestor "$ROOT_COMMIT" origin/main || die "root $ROOT_COMMIT is not on origin/main after fetch"
  fi
fi

if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): research $RES_COMMIT in $RWT, root ${ROOT_COMMIT:-none} in $WT"
  say "Remove the stage afterwards: git -C $RES worktree remove --force $RWT; git -C $ROOT worktree remove --force $WT"
  exit 0
fi
cat <<REPORT

RATIFIED $GATE_ID by $RATIFY_OPERATOR.
  research main: $RES_COMMIT
  root main:     ${ROOT_COMMIT:-already applied}
NO PROCESS WAS TOUCHED.  VERIFY (read-only): bash $SCRIPT_PATH --verify
ROLLBACK (operator): git revert the commits above on fresh origin/main worktrees, then push through serialized_push.py.
REPORT
