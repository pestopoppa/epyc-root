#!/bin/bash
# run_ak_c9_ratify2_20261109.sh -- ONE operator signature (RATIFY-AK-C9-2-20261109) over four AutoKernel items.
#
# WHAT YOU ARE SIGNING
#   A. GPU clock band. gpu_clock_policy.json changes from strict to request_phase_band, droop_band_mhz 120
#      (floor 1580 MHz). Pre-stated statistic: max(1700 - sclk_min_mhz) over invocations with no error and rc 0,
#      no trimming, over the complete invocations.jsonl of vidya-r18d-aa-wire-20261109-r3: n = 136 (COMPLETE, all
#      20 pairs in all 3 conditions, warmups included). Live effect: AutoKernel serving launches then use this band.
#      WORKLOAD CAVEAT: r3 is llama-bench single-stream prompt processing (pp512, 27B Q8_0), not np4 concurrent
#      serving with decode. It is not evidence of np4 droop. If np4 droops deeper, healthy launches are flagged
#      (costs compute); if shallower, the band admits some real droop. r3's windows include model load, and its
#      polling is 0.25 s. One device, one model, one session. Recommended before binding to SL-2: one pinned np4 A/A.
#      Also changes test_clock_policy.py::test_shipped_policy_is_strict, which pinned the old strict default, so it
#      asserts the signed band instead.
#   B. R18 comparator manifest. Re-pins comparator-dependencies.json to the live host (schemas.py, perl,
#      python3.13 -> python3.12), new sha256 5350aac8..., and accepts it alongside the old digest in the
#      adapter, the capture, the full-build successor and a new test.
#   C. Code budget. Ceilings at actual counts on research origin/main (next-code merged, 9dcd3c0e0) for the 21 rows
#      of the 2026-11-09 proposal. Four carry an OPEN design question in their approval text: accumulate.py,
#      run.py, serving.py, status.py. The ceilings do not settle those questions.
#      ALSO IN C, NOT IN THE PROPOSAL: fold2_gates.py 247, longctx.py 820, longctx_c8.py 99, production.py 1314,
#      provider_breaker.py 71. They are over ceiling on current main and no reviewer has examined that growth
#      (+5, +11, +2, +2, +4 lines). Without them the guard stays red.
#   D. Branch merges, each only if its own tests pass on the merged tree:
#      ak/retired-20261109 (390daf496): retired_mechanisms.py 201, dispatch_guard.py 205, run.py +1;
#      ak/planner-cpu-20261109 (3f6301af8): planner_only.py 221.
#      A branch that conflicts or fails is skipped with its ceilings; the other items proceed.
#
#   Review / dry run (default; throwaway worktrees only, nothing pushed or kept):
#     bash scripts/operator/run_ak_c9_ratify2_20261109.sh
#   Sign (the OPERATOR runs this; it reads RATIFY from /dev/tty):
#     bash scripts/operator/run_ak_c9_ratify2_20261109.sh --apply --operator '<your name>'
#   From a non-terminal prompt, give it a pty:
#     script -qfc "bash <this script> --apply --operator '<your name>'" /dev/null <<< RATIFY
#   Verify origin/main of both repos (read-only):
#     bash scripts/operator/run_ak_c9_ratify2_20261109.sh --verify
#
# Idempotent: work already on origin/main is skipped; re-run after any failure. Research is committed first, so the
# root receipt records its commit. Tests run at sign time, confined to CPUs 72-87. Touches no process and no checkout.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="/mnt/raid0/llm/epyc-root"
RES="/mnt/raid0/llm/epyc-inference-research"
STAGE_PARENT="/mnt/raid0/llm/tmp"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-C9-2-20261109"
LOCK_AGENT="operator-ratify-ak-c9-2"
SCRIPT_REL="scripts/operator/run_ak_c9_ratify2_20261109.sh"
RECEIPT_REL="artifacts/operator/ratify_ak_c9_2_20261109.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
AK="scripts/kernel_rnd/autokernel"
BASELINE="$AK/loop_code_budget_baseline.json"
BASELINE_PRE_SHA="b9a32d984eadfb4c37a8d7fb2d60c410b05af73fd1ea1efcb4576ef9dc7d6ee1"
POLICY="$AK/loop/gpu_clock_policy.json"
POLICY_TEST="$AK/loop/test_clock_policy.py"
POLICY_PRE_SHA="96d8cdf55a32dfe3bf9dfeb716b871987b75233db994d306ac727e3b245aa4ed"
BAND=120
R3_INV="/mnt/raid0/llm/tmp/vb-r18d-aa-wire-20261109-r3/out/invocations.jsonl"
R3_SHA="5a326d416db230b731b663bf849bd75233eaaa0f5ab494fda58efce450fedf40"
R3_N=136
MANIFEST="scripts/vidya/producers/r18_inputs/comparator-dependencies.json"
OLD_DIGEST="5adb079828658d11dd393fa61f3e59712872ae635102c2543c7c9d8823c927fd"
NEW_DIGEST="5350aac873b0b3626851912dc44c1d3579467edacb6a999e4acfd70f83a587fd"
SUCCESSOR="scripts/vidya/producers/r18_full_build_successor.py"
CAPTURE="scripts/vidya/producers/r18_symbol_capture.py"
ADAPTER="scripts/vidya/adapters/autokernel_r18_symbols.py"
R18_TEST="tests/vidya/test_r18_symbol_integration.py"
RETIRED_BRANCH="ak/retired-20261109"; RETIRED_SHA="390daf496"
RETIRED_TEST="$AK/loop/test_retired_mechanisms.py"
PLANNER_BRANCH="ak/planner-cpu-20261109"; PLANNER_SHA="3f6301af8"
PLANNER_TEST="$AK/loop/test_planner_only.py"
REF="operator ratification $GATE_ID (epyc-root $RECEIPT_REL)"
CPU_LIMIT=(taskset -c 72-87 nice -n 19 timeout 300)

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
for tool in git sha256sum awk diff patch taskset timeout "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
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

research_state() {
  local base policy
  base="$(g "$RES" show "origin/main:$BASELINE")"
  policy="$(g "$RES" show "origin/main:$POLICY")"
  if grep -qF -- "$GATE_ID" <<<"$base" && grep -qF -- "\"droop_band_mhz\": $BAND" <<<"$policy"; then echo already; fi
}
root_state() { g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && echo already || true; }
branch_on_main() { g "$RES" merge-base --is-ancestor "$1" origin/main 2>/dev/null; }

if [ "$MODE" = "verify" ]; then
  rc=0
  if [ "$(research_state)" = "already" ]; then ok "A and C on research origin/main"; else say "  FAIL  A/C not on research origin/main"; rc=1; fi
  if [ "$(root_state)" = "already" ]; then
    ok "B and receipt on root origin/main"
    if [ "$(g "$ROOT" show "origin/main:$MANIFEST" | sha256sum | awk '{print $1}')" = "$NEW_DIGEST" ]; then ok "manifest digest ${NEW_DIGEST:0:12}"; else say "  FAIL  manifest digest"; rc=1; fi
    receipt="$(g "$ROOT" show "origin/main:$RECEIPT_REL")"
    for pair in "retired:$RETIRED_SHA" "planner:$PLANNER_SHA"; do
      name="${pair%%:*}"; commit="${pair##*:}"
      want="$(RECEIPT="$receipt" NAME="$name" "$SYS_PY" -c 'import json,os;print(json.loads(os.environ["RECEIPT"])["merged"][os.environ["NAME"]])')"
      if branch_on_main "$commit"; then have=True; else have=False; fi
      if [ "$want" = "$have" ]; then ok "D $name: merged=$have, as the receipt records"; else say "  FAIL  D $name: receipt says $want, origin/main says $have"; rc=1; fi
    done
  else
    say "  FAIL  B/receipt not on root origin/main"; rc=1
  fi
  exit "$rc"
fi

RES_DONE="$(research_state)"; ROOT_DONE="$(root_state)"
if [ "$RES_DONE$ROOT_DONE" = "alreadyalready" ]; then
  say "ALREADY RATIFIED: all items are on origin/main. Nothing to do."; exit 0
fi

# ---- the pre-stated statistic, recomputed from the raw file
say "== A: droop statistic =="
if [ -f "$R3_INV" ]; then
  [ "$(sha "$R3_INV")" = "$R3_SHA" ] || die "$R3_INV changed since this script was prepared"
  "$SYS_PY" - "$R3_INV" "$BAND" "$R3_N" <<'PYEOF' || die "the droop statistic does not reproduce"
import json, sys
path, band, want_n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rows = [json.loads(line) for line in open(path, encoding="utf-8")]
used = [r for r in rows if r["error"] is None and r["returncode"] == 0]
droop = [1700 - r["residency"]["sclk_min_mhz"] for r in used]
print(f"  n={len(droop)} of {len(rows)} invocations; max droop {max(droop)} MHz")
sys.exit(0 if len(droop) == want_n and max(droop) == band else 1)
PYEOF
  ok "max droop $BAND MHz over n=$R3_N"
else
  say "  WARN  $R3_INV is gone; using the recorded result (band $BAND, n $R3_N)"
fi

# ---- throwaway stage: two detached worktrees, removed on exit
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-c9-2.XXXXXX")"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0
cleanup() {
  local rc=$?
  [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove --force "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
  [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
  rm -f "$STAGE"/baseline.before "$STAGE"/guard.out "$STAGE"/r18.patch
  rmdir "$STAGE" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"
RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"
WT_ADDED=1
ok "staged throwaway worktrees under $STAGE"

merge_if_green() {  # branch sha test-path -> returns 0 if merged
  local branch="$1" commit="$2" test_path="$3" tip trc=0
  say "== D: merge $branch ($commit) and test =="
  tip="$(g "$RES" rev-parse "refs/heads/$branch")" || { say "D STOPPED: $branch not found"; return 1; }
  case "$tip" in "$commit"*) ok "branch tip is $commit" ;; *) say "D STOPPED: $branch moved to $tip; the signed commit is $commit"; return 1 ;; esac
  if ! g "$RWT" merge --no-ff --no-commit "$commit" >/dev/null 2>&1; then
    g "$RWT" merge --abort 2>/dev/null || true
    say "D STOPPED: $branch conflicts. Not merged, no ceilings."; return 1
  fi
  ( cd "$RWT" && EPYC_ROOT="$WT" "${CPU_LIMIT[@]}" "$SYS_PY" -m pytest -q -p no:cacheprovider "$test_path" ) || trc=$?
  if [ "$trc" -ne 0 ]; then
    g "$RWT" merge --abort
    say "D STOPPED: $branch tests failed (exit $trc). Not merged, no ceilings."; return 1
  fi
  g "$RWT" commit -q -m "merge $branch ($commit), tests passed ($GATE_ID item D, signed by ${OPERATOR:-DRY-RUN})" \
    || die "merge commit failed (hook?). Nothing pushed; re-run."
  ok "$test_path passed on the merged tree"
}

DO_RETIRED=0; DO_PLANNER=0
if [ "$RES_DONE" != "already" ]; then
  say "== preflight research =="
  [ "$(sha "$RWT/$BASELINE")" = "$BASELINE_PRE_SHA" ] || die "$BASELINE changed since this script was prepared; re-derive, do not overwrite"
  [ "$(sha "$RWT/$POLICY")" = "$POLICY_PRE_SHA" ] || die "$POLICY changed since this script was prepared; re-derive, do not overwrite"
  ok "baseline and clock policy at pre-state"
  if ! branch_on_main "$RETIRED_SHA" && merge_if_green "$RETIRED_BRANCH" "$RETIRED_SHA" "$RETIRED_TEST"; then DO_RETIRED=1; fi
  if ! branch_on_main "$PLANNER_SHA" && merge_if_green "$PLANNER_BRANCH" "$PLANNER_SHA" "$PLANNER_TEST"; then DO_PLANNER=1; fi

  say "== A: exact new $POLICY =="
  printf '{"schema": "epyc.autokernel.gpu_clock_policy.v1", "mode": "request_phase_band", "pinned_level": "high", "nominal_sclk_mhz": 1700, "droop_band_mhz": %s, "min_request_samples": 8, "max_sample_gap_s": 1.0, "ratification": "%s"}\n' "$BAND" "$RECEIPT_REL" >"$RWT/$POLICY"
  cat "$RWT/$POLICY"
  "$SYS_PY" - "$RWT/$POLICY_TEST" "$BAND" <<'PYEOF' || die "could not update the shipped-policy test. Nothing committed."
import sys
path, band = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
old = """def test_shipped_policy_is_strict():
    active = cp.load()
    assert active.mode == cp.STRICT and active.droop_band_mhz is None
"""
new = f"""def test_shipped_policy_is_the_ratified_band():
    active = cp.load()
    assert active.mode == cp.BAND and active.droop_band_mhz == {band}
"""
if text.count(old) != 1:
    sys.exit("shipped-policy test not found exactly once")
open(path, "w", encoding="utf-8").write(text.replace(old, new))
PYEOF
  ( cd "$RWT" && EPYC_ROOT="$WT" "${CPU_LIMIT[@]}" "$SYS_PY" -m pytest -q -p no:cacheprovider "$POLICY_TEST" ) \
    || die "test_clock_policy fails with the band config. Nothing committed."
  ok "test_clock_policy passed with the band config"

  say "== C: budget ceilings =="
  cp "$RWT/$BASELINE" "$STAGE/baseline.before"
  "$SYS_PY" - "$RWT/$BASELINE" "$DO_RETIRED" "$DO_PLANNER" "$REF" "$RETIRED_SHA" "$PLANNER_SHA" <<'PYEOF' || die "baseline transform refused. Nothing committed."
import json, sys
path, retired, planner, ref, retired_sha, planner_sha = sys.argv[1:]
retired, planner = retired == "1", planner == "1"
D = "OPEN design question, not settled by this ceiling: "
rows = {
 "accumulate.py": (769, "a25f5ff79, 2f047a7b1 per-surface bundles and shared-COR fencing. " + D + "split _load_bundle_locked (+190 lines as one function) by surface and legacy path?"),
 "actor_metrics.py": (486, "c17d0d0b7, 6a3981e4b, 3e9c00e53 reasoning and section-pull metrics; reduction behind the discard-invariant custody pin"),
 "actor_orchestrator.py": (323, "952c4d859 abstain schema carries belief focus fields"),
 "actors.py": (3084, "7caa320c8, f212ddb5d, dd3ab6326 hotspot render, per-container claude binary, opencode v2 argv; reduction behind the custody pin"),
 "belief_context.py": (624, "952c4d859, 3bd5d85d9 profile focus symbols, unsourced-figure lint"),
 "bench.py": (439, "ak/next-code-20261109 growth, actual count after merge"),
 "champion.py": (218, "3bd5d85d9, c4976a843, e90b0aa9c stale-anchor and champion-currency refusals"),
 "claim.py": (830, "e50adce0b, b05e3c3da window-scoped device flock and ancestor-hold resolution"),
 "clock_policy.py": (183, "fd98d5d0e request-phase clock trace and ratifiable droop-band policy, new file"),
 "gpu_window.py": (459, "dc1436210, e50adce0b MI210 window must-fix list, bus-grant and schedule subsystem"),
 "hotspots.py": (209, "625b5000a AK-PROF-TWO-DENOM denominators and rendering"),
 "lane_watchdog.py": (475, "ak/next-code-20261109 growth, actual count after merge"),
 "loop.py": (1462, "e33cf3cd1, 9ddf6d38e, 3ab4ffbf1 same-state stop, empty-suite preflight, typed resume ineligibility; reduction behind the custody pin"),
 "new_epoch.py": (91, "a25f5ff79 per-surface anchor epochs"),
 "residency.py": (665, "dc1436210, e50adce0b, fd98d5d0e VRAM ceiling abort, own-launch tracking, clock trace"),
 "run.py": (6952, "40 commits since baseline plus next-code growth. " + D + "extract the duplicated attempt-record blocks (file is custody-pinned)?"),
 "seed_bundle.py": (139, "a25f5ff79, 2f047a7b1 surface-scoped seeding and stale-COR fence"),
 "serving.py": (2201, "15 commits plus next-code growth; target-steps, acceptance and refused-partial evidence. " + D + "move target-steps helpers into a module?"),
 "serving_gate.py": (213, "625b5000a, cae39d8c3 e2e design classification before an op win is confirmed"),
 "status.py": (381, "991033729 pool_health_signal, 4b4207f3b process identity. " + D + "should the alarm logic live in status?"),
 "surface_fold.py": (282, "d480cac2e refusal of ratified do-not-fold changes"),
 # Not in the 2026-11-09 proposal: over ceiling on current main, growth not reviewed.
 "fold2_gates.py": (247, "NOT in the 2026-11-09 proposal, growth unreviewed; latest a137475bc"),
 "longctx.py": (820, "NOT in the 2026-11-09 proposal, growth unreviewed; latest c835bd62d"),
 "longctx_c8.py": (99, "NOT in the 2026-11-09 proposal, growth unreviewed; latest 1bc36e200"),
 "production.py": (1314, "NOT in the 2026-11-09 proposal, growth unreviewed; latest a034d16e6"),
 "provider_breaker.py": (71, "NOT in the 2026-11-09 proposal, growth unreviewed; latest f0dfb52de"),
}
if retired:
    rows["retired_mechanisms.py"] = (201, f"{retired_sha} retired-mechanism refusal at formation, new file")
    rows["dispatch_guard.py"] = (205, f"{retired_sha} calls the retired-mechanism refusal")
    rows["run.py"] = (rows["run.py"][0] + 1, rows["run.py"][1] + f"; +1 for {retired_sha}")
if planner:
    rows["planner_only.py"] = (221, f"{planner_sha} planner-only CPU targets, actual count on the merged tree")
d = json.load(open(path, encoding="utf-8"))
e, files = d["exceptions"], d["files"]
for name, (ceiling, why) in rows.items():
    old = e[name]["ceiling"] if name in e else files.get(name)
    if old is not None and ceiling < old:
        sys.exit(f"{name}: ceiling would decrease from {old} to {ceiling}")
    text = f"{ref}, item C: {why}"
    e[name] = {"ceiling": ceiling, "approval": (e[name]["approval"] + "; " + text) if name in e else text}
d["exceptions"] = dict(sorted(e.items()))
with open(path, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)
    fh.write("\n")
PYEOF
  diff -u --label "a/$BASELINE" --label "b/$BASELINE" "$STAGE/baseline.before" "$RWT/$BASELINE" | cut -c1-260 || true

  say "== regrowth guard on the staged tree (must be green) =="
  grc=0; GOUT="$STAGE/guard.out"
  ( cd "$RWT" && "$SYS_PY" -m scripts.kernel_rnd.autokernel.check_regrowth_guards ) >"$GOUT" 2>&1 || grc=$?
  grep -E 'per-file code baseline|guard violation|^  - ' "$GOUT" | cut -c1-160 || true
  [ "$grc" -eq 0 ] || die "regrowth guard is red on the staged tree (exit $grc). Nothing committed."
  ok "guard green"
else
  say "research items already on origin/main"
fi

# ---- item B: the embedded patch, then the digest pins
if [ "$ROOT_DONE" != "already" ]; then
  say "== B: R18 manifest =="
  [ "$(sha "$WT/$MANIFEST")" = "$OLD_DIGEST" ] || die "$MANIFEST changed since this script was prepared; re-derive, do not overwrite"
  cat >"$STAGE/r18.patch" <<'PATCHEOF'
diff --git a/scripts/vidya/producers/r18_inputs/comparator-dependencies.json b/scripts/vidya/producers/r18_inputs/comparator-dependencies.json
index e97193a43..9744d49aa 100644
--- a/scripts/vidya/producers/r18_inputs/comparator-dependencies.json
+++ b/scripts/vidya/producers/r18_inputs/comparator-dependencies.json
@@ -5,10 +5,10 @@
   "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/evaluator/devices.py": "af8ee4813a4a80535f2628604bd53257259ef1aad5173c96863db68b1e990c3b",
   "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/evaluator/integrity.py": "dfc6dbc719aab525d4ddedd53ca087b00e1e632ed8147967175676884f415f1f",
   "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/evaluator/surface.py": "a8576e98dc6c0292bab6b4bdc08f3cc22ca6d1e1f9fdb9805d0e3bad775a7cf6",
-  "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/schemas.py": "4dd07e2492a534029654b4bad5a2fb1062d66ddf5582bbd3bda8b7f17ea88644",
+  "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/schemas.py": "e49b255577f24af26778336c05b722916cd4975624a7967443f0397e37925bfe",
   "/opt/rocm/bin/roc-obj-ls": "29445392525e6a9bbfccfb323a828ea5ebd47d676b42e2df2ae306bd84c11c08",
-  "/usr/bin/perl": "fa709dd80ec2ddd60b47b1a13964dcbe7c4b96fb08f91778485ae95a78685e4e",
-  "/usr/bin/python3.13": "efb29ce53d36ebaeee80e3aa44fd6c7f9d71bbded5fe1665240b2ed8ecaeee0e",
+  "/usr/bin/perl": "47bdc8a342556c1d140084417ef6cacd79a3362e4b6cc1e4754df55bdf1e3683",
+  "/usr/bin/python3.12": "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f",
   "@bundle/File/Which.pm": "e317605124d953a950d3d6cc7624d0e5358bb710eeaf20f3ec7889023f19dac0",
   "@bundle/URI/Escape.pm": "0bd8e615325fb77778b03ac7f025b9cc06b7e82410d39a55ebdb2ab18ae93ef6"
 }
PATCHEOF
  ( cd "$WT" && patch -s -p1 --no-backup-if-mismatch <"$STAGE/r18.patch" ) || die "the R18 patch no longer applies. Nothing committed."
  [ "$(sha "$WT/$MANIFEST")" = "$NEW_DIGEST" ] || die "patched manifest is not $NEW_DIGEST"
  ok "patch applied; manifest ${NEW_DIGEST:0:12}"
  "$SYS_PY" - "$WT" "$SUCCESSOR" "$CAPTURE" "$ADAPTER" "$R18_TEST" "$OLD_DIGEST" "$NEW_DIGEST" <<'PYEOF' || die "digest pin edit refused. Nothing committed."
import sys
from pathlib import Path
wt, successor, capture, adapter, test, old, new = sys.argv[1:]
def edit(rel, before, after):
    path = Path(wt) / rel
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        sys.exit(f"{rel}: expected exactly one match of {before[:60]!r}, found {text.count(before)}")
    path.write_text(text.replace(before, after), encoding="utf-8")
edit(successor, f"'comparator-dependencies.json':'{old}'}}", f"'comparator-dependencies.json':('{old}','{new}')}}")
edit(successor, "if hashlib.sha256((INPUTS/name).read_bytes()).hexdigest()!=digest: raise",
     "if hashlib.sha256((INPUTS/name).read_bytes()).hexdigest() not in (digest if isinstance(digest,tuple) else (digest,)): raise")
edit(capture, f"'{old}'): raise ValueError('comparator dependency manifest differs')",
     f"'{old}', '{new}'): raise ValueError('comparator dependency manifest differs')")
edit(adapter, f"'{old}'): raise ValueError('dependency manifest differs from v10 comparator closure')",
     f"'{old}', '{new}'): raise ValueError('dependency manifest differs from v10 comparator closure')")
marker = "def test_relocated_dependency_manifest_resolves_bundle(tmp_path):"
edit(test, marker, f"def test_dependency_manifest_digest_is_accepted():\n bundle, _ = _bundle_deps()\n assert capture.sha(bundle/'comparator-dependencies.json') in ('{old}', '{new}')\n\n" + marker)
PYEOF
  g "$WT" diff --stat -- "$MANIFEST" "$SUCCESSOR" "$CAPTURE" "$ADAPTER" "$R18_TEST"
  ( cd "$WT" && "${CPU_LIMIT[@]}" "$SYS_PY" -m pytest -q -p no:cacheprovider "$R18_TEST" ) \
    || die "$R18_TEST fails on the staged root tree. Nothing committed."
  ok "$R18_TEST passed"
fi

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE. Nothing committed, pushed or kept."
  say "  A/C: ${RES_DONE:-would apply}"
  say "  B:   ${ROOT_DONE:-would apply}"
  say "  D retired: $([ "$DO_RETIRED" -eq 1 ] && echo 'would merge' || echo 'not merging, see above')"
  say "  D planner: $([ "$DO_PLANNER" -eq 1 ] && echo 'would merge' || echo 'not merging, see above')"
  say "Sign with ONE command:"
  say "  script -qfc \"bash $SCRIPT_PATH --apply --operator '<your name>'\" /dev/null <<< RATIFY"
  exit 0
fi

# ---- confirm: typed by the human on the terminal
[ -r /dev/tty ] && [ -t 0 ] || die "no terminal to read the confirmation from; run from a terminal or through the script(1) wrapper"
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
RES_COMMIT="$RES_BASE"
if [ "$RES_DONE" != "already" ]; then
  g "$RWT" add -- "$BASELINE" "$POLICY" "$POLICY_TEST"
  g "$RWT" commit -q -m "autokernel: GPU clock band and code budget $GATE_ID (signed by $OPERATOR)" \
    -m "Items A and C of $GATE_ID. Band $BAND MHz from r3, n=$R3_N. Four budget rows carry open design questions." \
    || die "research commit failed (hook?). Nothing pushed; re-run."
  say "== push research main =="
  push_main "$RES" "$RWT"
  RES_COMMIT="$(g "$RWT" rev-parse HEAD)"
  g "$RES" fetch -q origin main
  g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
  ok "research main $RES_COMMIT"
fi

# ---- root commit + push
ROOT_COMMIT=""
if [ "$ROOT_DONE" != "already" ]; then
  if branch_on_main "$RETIRED_SHA"; then MERGED_RETIRED=1; else MERGED_RETIRED=0; fi
  if branch_on_main "$PLANNER_SHA"; then MERGED_PLANNER=1; else MERGED_PLANNER=0; fi
  WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OPERATOR="$OPERATOR" \
  TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" \
  SCRIPT_REL="$SCRIPT_REL" BAND="$BAND" N="$R3_N" NEW_DIGEST="$NEW_DIGEST" MR="$MERGED_RETIRED" MP="$MERGED_PLANNER" \
  "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Research is already pushed; re-run to finish."
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
        "A": f"GPU clock band droop_band_mhz {e['BAND']}, statistic over r3 n={e['N']}; single-stream pp512 workload, not np4",
        "B": f"R18 comparator manifest {e['NEW_DIGEST']}, accepted alongside the old digest",
        "C": "code budget at actual counts; accumulate, run, serving, status carry open design questions; five files outside the proposal included, growth unreviewed",
        "D": "ak/retired-20261109 and ak/planner-cpu-20261109, each only if its tests passed on the merged tree",
    },
    "merged": {"retired": e["MR"] == "1", "planner": e["MP"] == "1"},
    "base_origin_main": e["BASE"],
    "research_commit": e["RES_COMMIT"],
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
  "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 || die "receipt checker fails. Root not committed; research is pushed; re-run."
  COMMIT_PATHS=("$MANIFEST" "$SUCCESSOR" "$CAPTURE" "$ADAPTER" "$R18_TEST" "$RECEIPT_REL" "$INDEX_REL")
  g "$WT" add -- "${COMMIT_PATHS[@]}"
  staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
  want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
  [ "$staged" = "$want" ] || die "root index holds an unexpected path set; not committed: $staged"
  g "$WT" commit -q -m "RATIFIED $GATE_ID: GPU clock band, R18 manifest, code budget, branch merges (signed by $OPERATOR)" \
    -m "Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL." \
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
NO PROCESS WAS TOUCHED.  VERIFY (read-only): bash $SCRIPT_PATH --verify
ROLLBACK (operator): git revert the commits above on fresh origin/main worktrees, then push through serialized_push.py.
REPORT
