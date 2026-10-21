#!/bin/bash
# ratify_corpus_retrieval_off_20261021.sh — switch OFF corpus retrieval in the FROZEN model registry.
#
#   Review / dry run (default, writes nothing):  bash scripts/operator/ratify_corpus_retrieval_off_20261021.sh --dry-run
#   Apply (ff both lane commits to origin/main): RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_corpus_retrieval_off_20261021.sh --apply --attest RATIFY-CORPUS-RETRIEVAL-OFF-20261021
#   Verify the post-state (read-only):           bash scripts/operator/ratify_corpus_retrieval_off_20261021.sh --verify
#
# OPERATOR DIRECTIVE (2026-10-21): "proceed with fix. When ready, provide me with a ratification bash package
# and I'll execute."  An agent (corpus-flagoff-ratify) prepared and dry-ran this; ONLY the operator applies it.
#
# WHY. The corpus index /mnt/raid0/llm/cache/corpus/v3_sharded was deleted on purpose on 2026-07-04
# (handoffs/completed/corpus-augmented-prompt-lookup-revalidation.md, CPL-4/5: clean-window A/B, no proven
# benefit, worker_general quality gate FAILED). The registry still says corpus_retrieval.enabled: true with that
# path and seven role blocks (five of them in the live lean view) set acceleration.corpus_retrieval: true, so
# every request on those roles pays a lookup that ends failure_reason=no_index.
#
# WHAT LANDS (two lane commits, each a fast-forward of origin/main; nothing else is touched):
#   epyc-inference-research  MASTER orchestration/model_registry.yaml
#       runtime corpus_retrieval.enabled true -> false; 7 x role acceleration.corpus_retrieval true -> false;
#       index_path kept, annotated "DELETED 2026-07-04 (CPL-4/5)". The master is the SOURCE of the registry.
#   epyc-orchestrator        the DERIVED layer regenerated from that master by the repo's own tool
#       (scripts/registry/stack_change_pipeline.py update): orchestration/model_registry.yaml (lean view),
#       orchestration/model_descriptors.yaml, orchestration/derived/stack_priors.yaml,
#       docs/generated/current_stack_summary.md.  Editing ONLY the lean view would be silently reverted at the
#       next `orchestrator_stack.py start`, which recompiles it from the master (DERIVATION.md).
#   No code changes. The disabled path already exists in src/prompt_builders/builder.py
#   (build_corpus_context returns "" with reason=config_disabled BEFORE any retriever is built).
#
# WHEN IT TAKES EFFECT. At the NEXT stack start / API reload — NOT before. This script requires the production
# stack to be DOWN and starts nothing. Per the stack-change skill, "pipeline green" is not "serving": after
# `orchestrator_stack.py start`, confirm one real completion per role and that the corpus_retrieval events read
# status=skipped reason=config_disabled.
#
# ROLLBACK: `git revert` the two landed commits (shas in the receipt) and re-run the pipeline; the index itself
# is gone, so rollback restores only the (failing) lookup, which is why none is recommended.
#
# PINS. Every mismatch is refused; if origin/main has moved past a lane commit the lane is REGENERATED, never
# forced or rebased by this script.
#
# IDEMPOTENT. Both commits already on origin/main + receipt present -> "ALREADY RATIFIED", exit 0. Both commits on
# origin/main but no receipt -> only the receipt is written. Any other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"

GATE_ID="RATIFY-CORPUS-RETRIEVAL-OFF-20261021"
RECEIPT_REL="artifacts/operator/receipts/$GATE_ID.json"

# ---- pins (filled by the preparing agent; the operator verifies by reading them) ----
ORCH_REPO="${ORCH_REPO:-/workspace/repos/epyc-orchestrator}"
RESEARCH_REPO="${RESEARCH_REPO:-/mnt/raid0/llm/epyc-inference-research}"
ORCH_LANE_SHA="291972e5d41f1db7be31bd5807886391307b0f68"
RESEARCH_LANE_SHA="f75d8fa784eb6ffc9967f855cf1449c3c28e4cab"
ORCH_LANE_WT="/mnt/raid0/llm/worktrees/corpus-flagoff-orch-20261021"
RESEARCH_LANE_WT="/mnt/raid0/llm/worktrees/corpus-flagoff-research-20261021"
# sha256 of each changed file AS IT EXISTS at the lane commit (content, not git blob ids)
PIN_MASTER_SHA256="0e6a63bb72234290af01ee809563b3c6fb149eb9abc87c8b6a1771c510ae3d2d"
PIN_LEAN_SHA256="a7b705ba8cc5df2ea5dac0bb758181f148dab98d74367a976c8c93ac4e6550db"
PIN_DESCRIPTORS_SHA256="2f34c4e1dffd250b08189e1886ba14fbf5ec9375cf9b1547d602554d3996b149"
PIN_PRIORS_SHA256="3d21f563fa98f97bab87d46123d3a2e6ae31dfc4ac4e919ed33cd957d35f123d"
PIN_SUMMARY_SHA256="96f2aeb0afc45a217e7283c4182c18e69a11f89f2777cf59e958baff1b846d8d"
# the paths the two lane commits are allowed to touch (anything else is refused)
RESEARCH_ALLOWED=("orchestration/model_registry.yaml")
ORCH_ALLOWED=("tests/unit/test_registry_loader.py" "orchestration/model_registry.yaml" "orchestration/model_descriptors.yaml"
              "orchestration/derived/stack_priors.yaml" "docs/generated/current_stack_summary.md")

INDEX_PATH="/mnt/raid0/llm/cache/corpus/v3_sharded"
# every port the stack can listen on (orchestration/launch_manifest.yaml port_map + the API)
STACK_PORTS="8000 8070 8074 8083 8086 8090 8091 8092 8093 8094 8095 8096 8097 8098 8102 18070 9000 9001 9002 8190"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"
LOCK_AGENT="operator-ratify-corpus-flagoff"

MODE="review"; ATTEST=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)  MODE="apply" ;;
    --verify) MODE="verify" ;;
    --attest) shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --attest $GATE_ID]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha_stdin() { sha256sum | awk '{print $1}'; }
g() { local repo="$1"; shift; git -c safe.directory='*' -C "$repo" "$@" 2>/dev/null; }
blob_sha() { g "$1" show "$2:$3" | sha_stdin; }   # sha256 of a file's content at a commit

command -v python3 >/dev/null || die "python3 not on PATH"
command -v git >/dev/null || die "git not on PATH"
command -v ss >/dev/null || die "ss not on PATH"
[ -f "$PUSHER" ] || die "$PUSHER not found under ROOT=$ROOT"
case "$ORCH_LANE_SHA$RESEARCH_LANE_SHA$PIN_MASTER_SHA256" in *@@*) die "script was not finalised (unfilled pin)";; esac
if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply requires --attest $GATE_ID"
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
fi

# ---------------------------------------------------------------- state of each repo vs origin/main
g "$ORCH_REPO" fetch -q origin main || die "cannot fetch origin in $ORCH_REPO"
g "$RESEARCH_REPO" fetch -q origin main || die "cannot fetch origin in $RESEARCH_REPO"
g "$ORCH_REPO" cat-file -e "$ORCH_LANE_SHA^{commit}" || die "orchestrator lane commit $ORCH_LANE_SHA not in $ORCH_REPO"
g "$RESEARCH_REPO" cat-file -e "$RESEARCH_LANE_SHA^{commit}" || die "research lane commit $RESEARCH_LANE_SHA not in $RESEARCH_REPO"

landed() { g "$1" merge-base --is-ancestor "$2" origin/main && echo yes || echo no; }
ORCH_LANDED="$(landed "$ORCH_REPO" "$ORCH_LANE_SHA")"
RES_LANDED="$(landed "$RESEARCH_REPO" "$RESEARCH_LANE_SHA")"

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$ORCH_LANDED" = yes ] || { say "  FAIL  orchestrator lane $ORCH_LANE_SHA is not on origin/main"; ok=0; }
  [ "$RES_LANDED" = yes ]  || { say "  FAIL  research lane $RESEARCH_LANE_SHA is not on origin/main"; ok=0; }
  [ -f "$ROOT/$RECEIPT_REL" ] || { say "  FAIL  $RECEIPT_REL missing"; ok=0; }
  if [ "$ok" -eq 1 ]; then
    for spec in "$RESEARCH_REPO:orchestration/model_registry.yaml:$PIN_MASTER_SHA256" \
                "$ORCH_REPO:orchestration/model_registry.yaml:$PIN_LEAN_SHA256"; do
      repo="${spec%%:*}"; rest="${spec#*:}"; path="${rest%%:*}"; want="${rest#*:}"
      have="$(blob_sha "$repo" origin/main "$path")"
      [ "$have" = "$want" ] || { say "  NOTE  $repo:$path on origin/main differs from the pin (later edit?)"; }
    done
    say "VERIFIED: $GATE_ID — both lane commits are on origin/main and the receipt exists."; exit 0
  fi
  exit 1
fi

# ---------------------------------------------------------------- idempotence
if [ "$ORCH_LANDED" = yes ] && [ "$RES_LANDED" = yes ] && [ -f "$ROOT/$RECEIPT_REL" ]; then
  say "ALREADY RATIFIED: both lane commits are on origin/main and $RECEIPT_REL exists. Nothing to do."
  exit 0
fi

# ---------------------------------------------------------------- preconditions
say "== preconditions =="
# 1. each lane commit: right parent, right paths, right content, clean lane tree
check_lane() { # name repo sha wt allowed...
  local name="$1" repo="$2" sha="$3" wt="$4"; shift 4
  local landed_flag; landed_flag="$(landed "$repo" "$sha")"
  if [ "$landed_flag" = yes ]; then say "  ok  $name lane $sha already on origin/main"; return 0; fi
  local main; main="$(g "$repo" rev-parse origin/main)"
  g "$repo" merge-base --is-ancestor "$main" "$sha" \
    || die "$name: origin/main moved ($main) and is no longer an ancestor of the lane commit $sha; a fast-forward is impossible. REGENERATE the lane; this script never rebases or forces."
  local parent="$main" changed bad=""
  changed="$(g "$repo" diff --name-only "$main" "$sha")"
  local f a okp
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    okp=0; for a in "$@"; do [ "$f" = "$a" ] && okp=1; done
    [ "$okp" -eq 1 ] || bad="$bad $f"
  done <<<"$changed"
  [ -z "$bad" ] || die "$name: lane commit touches paths outside the allowed set:$bad"
  if [ -d "$wt" ]; then
    [ -z "$(g "$wt" status --porcelain --untracked-files=no)" ] || die "$name lane worktree $wt has uncommitted tracked changes"
    [ "$(g "$wt" rev-parse HEAD)" = "$sha" ] || die "$name lane worktree HEAD is not the pinned commit $sha"
  fi
  say "  ok  $name lane $sha is a clean fast-forward of origin/main ($parent) touching only allowed paths"
}
check_lane research "$RESEARCH_REPO" "$RESEARCH_LANE_SHA" "$RESEARCH_LANE_WT" "${RESEARCH_ALLOWED[@]}"
check_lane orchestrator "$ORCH_REPO" "$ORCH_LANE_SHA" "$ORCH_LANE_WT" "${ORCH_ALLOWED[@]}"

# 2. content pins
chk_pin() { # label repo sha path want
  local have; have="$(blob_sha "$2" "$3" "$4")"
  [ "$have" = "$5" ] || die "$1 content at $3 is $have, pin says $5"
  say "  ok  $1 sha256 $have"
}
chk_pin "research master registry" "$RESEARCH_REPO" "$RESEARCH_LANE_SHA" orchestration/model_registry.yaml "$PIN_MASTER_SHA256"
chk_pin "orchestrator lean registry" "$ORCH_REPO" "$ORCH_LANE_SHA" orchestration/model_registry.yaml "$PIN_LEAN_SHA256"
chk_pin "orchestrator descriptors" "$ORCH_REPO" "$ORCH_LANE_SHA" orchestration/model_descriptors.yaml "$PIN_DESCRIPTORS_SHA256"
chk_pin "orchestrator stack_priors" "$ORCH_REPO" "$ORCH_LANE_SHA" orchestration/derived/stack_priors.yaml "$PIN_PRIORS_SHA256"
chk_pin "orchestrator stack summary" "$ORCH_REPO" "$ORCH_LANE_SHA" docs/generated/current_stack_summary.md "$PIN_SUMMARY_SHA256"

# 3. the change really is "flags off, nothing else": no corpus_retrieval: true / enabled: true survives
g "$RESEARCH_REPO" show "$RESEARCH_LANE_SHA:orchestration/model_registry.yaml" | python3 -c '
import sys, yaml
d = yaml.safe_load(sys.stdin)
rt = d["runtime_defaults"]["corpus_retrieval"]
assert rt["enabled"] is False, "runtime corpus_retrieval.enabled is not false"
on = [r for r, v in d["roles"].items() if isinstance(v.get("acceleration"), dict) and v["acceleration"].get("corpus_retrieval")]
assert not on, f"roles still enabled: {on}"
print("  ok  master: runtime enabled=false, no role has acceleration.corpus_retrieval=true")
' || die "master content check failed"
g "$ORCH_REPO" show "$ORCH_LANE_SHA:orchestration/model_registry.yaml" | python3 -c '
import sys, yaml
d = yaml.safe_load(sys.stdin)
assert d["runtime_defaults"]["corpus_retrieval"]["enabled"] is False
on = [r for r, v in d["roles"].items() if isinstance(v.get("acceleration"), dict) and v["acceleration"].get("corpus_retrieval")]
assert not on, f"roles still enabled: {on}"
print("  ok  lean view: runtime enabled=false, no role has acceleration.corpus_retrieval=true")
' || die "lean-view content check failed"

# 4. the index really is absent
[ ! -e "$INDEX_PATH" ] || die "$INDEX_PATH EXISTS. The premise (index deleted 2026-07-04) is false; do not flag off a live index."
say "  ok  $INDEX_PATH is absent"

# 5. the production stack is DOWN (this takes effect at the next start; nothing here restarts anything)
listening="$(ss -ltnH 2>/dev/null | awk '{print $4}' | sed 's/.*://' | sort -u)"
up=""
for p in $STACK_PORTS; do printf '%s\n' "$listening" | grep -qx "$p" && up="$up $p"; done
[ -z "$up" ] || die "stack ports are listening:$up. The production stack must be DOWN. Stop it via orchestrator_stack.py (not this script), then re-run."
say "  ok  no stack port is listening ($STACK_PORTS)"

# 6. receipt not already spent
[ -f "$ROOT/$RECEIPT_REL" ] && [ "$ORCH_LANDED$RES_LANDED" != "yesyes" ] && die "$RECEIPT_REL exists but the lane commits are not both on origin/main. Resolve by hand."

# 7. push locks are obtainable (read-only check)
for r in "$RESEARCH_REPO" "$ORCH_REPO"; do
  st="$(python3 "$PUSHER" --agent "$LOCK_AGENT" --repo "$r" --lock-name push --status 2>&1 || true)"
  case "$st" in *FREE*) say "  ok  push lock FREE for $r" ;; *) die "push lock for $r is not free: $st" ;; esac
done

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN — nothing was written, nothing was pushed. --apply would:"
  [ "$RES_LANDED" = yes ] || say "  1. (research) take the push lock, git push origin $RESEARCH_LANE_SHA:refs/heads/main, release"
  [ "$ORCH_LANDED" = yes ] || say "  2. (orchestrator) take the push lock, git push origin $ORCH_LANE_SHA:refs/heads/main, release"
  say "  3. write $RECEIPT_REL (status ratified, sha256 pins, shas)"
  say "  Effective at the NEXT stack start; the stack is down now."
  say "DRY-RUN OK: $GATE_ID — all preconditions hold (research $RESEARCH_LANE_SHA, orchestrator $ORCH_LANE_SHA)."
  exit 0
fi

# ---------------------------------------------------------------- apply
push_locked() { # name repo sha
  local name="$1" repo="$2" sha="$3" tok
  tok="$(mktemp /mnt/raid0/llm/tmp/corpus-flagoff-push-token.XXXXXX)"; chmod 600 "$tok"
  python3 "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || { rm -f "$tok"; die "$name: could not take the push lock"; }
  local rc=0
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" git -c safe.directory='*' -C "$repo" push origin "$sha:refs/heads/main" || rc=$?
  python3 "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --release --token-file "$tok" >/dev/null || say "WARN: $name push lock release failed — check serialized_push.py --status"
  rm -f "$tok"
  [ "$rc" -eq 0 ] || die "$name: git push rejected (rc=$rc). Nothing else was pushed after this point; re-run to resume."
  say "  pushed $name $sha -> origin/main"
}
say ""; say "== applying =="
# research first: the master is the source, the orchestrator's derived layer is compiled from it
[ "$RES_LANDED" = yes ] || push_locked research "$RESEARCH_REPO" "$RESEARCH_LANE_SHA"
[ "$ORCH_LANDED" = yes ] || push_locked orchestrator "$ORCH_REPO" "$ORCH_LANE_SHA"
g "$RESEARCH_REPO" fetch -q origin main; g "$ORCH_REPO" fetch -q origin main
[ "$(landed "$RESEARCH_REPO" "$RESEARCH_LANE_SHA")" = yes ] || die "research lane commit is not on origin/main after the push"
[ "$(landed "$ORCH_REPO" "$ORCH_LANE_SHA")" = yes ] || die "orchestrator lane commit is not on origin/main after the push"

[ ! -e "$ROOT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists"
mkdir -p "$ROOT/artifacts/operator/receipts"
RECEIPT_ABS="$ROOT/$RECEIPT_REL" GATE_ID="$GATE_ID" OPERATOR="$RATIFY_OPERATOR" \
R_SHA="$RESEARCH_LANE_SHA" O_SHA="$ORCH_LANE_SHA" P_MASTER="$PIN_MASTER_SHA256" P_LEAN="$PIN_LEAN_SHA256" \
P_DESC="$PIN_DESCRIPTORS_SHA256" P_PRIORS="$PIN_PRIORS_SHA256" P_SUMMARY="$PIN_SUMMARY_SHA256" \
python3 - <<'PY'
import json, os, datetime
e = os.environ
doc = {
  "schema": "epyc.operator_receipt.v1",
  "token": e["GATE_ID"],
  "status": "ratified",
  "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "signed_by": e["OPERATOR"],
  "signature_channel": "terminal",
  "decision": "operator 2026-10-21: 'proceed with fix' - corpus retrieval OFF in the frozen model registry "
              "(index deleted 2026-07-04, CPL-4/5); effective at the next stack start",
  "landed": {
    "epyc-inference-research": {"commit": e["R_SHA"], "ref": "origin/main"},
    "epyc-orchestrator": {"commit": e["O_SHA"], "ref": "origin/main"},
  },
  "pinned_sha256": {
    "research:orchestration/model_registry.yaml": e["P_MASTER"],
    "orchestrator:orchestration/model_registry.yaml": e["P_LEAN"],
    "orchestrator:orchestration/model_descriptors.yaml": e["P_DESC"],
    "orchestrator:orchestration/derived/stack_priors.yaml": e["P_PRIORS"],
    "orchestrator:docs/generated/current_stack_summary.md": e["P_SUMMARY"],
  },
  "effective": "next orchestrator_stack.py start / API reload",
}
with open(e["RECEIPT_ABS"], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, sort_keys=True); fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
PY
say "  wrote $RECEIPT_REL"
git -C "$ROOT" add -- "$RECEIPT_REL" 2>/dev/null && git -C "$ROOT" commit -q --only -m "RATIFIED: corpus retrieval OFF in the frozen model registry ($GATE_ID)" -- "$RECEIPT_REL" 2>/dev/null \
  && say "  committed the receipt (push it under the push lock when convenient)" \
  || say "  NOTE: receipt left uncommitted; commit it with: git -C $ROOT commit --only -m 'RATIFIED: $GATE_ID' -- $RECEIPT_REL"
say ""
say "RATIFIED $GATE_ID by $RATIFY_OPERATOR: corpus retrieval OFF — research $RESEARCH_LANE_SHA + orchestrator $ORCH_LANE_SHA on origin/main; takes effect at the NEXT stack start (stack is down now); receipt $RECEIPT_REL"
