#!/bin/bash
# ratify_ak_loop_code_budget_new_modules_20261119.sh -- ONE operator signature to baseline the loop modules
# added since the 2026-11-09 budget review (operator decision 2026-11-19: "prep a baseline ratify").
#
# WHAT YOU ARE SIGNING:
#   research scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json gains one "files" entry per NEW in-scope
#   loop module, ceiling = its current code-line count (check_regrowth_guards.py metric), reason + box per module in
#   the root receipt. NOTHING ELSE changes: no existing ceiling, no exception, no deletion. Over-ceiling EXISTING
#   files (gates.py, run.py, ...) are a separate decision and are NOT touched here; the guard stays red on them.
#   The module table below is closed: a new in-scope file that is not in it refuses the run (no silent laundering).
#   A table entry whose file is not on research origin/main yet is skipped; re-run after it lands.
#
#   Review / dry run (default; throwaway worktrees, nothing pushed or kept, guard run before and after):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_loop_code_budget_new_modules_20261119.sh
#   Sign, commit and push both repos (the OPERATOR runs this):
#     RATIFY_OPERATOR='<your name>' bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_loop_code_budget_new_modules_20261119.sh --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-NEW-MODULES-20261119
#   Commit only (keep both stage worktrees, push nothing):  ... --apply --attest ... --no-push
#   Verify origin/main (read-only):  bash <this script> --verify
#
# ratify-targets: scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json
#
# Idempotent: once every in-scope module has an entry, it says ALREADY RATIFIED. Touches no process and no checkout.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"
SCRIPT_REL="scripts/operator/ratify_ak_loop_code_budget_new_modules_20261119.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-ak-loop-code-budget"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-LOOP-CODE-BUDGET-NEW-MODULES-20261119"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_loop_code_budget_new_modules_20261119.json"
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

# ---- the closed module table: file<TAB>box<TAB>one-line reason
MODULES_TSV="$(cat <<'TBL'
a2_unit_permit.py	AKU-04f / S3-AKU-01	per-unit A2 permit records
a2_unit_transport.py	AKU-04f	v2 unit records in journal validation, opt-in selected-unit transport glue
amdahl.py	AK-AMDAHL-PRUNE	e2e ceilings for the Amdahl prune
att_mfma_efficiency.py	INF48-LIVE-6	ATT MFMA efficiency signal
build_enrollment.py	AKU-10i / AKU-06i	versioned build enrollment records
call_budget.py	OAB-32	default per-call wall budget for every role and kind
composed_census.py	AKX-P3a	composed-census check on the ValidationBatch freeze
census_live.py	AKX-P1d	live census plumbing: taskset-pinned dispatch probe, census identity stamp
census_store.py	AKX-P1d	per-workload census store, freshness keys, live T0/T1 witnesses
cpu_aa_calibration.py	AK-GH-1 (TOUCHED-only LOO)	CPU A/A calibration record
cpu_keep_bundle.py	AK-GH-1 (TOUCHED-only LOO)	CPU accumulator bundle v1
cross_lane_gate.py	cross-lane quality gate	per-lane ppl_contract acceptance at global promotion
exact_lane.py	INF06	exact-order lane and token-ID identity judge
exploration_policy_replay.py	AK-WM-3	offline exploration-policy replay (observe-only)
gcn_gym.py	INF48-LIVE-6	GCN-Gym host half
gcn_replay.py	C5-ISA-2	GCN-Gym replay driver (hipModuleLaunchKernel)
goodhart_count.py	S3-AKU-13	Goodharted-keep count
gpu_counter_signals.py	INF48-LIVE-6	counter-grounded planner signals
isa_claims.py	INF48-LIVE-6	ISA claim gate
keep_frontier.py	S3-AKU-04	keep frontier
lineage_edit_diagnostics.py	AK-WM-3 (AK-lineage)	proposal-level cycling and edit taxonomy
loo_touched.py	AK-GH-1 (TOUCHED-only LOO)	TOUCHED-only leave-one-out
native_observation_witnesses.py	AKU-07o	contention and GPU-residency witnesses from in-window observation bytes
native_server_token_evidence.py	AKU-07r	frozen-prompt v1 pin, same-server token evidence join
numerics_edge.py	AKX-ALL-31.EDGE	edge-value families and seeded-defect twins
numerics_native.py	AKX-ALL-31.NATIVE	host side of the AK_NUMERICS_V1 native producer
operation_accounting.py	AKU-06l	child accounting and operation settlement v2
pareto_retain.py	AKX-PARETO-RETAIN	census retains the per-workload Pareto front of near-misses
profile_refresh.py	AKU-10i / AKU-06i	profile refresh records
promotion_evidence.py	S3-AKU-07	held-out promotion evidence
quant_codespace.py	AKX-ALL-31.QDEC	exhaustive code-space dequant check, host side
reflexion.py	AK-PM-17	reflexion fields on the per-round attempt record
route_defaults.py	AKX-AUTO-9	generated default CPU routes by file family
serving_shares.py	AKX-ALL-16	GPU serving-shares input
stage_receipts.py	AK-RSM-1	stage-receipt stop/resume controller contract
trial_lifecycle.py	AKU-04f / S3-AKU-01	typed trial lifecycle
two_instance_floor.py	AKX-P2d	two-instance floor job (W3/W4/W6 NUMA-half recipes)
variance_input_producer.py	U3-SEED	variance_input producer from paired RUNTIME_CONFIG serving records
variance_keep.py	U3-SEED / S3-AKU-04	variance-only keep rule and keep-time wiring
TBL
)"

# ---- stage
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-loop-budget.XXXXXX")"
[ -d "$STAGE" ] || die "could not create a stage directory"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$KEEP_STAGE" -eq 0 ]; then
    [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
    [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
    rm -f "${STAGE:?}/current.json" "${STAGE:?}/new_baseline.json" "${STAGE:?}/plan.tsv" "${STAGE:?}/modules.tsv" \
          "${STAGE:?}/before.txt" "${STAGE:?}/after.txt" "${STAGE:?}/before_v.txt" "${STAGE:?}/after_v.txt"
    rmdir "${STAGE:?}" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"; RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"; WT_ADDED=1
printf '%s\n' "$MODULES_TSV" >"$STAGE/modules.tsv"

guard() {  # baseline-path -> guard output; rc ignored by callers
  ( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --baseline "$1" 2>&1 )
}
violations() { grep -E '^  - ' "$1" | sed 's/^  - //' | sort || true; }

# ---- plan: which in-scope modules lack an entry
( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --emit-baseline-json ) >"$STAGE/current.json" || die "guard could not emit current counts"
PLAN="$("$SYS_PY" - "$RWT/$BASELINE" "$STAGE/current.json" "$STAGE/modules.tsv" "$STAGE/new_baseline.json" "$STAGE/plan.tsv" <<'PYEOF'
import json, sys
base_p, cur_p, tbl_p, out_p, plan_p = sys.argv[1:6]
base = json.load(open(base_p)); cur = json.load(open(cur_p))["files"]
table = {}
for ln in open(tbl_p, encoding="utf-8").read().splitlines():
    if ln.strip():
        f, box, why = ln.split("\t"); table[f] = (box, why)
missing = sorted(n for n in cur if n not in base["files"] and n not in base["exceptions"])
unknown = [n for n in missing if n not in table]
if unknown:
    print("UNKNOWN " + " ".join(unknown)); sys.exit(0)
for n in missing:
    base["files"][n] = cur[n]
base["files"] = dict(sorted(base["files"].items()))
if missing:
    with open(out_p, "w") as fh:
        json.dump(base, fh, indent=2); fh.write("\n")
    with open(plan_p, "w") as fh:
        fh.write("".join(f"{n}\t{cur[n]}\t{table[n][0]}\t{table[n][1]}\n" for n in missing))
print("NEW %d" % len(missing))
PYEOF
)"
case "$PLAN" in
  UNKNOWN*) die "in-scope modules not in this script's table (extend the table, do not bypass): ${PLAN#UNKNOWN }" ;;
esac
SKIPPED="$(cut -f1 "$STAGE/modules.tsv" | while read -r f; do
  "$SYS_PY" -c 'import json,sys;sys.exit(0 if sys.argv[1] in json.load(open(sys.argv[2]))["files"] else 1)' "$f" "$STAGE/current.json" || echo "$f"
done)"

if [ "$MODE" = "verify" ]; then
  if [ "$PLAN" = "NEW 0" ]; then ok "every in-scope loop module has a baseline entry on research origin/main"
  else say "  FAIL  $PLAN module(s) still lack an entry"; exit 1; fi
  if g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null; then ok "root receipt on origin/main"
  else say "  FAIL  root receipt not on origin/main"; exit 1; fi
  exit 0
fi
if [ "$PLAN" = "NEW 0" ]; then say "ALREADY RATIFIED: no in-scope module lacks a baseline entry. Nothing to do."; exit 0; fi
say "== $PLAN module(s) to baseline =="
awk -F'\t' '{printf "  %-34s %5s  %-28s %s\n",$1,$2,$3,$4}' "$STAGE/plan.tsv"
[ -z "$SKIPPED" ] || say "== table entries not on research origin/main (skipped, re-run later): $(echo $SKIPPED) =="

# ---- before / after guard, additions-only proof
guard "$RWT/$BASELINE" >"$STAGE/before.txt" || true
violations "$STAGE/before.txt" >"$STAGE/before_v.txt"
guard "$STAGE/new_baseline.json" >"$STAGE/after.txt" || true
violations "$STAGE/after.txt" >"$STAGE/after_v.txt"
say "== guard violations BEFORE: $(wc -l <"$STAGE/before_v.txt") =="; cat "$STAGE/before_v.txt"
say "== guard violations AFTER: $(wc -l <"$STAGE/after_v.txt") =="; cat "$STAGE/after_v.txt"
"$SYS_PY" - "$RWT/$BASELINE" "$STAGE/new_baseline.json" "$STAGE/before_v.txt" "$STAGE/after_v.txt" <<'PYEOF' || die "postflight failed; nothing committed"
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
assert {k: v for k, v in a.items() if k != "files"} == {k: v for k, v in b.items() if k != "files"}, "non-files field changed"
assert all(b["files"][k] == v for k, v in a["files"].items()), "an existing ceiling changed"
assert set(b["files"]) > set(a["files"]), "no entries added"
bv = set(open(sys.argv[3]).read().splitlines()); av = set(open(sys.argv[4]).read().splitlines())
assert av <= bv, "a violation appeared that was not there before"
gone = bv - av
assert gone and all("no baseline entry" in v for v in gone), "only 'no baseline entry' violations may clear"
print("  ok    additions only; existing ceilings, exceptions, header untouched; %d violations cleared, 0 introduced" % len(gone))
PYEOF
say "== remaining AFTER violations are existing-file overruns and are NOT in this script's scope =="

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: nothing committed, pushed or kept."
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
cp "$STAGE/new_baseline.json" "$RWT/$BASELINE"
g "$RWT" add -- "$BASELINE"
[ "$(g "$RWT" diff --cached --name-only HEAD)" = "$BASELINE" ] || die "research index holds an unexpected path set"
g "$RWT" commit -q -m "autokernel: loop code budget baseline, $(wc -l <"$STAGE/plan.tsv") new modules, $GATE_ID (signed by $RATIFY_OPERATOR)" \
  -m "One files entry per new in-scope loop module at its current code-line count; no existing ceiling or exception changed. Boxes in the root receipt." \
  -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 1 ]; then
  push_main "$RES" "$RWT"; RES_COMMIT="$RATIFY_PUSHED_SHA"
  g "$RES" fetch -q origin main
  g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
  ok "research main $RES_COMMIT"
fi

# ---- root receipt (+ push)
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OPERATOR="$RATIFY_OPERATOR" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_COMMIT="$RES_COMMIT" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" \
SCRIPT_REL="$SCRIPT_REL" PLAN_TSV="$STAGE/plan.tsv" BASELINE="$BASELINE" "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Re-run."
import json, os
e = os.environ
mods = {}
for ln in open(e["PLAN_TSV"], encoding="utf-8").read().splitlines():
    n, c, box, why = ln.split("\t"); mods[n] = {"ceiling": int(c), "box": box, "reason": why}
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified",
    "ratified_at": e["TS"], "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {"1": "2026-11-19: prep a baseline ratify for the loop code-budget guard; AKX-ALL-29.4 recorded as no change, collect data"},
    "items": {"1": f"research {e['BASELINE']}: one files entry per new loop module (additions only)"},
    "modules": mods, "base_origin_main": e["BASE"], "research_commit": e["RES_COMMIT"],
    "applied_by": e["SCRIPT_REL"], "ratify_script_sha256": e["SCRIPT_SHA"], "processes_touched": [],
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
g "$WT" commit -q -m "RATIFIED $GATE_ID: loop code-budget baseline for new modules (signed by $RATIFY_OPERATOR)" \
  -m "Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL. No process touched." \
  -m "Operator-Ratified: yes" || die "root commit failed (hook?); re-run."
ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"; ok "root committed ${ROOT_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 1 ]; then
  push_main "$ROOT" "$WT"; ROOT_COMMIT="$RATIFY_PUSHED_SHA"
  g "$ROOT" fetch -q origin main
  g "$ROOT" merge-base --is-ancestor "$ROOT_COMMIT" origin/main || die "root $ROOT_COMMIT is not on origin/main after fetch"
fi
if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): research $RES_COMMIT in $RWT, root $ROOT_COMMIT in $WT"
  say "Remove afterwards: git -C $RES worktree remove $RWT; git -C $ROOT worktree remove $WT"
  exit 0
fi
say ""; say "RATIFIED $GATE_ID by $RATIFY_OPERATOR. research main: $RES_COMMIT  root main: $ROOT_COMMIT. NO PROCESS WAS TOUCHED."
