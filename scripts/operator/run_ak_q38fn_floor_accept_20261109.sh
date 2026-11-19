#!/bin/bash
# run_ak_q38fn_floor_accept_20261109.sh -- ONE operator signature (RATIFY-AK-Q38FN-FLOOR-ACCEPT-20261109).
#
# WHAT YOU ARE SIGNING
#   Registers two Q38FN C9 (d210f85c2) A/A floors in research orchestration/model_registry.yaml, role
#   qwen38_flash_next_ud_iq4xs_local, numerics_epoch default, grade decision/quiet, t48, through
#   autokernel.loop.apply_registry_serving_floors:
#     serving 4.146% (n=24, reaper held; a second run, r4, measured 4.07%)   entry cbe4f8884cd99e53
#     64k     1.448% (n=24, r4; no second run)                               entry e2b694e5c3f68b73
#   DECISION: operator, 2026-11-09, decision tool, option 'Accept ~4.1%, add reaper skip' (session
#   7b25c5ae-26b3-499f-bce1-07c4ba197b8c); its text said the 64k floor 'would need the same acceptance'. Your
#   signature on this script is the formal record. Janitor reap skip: root main 9d597d559.
#   Both sealed records carry suspect: true, from unexplained MAD-outlier A/A pairs (recorded by this script in
#   the entry annotation and the receipt). You are accepting them anyway; nothing was excluded, the outlier
#   pairs remain in each floor and remain UNEXPLAINED; acceptance does not clear the flag. Floor records, plan files and the guard are not modified.
#
# WHAT THE LOOP DOES WITH THEM
#   Nothing in the registry lookup, _validate_matched_floor or gate_floor reads `suspect`, so
#   --floor-require-grade decision returns these entries. `suspect` is refused only by carry-forward (run.py
#   _carry_forward_floor), which is a later step and reads store files, not the registry.
#   ORDER: the loop checks the store's own anchor floor BEFORE the registry. On store-b0ba1d427 the serving bar
#   stays the r4 file (4.07%), and the 64k bar is the same record as this entry (1.448%). The 4.146% entry is
#   read only where no anchor floor exists (another store, a byte-equivalent build).
#
#   Review / dry run (default; throwaway worktrees, real apply, commit and lookup; nothing pushed or kept):
#     bash scripts/operator/run_ak_q38fn_floor_accept_20261109.sh
#   Sign (the OPERATOR runs this; it reads RATIFY from /dev/tty):
#     bash /workspace/scripts/operator/run_ak_q38fn_floor_accept_20261109.sh --apply --operator '<your name>'
#
# Idempotent: work already on origin/main is skipped; re-run after any failure. Research is pushed first, so the
# root receipt names its commit. Touches no process and no shared checkout.
# ROLLBACK: git revert the printed commits on fresh origin/main worktrees, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="/workspace"
RES="/mnt/raid0/llm/epyc-inference-research"
LLAMA="/mnt/raid0/llm/llama.cpp"
STAGE_PARENT="/mnt/raid0/llm/tmp"
SYS_PY="/usr/bin/python3"
VENV_PY="/mnt/raid0/llm/epyc-inference-research/.venv/bin/python"
PUSHER="/workspace/scripts/coordination/serialized_push.py"
PUSH_AGENT="autokernel"
BRANCH="ak/floor-accept-20261109"
ROOT_WT="/mnt/raid0/llm/worktrees/ak-floor-accept-20261109"
RES_WT="/mnt/raid0/llm/worktrees/ak-floor-accept-research-20261109"
GATE_ID="RATIFY-AK-Q38FN-FLOOR-ACCEPT-20261109"
SCRIPT_REL="scripts/operator/run_ak_q38fn_floor_accept_20261109.sh"
RECEIPT_REL="artifacts/operator/ratify_ak_q38fn_floor_accept_20261109.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
REGISTRY_REL="orchestration/model_registry.yaml"
ROLE="qwen38_flash_next_ud_iq4xs_local"
EPOCH="default"
BUILD="/mnt/raid0/llm/kernels/builds/cpu-20261109-d210f85c2-c9fold"
CHAMP_REF="ak/champion/llama-cpp-ffc1bac82eec"
CHAMP_SHA="d210f85c2cc8abb1c67cf79ed12582efd9e0026c"
SERVING_ID="cbe4f8884cd99e53"
LONGCTX_ID="e2b694e5c3f68b73"
SERVING_REC="/mnt/raid0/llm/autokernel/reaper-diag-q38fn-20261109/runtime-source-floors/cff9ad900700c8057a2783946e5e5dc5ed718818728dd1bdbdfb9e0199b16fb8/20a75532c2272217a1de67602fc0f37447ebc0b530c9295d598e1bfea4eaa6da/serving-floor.q38fn-802bf9ac6-cpu-t48-mtp-d4.requests-57c9006dfde7443a1bf9b58c08f1ac6834dddcdf3cafcfb770717f141b1d8640.matched_process_v2.pairs-5.json"
LONGCTX_REC="/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/store-b0ba1d427/longctx/q38fn-802bf9ac6-cpu-t48-mtp-d4/floors/anchors/2cb4b7d12a3a1ff3/serving-floor.q38fn-802bf9ac6-cpu-t48-mtp-d4-lc64k-23eea2fa.requests-0445fd119ede8328365a9ecf94daee939b320025886ae5a50131ef9382c97324.matched_process_v2.pairs-5.json"
SERVING_SHA="97224e99fbe63cc2d8b60a1a684059acdc95209320d2fa19b00268705d1ff817"
LONGCTX_SHA="08f6c28dae5700a9b43d3a0667dd14a579c5d19666d382637e86b121d7e9838d"
TRAILERS=$'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01F1v5qCZ3QJbHavUMsZnzEM'

MODE="review"; OPERATOR=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review"; shift ;;
    --apply)    MODE="apply"; shift ;;
    --operator) [ "$#" -ge 2 ] || { echo "--operator needs a name" >&2; exit 64; }; OPERATOR="$2"; shift 2 ;;
    *) echo "usage: $0 [--dry-run | --apply --operator <name>]" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf '\nREFUSING: %s\n' "$*" >&2; exit 65; }
ok()  { printf '  ok    %s\n' "$*"; }
g()   { git -c safe.directory='*' -C "$@"; }
for tool in git sha256sum "$SYS_PY" "$VENV_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$PUSHER" ] || die "$PUSHER missing"

if [ "$MODE" = "apply" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator "$OPERATOR"; OPERATOR="$RATIFY_OPERATOR"
  say "signer: $OPERATOR"
  [ -r /dev/tty ] && [ -t 0 ] || die "no terminal to read the confirmation from; run from a terminal or through the script(1) wrapper"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
g "$RES" fetch -q origin main || die "cannot fetch origin main in $RES"
ROOT_BASE="$(g "$ROOT" rev-parse origin/main)"
RES_BASE="$(g "$RES" rev-parse origin/main)"
say "== root origin/main $ROOT_BASE =="
say "== research origin/main $RES_BASE =="

research_state() {
  local reg
  reg="$(g "$RES" show "origin/main:$REGISTRY_REL")"
  if grep -qF -- "id: $SERVING_ID" <<<"$reg" && grep -qF -- "id: $LONGCTX_ID" <<<"$reg"; then echo already; fi
}
root_state() { if g "$ROOT" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null; then echo already; fi; }
RES_DONE="$(research_state)"; ROOT_DONE="$(root_state)"
if [ "$RES_DONE$ROOT_DONE" = "alreadyalready" ]; then say "ALREADY RATIFIED: both entries and the receipt are on origin/main."; exit 0; fi

# ---- preconditions
[ "$(g "$LLAMA" rev-parse "refs/heads/$CHAMP_REF")" = "$CHAMP_SHA" ] || die "$CHAMP_REF moved off C9; these floors would be stale_champion"
ok "champion ref is C9"

STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ak-floor-accept.XXXXXX")"
RWT=""; WT=""; THROW=0
cleanup() {
  local rc=$?
  if [ "$THROW" -eq 1 ]; then
    [ -z "$RWT" ] || g "$RES" worktree remove --force "$RWT" >/dev/null 2>&1 || say "WARN: could not remove $RWT"
    [ -z "$WT" ] || g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove $WT"
  fi
  rm -f "$STAGE"/plan-*.json "$STAGE"/accept.json
  rmdir "$STAGE" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT

# ---- worktrees: throwaway detached for review; the named branch for apply (reused and rebased on a re-run)
ensure_wt() {  # repo path base
  local repo="$1" path="$2" base="$3"
  if [ -e "$path" ]; then
    [ "$(g "$path" rev-parse --abbrev-ref HEAD)" = "$BRANCH" ] || die "$path exists and is not on $BRANCH"
    [ -z "$(g "$path" status --porcelain --untracked-files=no)" ] || die "$path has uncommitted tracked changes; inspect it, nothing was changed"
    g "$path" rebase -q origin/main || { g "$path" rebase --abort || true; die "$path does not rebase onto origin/main"; }
  else
    g "$repo" worktree add -q -b "$BRANCH" "$path" "$base" || die "could not create $path"
  fi
  g "$path" branch -q --set-upstream-to=origin/main "$BRANCH" || die "could not set upstream in $path"
}
if [ "$MODE" = "review" ]; then
  THROW=1
  RWT="$STAGE/research"; g "$RES" worktree add -q --detach "$RWT" "$RES_BASE" || { RWT=""; die "could not stage research worktree"; }
  WT="$STAGE/root";      g "$ROOT" worktree add -q --detach "$WT" "$ROOT_BASE" || { WT=""; die "could not stage root worktree"; }
  ok "staged throwaway worktrees under $STAGE"
else
  printf '\nBoth suspect floors will be registered and pushed to main in both repos, as operator "%s".\nType RATIFY to apply: ' "$OPERATOR"
  IFS= read -r answer < /dev/tty || die "could not read from the terminal"
  [ "$answer" = "RATIFY" ] || die "confirmation was '$answer', not RATIFY. Nothing changed."
  ensure_wt "$RES" "$RES_WT" "$RES_BASE"; RWT="$RES_WT"
  ensure_wt "$ROOT" "$ROOT_WT" "$ROOT_BASE"; WT="$ROOT_WT"
  ok "worktrees on $BRANCH"
fi

# ---- plan copies with the acceptance in `annotation`; the source plans and records stay untouched
say "== floor facts, read from the sealed records =="
SIGNER="${OPERATOR:-DRY-RUN}"
GATE_ID="$GATE_ID" SIGNER="$SIGNER" RECEIPT_REL="$RECEIPT_REL" STAGE="$STAGE" ROLE="$ROLE" EPOCH="$EPOCH" CHAMP_SHA="$CHAMP_SHA" \
SERVING_REC="$SERVING_REC" LONGCTX_REC="$LONGCTX_REC" SERVING_SHA="$SERVING_SHA" LONGCTX_SHA="$LONGCTX_SHA" \
SERVING_ID="$SERVING_ID" LONGCTX_ID="$LONGCTX_ID" "$SYS_PY" - <<'PYEOF' || die "the floor facts do not match what this script was prepared against. Nothing changed."
import hashlib, json, os
e = os.environ
RATIONALE = {
  "serving": "Two independent 24-pair runs on C9 agree on the level (this run 4.146%, r4 4.07%). The outlier guard found no independent degraded-host evidence for these pairs and they remain in the floor.",
  "longctx": "Single run; one pair flagged, which the guard could not tie to independent degraded-host evidence; it remains in the floor. No second 64k run corroborates this level.",
}
want = {"serving": (e["SERVING_REC"], e["SERVING_SHA"], e["SERVING_ID"], 4.146, 2), "longctx": (e["LONGCTX_REC"], e["LONGCTX_SHA"], e["LONGCTX_ID"], 1.448, 1)}
accept = {}
for kind, (rec, sha, eid, pct, n_out) in want.items():
    plan = json.load(open(rec + ".registry-plan.json", encoding="utf-8"))
    entry = plan["entry"]
    raw = open(rec, "rb").read()
    row = json.loads(raw)
    guard = row.get("outlier_guard") or {}
    pairs = guard.get("unexplained_outliers") or []
    checks = {
        "record sha": hashlib.sha256(raw).hexdigest() == sha == entry["record_sha256"],
        "entry id": entry["id"] == eid, "floor_pct": entry["floor_pct"] == pct == row["floor_pct"],
        "record path": entry["record"] == rec, "role": plan["role"] == e["ROLE"],
        "epoch": entry["numerics_epoch"] == e["EPOCH"], "n": entry["n"] == 24 == row["n"], "k": entry["k"] == 5,
        "grade": entry["grade"] == {"claim_class": "decision", "co_tenancy": "quiet", "threads": 48},
        "build": entry["build"]["commit"] == e["CHAMP_SHA"],
        "suspect": row.get("suspect") is True and guard.get("suspect") is True,
        "outliers": len(pairs) == n_out, "nothing excluded": guard.get("excluded") == [],
    }
    bad = [k for k, ok in checks.items() if not ok]
    if bad:
        raise SystemExit(f"{kind}: {bad}")
    entry["annotation"] = (f"OPERATOR ACCEPTED suspect: true ({e['GATE_ID']}, signed {e['SIGNER']}; epyc-root receipt indexed by that gate id). "
                           f"The sealed record stays suspect: true; these pairs remain unexplained and in the floor: {json.dumps(pairs, sort_keys=True)}. {RATIONALE[kind]} "
                           f"Decision: operator 2026-11-09, option 'Accept ~4.1%, add reaper skip', session 7b25c5ae-26b3-499f-bce1-07c4ba197b8c; the signature on the ratify script is the formal record. Janitor reap skip: epyc-root 9d597d559.")
    json.dump(plan, open(f"{e['STAGE']}/plan-{kind}.json", "w", encoding="utf-8"), indent=1)
    accept[kind] = {"entry_id": eid, "floor_pct": pct, "n": 24, "k": 5, "record": rec, "record_sha256": sha,
                    "suspect": True, "unexplained_outliers": pairs, "rationale": RATIONALE[kind]}
    print(f"  {kind}: {pct}% n=24, suspect, outliers " + ", ".join(f"pair {p['pair_index']} {p['effect_pct']}%" for p in pairs))
json.dump(accept, open(f"{e['STAGE']}/accept.json", "w", encoding="utf-8"), indent=1)
PYEOF
ok "records, plans and outlier pairs match"

# ---- research: one applier run and one commit per floor (the applier requires a clean tree)
RENV=(env "EPYC_ROOT_REPO=/workspace" "PYTHONPATH=$RWT:$RWT/scripts/kernel_rnd:$RWT/scripts/lib:/mnt/raid0/llm/epyc-orchestrator")
register() {  # kind id record pct
  local kind="$1" id="$2" rec="$3" pct="$4" out
  say "== register $kind $id =="
  out="$(cd "$RWT/scripts/kernel_rnd" && "${RENV[@]}" "$VENV_PY" -m autokernel.loop.apply_registry_serving_floors \
        --registry "$RWT/$REGISTRY_REL" --plan "$STAGE/plan-$kind.json")" || die "applier refused $kind. Nothing pushed."
  printf '%s\n' "$out" | tail -n 1 | cut -c1-140
  if [ -n "$(g "$RWT" status --porcelain --untracked-files=no)" ]; then
    [ "$(g "$RWT" diff --name-only)" = "$REGISTRY_REL" ] || die "applier touched more than the registry"
    g "$RWT" add -- "$REGISTRY_REL"
    g "$RWT" commit -q -m "registry: accept suspect Q38FN C9 $kind floor $pct% for $ROLE ($GATE_ID, signed by $SIGNER)" -m "$TRAILERS" \
      || die "research commit failed (hook?). Nothing pushed; re-run."
  fi
  say "== lookup $kind (--require-grade decision) =="
  out="$(cd "$RWT/scripts/kernel_rnd" && "${RENV[@]}" "$VENV_PY" -m autokernel.loop.floor_registry --master "$RWT/$REGISTRY_REL" --source-repo "$LLAMA" \
        lookup --build "$BUILD" --floor "$rec" --numerics-epoch "$EPOCH" --require-grade decision --role "$ROLE" 2>&1)" \
    || die "lookup MISS for $kind after registering: $out"
  grep -qF -- "$id" <<<"$out" || grep -qF -- "$pct" <<<"$out" || die "lookup for $kind did not return this entry: $out"
  ok "lookup hit: $(printf '%s' "$out" | tail -n 1 | cut -c1-150)"
}
push_here() {  # worktree
  local prc=0
  ( cd "$1" && AGENT_ID="$PUSH_AGENT" "$SYS_PY" "$PUSHER" --agent "$PUSH_AGENT" --repo . --push ) || prc=$?
  [ "$prc" -eq 0 ] || die "push failed in $1 (rc=$prc; origin/main probably moved). Re-run; applied items are skipped."
}

RES_COMMIT="$RES_BASE"
if [ "$RES_DONE" != "already" ]; then
  register serving "$SERVING_ID" "$SERVING_REC" 4.146
  register longctx "$LONGCTX_ID" "$LONGCTX_REC" 1.448
  RES_COMMIT="$(g "$RWT" rev-parse HEAD)"
  if [ "$MODE" = "apply" ]; then
    g "$RES" fetch -q origin main
    g "$RWT" rebase -q origin/main || { g "$RWT" rebase --abort || true; die "research rebase failed. Nothing pushed; re-run."; }
    say "== push research main =="
    push_here "$RWT"
    RES_COMMIT="$(g "$RWT" rev-parse HEAD)"
    g "$RES" fetch -q origin main
    g "$RES" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research $RES_COMMIT is not on origin/main after fetch"
    ok "research main $RES_COMMIT"
  fi
else
  RES_COMMIT="$(g "$RES" rev-parse origin/main)"
  say "research entries already on origin/main"
fi

# ---- root receipt, plus this script for provenance
ROOT_COMMIT=""
if [ "$ROOT_DONE" != "already" ]; then
  say "== root receipt =="
  cp "$SCRIPT_PATH" "$WT/$SCRIPT_REL"
  WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" GATE_ID="$GATE_ID" SIGNER="$SIGNER" STAGE="$STAGE" ROLE="$ROLE" EPOCH="$EPOCH" \
  TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" RES_COMMIT="$RES_COMMIT" SCRIPT_REL="$SCRIPT_REL" SCRIPT_SHA="$(sha256sum -- "$SCRIPT_PATH" | awk '{print $1}')" \
  "$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Research is already pushed; re-run to finish."
import json, os
e = os.environ
doc = {
    "schema": "epyc.operator_ratification.v1", "gate_id": e["GATE_ID"], "status": "ratified", "ratified_at": e["TS"],
    "operator": e["SIGNER"], "signature_channel": "operator-run script (typed RATIFY on the terminal)",
    "decision": "Accept two floors marked suspect: true, for registration at decision/quiet grade.",
    "operator_decision": {"date": "2026-11-09", "channel": "decision tool", "option": "Accept ~4.1%, add reaper skip",
                          "session": "7b25c5ae-26b3-499f-bce1-07c4ba197b8c",
                          "scope_note": "the option text said the 64k floor (r4 1.448%, also suspect) 'would need the same acceptance'",
                          "formal_record": "the operator's signature on this script"},
    "suspect_flag_cleared": False, "outliers_remain_unexplained": True,
    "janitor_reap_skip_commit": "9d597d559",
    "role": e["ROLE"], "numerics_epoch": e["EPOCH"],
    "floors": json.load(open(f"{e['STAGE']}/accept.json", encoding="utf-8")),
    "loop_behaviour": ("suspect is not read by floor_registry lookup, _validate_matched_floor or gate_floor, so require-grade decision returns these entries; "
                       "carry-forward still refuses a suspect store floor. On store-b0ba1d427 the anchor floor takes precedence over the registry: "
                       "serving gates on the r4 file (4.07%), 64k on the same record as its entry."),
    "records_modified": False, "research_commit": e["RES_COMMIT"], "applied_by": e["SCRIPT_REL"],
    "ratify_script_sha256": e["SCRIPT_SHA"], "processes_touched": [],
}
with open(os.path.join(e["WT"], e["RECEIPT_REL"]), "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
idx = os.path.join(e["WT"], e["INDEX_REL"])
os.makedirs(os.path.dirname(idx), exist_ok=True)
with open(idx, "w", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "ratify", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n")
PYEOF
  "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1 || die "receipt checker fails. Root not committed; re-run."
  ok "receipt checker passes"
  g "$WT" add -- "$RECEIPT_REL" "$INDEX_REL" "$SCRIPT_REL"
  staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
  want="$(printf '%s\n' "$RECEIPT_REL" "$INDEX_REL" "$SCRIPT_REL" | sort)"
  [ "$staged" = "$want" ] || die "root index holds an unexpected path set; not committed: $staged"
  g "$WT" commit -q -m "RATIFIED $GATE_ID: accept suspect Q38FN C9 floors (signed by $SIGNER)" \
    -m "Research commit: $RES_COMMIT. Receipt: $RECEIPT_REL." -m "$TRAILERS" || die "root commit failed (hook?); re-run."
  ok "root commit staged paths: $(printf '%s' "$staged" | wc -l | awk '{print $1+1}')"
  if [ "$MODE" = "apply" ]; then
    g "$ROOT" fetch -q origin main
    g "$WT" rebase -q origin/main || { g "$WT" rebase --abort || true; die "root rebase failed; re-run."; }
    say "== push root main =="
    push_here "$WT"
    ROOT_COMMIT="$(g "$WT" rev-parse HEAD)"
    g "$ROOT" fetch -q origin main
    g "$ROOT" merge-base --is-ancestor "$ROOT_COMMIT" origin/main || die "root $ROOT_COMMIT is not on origin/main after fetch"
  fi
fi

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE. Real apply, commits, lookup and receipt check ran on throwaway worktrees; nothing pushed or kept."
  say "Sign with ONE command:"
  say "  bash $SCRIPT_PATH --apply --operator '<your name>'"
  exit 0
fi

cat <<REPORT

RATIFIED $GATE_ID by $OPERATOR.
  research main: $RES_COMMIT
  root main:     ${ROOT_COMMIT:-already applied}
NO PROCESS WAS TOUCHED.
ROLLBACK (operator): git revert the commits above on fresh origin/main worktrees, then push through serialized_push.py.
REPORT
