#!/bin/bash
# ratify_handoff_standard_20261120.sh — ONE operator signature for the handoff-standard Stage C human-only edits
# (C7 ratify package, /mnt/raid0/llm/tmp/dispatcher-redesign-20261119/STAGE-C-BRIEF.md §C7; operator decisions
# 1, 3, 5, 6 of 2026-11-19 in HANDOFF-STANDARD.md):
#   1. agents/shared/SESSION_LIFECYCLE.md  Two axioms: [ ]/[x] only, the ONE tick suffix and its writers, the /log
#      child form, `.box-index.json` as a planner read path, "and the generated index rows".
#   2. agents/shared/OPERATING_CONSTRAINTS.md  Dispatching Backlog Work: identity = text_sha of the first line,
#      screener source = .box-index.json + holds.yaml; ruling (b) gains the header/Status wording for the hand-row drop.
#   3. CLAUDE.md § Handoff Workflow: generated rows, header-not-row editing, diff-scoped --check, holds.yaml.
#   (agents/shared/INVARIANTS.md: unchanged — invariant 9 needs no dispatcher clause while taskflow is not live.)
# The text lives in scripts/operator/ratify_handoff_standard_xform_20261120.py (exact, single-occurrence anchors).
#
#   Review (default; trial apply in a throwaway worktree, prints the diff, keeps nothing):
#     bash scripts/operator/ratify_handoff_standard_20261120.sh
#   Dry-apply THROUGH THE REAL GIT HOOKS (commits in the throwaway stage, never pushes, then discards):
#     bash scripts/operator/ratify_handoff_standard_20261120.sh --dry-apply
#   Sign, commit and push (the OPERATOR runs this ONE line; piped from origin/main, works from a stale clone):
#     git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/ratify_handoff_standard_20261120.sh | ROOT=/mnt/raid0/llm/epyc-root RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest RATIFY-HANDOFF-STANDARD-20261120
#   Verify origin/main (read-only):   ... --verify
#
# ratify-targets: CLAUDE.md agents/shared/SESSION_LIFECYCLE.md agents/shared/OPERATING_CONSTRAINTS.md
# SAFETY: stages a detached worktree of origin/main; your checkout is never touched. Refuses unless every target's
# sha256 equals its PRE pin (or all equal the POST pins = ALREADY RATIFIED). Touches no process.
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_REL="scripts/operator/ratify_handoff_standard_20261120.sh"
# Piped invocation (`git show origin/main:<this> | ROOT=<clone> bash -s -- ...`): BASH_SOURCE is empty / not a file.
# Then ROOT is REQUIRED, and the script's own bytes are taken from the staged origin/main copy below (the exact bytes
# `git show origin/main:` piped in), so SCRIPT_SHA is the hash of what ran.
SRC="${BASH_SOURCE[0]:-}"
if [ -n "$SRC" ] && [ -f "$SRC" ]; then
  SCRIPT_PATH="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"
  ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
  PIPED=0
else
  [ -n "${ROOT:-}" ] || { echo "REFUSING: piped run (no script file) needs ROOT=<epyc-root clone>" >&2; exit 64; }
  SCRIPT_PATH=""   # set to the staged origin/main copy once the stage exists
  PIPED=1
fi
XFORM_REL="scripts/operator/ratify_handoff_standard_xform_20261120.py"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-handoff-standard"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-HANDOFF-STANDARD-20261120"
TARGETS=("CLAUDE.md" "agents/shared/SESSION_LIFECYCLE.md" "agents/shared/OPERATING_CONSTRAINTS.md")
PRE_SHAS=("7bebaeb7167415b3c85e2a663e1c002cfd8f19b912d8a78c1b90ece6132a6e6c"
          "5926bf19a8f8c7996ca7bd1ddfc663cf2e4caa5b6e96c70a6adffc93e60f7dfb"
          "b6ff16c9f66eea35dbbfc72de3704f56f499578a2edaaf558464f0939650c0d4")
POST_SHAS=("5e7b8b5a0f0e102d8576b625a399ab2aa9a723e8cd84b4bbbe73abc88c38f7f5"
           "8cd48b8cbeff9489be9963535f4ddb5114d4682fbc3b8e610939726e60f74eb8"
           "33e405bcab00eb8cc0ea8437dea395320801c1bff382c76163134d4f30a5c575")
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_handoff_standard_20261120.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_handoff_standard_20261120.receipt.json"
PROTOCOL_ID="HANDOFF-STANDARD-STAGE-C-HUMAN-ONLY"
ANCHOR1="count CHECKBOX STATE ONLY.** Prose status is"
ANCHOR2="**The identity is the box's first line, hashed.**"
ANCHOR3="**Handoff standard (2026-11-19/20)**"

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
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-handoff-standard.XXXXXX")"
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
  say "ALREADY RATIFIED: every target is at its post-state pin and the receipt index is present. Nothing to do."; exit 0
fi
[ ! -e "$WT/$INDEX_REL" ] || die "receipt index exists but the targets are not at the post-state pins (half state)."
for i in "${!TARGETS[@]}"; do
  have="$(sha "$WT/${TARGETS[$i]}")"
  [ "$have" = "${PRE_SHAS[$i]}" ] || die "${TARGETS[$i]} on $BASE is ${have:0:12}, expected pre-state ${PRE_SHAS[$i]:0:12}. The base changed since this script was prepared; re-derive the pins (run the xform on the new base), do not overwrite."
  ok "${TARGETS[$i]} at pre-state ${PRE_SHAS[$i]:0:12}"
done
[ -f "$WT/$XFORM_REL" ] || die "$XFORM_REL is not on $BASE"
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 before the amendment"
else die "receipt checker does not exit 0 before the amendment"; fi

# ---- apply in the stage, show the exact change
mkdir -p "$STAGE/before"
for t in "${TARGETS[@]}"; do mkdir -p "$STAGE/before/$(dirname "$t")"; cp "$WT/$t" "$STAGE/before/$t"; done
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" \
  --state "${TARGETS[0]}" --state "${TARGETS[1]}" --state "${TARGETS[2]}" --out "$STAGE/pre.json" \
  || die "could not snapshot the pre-amendment state"
"$SYS_PY" "$WT/$XFORM_REL" "$WT" || die "transform refused (an anchor moved); nothing written"
for i in "${!TARGETS[@]}"; do
  t="${TARGETS[$i]}"
  say "== exact change to $t =="
  diff -u --label "a/$t" --label "b/$t" "$STAGE/before/$t" "$WT/$t" || true
  [ "$(sha "$WT/$t")" = "${POST_SHAS[$i]}" ] || die "postflight: $t post-state $(sha "$WT/$t") != pin ${POST_SHAS[$i]}."
done
for a in "$ANCHOR1" "$ANCHOR2" "$ANCHOR3"; do
  n=0; for t in "${TARGETS[@]}"; do n=$((n + $(grep -cF -- "$a" "$WT/$t" || true))); done
  [ "$n" -eq 1 ] || die "postflight: anchor occurs $n times across the targets: $a"
done
ok "every target at its post-state pin; each anchor once"

# ---- receipts
say "== MEASUREMENT.md section-5 consolidated receipt =="
receipt_rc=0
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$WT" --pre "$STAGE/pre.json" --protocol-id "$PROTOCOL_ID" \
  --anchor "$ANCHOR1" --anchor "$ANCHOR2" --anchor "$ANCHOR3" \
  --ratification-id "$GATE_ID" --script "$SCRIPT_PATH" \
  --operator "${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
  --no-evidence-reason "workflow doctrine (handoff standard Stage C), not a measured claim; operator decisions 2026-11-19" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum CLAUDE.md | cut -d' ' -f1)\" = ${POST_SHAS[0]}" \
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
       "operator_decisions": {"1-6": "2026-11-19 handoff standard decisions (HANDOFF-STANDARD.md 'Operator decisions')",
                              "stage-c": "2026-11-20 Stage C brief §C7 ratify package"},
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
  -m "RATIFIED $GATE_ID: handoff standard Stage C human-only edits (signed by ${RATIFY_OPERATOR:-DRY-APPLY})" \
  -m "SESSION_LIFECYCLE Two axioms, OPERATING_CONSTRAINTS Dispatching Backlog Work + ruling (b), CLAUDE.md Handoff Workflow. Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
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
