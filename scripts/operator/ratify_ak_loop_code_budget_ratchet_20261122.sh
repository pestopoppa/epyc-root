#!/bin/bash
# ratify_ak_loop_code_budget_ratchet_20261122.sh -- ONE operator signature: per-file RATCHET baseline for the
# existing-file overruns of the AutoKernel loop code-budget guard (OP-AK-CODEBUDGET-43, decided 2026-11-19:
# "ratify a per-file ratchet baseline; each file's current size becomes its cap, any growth fails").
#
# WHAT YOU ARE SIGNING (prepared 2026-11-22 against research origin/main c8e942e61):
#   ONE signature for the two kinds of red on the AutoKernel loop code-budget guard, same rules as
#   RATIFY-AK-LOOP-CODE-BUDGET-NEW-MODULES-20261119 and RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261119:
#     kind=new     -> a new in-scope module gains a "files" entry at cap = min(table cap, size at signing). 11 rows.
#     kind=ratchet -> an existing file's enforced ceiling becomes an exception at cap = min(table cap, size at signing).
#                     29 rows. A file that already had an exception records the trim-or-split obligation AK-TRIM-OR-SPLIT-SMALL-20261122.
#   NOT IN THIS PACKAGE: 15 files already carry an open trim-or-split obligation from the 2026-11-19 ratchet;
#   the policy forbids a third ratchet, so they stay red until trimmed or split by their owners:
#     actors.py campaign_control.py driver_execution.py gates.py loop.py native_scientific_witness.py pipeline.py pool.py profile_preparation.py run.py scheduling.py source_build_execution.py unified_driver.py unified_worker.py worker_lifecycle.py
#   Pull-free single line (fish or bash): see run_ratify_codebudget_ratchet_autokernel_20261122.sh
#   Per-file justification: every row is growth landed on research main by the AKU / AKPL / WP lanes between
#   2026-11-19 and 2026-11-22; old/new ceiling per file is printed by the dry run and written to the root receipt.
#   Prepared and plan/postflight-simulated offline (55 -> 15 violations, the 15 above); the full dry run is the operator's.
#
#   Review / dry run (default; throwaway worktrees, nothing pushed or kept):  bash <this script>
#   Sign:    RATIFY_OPERATOR='<name>' bash <this script> --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261122
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
SCRIPT_REL="scripts/operator/ratify_ak_loop_code_budget_ratchet_20261122.sh"
STAGE_PARENT="${STAGE_PARENT:-/mnt/raid0/llm/tmp}"
LOCK_AGENT="operator-ratify-ak-loop-code-budget"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261122"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_loop_code_budget_ratchet_20261122.json"
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

# ---- closed table: file<TAB>cap (code lines, size at prep)<TAB>kind<TAB>obligation box (twice-ratcheted files only)
RATCHET_TSV="$(cat <<'TBL'
a2_unit_transport.py	126	ratchet	
actor_context.py	517	ratchet	AK-TRIM-OR-SPLIT-SMALL-20261122
campaign_service.py	718	ratchet	AK-TRIM-OR-SPLIT-SMALL-20261122
census_update.py	277	new	
direct_historical_control.py	587	ratchet	
experiment_plan.py	933	ratchet	AK-TRIM-OR-SPLIT-SMALL-20261122
feed_runtime.py	507	ratchet	
gate_eval.py	281	new	
gate_eval_replay.py	173	new	
gcn_gym.py	135	ratchet	
guard_bands.py	131	ratchet	
host_blocked.py	31	new	
host_claim_provider.py	360	new	
integrity.py	369	ratchet	AK-TRIM-OR-SPLIT-SMALL-20261122
integrity_pack.py	140	new	
keep_lesson.py	59	new	
lifecycle_observation.py	1707	ratchet	
lineage_taxonomy_wire.py	72	new	
loo_touched.py	91	ratchet	
maintenance_execution.py	839	ratchet	
measurement_capture.py	721	ratchet	
native_observation_witnesses.py	187	ratchet	
native_retention_catalog.py	764	ratchet	
operation_accounting.py	380	ratchet	
promotion_evidence.py	57	ratchet	
provider_factories.py	37	ratchet	
runtime_admission.py	799	ratchet	
runtime_aggregates.py	302	ratchet	
serial_scheduling.py	599	ratchet	
source_loo.py	205	ratchet	
stage_bodies.py	376	new	
standalone_runtime.py	742	ratchet	
startup_factory.py	522	ratchet	
tail_timing.py	328	ratchet	
tailsplit.py	156	new	
trial_lifecycle.py	118	ratchet	
typed_planner.py	116	new	
validation_consumer.py	621	ratchet	
validation_projection_source.py	247	ratchet	
validation_semantic_adapter.py	608	ratchet	
TBL
)"

STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-cb-ratchet22.XXXXXX")"
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
PLAN="$("$SYS_PY" - "$RWT/$BASELINE" "$STAGE/current.json" "$STAGE/table.tsv" "$STAGE/new_baseline.json" "$STAGE/plan.tsv" "$STAGE/untabled.tsv" "$GATE_ID" <<'PYEOF'
import json, sys
base_p, cur_p, tbl_p, out_p, plan_p, un_p, gate = sys.argv[1:8]
base = json.load(open(base_p)); cur = json.load(open(cur_p))["files"]
table = {}
for ln in open(tbl_p, encoding="utf-8").read().splitlines():
    if ln.strip():
        f, size, kind, box = (ln.split("\t") + [""])[:4]
        assert kind in ("ratchet", "new"), ln
        table[f] = (int(size), kind, box)
ex = base["exceptions"]
def ceil(n): return ex[n]["ceiling"] if n in ex else base["files"].get(n, 0)
over = sorted(n for n in cur if ((n in base["files"] or n in ex) and cur[n] > ceil(n)) or (n not in base["files"] and n not in ex))
new_mods = {n for n in over if n not in base["files"] and n not in ex}
plan, untabled = [], []
for n in over:
    if n not in table:
        untabled.append((n, "not in table")); continue
    size, kind, box = table[n]
    cap = min(cur[n], size)
    if n in ex and "trim-or-split obligation" in ex[n]["approval"]:
        untabled.append((n, "open trim-or-split obligation: no third ratchet")); continue
    if n in new_mods:
        if kind != "new":
            untabled.append((n, "new module tabled as a ratchet")); continue
        base["files"][n] = cap; plan.append((n, 0, cap, cur[n], size, kind, "")); continue
    if cap <= ceil(n):
        untabled.append((n, f"table cap {size} is not above the ceiling")); continue
    obligation = ""
    if n in ex:
        assert box, f"{n}: twice-ratcheted file without an obligation box in the table"
        obligation = box
        ex[n]["ceiling"] = cap
        ex[n]["approval"] += (f" | ratchet {cap} ({kind}): {gate} (OP-AK-CODEBUDGET-43 procedure, 2026-11-22 package) | RATCHETED TWICE: "
                              f"trim-or-split obligation {box} (epyc-root handoffs/active/autokernel-loop.md); "
                              "no further ratchet of this file until that box closes")
    else:
        ex[n] = {"ceiling": cap, "approval": f"ratchet {cap} ({kind}): {gate} (OP-AK-CODEBUDGET-43 procedure, 2026-11-22 package); "
                 f"frozen baseline {base['files'][n]}. A second ratchet carries a trim-or-split obligation."}
    plan.append((n, 0, cap, cur[n], size, kind, obligation))
pristine = json.load(open(base_p)); pex = pristine["exceptions"]
plan = [(n, pex[n]["ceiling"] if n in pex else pristine["files"].get(n, 0), cap, now, size, kind, ob)
        for (n, _o, cap, now, size, kind, ob) in plan]
with open(un_p, "w") as fh:
    fh.write("".join(f"{n}\t{cur[n]}\t{ceil(n)}\t{why}\n" for n, why in untabled))
with open(plan_p, "w") as fh:
    fh.write("".join("%s\t%d\t%d\t%d\t%d\t%s\t%s\n" % r for r in plan))
if plan:
    base["files"] = dict(sorted(base["files"].items()))
    with open(out_p, "w") as fh:
        json.dump(base, fh, indent=2); fh.write("\n")
print("RAISE %d" % len(plan))
PYEOF
)"

if [ "$MODE" = "verify" ]; then
  rc=0
  if [ "$PLAN" = "RAISE 0" ]; then ok "no table file is over its ceiling on research origin/main (package applied)"
  else say "  FAIL  $PLAN table file(s) still over ceiling"; rc=1; fi
  if g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null; then ok "root receipt on origin/main"
  else say "  FAIL  root receipt not on origin/main"; rc=1; fi
  [ ! -s "$STAGE/untabled.tsv" ] || say "  note  overruns outside the ratified table (out of scope, guard stays red): $(cut -f1 "$STAGE/untabled.tsv" | tr '\n' ' ')"
  if [ "$rc" -eq 0 ]; then say "PASS $GATE_ID"; else say "FAIL $GATE_ID"; fi
  exit "$rc"
fi
if [ "$PLAN" = "RAISE 0" ]; then say "ALREADY RATIFIED: no table file is over its ceiling. Nothing to do."; exit 0; fi
say "== $PLAN ceiling(s) to ratchet (file, old ceiling -> new cap, current, prepared) =="
awk -F'\t' '{printf "  %-34s %5s -> %5s   now %5s  prep %5s  %-10s %s\n",$1,$2,$3,$4,$5,$6,$7}' "$STAGE/plan.tsv"
OBLIG="$(awk -F'\t' '$7!=""{print $7}' "$STAGE/plan.tsv" | sort -u)"
if [ -n "$OBLIG" ]; then
  say "== RATCHETED TWICE: $(printf '%s\n' "$OBLIG" | wc -l) trim-or-split obligation box(es) recorded in the approval text:"
  g "$ROOT" show "$ROOT_BASE:handoffs/active/autokernel-loop.md" >"$STAGE/akl.txt" || die "cannot read autokernel-loop.md at root origin/main"
  for box in $OBLIG; do
    grep -qF -- "**$box " "$STAGE/akl.txt" || grep -qF -- "**$box —" "$STAGE/akl.txt" || die "obligation box $box is not filed in handoffs/active/autokernel-loop.md on root origin/main"
  done
  ok "every obligation box is filed on root origin/main: $(printf '%s ' $OBLIG)"
fi
if [ -s "$STAGE/untabled.tsv" ]; then
  say "== overruns NOT ratcheted (left red, not laundered):"
  awk -F'\t' '{printf "  %-34s now %5s  ceiling %5s  (%s)\n",$1,$2,$3,$4}' "$STAGE/untabled.tsv"
fi

guard "$RWT/$BASELINE" >"$STAGE/before.txt" || true; violations "$STAGE/before.txt" >"$STAGE/before_v.txt"
guard "$STAGE/new_baseline.json" >"$STAGE/after.txt" || true; violations "$STAGE/after.txt" >"$STAGE/after_v.txt"
say "== guard violations BEFORE: $(wc -l <"$STAGE/before_v.txt")  AFTER: $(wc -l <"$STAGE/after_v.txt") =="
[ ! -s "$STAGE/after_v.txt" ] || cat "$STAGE/after_v.txt"
"$SYS_PY" - "$RWT/$BASELINE" "$STAGE/new_baseline.json" "$STAGE/before_v.txt" "$STAGE/after_v.txt" "$STAGE/plan.tsv" <<'PYEOF' || die "postflight failed; nothing committed"
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
plan = {}
for ln in open(sys.argv[5]).read().splitlines():
    n, _old, cap, _now, _prep, kind, ob = ln.split("\t")
    plan[n] = (int(cap), kind, ob)
keep = lambda d: {k: v for k, v in d.items() if k not in ("files", "exceptions")}
assert keep(a) == keep(b), "a header field changed"
assert set(a["files"]) <= set(b["files"]) and set(b["files"]) - set(a["files"]) == {n for n, (_c, k, _o) in plan.items() if k == "new"}, "files entries added/removed outside the plan"
ea, eb = a["exceptions"], b["exceptions"]
added = set(eb) - set(ea)
assert not (set(ea) - set(eb)), "an exception was removed"
assert added <= {n for n, (_c, k, _o) in plan.items() if k == "ratchet"}, "an exception was added outside the plan"
for k in sorted(set(b["files"]) | set(ea)):
    old = ea[k]["ceiling"] if k in ea else a["files"].get(k, 0)
    new = eb[k]["ceiling"] if k in eb else b["files"][k]
    if k in plan:
        cap, kind, ob = plan[k]
        assert new == cap > old, f"{k}: enforced ceiling not raised to the planned cap"
        if kind == "new":
            assert k not in eb and b["files"][k] == cap, f"{k}: new module must only gain its files value"
        else:
            assert b["files"].get(k) == a["files"].get(k), f"{k}: frozen files value changed"
        if k in ea:
            assert eb[k]["approval"].startswith(ea[k]["approval"]), f"{k}: prior approval text not preserved"
            assert ob and ob in eb[k]["approval"] and "RATCHETED TWICE" in eb[k]["approval"], f"{k}: obligation not recorded"
    else:
        assert new == old and b["files"].get(k) == a["files"].get(k), f"{k}: ceiling outside the plan changed"
        if k in ea:
            assert eb[k] == ea[k], f"{k}: exception outside the plan changed"
bv = set(open(sys.argv[3]).read().splitlines()); av = set(open(sys.argv[4]).read().splitlines())
assert av <= bv, "a violation appeared that was not there before"
print("  ok    ratchet only: %d ceilings raised to their caps (%d new exception entries, %d twice-ratcheted with "
      "obligations), files values frozen except rebaselines, header untouched, prior approvals preserved; "
      "%d violations cleared, 0 introduced" % (len(plan), len(added), sum(1 for v in plan.values() if v[2]),
                                               len(bv - av)))
PYEOF

if [ "$MODE" = "review" ]; then
  say ""; say "DRY RUN COMPLETE: nothing committed, pushed or kept."
  say "Sign with ONE command (fish or bash):"
  say "  git -C /mnt/raid0/llm/epyc-root fetch -q origin main; and git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ratify_codebudget_ratchet_autokernel_20261122.sh | env RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest $GATE_ID"
  exit 0
fi

push_or_die() {  # repo worktree -> sets PUSHED
  local prc=0
  ratify_push_main_retry "$1" "$2" "$LOCK_AGENT" "$PUSHER" "$STAGE" || prc=$?
  [ "$prc" -eq 0 ] || die "push failed for $2 (rc=$prc). Re-run; an applied ratchet reports ALREADY RATIFIED."
  PUSHED="$RATIFY_PUSHED_SHA"
}

g "$RES" fetch -q origin main || die "cannot re-fetch research origin main before commit"
[ "$(g "$RES" rev-parse origin/main)" = "$RES_BASE" ] || die "research origin/main moved since it was measured ($RES_BASE); nothing committed. Re-run to measure the new tip."
cp "$STAGE/new_baseline.json" "$RWT/$BASELINE"
g "$RWT" add -- "$BASELINE"
[ "$(g "$RWT" diff --cached --name-only HEAD)" = "$BASELINE" ] || die "research index holds an unexpected path set"
N="$(wc -l <"$STAGE/plan.tsv")"
g "$RWT" commit -q -m "autokernel: loop code budget per-file ratchet, $N new-module entries and existing-file ceilings, $GATE_ID (signed by $RATIFY_OPERATOR)" \
  -m "OP-AK-CODEBUDGET-43 (2026-11-22 package): new modules gain files entries; each listed existing file's enforced ceiling = min(prepared cap, size on research origin/main $RES_BASE at signing), recorded as an exception over the frozen files value Twice-ratcheted files carry a trim-or-split obligation. Per-file table in the root receipt." \
  -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 1 ]; then push_or_die "$RES" "$RWT"; RES_COMMIT="$PUSHED"; ok "research main $RES_COMMIT"; fi

WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OPERATOR="$RATIFY_OPERATOR" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" \
SCRIPT_REL="$SCRIPT_REL" RES_BASE="$RES_BASE" PLAN_TSV="$STAGE/plan.tsv" UN_TSV="$STAGE/untabled.tsv" BASELINE="$BASELINE" "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Re-run."
import json, os
e = os.environ
files = {}
for ln in open(e["PLAN_TSV"], encoding="utf-8").read().splitlines():
    n, old, cap, now, prep, kind, ob = ln.split("\t")
    files[n] = {"old_ceiling": int(old), "ratchet_cap": int(cap), "size_at_signing": int(now), "size_at_prep": int(prep),
                "kind": kind, **({"trim_or_split_obligation": ob} if ob else {})}
untabled = {ln.split("\t")[0]: ln.split("\t")[3] for ln in open(e["UN_TSV"], encoding="utf-8").read().splitlines() if ln}
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified",
    "ratified_at": e["TS"], "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {"1": "2026-11-19 OP-AK-CODEBUDGET-43 procedure (trim first, then ratchet; twice-ratcheted => trim-or-split obligation; no third ratchet)", "2": "2026-11-22 package: new modules baselined and first/second ratchets for growth landed 2026-11-19..22; obligation-carrying files left red"},
    "items": {"1": f"research {e['BASELINE']}: ratchet ceilings for the listed existing files (raise to cap only)"},
    "metric": "python_nonblank_noncomment_nondocstring_physical_lines.v1",
    "files": files, "overruns_left_out_of_scope": untabled, "base_origin_main": e["BASE"], "research_measured_at_signing": e["RES_BASE"],
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
