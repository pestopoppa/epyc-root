#!/bin/bash
# run_ak_c9_ratify_20261109.sh -- ONE operator signature (RATIFY-AK-C9-20261109) over three AutoKernel items.
#
# WHAT YOU ARE SIGNING
#   1. AK-FUSE-GRAPH-KLD-1 keep-path rule. Adds section P-AK-SEARCH-1-A5 to measurement/protocols/kernel-research.md:
#      a keep whose patch touches graph-fusion, ggml-alloc or graph-matcher files must pass graph_kld_gate against
#      the champion's saved base logits. It sets NO numbers: K and S stay unset, so the verdict is threshold_unset (a
#      refusal). It also records that the gate is NOT yet called from the keep path, so nothing is enforced until
#      that wiring lands.
#   2. Countersign of the 35 AutoKernel regrowth-review exceptions in research loop_code_budget_baseline.json
#      (commit 77ee71532): "operator countersign pending" becomes this ratification's reference. Ceilings unchanged.
#   3. Planner-only budget, conditional. Sets exception ceilings planner_only.py 167 and run.py 6909 and merges
#      ak/planner-only-20261109 (0358db7a3) into research main, ONLY if that branch's tests pass on the merge.
#      If they fail, or the merge conflicts, item 3 is skipped entirely (no merge, no entries) and items 1-2 proceed.
#      NOTE: at preparation, run.py on the merged tree counted 6910 lines, one over the 6909 you are asked to sign,
#      so run.py would stay red on the regrowth guard by 1. The review below prints the live count.
#   NOT included: the 13 unraised overrun files (serving.py etc.); they need separate review.
#
#   Review / dry run (default; everything happens in throwaway worktrees, nothing is pushed or kept):
#     bash /mnt/raid0/llm/worktrees/ak-ratify-20261109/scripts/operator/run_ak_c9_ratify_20261109.sh
#   Sign, commit and push both repos (the OPERATOR runs this, from a real terminal; it asks you to type RATIFY):
#     bash /mnt/raid0/llm/worktrees/ak-ratify-20261109/scripts/operator/run_ak_c9_ratify_20261109.sh --apply --operator '<your name>'
#   Verify origin/main of both repos (read-only):
#     bash /mnt/raid0/llm/worktrees/ak-ratify-20261109/scripts/operator/run_ak_c9_ratify_20261109.sh --verify
#
# ratify-targets: measurement/protocols/kernel-research.md
#
# Idempotent: an item already on origin/main reports "already applied" and is skipped; re-run after any failure.
# Research is committed first, so the root receipt records its commit. Touches no process and no checkout.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="/mnt/raid0/llm/epyc-root"
RES="/mnt/raid0/llm/epyc-inference-research"
STAGE_PARENT="/mnt/raid0/llm/tmp"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-C9-20261109"
LOCK_AGENT="operator-ratify-ak-c9"
SCRIPT_REL="scripts/operator/run_ak_c9_ratify_20261109.sh"
TARGET="measurement/protocols/kernel-research.md"
PRE_SHA="f4223c738e5aa6ba75134fa78e2c558e9cefe40f49967fe4de7f505487173c75"
ANCHOR="## P-AK-SEARCH-1-A5"
RECEIPT_REL="artifacts/operator/ratify_ak_c9_20261109.json"
CONSOLIDATED_REL="artifacts/operator/ratify_ak_c9_20261109.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
BASELINE="scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json"
BASELINE_PRE_SHA="9d8b0166b131bce539e5139be6d1c1ab2ff234f54a1b12f0f54aaea0eae518c6"
PLANNER_BRANCH="ak/planner-only-20261109"
PLANNER_SHA="0358db7a3"
PLANNER_TEST="scripts/kernel_rnd/autokernel/loop/test_planner_only.py"
CEIL_PLANNER=167
CEIL_RUN=6909
REF="operator countersign $GATE_ID (epyc-root $RECEIPT_REL)"

MODE="review"; OPERATOR=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review"; shift ;;
    --apply)    MODE="apply"; shift ;;
    --verify)   MODE="verify"; shift ;;
    --operator) [ "$#" -ge 2 ] || { echo "--operator needs a name" >&2; exit 64; }; OPERATOR="$2"; shift 2 ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --operator <name>]" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf '\nREFUSING: %s\n' "$*" >&2; exit 65; }
ok()  { printf '  ok    %s\n' "$*"; }
g()   { git -c safe.directory='*' -C "$@"; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
for tool in git sha256sum awk diff "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "$ROOT is not an epyc-root checkout"
g "$RES" rev-parse --git-dir >/dev/null 2>&1 || die "$RES is not a git checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"

if [ "$MODE" = "apply" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator "$OPERATOR"; OPERATOR="$RATIFY_OPERATOR"
  say "signer: $OPERATOR"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
g "$RES" fetch -q origin main || die "cannot fetch origin main in $RES"
ROOT_BASE="$(g "$ROOT" rev-parse origin/main)"
RES_BASE="$(g "$RES" rev-parse origin/main)"
say "== root origin/main $ROOT_BASE =="
say "== research origin/main $RES_BASE =="

# Each item's state on origin/main (empty, or "already").
item1_state() { g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && echo already || true; }
baseline_on_main() { g "$RES" show "origin/main:$BASELINE"; }
item2_state() { local out; out="$(baseline_on_main)"; grep -q 'operator countersign pending' <<<"$out" || echo already; }
item3_state() {
  if g "$RES" merge-base --is-ancestor "$PLANNER_SHA" origin/main \
     && baseline_on_main | "$SYS_PY" -c "
import json,sys
e=json.load(sys.stdin)['exceptions']
sys.exit(0 if e.get('planner_only.py',{}).get('ceiling')==$CEIL_PLANNER and e.get('run.py',{}).get('ceiling')==$CEIL_RUN else 1)"; then
    echo already
  fi
}

if [ "$MODE" = "verify" ]; then
  rc=0
  for i in 1 2 3; do
    if [ "$("item${i}_state")" = "already" ]; then ok "item $i on origin/main"; else say "  FAIL  item $i not on origin/main"; rc=1; fi
  done
  exit "$rc"
fi

ITEM1="$(item1_state)"; ITEM2="$(item2_state)"; ITEM3="$(item3_state)"
if [ "$ITEM1$ITEM2$ITEM3" = "alreadyalreadyalready" ]; then
  say "ALREADY RATIFIED: all three items are on origin/main. Nothing to do."; exit 0
fi

# ---- throwaway stage: two detached worktrees, removed on exit
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-c9.XXXXXX")"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0
cleanup() {
  local rc=$?
  [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove --force "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
  [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
  rm -f "$STAGE"/pre.json "$STAGE"/before.md "$STAGE"/baseline.before "$STAGE"/guard.out
  rmdir "$STAGE" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"
RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"
WT_ADDED=1
ok "staged throwaway worktrees under $STAGE"

# ---- preflight
say "== preflight (mode=$MODE) =="
if [ "$ITEM1" != "already" ]; then
  [ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL exists without the index (half state); not touching it"
  ! grep -qF -- "$ANCHOR" "$WT/$TARGET" || die "$ANCHOR already present without a receipt; reconcile by hand"
  [ "$(sha "$WT/$TARGET")" = "$PRE_SHA" ] || die "$TARGET changed since this script was prepared; re-derive, do not overwrite"
  ok "$TARGET at pre-state ${PRE_SHA:0:12}"
fi
if [ "$ITEM2" != "already" ] && [ "$ITEM3" != "already" ]; then
  [ "$(sha "$RWT/$BASELINE")" = "$BASELINE_PRE_SHA" ] || die "$BASELINE changed since this script was prepared; re-derive, do not overwrite"
  ok "baseline at pre-state ${BASELINE_PRE_SHA:0:12}"
fi

# ---- item 3 eligibility: the merge, then the branch's own tests on the merged tree
DO_ITEM3=0
if [ "$ITEM3" = "already" ]; then
  say "item 3: already applied"
else
  say "== item 3: merge $PLANNER_BRANCH ($PLANNER_SHA) and test =="
  tip="$(g "$RES" rev-parse "refs/heads/$PLANNER_BRANCH")" || die "branch $PLANNER_BRANCH not found"
  case "$tip" in "$PLANNER_SHA"*) ok "branch tip is $PLANNER_SHA" ;; *) die "$PLANNER_BRANCH moved to $tip; the signed commit is $PLANNER_SHA" ;; esac
  if g "$RWT" merge --no-ff --no-commit "$PLANNER_SHA" >/dev/null 2>&1; then
    trc=0
    ( cd "$RWT" && EPYC_ROOT="$WT" "$SYS_PY" -m pytest -q "$PLANNER_TEST" ) || trc=$?
    if [ "$trc" -eq 0 ]; then
      DO_ITEM3=1; ok "$PLANNER_TEST passed on the merged tree"
    else
      g "$RWT" merge --abort
      say "ITEM 3 STOPPED: tests failed (exit $trc). No merge, no budget entries. Items 1-2 continue."
    fi
  else
    g "$RWT" merge --abort 2>/dev/null || true
    say "ITEM 3 STOPPED: the merge conflicts. No merge, no budget entries. Items 1-2 continue."
  fi
fi

# ---- items 2 and 3: baseline edit
if [ "$MODE" = "apply" ] && [ "$DO_ITEM3" -eq 1 ]; then
  g "$RWT" commit -q -m "merge $PLANNER_BRANCH ($PLANNER_SHA), tests passed ($GATE_ID item 3, signed by $OPERATOR)" \
    || die "merge commit failed (hook?). Nothing pushed; re-run."
fi
if [ "$ITEM2" != "already" ] || [ "$DO_ITEM3" -eq 1 ]; then
  cp "$RWT/$BASELINE" "$STAGE/baseline.before"
  DO2=1; [ "$ITEM2" != "already" ] || DO2=0
  "$SYS_PY" - "$RWT/$BASELINE" "$DO2" "$DO_ITEM3" "$REF" "$GATE_ID" "$PLANNER_SHA" "$CEIL_PLANNER" "$CEIL_RUN" <<'PYEOF' || die "baseline transform refused. Nothing committed."
import json, sys
path, do2, do3, ref, gate, planner, ceil_p, ceil_r = sys.argv[1:]
do2, do3, ceil_p, ceil_r = do2 == "1", do3 == "1", int(ceil_p), int(ceil_r)
PENDING = "operator countersign pending"
d = json.load(open(path, encoding="utf-8"))
e = d["exceptions"]
if do2:
    hits = [k for k, v in e.items() if PENDING in v["approval"]]
    if len(hits) != 35:
        sys.exit(f"expected exactly 35 pending exceptions, found {len(hits)}")
    ceilings = {k: v["ceiling"] for k, v in e.items()}
    for k in hits:
        if e[k]["approval"].count(PENDING) != 1:
            sys.exit(f"{k}: pending text is not unique")
        e[k]["approval"] = e[k]["approval"].replace(PENDING, ref)
    if ceilings != {k: v["ceiling"] for k, v in e.items()}:
        sys.exit("a ceiling moved during the countersign")
if do3:
    if "planner_only.py" in e:
        sys.exit("planner_only.py already has an exception")
    if ceil_r < e["run.py"]["ceiling"]:
        sys.exit("run.py ceiling would decrease")
    item = f"{gate} item 3: planner-only {planner}"
    e["run.py"]["approval"] += f"; {item}, ceiling {e['run.py']['ceiling']} -> {ceil_r}"
    e["run.py"]["ceiling"] = ceil_r
    e["planner_only.py"] = {"ceiling": ceil_p, "approval": f"{ref}; {item}"}
    d["exceptions"] = dict(sorted(e.items()))
with open(path, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)
    fh.write("\n")
PYEOF
  say "== exact change to research $BASELINE =="
  diff -u --label "a/$BASELINE" --label "b/$BASELINE" "$STAGE/baseline.before" "$RWT/$BASELINE" | cut -c1-260 || true
  grep -q 'operator countersign pending' "$RWT/$BASELINE" && die "pending text survived the countersign"
  say "== regrowth guard on the staged tree (expected: still red for the unraised overruns, which are not part of this) =="
  grc=0; GOUT="$STAGE/guard.out"
  ( cd "$RWT" && "$SYS_PY" -m scripts.kernel_rnd.autokernel.check_regrowth_guards ) >"$GOUT" 2>&1 || grc=$?
  cut -c1-160 "$GOUT"
  say "guard exit $grc (non-zero is expected while the unraised overruns remain)"
  if grep -qE 'invalid exception|stale exception|cannot read valid baseline|baseline fields do not match' "$GOUT"; then
    die "the guard rejects the edited baseline itself. Nothing committed."
  fi
fi

# ---- item 1: amendment text, consolidated receipt, decision receipt
if [ "$ITEM1" != "already" ]; then
  say "== exact change to $TARGET =="
  cp "$WT/$TARGET" "$STAGE/before.md"
  "$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" --state "$TARGET" --out "$STAGE/pre.json" \
    || die "could not snapshot the pre-amendment state"
  cat >>"$WT/$TARGET" <<'AMENDEOF'

## P-AK-SEARCH-1-A5 — graph-level KLD / same-top rule for graph-fusion keeps (AK-FUSE-GRAPH-KLD-1, RATIFIED 2026-11-09)

For any keep candidate whose patch touches graph-fusion, ggml-alloc or graph-matcher files
(`gates.touches_graph_fusion`), the keep path requires `gates.graph_kld_gate` to pass against the
champion's saved base logits (wikitext-2, `-c 4096 --chunks 16`, Q38FN UD-IQ4_XS and the 27B lane,
`--kl-divergence-base` saved once per champion).

Pass means mean KLD <= K and same-top >= S, where K and S are set from the champion's own A/A floor
measured on the same model/chunks (K = A/A mean KLD plus a margin the operator chooses, S = A/A
same-top minus a margin). The known-bad replay (C7 c420b9d1a Q38FN: KLD 0.1865, same-top 88.6%) must
fail under the chosen values, and the H15 on/off pair is the within-run control.

K and S are not set by this amendment. They are human-only values, supplied to
`gates.KldThresholds.from_config` as `max_mean_kld` and `min_same_top_pct`; both are required, and
neither has a default. Until both are supplied the verdict is `threshold_unset`, a reported refusal
(never a pass, never a silent skip). The A/A floor run (about 10-25 GPU-min per model, 16 GB base
logits each) is the evidence the operator sizes the margins from.

Enforcement state at ratification: `graph_kld_gate` exists in `loop/gates.py` but is not yet called
from the keep path in `loop/run.py`, and no run-level config input for the thresholds exists yet.
Until that wiring lands this rule is not mechanically enforced, and a fusion keep is not refused
automatically by the gate.
AMENDEOF
  diff -u --label "a/$TARGET" --label "b/$TARGET" "$STAGE/before.md" "$WT/$TARGET" || true
  removed="$(diff "$STAGE/before.md" "$WT/$TARGET" | grep -c '^<' || true)"
  [ "$removed" -eq 0 ] || die "postflight: $removed lines removed; additions only expected"
  [ "$(grep -cF -- "$ANCHOR" "$WT/$TARGET")" -eq 1 ] || die "postflight: the amendment heading must occur exactly once"
  ok "additions only (0 lines removed); heading once"

  say "== MEASUREMENT.md section-5 consolidated receipt =="
  "$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
    --repo-root "$WT" --pre "$STAGE/pre.json" \
    --protocol-id "P-AK-SEARCH-1-A5" --anchor "$ANCHOR" \
    --ratification-id "$GATE_ID" --script "$SCRIPT_PATH" \
    --operator "${OPERATOR:-DRY-RUN-PREVIEW}" \
    --no-evidence-reason "keep-path rule that sets no numeric threshold; the thresholds and their A/A floor evidence are a later human-only step" \
    --validation "grep -qF 'P-AK-SEARCH-1-A5' $TARGET" \
    --out "$WT/$CONSOLIDATED_REL" || die "consolidated receipt refused. Nothing committed."
  ok "consolidated receipt: $CONSOLIDATED_REL"
fi

COMMIT_PATHS=("$TARGET" "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")
if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE. Nothing committed, pushed or kept."
  say "  item 1: ${ITEM1:-would apply}"
  say "  item 2: ${ITEM2:-would apply}"
  if [ "$ITEM3" = "already" ]; then say "  item 3: already"; elif [ "$DO_ITEM3" -eq 1 ]; then say "  item 3: would merge and add entries"; else say "  item 3: STOPPED, see above"; fi
  say "Sign with ONE command, from a real terminal:"
  say "  bash $SCRIPT_PATH --apply --operator '<your name>'"
  exit 0
fi

# ---- confirm: typed by the human on the terminal
[ -r /dev/tty ] && [ -t 0 ] || die "no terminal to read the confirmation from; run this from an interactive terminal"
printf '\nThe changes above will be committed and pushed to main in both repos, as operator "%s".\nType RATIFY to apply: ' "$OPERATOR"
IFS= read -r answer < /dev/tty || die "could not read from the terminal"
[ "$answer" = "RATIFY" ] || die "confirmation was '$answer', not RATIFY. Nothing pushed."

push_main() {  # repo-for-lock worktree
  local tokdir tok prc=0
  tokdir="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$1" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || die "could not take the push lock for $1; re-run."
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$2" push -q origin HEAD:refs/heads/main || prc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$1" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: push lock release failed for $1"
  rm -f "$tok"; rmdir "$tokdir" 2>/dev/null || true
  [ "$prc" -eq 0 ] || die "push rejected in $2 (rc=$prc; origin/main probably moved). Re-run; applied items are skipped."
}

# ---- research commit + push (first, so the root receipt can name it)
RES_COMMIT="$(item3_state >/dev/null; g "$RES" rev-parse origin/main)"
if ! g "$RWT" diff --quiet -- "$BASELINE" || [ "$(g "$RWT" rev-parse HEAD)" != "$RES_BASE" ]; then
  g "$RWT" add -- "$BASELINE"
  if ! g "$RWT" diff --cached --quiet; then
    g "$RWT" commit -q -m "autokernel: budget countersign $GATE_ID (signed by $OPERATOR)" \
      -m "Items 2 and 3 of $GATE_ID. Ceilings of the 35 countersigned exceptions are unchanged." \
      || die "baseline commit failed (hook?). Nothing pushed; re-run."
  fi
  say "== push research main =="
  push_main "$RES" "$RWT"
  RES_COMMIT="$(g "$RWT" rev-parse HEAD)"
  g "$RES" fetch -q origin main
  g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
  ok "research main $RES_COMMIT"
fi

# ---- root commit + push
ROOT_COMMIT=""
if [ "$ITEM1" != "already" ]; then
  RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" \
  TARGET="$TARGET" PRE="$PRE_SHA" POST="$(sha "$WT/$TARGET")" OPERATOR="$OPERATOR" TS="$RATIFIED_AT" BASE="$ROOT_BASE" \
  RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" DO3="$DO_ITEM3" CP="$CEIL_PLANNER" CR="$CEIL_RUN" \
  "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Research is already pushed; re-run to finish item 1."
import json, os
e = os.environ
doc = {
    "schema": "epyc.operator_ratification.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (typed RATIFY on the terminal)",
    "items": {
        "1": "AK-FUSE-GRAPH-KLD-1 keep-path rule, P-AK-SEARCH-1-A5; no numeric thresholds set; not yet wired into the keep path",
        "2": "countersign of the 35 regrowth-review exceptions (research 77ee71532); ceilings unchanged",
        "3": (f"planner-only budget: planner_only.py {e['CP']}, run.py {e['CR']}; ak/planner-only-20261109 (0358db7a3) merged"
              if e["DO3"] == "1" else "planner-only: NOT applied in this run (tests failed, merge conflicted, or already applied)"),
    },
    "not_included": "the 13 unraised overrun files",
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
  "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 || die "receipt checker fails after the amendment. Root not committed; research is pushed; re-run."
  g "$WT" add -- "${COMMIT_PATHS[@]}"
  staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
  want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
  [ "$staged" = "$want" ] || die "root index holds an unexpected path set; not committed: $staged"
  g "$WT" commit -q -m "RATIFIED $GATE_ID: AK-FUSE-GRAPH-KLD-1 keep rule, budget countersign, planner-only (signed by $OPERATOR)" \
    -m "Research commit: $RES_COMMIT. Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL." \
    || die "root commit failed (hook?); re-run."
  say "== push root main =="
  push_main "$ROOT" "$WT"
  ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"
  g "$ROOT" fetch -q origin main
  g "$ROOT" merge-base --is-ancestor "$ROOT_COMMIT" origin/main || die "root $ROOT_COMMIT is not on origin/main after fetch"
fi

cat <<REPORT

RATIFIED $GATE_ID by $OPERATOR.
  research main: $RES_COMMIT
  root main:     ${ROOT_COMMIT:-already applied}
  item 3:        $([ "$DO_ITEM3" -eq 1 ] && echo merged || echo "not applied in this run")
NO PROCESS WAS TOUCHED.  VERIFY (read-only): bash $SCRIPT_PATH --verify
ROLLBACK (operator): git revert the commits above on fresh origin/main worktrees, then push through serialized_push.py.
REPORT
