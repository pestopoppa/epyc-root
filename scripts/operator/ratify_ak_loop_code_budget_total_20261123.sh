#!/bin/bash
# ratify_ak_loop_code_budget_total_20261123.sh -- ONE operator signature migrating the AutoKernel loop code
# budget to a single total (operator ruling 2026-11-23: "Adopt the total-budget redesign"; audit
# /mnt/raid0/llm/tmp/code-budget-audit-20261123/REPORT.md §5).
#
# WHAT YOU ARE SIGNING (research scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json, nothing else):
#   1. "total_ceiling" = max(126300, ceil(measured loop/ code total at signing x 1.02)) -- operator ruling
#      2026-11-23: "measured + 2% headroom". Measured with the guard's own code-only metric
#      (composition_by_file over loop/); the census branch has landed, so there is no census allowance.
#   2. "total_ceiling_approval" = this gate id.
#   3. The per-file "exceptions" block is retired (per-file numbers are advisory after research 48997f7f0).
#   The guard (research 48997f7f0+) then fails only when loop/ total > total_ceiling; raising it again needs
#   another operator ratify (the guard refuses an unsigned raise from git history).
#
#   Review / dry run (default; throwaway worktrees, nothing pushed or kept):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_loop_code_budget_total_20261123.sh
#   Sign, commit and push both repos (the OPERATOR runs this):
#     RATIFY_OPERATOR='<your name>' bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_ak_loop_code_budget_total_20261123.sh --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-20261123
#   Commit only (keep stage worktrees, push nothing):  ... --apply --attest ... --no-push
#   Verify origin/main (read-only):  bash <this script> --verify
#
# ratify-targets: scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json
#
# Idempotent: once total_ceiling carries this gate id it says ALREADY RATIFIED. Touches no process.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"
SCRIPT_REL="scripts/operator/ratify_ak_loop_code_budget_total_20261123.sh"
STAGE_PARENT="${STAGE_PARENT:-/mnt/raid0/llm/tmp}"
LOCK_AGENT="operator-ratify-ak-loop-code-budget"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-20261123"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_loop_code_budget_total_20261123.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
AK="scripts/kernel_rnd/autokernel"
BASELINE="$AK/loop_code_budget_baseline.json"
GUARD_MOD="scripts.kernel_rnd.autokernel.check_regrowth_guards"
FLOOR_TOTAL=126300
HEADROOM_PCT=2   # operator ruling 2026-11-23: total = measured + 2%
RULING='2026-11-23 operator: "Adopt the total-budget redesign." (code-budget audit REPORT.md §5); sizing ruling 2026-11-23: total = measured + 2% headroom'

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

if [ "$MODE" = "verify" ]; then
  g "$RES" show "origin/main:$BASELINE" | "$SYS_PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("total_ceiling_approval")==sys.argv[1] and "exceptions" not in d else 1)' "$GATE_ID" \
    && ok "research baseline carries total_ceiling under $GATE_ID, exceptions retired" || { say "  FAIL  research baseline not migrated"; exit 1; }
  g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && ok "root receipt on origin/main" || { say "  FAIL  root receipt not on origin/main"; exit 1; }
  exit 0
fi

STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-loop-total.XXXXXX")"
[ -d "$STAGE" ] || die "could not create a stage directory"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$KEEP_STAGE" -eq 0 ]; then
    [ "$RWT_ADDED" -eq 0 ] || g "$RES" worktree remove "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
    [ "$WT_ADDED" -eq 0 ] || g "$ROOT" worktree remove "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
    rm -f "${STAGE:?}/new_baseline.json" "${STAGE:?}/plan.json" "${STAGE:?}/after.txt"
    rmdir "${STAGE:?}" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"; RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"; WT_ADDED=1
grep -q 'def effective_total_ceiling' "$RWT/$AK/check_regrowth_guards.py" \
  || die "research origin/main does not carry the total-budget guard (48997f7f0); land it first"

# ---- plan
( cd "$RWT" && FLOOR="$FLOOR_TOTAL" PCT="$HEADROOM_PCT" GATE="$GATE_ID" B="$BASELINE" OUT="$STAGE/new_baseline.json" PLAN="$STAGE/plan.json" "$SYS_PY" - <<'PYEOF'
import json, os
import scripts.kernel_rnd.autokernel.check_regrowth_guards as g
from pathlib import Path
e = os.environ
raw = json.loads(Path(e["B"]).read_text(encoding="utf-8"))
if raw.get("total_ceiling_approval") == e["GATE"]:
    print("ALREADY"); raise SystemExit(0)
measured = sum(g.composition_by_file(Path("scripts/kernel_rnd/autokernel/loop")).values())
old, old_src = g.effective_total_ceiling(raw)
pct = int(e["PCT"])
new_total_raw = -(-measured * (100 + pct) // 100)   # ceil(measured * 1.02), integer-exact
headroom = new_total_raw - measured
new_total = max(int(e["FLOOR"]), new_total_raw)
new = {k: v for k, v in raw.items() if k not in ("exceptions", "total_ceiling", "total_ceiling_approval")}
new["total_ceiling"] = new_total
new["total_ceiling_approval"] = e["GATE"]
assert not g.validate_baseline(new), g.validate_baseline(new)
Path(e["OUT"]).write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
plan = {"old_total_ceiling": old, "old_total_ceiling_source": old_src,
        "old_total_ceiling_field": raw.get("total_ceiling"),
        "old_exceptions_count": len(raw.get("exceptions", {})),
        "old_exceptions_ceiling_sum": sum(x["ceiling"] for x in raw.get("exceptions", {}).values()),
        "measured_total": measured, "headroom_pct": pct, "headroom_lines": headroom,
        "ceil_measured_x_1_02": new_total_raw,
        "floor": int(e["FLOOR"]), "new_total_ceiling": new_total,
        "files_entries_unchanged": len(raw["files"])}
Path(e["PLAN"]).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
print("PLAN")
PYEOF
) >"$STAGE/plan.out" || die "could not plan"
if grep -qx ALREADY "$STAGE/plan.out"; then rm -f "$STAGE/plan.out"; say "ALREADY RATIFIED: total_ceiling carries $GATE_ID. Nothing to do."; exit 0; fi
rm -f "$STAGE/plan.out"
say "== plan (total = max($FLOOR_TOTAL, ceil(measured x 1.02))) =="; cat "$STAGE/plan.json"

# ---- postflight: only the three intended changes, and the guard is green on the new baseline
"$SYS_PY" - "$RWT/$BASELINE" "$STAGE/new_baseline.json" <<'PYEOF' || die "postflight failed; nothing committed"
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
strip = lambda d: {k: v for k, v in d.items() if k not in ("exceptions", "total_ceiling", "total_ceiling_approval")}
assert strip(a) == strip(b), "a field other than total_ceiling/approval/exceptions changed"
assert "exceptions" not in b
print("  ok    only total_ceiling, total_ceiling_approval and the exceptions retirement differ")
PYEOF
( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --baseline "$STAGE/new_baseline.json" --no-raise-check ) >"$STAGE/after.txt" 2>&1 \
  || { cat "$STAGE/after.txt"; die "guard is red on the new baseline"; }
grep -E 'loop code budget:' "$STAGE/after.txt" | sed 's/^/  ok    /'

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: nothing committed, pushed or kept."
  say "Sign with ONE command:"
  say "  RATIFY_OPERATOR='<your name>' bash $SCRIPT_PATH --apply --attest $GATE_ID"
  exit 0
fi

push_main() {  # repo-for-lock worktree
  local tokdir tok prc=0
  tokdir="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$1" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || die "could not take the push lock for $1; re-run."
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$2" push -q origin HEAD:refs/heads/main || prc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$1" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: push lock release failed for $1"
  rm -f "${tok:?}"; rmdir "${tokdir:?}" 2>/dev/null || true
  [ "$prc" -eq 0 ] || die "push rejected in $2 (rc=$prc; origin/main probably moved). Re-run."
}

# ---- research commit (+ push)
cp "$STAGE/new_baseline.json" "$RWT/$BASELINE"
g "$RWT" add -- "$BASELINE"
[ "$(g "$RWT" diff --cached --name-only HEAD)" = "$BASELINE" ] || die "research index holds an unexpected path set"
NEW_TOTAL="$("$SYS_PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["new_total_ceiling"])' "$STAGE/plan.json")"
g "$RWT" commit -q -m "autokernel: loop code budget total_ceiling $NEW_TOTAL, exceptions retired, $GATE_ID (signed by $RATIFY_OPERATOR)" \
  -m "Total-budget migration (code-budget audit 2026-11-23 §5). Old and new values in the root receipt." \
  -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" ) >"$STAGE/after.txt" 2>&1 || { cat "$STAGE/after.txt"; die "guard (with raise check) red after commit; nothing pushed"; }
ok "guard green with the git raise check on the signed commit"
if [ "$DO_PUSH" -eq 1 ]; then
  push_main "$RES" "$RWT"
  g "$RES" fetch -q origin main
  g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
  ok "research main $RES_COMMIT"
fi

# ---- root receipt (+ push)
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OPERATOR="$RATIFY_OPERATOR" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_BASE="$RES_BASE" RES_COMMIT="$RES_COMMIT" \
SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" PLAN_JSON="$STAGE/plan.json" BASELINE="$BASELINE" \
RULING="$RULING" "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Re-run."
import json, os
e = os.environ
plan = json.load(open(e["PLAN_JSON"]))
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified",
    "ratified_at": e["TS"], "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {"1": e["RULING"]},
    "items": {"1": f"research {e['BASELINE']}: total_ceiling {plan['old_total_ceiling']} -> {plan['new_total_ceiling']}",
              "2": f"research {e['BASELINE']}: per-file exceptions block retired ({plan['old_exceptions_count']} entries)"},
    "old": {"total_ceiling": plan["old_total_ceiling"], "source": plan["old_total_ceiling_source"],
            "total_ceiling_field": plan["old_total_ceiling_field"],
            "exceptions_count": plan["old_exceptions_count"],
            "exceptions_ceiling_sum": plan["old_exceptions_ceiling_sum"]},
    "new": {"total_ceiling": plan["new_total_ceiling"], "total_ceiling_approval": e["GATE_ID"], "exceptions": None},
    "sizing": {"rule": "total_ceiling = max(floor, ceil(measured_total_at_signing * 1.02))",
               "formula": "ceil(measured_total * 1.02)", "floor": plan["floor"],
               "metric": "guard code-only metric: sum(composition_by_file(loop/)) in check_regrowth_guards",
               "measured_total": plan["measured_total"], "headroom_pct": plan["headroom_pct"],
               "headroom_lines": plan["headroom_lines"], "ceil_measured_x_1_02": plan["ceil_measured_x_1_02"],
               "operator_ruling": "2026-11-23 operator: set total code-line ceiling to measured + 2% headroom"},
    "unsigned_entries_ratified_here": {
        "cpu_fold_record.py": {"files_ceiling": 69, "research_commit": "3f49fb474",
                               "note": "added unsigned 2026-11-23, ratified here (counted in measured_total)"},
        "accumulator_surfaces.py": {"files_ceiling": 86, "research_commit": "1be8120bf",
                                    "note": "added unsigned 2026-11-23, ratified here (counted in measured_total)"}},
    "obligation": "any later raise of total_ceiling is a new operator ratify; lowering is ordinary code (--tighten-total)",
    "base_origin_main": e["BASE"], "research_base": e["RES_BASE"], "research_commit": e["RES_COMMIT"],
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
g "$WT" commit -q -m "RATIFIED $GATE_ID: AutoKernel loop code budget becomes one total (signed by $RATIFY_OPERATOR)" \
  -m "Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL. No process touched." \
  -m "Operator-Ratified: yes" || die "root commit failed (hook?); re-run."
ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"; ok "root committed ${ROOT_COMMIT:0:12}"
if [ "$DO_PUSH" -eq 1 ]; then
  push_main "$ROOT" "$WT"
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
