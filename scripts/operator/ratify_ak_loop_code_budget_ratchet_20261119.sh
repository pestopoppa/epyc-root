#!/bin/bash
# ratify_ak_loop_code_budget_ratchet_20261119.sh -- ONE operator signature: per-file RATCHET baseline for the
# existing-file overruns of the AutoKernel loop code-budget guard (OP-AK-CODEBUDGET-43, decided 2026-11-19:
# "ratify a per-file ratchet baseline; each file's current size becomes its cap, any growth fails").
#
# WHAT YOU ARE SIGNING:
#   research scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json: for each file in the closed table below,
#   its enforced ceiling (its "exceptions" entry when it has one, else "files") is RAISED to min(prepared size, size on origin/main at signing). Nothing else changes: no new
#   entry, no new exception (an existing one keeps its approval text plus a ratchet note), no other ceiling, no header field. The guard (check_regrowth_guards.py) already enforces the
#   ratchet: any growth over the ceiling fails, a shrink passes and never raises the ceiling.
#   The table is closed. An overrun NOT in it (a file that grew after prep) is left red and listed, never laundered.
#   Prepared 2026-11-19 against research origin/main: 46 overruns (the decision row said 43; 3 more grew past
#   ceiling between the report and prep). Unit: python_nonblank_noncomment_nondocstring_physical_lines.v1.
#
#   Pull-free single line (fish or bash): see run_ratify_codebudget_ratchet_autokernel_20261119.sh
#   Review / dry run (default; throwaway worktrees, nothing pushed or kept):  bash <this script>
#   Sign:    RATIFY_OPERATOR='<name>' bash <this script> --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261119
#   Commit only:  ... --apply --attest ... --no-push        Verify origin/main (read-only):  --verify
#
# ratify-targets: scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json
#
# Idempotent: when no table file is over its ceiling it says ALREADY RATIFIED. Touches no process and no checkout.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"
SCRIPT_REL="scripts/operator/ratify_ak_loop_code_budget_ratchet_20261119.sh"
STAGE_PARENT="${STAGE_PARENT:-/mnt/raid0/llm/tmp}"
LOCK_AGENT="operator-ratify-ak-loop-code-budget"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261119"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_loop_code_budget_ratchet_20261119.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
AK="scripts/kernel_rnd/autokernel"
BASELINE="$AK/loop_code_budget_baseline.json"
GUARD_MOD="scripts.kernel_rnd.autokernel.check_regrowth_guards"

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
for tool in git sha256sum awk "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "ROOT=$ROOT is not an epyc-root checkout"
[ -f "$ROOT/scripts/operator/lib/push_retry.sh" ] || die "push-retry lib missing under $ROOT"
g "$RES" rev-parse --git-dir >/dev/null 2>&1 || die "RES=$RES is not a git checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"
# shellcheck source=/dev/null
source "$ROOT/scripts/operator/lib/push_retry.sh"

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

# ---- closed ratchet table: file<TAB>prepared size (code lines)<TAB>ceiling at prep
RATCHET_TSV="$(cat <<'TBL'
actor_lifecycle.py	320	286
actor_metrics.py	491	486
actor_orchestrator.py	377	323
actor_preparation.py	503	493
actor_preparation_state.py	310	209
actors.py	3118	3084
ak_check.py	1090	1081
archive.py	511	500
bench.py	451	439
blast_radius.py	236	106
campaign_control.py	4817	4473
candidate_manifest.py	1171	1152
candidate_transactions.py	950	905
census.py	151	150
claim.py	855	830
cpu_route_witness.py	298	278
cross_target.py	437	417
dispatch_guard.py	213	205
driver_execution.py	982	959
gates.py	3280	3104
gpu_serving_profile.py	748	699
hip_launch_proof.py	96	75
keep_screen.py	386	378
lane_watchdog.py	486	475
loop.py	1474	1462
native_scientific_witness.py	675	623
native_server_t0_witness.py	667	657
numerics_gates.py	215	214
pipeline.py	380	364
planner_only.py	241	221
pool.py	495	490
production.py	1330	1314
profile_preparation.py	621	577
resolved_recipe.py	1379	1374
roofline_coverage.py	229	227
run.py	7083	6953
scheduling.py	2102	1927
serial_run.py	2560	2558
serving.py	2204	2201
source_build_execution.py	482	429
standalone_inputs.py	773	770
surface_validation.py	414	388
target_profile_execution.py	280	267
unified_driver.py	1295	1293
unified_worker.py	2250	2247
worker_lifecycle.py	2491	2259
TBL
)"

STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-cb-ratchet.XXXXXX")"
[ -d "$STAGE" ] || die "could not create a stage directory"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$KEEP_STAGE" -eq 0 ]; then
    [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
    [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
    rm -f "${STAGE:?}"/*.json "${STAGE:?}"/*.tsv "${STAGE:?}"/*.txt
    rmdir "${STAGE:?}" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"; RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"; WT_ADDED=1
printf '%s\n' "$RATCHET_TSV" >"$STAGE/table.tsv"

guard() { ( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --baseline "$1" 2>&1 ); }
violations() { grep -E '^  - ' "$1" | sed 's/^  - //' | sort || true; }

( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --emit-baseline-json ) >"$STAGE/current.json" || die "guard could not emit current counts"
PLAN="$("$SYS_PY" - "$RWT/$BASELINE" "$STAGE/current.json" "$STAGE/table.tsv" "$STAGE/new_baseline.json" "$STAGE/plan.tsv" "$STAGE/untabled.tsv" <<'PYEOF'
import json, sys
base_p, cur_p, tbl_p, out_p, plan_p, un_p = sys.argv[1:7]
base = json.load(open(base_p)); cur = json.load(open(cur_p))["files"]
table = {}
for ln in open(tbl_p, encoding="utf-8").read().splitlines():
    if ln.strip():
        f, size, _old = ln.split("\t"); table[f] = int(size)
ex = base["exceptions"]
def ceil(n): return ex[n]["ceiling"] if n in ex else base["files"][n]
over = sorted(n for n in cur if (n in base["files"] or n in ex) and cur[n] > ceil(n))
plan, untabled = [], []
for n in over:
    if n not in table:
        untabled.append(n); continue
    cap = min(cur[n], table[n])
    if cap > ceil(n):
        plan.append((n, ceil(n), cap, cur[n], table[n]))
        if n in ex:   # an exception ceiling is what the guard enforces: ratchet it, keep the old approval text
            ex[n]["ceiling"] = cap
            ex[n]["approval"] += " | ratchet " + str(cap) + ": RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261119 (OP-AK-CODEBUDGET-43)"
        else:
            base["files"][n] = cap
with open(un_p, "w") as fh:
    fh.write("".join(f"{n}\t{cur[n]}\t{ceil(n)}\n" for n in untabled))
with open(plan_p, "w") as fh:
    fh.write("".join("%s\t%d\t%d\t%d\t%d\n" % r for r in plan))
if plan:
    with open(out_p, "w") as fh:
        json.dump(base, fh, indent=2); fh.write("\n")
print("RAISE %d" % len(plan))
PYEOF
)"

if [ "$MODE" = "verify" ]; then
  rc=0
  if [ "$PLAN" = "RAISE 0" ]; then ok "no table file is over its ceiling on research origin/main (ratchet in place)"
  else say "  FAIL  $PLAN table file(s) still over ceiling"; rc=1; fi
  if g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null; then ok "root receipt on origin/main"
  else say "  FAIL  root receipt not on origin/main"; rc=1; fi
  [ ! -s "$STAGE/untabled.tsv" ] || say "  note  overruns outside the ratified table (out of scope, guard stays red): $(cut -f1 "$STAGE/untabled.tsv" | tr '\n' ' ')"
  if [ "$rc" -eq 0 ]; then say "PASS $GATE_ID"; else say "FAIL $GATE_ID"; fi
  exit "$rc"
fi
if [ "$PLAN" = "RAISE 0" ]; then say "ALREADY RATIFIED: no table file is over its ceiling. Nothing to do."; exit 0; fi
say "== $PLAN ceiling(s) to ratchet (file, old ceiling -> new cap, current, prepared) =="
awk -F'\t' '{printf "  %-34s %5s -> %5s   now %5s  prep %5s\n",$1,$2,$3,$4,$5}' "$STAGE/plan.tsv"
if [ -s "$STAGE/untabled.tsv" ]; then
  say "== overruns NOT in the table (left red, not laundered):"
  awk -F'\t' '{printf "  %-34s now %5s  ceiling %5s\n",$1,$2,$3}' "$STAGE/untabled.tsv"
fi

guard "$RWT/$BASELINE" >"$STAGE/before.txt" || true; violations "$STAGE/before.txt" >"$STAGE/before_v.txt"
guard "$STAGE/new_baseline.json" >"$STAGE/after.txt" || true; violations "$STAGE/after.txt" >"$STAGE/after_v.txt"
say "== guard violations BEFORE: $(wc -l <"$STAGE/before_v.txt")  AFTER: $(wc -l <"$STAGE/after_v.txt") =="
[ ! -s "$STAGE/after_v.txt" ] || cat "$STAGE/after_v.txt"
"$SYS_PY" - "$RWT/$BASELINE" "$STAGE/new_baseline.json" "$STAGE/before_v.txt" "$STAGE/after_v.txt" "$STAGE/plan.tsv" <<'PYEOF' || die "postflight failed; nothing committed"
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
plan = {ln.split("\t")[0]: int(ln.split("\t")[2]) for ln in open(sys.argv[5]).read().splitlines()}
keep = lambda d: {k: v for k, v in d.items() if k not in ("files", "exceptions")}
assert keep(a) == keep(b), "a header field changed"
assert set(a["files"]) == set(b["files"]) and set(a["exceptions"]) == set(b["exceptions"]), "an entry was added or removed"
ea, eb = a["exceptions"], b["exceptions"]
for k in sorted(set(a["files"]) | set(ea)):
    v = a["files"].get(k)
    old = ea[k]["ceiling"] if k in ea else v
    new = eb[k]["ceiling"] if k in eb else b["files"][k]
    if k in plan:
        assert new == plan[k] > old, f"{k}: enforced ceiling not raised to the planned cap"
    else:
        assert new == old, f"{k}: ceiling outside the plan changed"
    assert k not in ea or b["files"].get(k) == v, f"{k}: files value changed under an exception"
    if k in ea:
        assert eb[k]["approval"].startswith(ea[k]["approval"]), f"{k}: prior approval text not preserved"
        if k not in plan:
            assert eb[k] == ea[k], f"{k}: exception outside the plan changed"
bv = set(open(sys.argv[3]).read().splitlines()); av = set(open(sys.argv[4]).read().splitlines())
assert av <= bv, "a violation appeared that was not there before"
print("  ok    ratchet only: %d ceilings raised to their caps, no entry added/removed, header untouched, prior approvals preserved; "
      "%d violations cleared, 0 introduced" % (len(plan), len(bv - av)))
PYEOF

if [ "$MODE" = "review" ]; then
  say ""; say "DRY RUN COMPLETE: nothing committed, pushed or kept."
  say "Sign with ONE command (fish or bash):"
  say "  git -C /mnt/raid0/llm/epyc-root fetch -q origin main; and git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ratify_codebudget_ratchet_autokernel_20261119.sh | env RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest $GATE_ID"
  exit 0
fi

push_or_die() {  # repo worktree -> sets PUSHED
  local prc=0
  ratify_push_main_retry "$1" "$2" "$LOCK_AGENT" "$PUSHER" "$STAGE" || prc=$?
  [ "$prc" -eq 0 ] || die "push failed for $2 (rc=$prc). Re-run; an applied ratchet reports ALREADY RATIFIED."
  PUSHED="$RATIFY_PUSHED_SHA"
}

cp "$STAGE/new_baseline.json" "$RWT/$BASELINE"
g "$RWT" add -- "$BASELINE"
[ "$(g "$RWT" diff --cached --name-only HEAD)" = "$BASELINE" ] || die "research index holds an unexpected path set"
N="$(wc -l <"$STAGE/plan.tsv")"
g "$RWT" commit -q -m "autokernel: loop code budget per-file ratchet, $N existing-file ceilings, $GATE_ID (signed by $RATIFY_OPERATOR)" \
  -m "OP-AK-CODEBUDGET-43: each listed file's ceiling = its size at decision; any growth fails, shrink passes. No entry added, no exception. Per-file table in the root receipt." \
  -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 1 ]; then push_or_die "$RES" "$RWT"; RES_COMMIT="$PUSHED"; ok "research main $RES_COMMIT"; fi

WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OPERATOR="$RATIFY_OPERATOR" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" \
SCRIPT_REL="$SCRIPT_REL" PLAN_TSV="$STAGE/plan.tsv" UN_TSV="$STAGE/untabled.tsv" BASELINE="$BASELINE" "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Re-run."
import json, os
e = os.environ
files = {}
for ln in open(e["PLAN_TSV"], encoding="utf-8").read().splitlines():
    n, old, cap, now, prep = ln.split("\t")
    files[n] = {"old_ceiling": int(old), "ratchet_cap": int(cap), "size_at_signing": int(now), "size_at_prep": int(prep)}
untabled = [ln.split("\t")[0] for ln in open(e["UN_TSV"], encoding="utf-8").read().splitlines() if ln]
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified",
    "ratified_at": e["TS"], "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {"1": "2026-11-19 OP-AK-CODEBUDGET-43: ratify a per-file ratchet baseline for the existing-file overruns; each file's current size becomes its cap, any growth fails"},
    "items": {"1": f"research {e['BASELINE']}: ratchet ceilings for the listed existing files (raise to cap only)"},
    "metric": "python_nonblank_noncomment_nondocstring_physical_lines.v1",
    "files": files, "overruns_left_out_of_scope": untabled, "base_origin_main": e["BASE"],
    "research_commit": e["RES_COMMIT"], "applied_by": e["SCRIPT_REL"], "ratify_script_sha256": e["SCRIPT_SHA"],
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
"$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 || die "receipt checker fails. Root not committed."
ok "receipt checker exits 0"
g "$WT" add -- "$RECEIPT_REL" "$INDEX_REL"
want="$(printf '%s\n%s\n' "$RECEIPT_REL" "$INDEX_REL" | sort)"
[ "$(g "$WT" diff --cached --name-only HEAD | sort)" = "$want" ] || die "root index holds an unexpected path set"
g "$WT" commit -q -m "RATIFIED $GATE_ID: loop code-budget per-file ratchet (signed by $RATIFY_OPERATOR)" \
  -m "Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL. No process touched." \
  -m "Operator-Ratified: yes" || die "root commit failed (hook?); re-run."
ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"; ok "root committed ${ROOT_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): research $RES_COMMIT in $RWT, root $ROOT_COMMIT in $WT"
  say "Remove afterwards: git -C $RES worktree remove $RWT; git -C $ROOT worktree remove $WT"
  exit 0
fi
push_or_die "$ROOT" "$WT"; ROOT_COMMIT="$PUSHED"
say ""; say "RATIFIED $GATE_ID by $RATIFY_OPERATOR. research main: $RES_COMMIT  root main: $ROOT_COMMIT. NO PROCESS WAS TOUCHED."
