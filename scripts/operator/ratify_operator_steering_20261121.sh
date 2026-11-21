#!/bin/bash
# ratify_operator_steering_20261121.sh — ONE operator signature for the three human-only rules of the operator-steering
# analysis (/mnt/raid0/llm/tmp/operator-steering-analysis-20261121/REPORT.md §2(b) "Rules"; the non-hook mechanisms
# landed separately in scripts/session/ and .claude/skills/report-format/):
#   1. "An authorized action is executed, not re-asked."
#   2. "A report's last line is the next action and its owner."
#   3. "Re-probe a blocker older than one hour before repeating it."
#   agents/shared/OPERATING_CONSTRAINTS.md  Act, Don't Defer: a new "Reporting and acting" block carrying the 3 rules
#   agents/shared/SESSION_LIFECYCLE.md      At every task boundary: boundary reports follow the rules (pointer)
#   CLAUDE.md                               Act, Don't Defer: one bullet naming the 3 rules + the report-format skill
# Additions only; nothing else changes. The transform is inline below (exact, single-occurrence anchors).
# Modelled exactly on ratify_task_brief_20261120.sh.
#
#   Review (default; trial apply in a throwaway worktree, prints the diff, keeps nothing):
#     bash scripts/operator/ratify_operator_steering_20261121.sh
#   Dry-apply THROUGH THE REAL GIT HOOKS (commits in the throwaway stage, never pushes, then discards):
#     bash scripts/operator/ratify_operator_steering_20261121.sh --dry-apply
#   Sign, commit and push (the OPERATOR runs this ONE line; piped from origin/main, works from a stale clone):
#     git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/ratify_operator_steering_20261121.sh | ROOT=/mnt/raid0/llm/epyc-root RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest RATIFY-OPERATOR-STEERING-20261121
#   Verify origin/main (read-only):   ... --verify
#
# ratify-targets: agents/shared/OPERATING_CONSTRAINTS.md agents/shared/SESSION_LIFECYCLE.md CLAUDE.md
# SAFETY: stages a detached worktree of origin/main; your checkout is never touched. Refuses unless every target's
# sha256 equals its PRE pin (or all POST pins = ALREADY RATIFIED). Touches no process.
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_REL="scripts/operator/ratify_operator_steering_20261121.sh"
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
STAGE_PARENT="${STAGE_PARENT:-/mnt/raid0/llm/tmp}"
LOCK_AGENT="operator-ratify-operator-steering"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-OPERATOR-STEERING-20261121"
TARGETS=("agents/shared/OPERATING_CONSTRAINTS.md" "agents/shared/SESSION_LIFECYCLE.md" "CLAUDE.md")
PRE_SHAS=("8e69280549e66d09bfc28315bec2d584523fdbe97829b4fdbb2dbe806ec8e6f5" "8cd48b8cbeff9489be9963535f4ddb5114d4682fbc3b8e610939726e60f74eb8" "5e7b8b5a0f0e102d8576b625a399ab2aa9a723e8cd84b4bbbe73abc88c38f7f5")
POST_SHAS=("7e5af9f8a61fdaa2c858a7f237630251651359c181690e0bfbbecb2ba6460063" "77064cc8b97e3615ee9996c6bdd9611013fe8a71b0be29152f06ab913987a047" "910f9e0de59c751643c7c1fbcc417ede2ec95f54acedfac8501f459853d6116a")
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_operator_steering_20261121.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_operator_steering_20261121.receipt.json"
PROTOCOL_ID="OPERATOR-STEERING-RULES-HUMAN-ONLY"
ANCHOR1="**An authorized action is executed, not re-asked.**"
ANCHOR2="**A report's last line is the next action and its owner.**"
ANCHOR3="**Re-probe a blocker older than one hour before repeating it.**"

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
g() { git -c safe.directory='*' -C "$@"; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
ok() { printf '  ok    %s\n' "$*"; }
for tool in git sha256sum awk diff "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "ROOT=$ROOT is not an epyc-root checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"

if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply needs the typed confirmation --attest $GATE_ID. Nothing written."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  say "signer: $RATIFY_OPERATOR"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
BASE="${BASE_REF:-origin/main}"
[ "$MODE" != "apply" ] || [ "$BASE" = "origin/main" ] || die "--apply always stages from origin/main; unset BASE_REF."
BASE_SHA="$(g "$ROOT" rev-parse --verify "$BASE^{commit}")" || die "cannot resolve $BASE"
say "== base $BASE = $BASE_SHA =="

if [ "$MODE" = "verify" ]; then
  for i in "${!TARGETS[@]}"; do
    have="$(g "$ROOT" show "origin/main:${TARGETS[$i]}" | sha256sum | awk '{print $1}')"
    [ "$have" = "${POST_SHAS[$i]}" ] || { say "  FAIL  ${TARGETS[$i]} is ${have:0:12}, post-state is ${POST_SHAS[$i]:0:12}"; exit 1; }
    ok "${TARGETS[$i]} at post-state ${POST_SHAS[$i]:0:12}"
  done
  for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
    g "$ROOT" cat-file -e "origin/main:$f" 2>/dev/null && ok "$f on origin/main" || { say "  FAIL  $f not on origin/main"; exit 1; }
  done
  say "VERIFIED: $GATE_ID is on origin/main, pinned and receipted."; exit 0
fi

# ---- stage
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-operator-steering.XXXXXX")"
WT="$STAGE/root"; WT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$WT_ADDED" -eq 1 ] && [ "$KEEP_STAGE" -eq 0 ]; then
    g "$WT" checkout -q -- . >/dev/null 2>&1 || true
    for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
      if [ -e "$WT/$f" ] && ! g "$WT" ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
        bash "$ROOT/scripts/safety/guarded_rm.sh" "$WT/$f" >/dev/null 2>&1 || true
      fi
    done
    g "$ROOT" worktree remove "$WT" >/dev/null 2>&1 || say "WARN: stage worktree left at $WT (inspect, then: git -C $ROOT worktree remove $WT)"
  fi
  if [ "$KEEP_STAGE" -eq 0 ] && [ -d "$STAGE" ]; then   # trash-first (guarded_rm.sh), never a raw delete
    bash "$ROOT/scripts/safety/guarded_rm.sh" "$STAGE" >/dev/null 2>&1 || say "WARN: stage dir left at $STAGE"
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$ROOT" worktree add -q --detach "$WT" "$BASE_SHA" || die "could not stage a worktree of $BASE"
WT_ADDED=1
ok "staged detached worktree $WT at ${BASE_SHA:0:12}"
if [ "$PIPED" -eq 1 ]; then
  SCRIPT_PATH="$WT/$SCRIPT_REL"
  [ -f "$SCRIPT_PATH" ] || die "piped run: $SCRIPT_REL is not on $BASE, so the bytes that ran cannot be hashed"
  ok "piped run: script bytes = origin/main copy, sha256 $(sha "$SCRIPT_PATH" | cut -c1-12)"
fi
ONE_LINER="git -C $ROOT fetch -q origin main && git -C $ROOT show origin/main:$SCRIPT_REL | ROOT=$ROOT RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest $GATE_ID"

# ---- preflight
say "== preflight (mode=$MODE) =="
all_post=1
for i in "${!TARGETS[@]}"; do [ "$(sha "$WT/${TARGETS[$i]}")" = "${POST_SHAS[$i]}" ] || all_post=0; done
if [ "$all_post" -eq 1 ] && [ -f "$WT/$INDEX_REL" ]; then
  say "ALREADY RATIFIED: the target is at its post-state pin and the receipt index is present. Nothing to do."; exit 0
fi
[ ! -e "$WT/$INDEX_REL" ] || die "receipt index exists but the target is not at the post-state pin (half state)."
for i in "${!TARGETS[@]}"; do
  have="$(sha "$WT/${TARGETS[$i]}")"
  [ "$have" = "${PRE_SHAS[$i]}" ] || die "${TARGETS[$i]} on $BASE is ${have:0:12}, expected pre-state ${PRE_SHAS[$i]:0:12}. The base changed since this script was prepared; re-derive the pins, do not overwrite."
  ok "${TARGETS[$i]} at pre-state ${PRE_SHAS[$i]:0:12}"
done
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 before the amendment"
else die "receipt checker does not exit 0 before the amendment"; fi

# ---- apply in the stage, show the exact change
mkdir -p "$STAGE/before"
for t in "${TARGETS[@]}"; do mkdir -p "$STAGE/before/$(dirname "$t")"; cp "$WT/$t" "$STAGE/before/$t"; done
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" \
  --state "${TARGETS[0]}" --state "${TARGETS[1]}" --state "${TARGETS[2]}" --out "$STAGE/pre.json" \
  || die "could not snapshot the pre-amendment state"
"$SYS_PY" - "$WT" <<'PYEOF' || die "transform refused (an anchor moved); nothing written"
import os, sys
wt = sys.argv[1]
EDITS = [
    ("agents/shared/OPERATING_CONSTRAINTS.md",
     "(origin: 2026-08-03, three consecutive identical \"Deferred\" lists; Appendix)\n",
     "\n**Reporting and acting (operator-steering analysis, ratified 2026-11-21).** About 73 % of the operator's turns\n"
     "compensated for an agent that did not act on, or did not report, what it already knew\n"
     "(`/mnt/raid0/llm/tmp/operator-steering-analysis-20261121/REPORT.md` §2). Three rules close that:\n\n"
     "- **An authorized action is executed, not re-asked.** Once the operator said go (approved, proceed, do it),\n"
     "  or a standing rule covers it, the next report says it is done or running. Asking again, or ending a\n"
     "  report on \"shall I?\", re-opens a closed decision.\n"
     "- **A report's last line is the next action and its owner.** `Next: <owner> <action> <when or trigger>`.\n"
     "  The rest of the report follows the `report-format` skill (`.claude/skills/report-format/`): headline,\n"
     "  numbers with unit/baseline/direction, running/queued with ETA, blocked on what until when and why, exact\n"
     "  operator commands from `scripts/session/pending_operator_cmds.py combined`, IDs expanded on first use.\n"
     "- **Re-probe a blocker older than one hour before repeating it.** `scripts/session/recheck_blocker.py`\n"
     "  (codex-login, which, python, model, disk, row); a CLEAR result means act, not report. A stale blocker\n"
     "  repeated as current is a false statement to the operator.\n"),
    ("agents/shared/SESSION_LIFECYCLE.md",
     "<session-id>` on clear — resume rather than rediscover if context was cleared by mistake.\n",
     "\n**Every boundary report ends on `Next:` + owner and repeats no unprobed blocker.** Whichever row above\n"
     "applies, the report that closes the boundary follows `OPERATING_CONSTRAINTS.md` → *Act, Don't Defer* →\n"
     "*Reporting and acting*: its last line is the next action and its owner, an authorized action is executed\n"
     "rather than re-asked, and a blocker older than one hour is re-probed (`scripts/session/recheck_blocker.py`)\n"
     "before it is repeated.\n"),
    ("CLAUDE.md",
     "- Mentioning something in passing is fine. Mentioning it **instead of doing it** is the failure.\n",
     "- **Reporting and acting (2026-11-21):** an authorized action is executed, not re-asked; a report's last line\n"
     "  is `Next:` + owner; re-probe a blocker older than 1 h (`scripts/session/recheck_blocker.py`) before\n"
     "  repeating it. Report shape: `.claude/skills/report-format/`. Canonical: `OPERATING_CONSTRAINTS.md` →\n"
     "  *Act, Don't Defer* → *Reporting and acting*.\n"),
]
for rel, anchor, add in EDITS:
    p = os.path.join(wt, rel)
    t = open(p, encoding="utf-8").read()
    if t.count(anchor) != 1:
        sys.exit(f"{rel}: anchor occurs {t.count(anchor)} times")
    open(p, "w", encoding="utf-8").write(t.replace(anchor, anchor + add, 1))
PYEOF
for i in "${!TARGETS[@]}"; do
  t="${TARGETS[$i]}"
  say "== exact change to $t =="
  diff -u --label "a/$t" --label "b/$t" "$STAGE/before/$t" "$WT/$t" || true
  [ "$(sha "$WT/$t")" = "${POST_SHAS[$i]}" ] || die "postflight: $t post-state $(sha "$WT/$t") != pin ${POST_SHAS[$i]}."
done
for an in "$ANCHOR1" "$ANCHOR2" "$ANCHOR3"; do
  n=$(grep -cF -- "$an" "$WT/${TARGETS[0]}" || true)
  [ "$n" -eq 1 ] || die "postflight: anchor occurs $n times in ${TARGETS[0]}: $an"
done
ok "targets at their post-state pins; anchors once"

# ---- receipts
say "== MEASUREMENT.md section-5 consolidated receipt =="
receipt_rc=0
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$WT" --pre "$STAGE/pre.json" --protocol-id "$PROTOCOL_ID" \
  --anchor "$ANCHOR1" --anchor "$ANCHOR2" --anchor "$ANCHOR3" \
  --ratification-id "$GATE_ID" --script "$SCRIPT_PATH" \
  --operator "${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
  --no-evidence-reason "workflow doctrine (operator-steering rules, steering analysis 2026-11-21 §2(b)), not a measured claim" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum ${TARGETS[0]} | cut -d' ' -f1)\" = ${POST_SHAS[0]}" \
  --validation "test \"\$(sha256sum ${TARGETS[1]} | cut -d' ' -f1)\" = ${POST_SHAS[1]}" \
  --validation "test \"\$(sha256sum ${TARGETS[2]} | cut -d' ' -f1)\" = ${POST_SHAS[2]}" \
  --out "$WT/$CONSOLIDATED_REL" || receipt_rc=$?
[ "$receipt_rc" -eq 0 ] || die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Nothing committed or pushed."
ok "consolidated receipt: $CONSOLIDATED_REL"

WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" \
TARGETS="${TARGETS[*]}" PRES="${PRE_SHAS[*]}" POSTS="${POST_SHAS[*]}" OPERATOR="${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" BASE_SHA="$BASE_SHA" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" \
"$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Nothing committed or pushed."
import json, os
e = os.environ
ts, pre, post = e["TARGETS"].split(), e["PRES"].split(), e["POSTS"].split()
doc = {"schema": "epyc.operating_constraints_amendment.v1", "gate_id": e["GATE_ID"], "status": "ratified",
       "ratified_at": e["TS"], "operator": e["OPERATOR"],
       "signature_channel": "operator-run script (--attest typed confirmation)",
       "operator_decisions": {"operator-steering": "2026-11-21 approval: non-hook mechanisms + three human-only rules (authorized action executed, not re-asked; report last line = next action + owner; re-probe a blocker older than 1 h)"},
       "base_origin_main": e["BASE_SHA"], "consolidated_receipt": e["CONSOLIDATED_REL"],
       "state": {t: {"sha256_before": a, "sha256_after": b} for t, a, b in zip(ts, pre, post)},
       "applied_by": e["SCRIPT_REL"], "ratify_script_sha256": e["SCRIPT_SHA"], "processes_touched": []}
wt = e["WT"]
with open(os.path.join(wt, e["RECEIPT_REL"]), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(wt, e["INDEX_REL"])), exist_ok=True)
with open(os.path.join(wt, e["INDEX_REL"]), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "ratify", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(f"  ok    decision receipt {e['RECEIPT_REL']}")
print(f"  ok    keyed index      {e['INDEX_REL']}")
PYEOF
"$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 && ok "receipt checker exits 0 after the amendment" \
  || die "receipt checker fails after the amendment. Nothing committed or pushed."

COMMIT_PATHS=("${TARGETS[@]}" "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")
if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: all checks passed in a throwaway stage. Nothing committed or pushed. --apply would commit:"
  printf '    %s\n' "${COMMIT_PATHS[@]}"
  say "Sign with ONE command:"
  say "    $ONE_LINER"
  exit 0
fi

# ---- commit (dry-apply commits too, in the stage, so the REAL commit-msg / pre-commit hooks judge it)
say "== commit (stage, detached at ${BASE_SHA:0:12}) =="
g "$WT" add -- "${COMMIT_PATHS[@]}"
staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged" = "$want" ] || die "stage index holds an unexpected path set; NOT committed. Staged: $(echo $staged)"
g "$WT" commit -q \
  -m "RATIFIED $GATE_ID: operator-steering reporting and acting rules (signed by ${RATIFY_OPERATOR:-DRY-APPLY})" \
  -m "OPERATING_CONSTRAINTS Act, Don't Defer gains 'Reporting and acting' (authorized action executed, not re-asked; a report's last line = next action + owner; re-probe a blocker older than 1 h); SESSION_LIFECYCLE task-boundary pointer; CLAUDE.md one bullet. Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
  -m "Operator-Ratified: yes" \
  || die "commit failed (a hook refused it?). Nothing pushed; re-run to retry."
COMMIT_SHA="$(g "$WT" rev-parse HEAD)"
ok "committed ${COMMIT_SHA:0:12} (real git hooks passed)"
if [ "$MODE" = "dry-apply" ]; then
  say "DRY-APPLY COMPLETE: the signed commit passed the real hooks in the throwaway stage and is DISCARDED (never pushed)."
  say "Sign with ONE command:"
  say "    $ONE_LINER"
  exit 0
fi
if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1; say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): $COMMIT_SHA in $WT"; exit 0
fi

say "== push (serialized, push lock) =="
TOKDIR="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$TOKDIR"; TOK="$TOKDIR/lease.token"
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --acquire --token-file "$TOK" >/dev/null \
  || die "could not take the push lock. Nothing pushed; re-run."
prc=0
AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$WT" push -q origin HEAD:refs/heads/main || prc=$?
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --release --token-file "$TOK" >/dev/null \
  || say "WARN: push lock release failed; check: python3 $PUSHER --agent $LOCK_AGENT --repo $ROOT --lock-name push --status"
bash "$ROOT/scripts/safety/guarded_rm.sh" "$TOKDIR" >/dev/null 2>&1 || true
[ "$prc" -eq 0 ] || die "git push rejected (rc=$prc; origin/main probably moved). Nothing landed; re-run."
g "$ROOT" fetch -q origin main
[ -z "$(g "$WT" cherry origin/main HEAD)" ] || die "push reported success but origin/main does not carry $COMMIT_SHA"
say "RATIFIED AND PUSHED: $COMMIT_SHA ($GATE_ID)"
