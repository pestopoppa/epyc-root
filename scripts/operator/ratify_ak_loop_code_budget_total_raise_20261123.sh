#!/bin/bash
# ratify_ak_loop_code_budget_total_raise_20261123.sh -- ONE operator signature CORRECTING the AutoKernel loop code
# budget total_ceiling. RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-20261123 was executed from a stale clone (old sizing), so research
# main carries total_ceiling 126598 with ZERO headroom (research dab0660a7). The operator ruling was
# "measured + 2% headroom". This raise changes EXACTLY ONE field of the research baseline:
#   total_ceiling 126598 -> max(129130, ceil(measured loop/ code total at signing x 1.02))
#   (measured with the guard's own code-only metric: composition_by_file over loop/), plus the approval id
#   total_ceiling_approval -> RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-RAISE-20261123 (the guard needs a RATIFY-* id on a raise).
# Nothing else in the baseline may change (postflight enforces it). The research commit carries the
# "Operator-Ratified: yes" trailer the guard (research 48997f7f0) demands; the root commit records the receipt.
#
#   Review / dry run (default; throwaway worktrees, nothing pushed or kept):
#     bash scripts/operator/ratify_ak_loop_code_budget_total_raise_20261123.sh
#   Dry-apply THROUGH THE REAL GIT HOOKS (commits in the throwaway stages, never pushes, then discards):
#     bash scripts/operator/ratify_ak_loop_code_budget_total_raise_20261123.sh --dry-apply
#   Sign, commit and push both repos (the OPERATOR runs this ONE line; piped from origin/main, so a stale clone cannot run old code):
#     git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/ratify_ak_loop_code_budget_total_raise_20261123.sh | ROOT=/mnt/raid0/llm/epyc-root RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-RAISE-20261123
#   Commit only (keep stage worktrees, push nothing):  ... --apply --attest ... --no-push
#   Verify origin/main (read-only):  ... --verify
#
# ratify-targets: scripts/kernel_rnd/autokernel/loop_code_budget_baseline.json
#
# Idempotent: once total_ceiling_approval carries this gate id AND the root receipt is on origin/main it says
# ALREADY RATIFIED; if only the research half landed, a re-run writes just the root receipt. Touches no process.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_REL="scripts/operator/ratify_ak_loop_code_budget_total_raise_20261123.sh"
SRC="${BASH_SOURCE[0]:-}"
if [ -n "$SRC" ] && [ -f "$SRC" ]; then
  SCRIPT_PATH="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"
  ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
  PIPED=0
else
  [ -n "${ROOT:-}" ] || { echo "REFUSING: piped run (no script file) needs ROOT=<epyc-root clone>" >&2; exit 64; }
  SCRIPT_PATH=""
  PIPED=1
fi
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"
STAGE_PARENT="${STAGE_PARENT:-/mnt/raid0/llm/tmp}"
LOCK_AGENT="operator-ratify-ak-loop-code-budget-raise"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-RAISE-20261123"
OLD_GATE="RATIFY-AK-LOOP-CODE-BUDGET-TOTAL-20261123"
OLD_TOTAL=126598
FLOOR_TOTAL=129130   # ceil(126598 x 1.02): the floor if the measured total is still 126598
HEADROOM_PCT=2       # operator ruling 2026-11-23: total = measured + 2%
REASON="corrects stale-clone execution of the 2026-11-23 total ratify; operator ruling measured+2%"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ak_loop_code_budget_total_raise_20261123.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
AK="scripts/kernel_rnd/autokernel"
BASELINE="$AK/loop_code_budget_baseline.json"
GUARD_MOD="scripts.kernel_rnd.autokernel.check_regrowth_guards"

MODE="review"; ATTEST=""; DO_PUSH=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --dry-apply) MODE="dry-apply" ;;
    --apply)   MODE="apply" ;;
    --verify)  MODE="verify" ;;
    --no-push) DO_PUSH=0 ;;
    --attest)  shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --dry-apply | --verify | --apply --attest $GATE_ID [--no-push]]" >&2; exit 64 ;;
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
ONE_LINER="git -C $ROOT fetch -q origin main && git -C $ROOT show origin/main:$SCRIPT_REL | ROOT=$ROOT RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest $GATE_ID"

if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply needs the typed confirmation --attest $GATE_ID. Nothing written."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  say "signer: $RATIFY_OPERATOR"
fi
SIGNER="${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}"

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
g "$RES" fetch -q origin main || die "cannot fetch origin main in $RES"
ROOT_BASE="$(g "$ROOT" rev-parse origin/main)"
RES_BASE="$(g "$RES" rev-parse origin/main)"
say "== root origin/main $ROOT_BASE =="
say "== research origin/main $RES_BASE =="

if [ "$MODE" = "verify" ]; then
  g "$RES" show "origin/main:$BASELINE" | "$SYS_PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("total_ceiling_approval")==sys.argv[1] and d.get("total_ceiling",0)>=int(sys.argv[2]) else 1)' "$GATE_ID" "$FLOOR_TOTAL" \
    && ok "research baseline carries total_ceiling >= $FLOOR_TOTAL under $GATE_ID" || { say "  FAIL  research baseline not raised under $GATE_ID"; exit 1; }
  for f in "$RECEIPT_REL" "$INDEX_REL"; do
    g "$ROOT" cat-file -e "origin/main:$f" 2>/dev/null && ok "$f on origin/main" || { say "  FAIL  $f not on origin/main"; exit 1; }
  done
  say "VERIFIED: $GATE_ID is on research and root origin/main, receipted."; exit 0
fi

STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-loop-raise.XXXXXX")"
[ -d "$STAGE" ] || die "could not create a stage directory"
WT="$STAGE/root"; RWT="$STAGE/research"; WT_ADDED=0; RWT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$? f
  if [ "$KEEP_STAGE" -eq 0 ]; then
    if [ "$RWT_ADDED" -eq 1 ]; then
      g "$RWT" checkout -q -- . >/dev/null 2>&1 || true
      g "$RES" worktree remove "$RWT" >/dev/null 2>&1 || say "WARN: stage worktree left at $RWT (git -C $RES worktree remove $RWT)"
    fi
    if [ "$WT_ADDED" -eq 1 ]; then
      g "$WT" checkout -q -- . >/dev/null 2>&1 || true
      for f in "$RECEIPT_REL" "$INDEX_REL"; do
        if [ -e "$WT/$f" ] && ! g "$WT" ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
          bash "$ROOT/scripts/safety/guarded_rm.sh" "$WT/$f" >/dev/null 2>&1 || true
        fi
      done
      g "$ROOT" worktree remove "$WT" >/dev/null 2>&1 || say "WARN: stage worktree left at $WT (git -C $ROOT worktree remove $WT)"
    fi
    bash "$ROOT/scripts/safety/guarded_rm.sh" "$STAGE" >/dev/null 2>&1 || say "WARN: stage dir left at $STAGE"
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || die "could not stage a research worktree"; RWT_ADDED=1
g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || die "could not stage a root worktree"; WT_ADDED=1
if [ "$PIPED" -eq 1 ]; then
  SCRIPT_PATH="$WT/$SCRIPT_REL"
  [ -f "$SCRIPT_PATH" ] || die "piped run: $SCRIPT_REL is not on origin/main, so the bytes that ran cannot be hashed"
  ok "piped run: script bytes = origin/main copy, sha256 $(sha "$SCRIPT_PATH" | cut -c1-12)"
fi
grep -q 'def check_total_raise' "$RWT/$AK/check_regrowth_guards.py" \
  || die "research origin/main does not carry the total-budget guard (48997f7f0); land it first"

# ---- plan
( cd "$RWT" && FLOOR="$FLOOR_TOTAL" PCT="$HEADROOM_PCT" GATE="$GATE_ID" OLDGATE="$OLD_GATE" OLDTOTAL="$OLD_TOTAL" B="$BASELINE" \
  OUT="$STAGE/new_baseline.json" PLAN="$STAGE/plan.json" "$SYS_PY" - <<'PYEOF'
import json, os
import scripts.kernel_rnd.autokernel.check_regrowth_guards as g
from pathlib import Path
e = os.environ
raw = json.loads(Path(e["B"]).read_text(encoding="utf-8"))
measured = sum(g.composition_by_file(Path("scripts/kernel_rnd/autokernel/loop")).values())
pct = int(e["PCT"])
raw_new = -(-measured * (100 + pct) // 100)          # ceil(measured * 1.02), integer-exact
new_total = max(int(e["FLOOR"]), raw_new)
if raw.get("total_ceiling_approval") == e["GATE"]:
    state, new_total = "RESUME", raw["total_ceiling"]   # research half already landed
else:
    state = "FRESH"
    if raw.get("total_ceiling") != int(e["OLDTOTAL"]) or raw.get("total_ceiling_approval") != e["OLDGATE"]:
        raise SystemExit(f"baseline is total_ceiling={raw.get('total_ceiling')!r} approval={raw.get('total_ceiling_approval')!r}; "
                         f"expected {e['OLDTOTAL']} under {e['OLDGATE']}. The base changed; re-derive, do not overwrite.")
    new = dict(raw)                                   # key order preserved: only two values change
    new["total_ceiling"] = new_total
    new["total_ceiling_approval"] = e["GATE"]
    assert not g.validate_baseline(new), g.validate_baseline(new)
    Path(e["OUT"]).write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
plan = {"state": state, "old_total_ceiling": int(e["OLDTOTAL"]), "old_gate": e["OLDGATE"],
        "measured_total": measured, "headroom_pct": pct, "ceil_measured_x_1_02": raw_new,
        "floor": int(e["FLOOR"]), "new_total_ceiling": new_total, "headroom_lines": new_total - measured}
Path(e["PLAN"]).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
PYEOF
) >"$STAGE/plan.out" 2>&1 || { cat "$STAGE/plan.out" >&2; die "could not plan"; }
STATE="$("$SYS_PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["state"])' "$STAGE/plan.json")"
NEW_TOTAL="$("$SYS_PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["new_total_ceiling"])' "$STAGE/plan.json")"
if [ "$STATE" = "RESUME" ] && g "$WT" cat-file -e "HEAD:$INDEX_REL" 2>/dev/null; then
  say "ALREADY RATIFIED: total_ceiling_approval carries $GATE_ID and the root receipt is on origin/main. Nothing to do."; exit 0
fi
say "== plan: total_ceiling = max($FLOOR_TOTAL, ceil(measured x 1.02)); state=$STATE =="; cat "$STAGE/plan.json"

# postflight (pure function of two baseline files): exactly total_ceiling + approval differ, nothing else
postflight() {  # old.json new.json
  "$SYS_PY" - "$1" "$2" "$GATE_ID" "$OLD_TOTAL" "$NEW_TOTAL" <<'PYEOF'
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
gate, old_total, new_total = sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
assert changed == ["total_ceiling", "total_ceiling_approval"], f"fields changed: {changed}"
assert list(a) == list(b), "key set or order changed"
assert a["total_ceiling"] == old_total, f"old total {a['total_ceiling']} != {old_total}"
assert b["total_ceiling"] == new_total and new_total > old_total, f"new total {b['total_ceiling']}"
assert b["total_ceiling_approval"] == gate and gate.startswith("RATIFY-")
print("  ok    postflight: only total_ceiling (%d -> %d) and total_ceiling_approval changed" % (old_total, new_total))
PYEOF
}

if [ "$STATE" = "FRESH" ]; then
  postflight "$RWT/$BASELINE" "$STAGE/new_baseline.json" || die "postflight failed; nothing committed"
  ( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" --baseline "$STAGE/new_baseline.json" --no-raise-check ) >"$STAGE/after.txt" 2>&1 \
    || { cat "$STAGE/after.txt"; die "guard is red on the new baseline"; }
  grep -E 'loop code budget:' "$STAGE/after.txt" | sed 's/^/  ok    /' || true
fi

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: nothing committed, pushed or kept. Planned total_ceiling: $OLD_TOTAL -> $NEW_TOTAL."
  say "Sign with ONE command:"
  say "  $ONE_LINER"
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
  bash "$ROOT/scripts/safety/guarded_rm.sh" "$tokdir" >/dev/null 2>&1 || true
  [ "$prc" -eq 0 ] || die "push rejected in $2 (rc=$prc; origin/main probably moved). Re-run."
}

# ---- research commit (+ push)
if [ "$STATE" = "FRESH" ]; then
  cp "$STAGE/new_baseline.json" "$RWT/$BASELINE"
  g "$RWT" add -- "$BASELINE"
  [ "$(g "$RWT" diff --cached --name-only HEAD)" = "$BASELINE" ] || die "research index holds an unexpected path set"
  g "$RWT" commit -q -m "autokernel: loop code budget total_ceiling $OLD_TOTAL -> $NEW_TOTAL, $GATE_ID (signed by $SIGNER)" \
    -m "Corrects the stale-clone execution of $OLD_GATE (old sizing, zero headroom). Operator ruling: total = measured + 2%. Formula: max($FLOOR_TOTAL, ceil(measured x 1.02)). Only total_ceiling and total_ceiling_approval change. Receipt in epyc-root: $RECEIPT_REL." \
    -m "Operator-Ratified: yes" || die "research commit failed (hook?). Nothing pushed; re-run."
  RES_COMMIT="$(g "$RWT" rev-parse HEAD)"; ok "research committed ${RES_COMMIT:0:12}"
  g "$RWT" show "HEAD^:$BASELINE" >"$STAGE/parent_baseline.json"
  postflight "$STAGE/parent_baseline.json" "$RWT/$BASELINE" || die "postflight on the committed baseline failed; nothing pushed"
  ( cd "$RWT" && "$SYS_PY" -m "$GUARD_MOD" ) >"$STAGE/after.txt" 2>&1 || { cat "$STAGE/after.txt"; die "guard (with raise check) red after commit; nothing pushed"; }
  ok "guard green with the git raise check on the signed commit"
  grep -E 'loop code budget:|raise check' "$STAGE/after.txt" | sed 's/^/  ok    /' || true
  if [ "$MODE" = "apply" ] && [ "$DO_PUSH" -eq 1 ]; then
    push_main "$RES" "$RWT"
    g "$RES" fetch -q origin main
    g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
    ok "research main $RES_COMMIT"
  fi
else
  RES_COMMIT="$(g "$RWT" log -1 --format=%H -- "$BASELINE")"
  ok "resume: research half already on origin/main ($RES_COMMIT); writing the root receipt only"
fi

# ---- root receipt (+ push)
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" OLD_GATE="$OLD_GATE" OPERATOR="$SIGNER" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE="$ROOT_BASE" RES_BASE="$RES_BASE" RES_COMMIT="$RES_COMMIT" \
SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" PLAN_JSON="$STAGE/plan.json" BASELINE="$BASELINE" \
REASON="$REASON" "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Re-run."
import json, os
e = os.environ
plan = json.load(open(e["PLAN_JSON"]))
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified",
    "ratified_at": e["TS"], "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "reason": e["REASON"],
    "operator_decisions": {"1": "2026-11-23 operator: total code-line ceiling = measured + 2% headroom (correction of a stale-clone execution)"},
    "items": {"1": f"research {e['BASELINE']}: total_ceiling {plan['old_total_ceiling']} -> {plan['new_total_ceiling']}"},
    "old": {"total_ceiling": plan["old_total_ceiling"], "total_ceiling_approval": e["OLD_GATE"],
            "research_commit": "dab0660a7"},
    "new": {"total_ceiling": plan["new_total_ceiling"], "total_ceiling_approval": e["GATE_ID"]},
    "sizing": {"rule": "total_ceiling = max(floor, ceil(measured_total_at_signing * 1.02))",
               "formula": "ceil(measured_total * 1.02)", "floor": plan["floor"],
               "metric": "guard code-only metric: sum(composition_by_file(loop/)) in check_regrowth_guards",
               "measured_total": plan["measured_total"], "headroom_pct": plan["headroom_pct"],
               "headroom_lines": plan["headroom_lines"], "ceil_measured_x_1_02": plan["ceil_measured_x_1_02"]},
    "fields_changed": ["total_ceiling", "total_ceiling_approval"],
    "obligation": "any later raise of total_ceiling is a new operator ratify; lowering is ordinary code (--tighten-total)",
    "base_origin_main": e["BASE"], "research_base": e["RES_BASE"], "research_commit_new": e["RES_COMMIT"],
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
g "$WT" commit -q -m "RATIFIED $GATE_ID: AutoKernel loop code budget total_ceiling $OLD_TOTAL -> $NEW_TOTAL (signed by $SIGNER)" \
  -m "$REASON. Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL. No process touched." \
  -m "Operator-Ratified: yes" || die "root commit failed (hook?); re-run."
ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"; ok "root committed ${ROOT_COMMIT:0:12}"
if [ "$MODE" = "dry-apply" ]; then
  say ""
  say "DRY-APPLY COMPLETE: both signed commits passed the real hooks in throwaway stages and are DISCARDED (never pushed)."
  say "Sign with ONE command:"
  say "  $ONE_LINER"
  exit 0
fi
if [ "$DO_PUSH" -eq 1 ]; then
  push_main "$ROOT" "$WT"
  g "$ROOT" fetch -q origin main
  g "$ROOT" merge-base --is-ancestor "$ROOT_COMMIT" origin/main || die "root $ROOT_COMMIT is not on origin/main after fetch"
fi
if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): research ${RES_COMMIT} in $RWT, root $ROOT_COMMIT in $WT"
  say "Remove afterwards: git -C $RES worktree remove $RWT; git -C $ROOT worktree remove $WT"
  exit 0
fi
say ""; say "RATIFIED $GATE_ID by $SIGNER. total_ceiling $OLD_TOTAL -> $NEW_TOTAL. research main: $RES_COMMIT  root main: $ROOT_COMMIT. NO PROCESS WAS TOUCHED."
