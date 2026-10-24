#!/bin/bash
# ratify_fused_decode_off_architect_general_20261024.sh -- operator signature AND landing for
# RATIFY-FUSED-OFF-ARCHGEN-20261024: GGML_FUSED_DECODE_OFF=1 DECLARED for the production architect_general role
# (:8074, Qwen3.8-Flash-Next UD-IQ4_XS, qwen4exp, full CPU).
#
#   Review / dry run (default; pushes nothing, writes no receipt, removes its scratch worktrees):
#     bash scripts/operator/ratify_fused_decode_off_architect_general_20261024.sh --dry-run
#   Sign and land (the OPERATOR runs this, from a terminal, typing their own name):
#     RATIFY_OPERATOR='Your Full Name' bash scripts/operator/ratify_fused_decode_off_architect_general_20261024.sh --apply --attest RATIFY-FUSED-OFF-ARCHGEN-20261024
#     (a value containing '<', '>' or the word 'name' is refused, so the line above refuses until you edit it)
#   Verify the post-state (read-only apart from scratch worktrees it removes):
#     bash scripts/operator/ratify_fused_decode_off_architect_general_20261024.sh --verify
#   Compare two offline exports (read-only; how the pinned env_diff.txt was produced):
#     bash scripts/operator/ratify_fused_decode_off_architect_general_20261024.sh --compare BEFORE.json AFTER.json
#
# Run it from a checkout of epyc-root branch ratify/fused-decode-off-architect-general-20261024 (it holds the
# pinned evidence). Package summary: /mnt/raid0/llm/tmp/ratify-fused-off-20261024/PACKAGE.md (copied into the
# landing commit).
#
# WHY: the qwen4exp fused decode is default-ON in v10 code. Nothing declared it OFF for :8074. stack_env's
# architect_general block was {}, build_launch_env strips every undeclared GGML_* key, /etc/environment sets none,
# and the only GGML_FUSED_DECODE_OFF: '1' is in the registry's descriptive optimal_cpu_serving block, which no
# code reads. So :8074 serves the fused path, while every measured Q38FN number (research recipe, AK q38fn
# campaigns, the 43.28 t/s optimal_cpu_serving decode) ran OFF=1. The fused MoE path has an open defect at
# synthetic weight scales (FD-DIV-1b), and v10's fused path writes debug files under /tmp/qwen4exp-builds (CH-24).
#
# WHERE THE DECLARATION LIVES: a launch ENV knob is declared in epyc-orchestrator scripts/server/stack_env.py
# _ROLE_ENV_BLOCKS (code, hand-edited source). It is not compiled from the research master, has no derived file,
# and is attested live by scripts/server/env_attestation.py against /proc/<pid>/environ. Precedent: 30626243
# (GGML_NUMA_REPACK_INTERLEAVE removal). The research repo is NOT changed; its master is read only as the
# export's input.
#
# WHAT IT CHANGES (pinned branch tip, pushed, not merged):
#   epyc-orchestrator  scripts/server/stack_env.py (architect_general: {GGML_FUSED_DECODE_OFF: "1"});
#                      scripts/server/autokernel_enrollment.py (the offline export's env transform carried the
#                      pre-5fd6bbdb strip and would have DROPPED the declared key; it now mirrors the launcher);
#                      tests/unit/test_ratify_fused_off_architect_general.py (new);
#                      tests/unit/test_launch_env_strip_preserve.py (neutrality test gains a ratified allow-list)
#   epyc-root          this script, the evidence dir, the CH-24 premise fix in
#                      handoffs/active/autokernel-champion-aggregate.md, PACKAGE.md, the receipt + keyed index
#
# WHAT IT DOES (--apply), in order, each step refusing on any mismatch:
#   1. checks the signer: --attest token typed, RATIFY_OPERATOR set and not a placeholder, then the shared
#      ratify_require_operator rules (no system/login/agent name);
#   2. verifies the sha256 of every pinned evidence file, and that origin/<branch> of the orchestrator is EXACTLY
#      the pinned commit;
#   3. stages, in scratch worktrees at a FRESH origin/main: a fast-forward to the pin when possible, else a clean
#      --no-ff merge (a conflict refuses: the package is STALE); a path allow-list check of the pinned change;
#   4. PROVES THE ENV: the offline production export (scripts.server.autokernel_enrollment: the real
#      build_server_command + build_launch_env, prepare_runtime_dirs=False, launches nothing) on pre-landing
#      origin/main and on the staged tree, both against research origin/main. architect_general@8074's environment
#      must gain exactly GGML_FUSED_DECODE_OFF=1, every other field of every target must be byte-identical, and no
#      other target may carry the key. (If the export refuses because the lean registry is stale against the
#      master, stack_change_pipeline.py update refreshes BOTH scratch trees first; that refresh is discarded.)
#   5. runs the file-scoped orchestrator tests on the staged tree;
#   6. pushes the orchestrator as a fast-forward of origin/main through serialized_push.py's push lock, then ONE
#      root commit (script + evidence + CH-24 fix + landing env proof + PACKAGE.md + receipt + keyed index).
#
# WHAT IT DOES NOT DO: reload, start, stop or signal ANY process; set the stack-change-pending marker; touch a
# kernel tree or the kernel store; change the research repo. The declaration takes effect at :8074's next launch:
# `python3 scripts/server/orchestrator_stack.py reload architect_general`, run by the session that owns that
# role's inference at its own boundary (CLAUDE.md, Process Management). Printed at the end, never run here.
# Until then a running :8074 FAILS env attestation on GGML_FUSED_DECODE_OFF (declared, absent live): that is
# the true state, not a defect of this change.
#
# IDEMPOTENT / RESUMABLE: an orchestrator pin already on origin/main is skipped; a rejected push stops everything
# after it and a re-run resumes. Pin + receipt index on origin/main -> "ALREADY RATIFIED", exit 0.
#
# ROLLBACK: `git revert --no-edit <base>..<tip>` (fast-forward) or `git revert -m 1 <merge>` in the orchestrator
# (the receipt records both), then the owner reloads architect_general. Rolling back restores the fused path.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SRC_ROOT="${SRC_ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"   # the checkout holding the evidence

GATE_ID="RATIFY-FUSED-OFF-ARCHGEN-20261024"
BRANCH="ratify/fused-decode-off-architect-general-20261024"
EVID_REL="artifacts/operator/ratify-fused-off-archgen-20261024"
SCRIPT_REL="scripts/operator/ratify_fused_decode_off_architect_general_20261024.sh"
RECEIPT_REL="artifacts/operator/ratify_fused_decode_off_architect_general_20261024.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
FIX_REL="$EVID_REL/ch24_premise_fix.json"
PACKAGE_SRC="${PACKAGE_SRC:-/mnt/raid0/llm/tmp/ratify-fused-off-20261024/PACKAGE.md}"

ORCH_REPO="${ORCH_REPO:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH_REPO="${RESEARCH_REPO:-/mnt/raid0/llm/epyc-inference-research}"
ROOT_REPO="${ROOT_REPO:-/mnt/raid0/llm/epyc-root}"
ORCH_PY="${ORCH_PY:-/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python}"
SYS_PY="/usr/bin/python3"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-fused-off-archgen"

# ---- pins (filled by the preparing agent; the operator verifies by reading them) ----
ORCH_PIN="bd6123ee7fa802ad9a7f1055a69d88213f6e283c"
ROOT_PINS=(
  "a31467c136c21c280f1f5c105c508665b2196384e65b5ceea16e1fe11a902f8c $EVID_REL/env_before.json"
  "9957bfc201438cc18400b3aaaa4772569eee09d9b09738731c47e9e0f3bd732b $EVID_REL/env_after.json"
  "b9b3d7475cb62f188f6cafa682c7360fb27b62624abe976259c7f9fc088a0bb1 $EVID_REL/env_diff.txt"
  "978f951c7d7f7497eea337be016b6d79d2a744ff494cea8ae2d5c60122a650aa $EVID_REL/qwen4exp_builds_listing.txt"
  "4b1a0e2352fe4704541f626ac742692a36035ac840feda3a40cab677666f34ec $FIX_REL"
)
TARGET="architect_general@8074"     # the ONE launch target whose env changes
KEY="GGML_FUSED_DECODE_OFF"; VALUE="1"
# paths the pinned change may touch (anything else is refused)
ORCH_ALLOWED=(scripts/server/stack_env.py scripts/server/autokernel_enrollment.py
              tests/unit/test_ratify_fused_off_architect_general.py tests/unit/test_launch_env_strip_preserve.py)
ORCH_TESTS=(tests/unit/test_ratify_fused_off_architect_general.py tests/unit/test_launch_env_strip_preserve.py
            tests/unit/test_launch_env_every_branch.py tests/unit/test_stack_env.py tests/unit/test_env_attestation.py
            tests/unit/test_autokernel_enrollment.py tests/unit/test_diag_env_override.py
            tests/unit/test_aux_service_env.py tests/unit/test_build_server_command_helpers.py)

MODE="review"; ATTEST=""; CMP_BEFORE=""; CMP_AFTER=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)  MODE="apply" ;;
    --verify) MODE="verify" ;;
    --attest) shift; ATTEST="${1:-}" ;;
    --compare) MODE="compare"; CMP_BEFORE="${2:-}"; CMP_AFTER="${3:-}"; shift 2 || true ;;
    *) echo "usage: $0 [--dry-run | --verify | --compare BEFORE AFTER | --apply --attest $GATE_ID]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
g() { local repo="$1"; shift; git -c safe.directory='*' -C "$repo" "$@"; }
sha_of() { sha256sum -- "$1" | awk '{print $1}'; }

compare_env() { # before after [state-only] -> prints the table; exits 65 on any violation
  TARGET="$TARGET" KEY="$KEY" VALUE="$VALUE" "$SYS_PY" -I - "$@" <<'PY'
import json, os, sys

target, key, value = os.environ["TARGET"], os.environ["KEY"], os.environ["VALUE"]
state_only = len(sys.argv) > 3 and sys.argv[3] == "state-only"
after = {t["target_id"]: t for t in json.load(open(sys.argv[2]))["targets"]}
before = {} if state_only else {t["target_id"]: t for t in json.load(open(sys.argv[1]))["targets"]}
bad = []
if target not in after:
    bad.append(f"{target} missing from the export")
if not state_only and set(before) != set(after):
    bad.append(f"target set changed: {sorted(set(before) ^ set(after))}")
for tid, t in sorted(after.items()):
    env = t.get("environment") or {}
    if tid == target:
        ok = env.get(key) == value
        if ok and not state_only:
            b_env = before[tid].get("environment") or {}
            ok = key not in b_env and {k: v for k, v in env.items() if k != key} == b_env
        verdict = f"+ {key}={value} ONLY" if ok else "VIOLATION (env)"
        if t.get("aliases"):
            ok = False; verdict = f"VIOLATION (roles ride this process: {t['aliases']})"
    else:
        ok = key not in env and (state_only or env == (before[tid].get("environment") or {}))
        verdict = ("no key" if state_only else "byte-identical") if ok else "VIOLATION (env)"
    if not state_only:
        for k in sorted((set(t) | set(before[tid])) - {"environment"}):
            if t.get(k) != before[tid].get(k):
                ok = False; verdict = f"VIOLATION ({k} changed)"
    if not ok:
        bad.append(f"{tid}: {verdict}")
    print(f"  {verdict:36} {tid:36} aliases={t.get('aliases') or []}")
if bad:
    print("ENV CHECK FAILED:\n  " + "\n  ".join(bad)); sys.exit(65)
print(f"ENV CHECK OK: {target} gains exactly {key}={value} and carries no alias role; "
      + ("no other target carries the key" if state_only
         else f"every other field of all {len(after)} targets is byte-identical"))
PY
}

if [ "$MODE" = "compare" ]; then
  [ -f "$CMP_BEFORE" ] && [ -f "$CMP_AFTER" ] || die "--compare needs two export files"
  compare_env "$CMP_BEFORE" "$CMP_AFTER"; exit $?
fi

for tool in git sha256sum awk timeout "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -x "$ORCH_PY" ] || die "orchestrator interpreter $ORCH_PY missing"
PUSHER="$ROOT_REPO/scripts/coordination/serialized_push.py"
[ -f "$PUSHER" ] || die "$PUSHER not found"
case "$ORCH_PIN ${ROOT_PINS[*]}" in *@@*) die "script was not finalised (unfilled pin)";; esac

# ---------------------------------------------------------------- 1. signer
check_operator_value() { # refuse placeholder-looking values BEFORE the shared rules
  local v="${RATIFY_OPERATOR:-}" low
  [ -n "${v//[[:space:]]/}" ] || die "RATIFY_OPERATOR is required: type your own name, e.g. RATIFY_OPERATOR='Jane Doe'"
  case "$v" in *'<'*|*'>'*) die "RATIFY_OPERATOR='$v' contains '<' or '>': that is a placeholder, type your own name";; esac
  low="$(printf '%s' "$v" | tr '[:upper:]' '[:lower:]')"
  case "$low" in *name*) die "RATIFY_OPERATOR='$v' contains the word 'name': that is a placeholder, type your own name";; esac
}
if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply requires the typed confirmation --attest $GATE_ID"
  check_operator_value
  # shellcheck source=/dev/null
  source "$ROOT_REPO/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator   # exits 65 on an unset/default/system/login/agent name
  check_operator_value      # again on the trimmed value
  say "signer: $RATIFY_OPERATOR"
elif [ -n "${RATIFY_OPERATOR:-}" ]; then
  check_operator_value; say "signer value pre-checked: $RATIFY_OPERATOR (not used: no --apply)"
fi

# ---------------------------------------------------------------- 2. pins
say "== pins (source checkout $SRC_ROOT) =="
for pin in "${ROOT_PINS[@]}"; do
  want="${pin%% *}"; rel="${pin#* }"
  [ -f "$SRC_ROOT/$rel" ] || die "missing evidence file $rel"
  have="$(sha_of "$SRC_ROOT/$rel")"
  [ "$have" = "$want" ] || die "$rel sha256 $have != pinned $want (package changed after preparation)"
  say "  ok  $rel  $have"
done
SCRIPT_SHA="$(sha_of "$SCRIPT_PATH")"
say "  this script sha256 $SCRIPT_SHA (recorded in the receipt)"

for r in "$ORCH_REPO" "$RESEARCH_REPO" "$ROOT_REPO"; do
  g "$r" fetch -q origin main || die "cannot fetch origin main in $r"
done
g "$ORCH_REPO" cat-file -e "$ORCH_PIN^{commit}" 2>/dev/null || g "$ORCH_REPO" fetch -q origin "refs/heads/$BRANCH" \
  || die "orchestrator: pinned commit $ORCH_PIN absent and origin/$BRANCH not fetchable"
g "$ORCH_REPO" cat-file -e "$ORCH_PIN^{commit}" 2>/dev/null || die "orchestrator: pinned commit $ORCH_PIN not present after fetch"
landed() { g "$1" merge-base --is-ancestor "$2" origin/main && echo yes || echo no; }
ORCH_LANDED="$(landed "$ORCH_REPO" "$ORCH_PIN")"
if [ "$ORCH_LANDED" = yes ]; then
  say "  ok  epyc-orchestrator: pin ${ORCH_PIN:0:12} already on origin/main"
else
  tip="$(g "$ORCH_REPO" ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
  [ "$tip" = "$ORCH_PIN" ] || die "epyc-orchestrator: origin/$BRANCH is '${tip:-absent}', not the pinned $ORCH_PIN"
  say "  ok  epyc-orchestrator: origin/$BRANCH == pin ${ORCH_PIN:0:12}"
fi
INDEX_LANDED=no
g "$ROOT_REPO" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && INDEX_LANDED=yes
say "  orchestrator on origin/main: $ORCH_LANDED; receipt index: $INDEX_LANDED"

if [ "$MODE" != "verify" ]; then
  if [ "$ORCH_LANDED$INDEX_LANDED" = "yesyes" ]; then
    say "ALREADY RATIFIED: the pin and $INDEX_REL are on origin/main. Nothing to do (--verify re-proves the env)."
    exit 0
  fi
  [ "$INDEX_LANDED" = no ] || die "$INDEX_REL is on origin/main but the code is not landed. Resolve by hand."
  for r in "$ORCH_REPO" "$ROOT_REPO"; do   # push locks free (read-only)
    st="$("$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$r" --lock-name push --status 2>&1 || true)"
    case "$st" in *FREE*) say "  ok  push lock FREE for $r" ;; *) die "push lock for $r is not free: $st" ;; esac
  done
fi

# ---------------------------------------------------------------- scratch worktrees
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-fused-off-land.XXXXXX")"
WT_ADDED=()
ROOT_COPIED=()
ROOT_WT="$STAGE/root"
cleanup() {
  local wt rel
  for wt in "${WT_ADDED[@]}"; do
    local repo="${wt%%|*}" path="${wt#*|}"
    [ -d "$path" ] || continue
    g "$path" merge --abort >/dev/null 2>&1 || true        # only ever inside OUR scratch worktree
    g "$path" reset -q >/dev/null 2>&1 || true
    g "$path" checkout -q -- . >/dev/null 2>&1 || true     # scratch-only: CH-24 fix / derived refresh
    if [ "$path" = "$ROOT_WT" ]; then
      for rel in "${ROOT_COPIED[@]}"; do
        g "$path" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 || rm -f -- "$path/$rel"
      done
      find "$path/$EVID_REL" "$path/artifacts/operator/receipts" -depth -type d -empty -delete 2>/dev/null || true
    fi
    g "$repo" worktree remove "$path" >/dev/null 2>&1 || say "NOTE: scratch worktree left at $path (inspect, then: git -C $repo worktree remove $path)"
  done
  rm -f -- "$STAGE"/*.txt "$STAGE"/*.json
  rmdir "$STAGE" 2>/dev/null || true
}
trap cleanup EXIT

add_wt() { # repo path rev
  g "$1" worktree add -q --detach "$2" "$3" || die "cannot add a scratch worktree for $1 at $3"
  WT_ADDED+=("$1|$2")
}

check_paths() { # name worktree base tip allowed-var
  local name="$1" wt="$2" base="$3" tip="$4"; local -n allowed="$5"
  local f a okp bad=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue; okp=0
    for a in "${allowed[@]}"; do [ "$f" = "$a" ] && okp=1; done
    [ "$okp" -eq 1 ] || bad="$bad $f"
  done < <(g "$wt" diff --name-only "$(g "$wt" merge-base "$base" "$tip")" "$tip")
  [ -z "$bad" ] || die "$name: the pinned change touches paths outside the allow-list:$bad"
}

land_onto_main() { # name wt pin -> HEAD of wt = origin/main + pin
  local name="$1" wt="$2" pin="$3"
  if g "$wt" merge-base --is-ancestor HEAD "$pin"; then
    g "$wt" merge -q --ff-only "$pin" >/dev/null || die "$name: fast-forward to $pin failed"
    say "  ok  $name: origin/main fast-forwards to pin ${pin:0:12}"
  else
    g "$wt" merge -q --no-ff --no-edit -m "Merge $BRANCH into main ($GATE_ID, operator-signed${RATIFY_OPERATOR:+ by $RATIFY_OPERATOR})" "$pin" >/dev/null 2>&1 \
      || { g "$wt" merge --abort >/dev/null 2>&1 || true;
           die "STALE: $BRANCH no longer merges cleanly onto $name origin/main. The preparer must REGENERATE it; do not reconcile at signing."; }
    say "  ok  $name: origin/main moved; clean --no-ff merge of pin ${pin:0:12} -> $(g "$wt" rev-parse --short HEAD)"
  fi
}

refresh_derived() { # label orch-wt research-master -> stack_change_pipeline update in scratch (discarded later)
  local label="$1" wt="$2" master="$3" out="$STAGE/update-$1.txt" step
  (cd "$wt" && nice -n 19 timeout 900 "$ORCH_PY" scripts/registry/stack_change_pipeline.py update \
     --research-registry "$master" >"$out" 2>&1) || true
  for step in lean_registry guard guard_strict stack_manifest_registry; do
    awk -v s="$step:" '$1==s {print $2}' "$out" | awk '$1=="ok"{f=1} END{exit !f}' \
      || { tail -30 "$out" >&2; die "$label: stack_change_pipeline step $step is not ok"; }
  done
  say "  ok  $label: lean registry refreshed in scratch for the export (discarded; never committed)"
}

export_env() { # label orch-wt research-master revision -> $STAGE/env-<label>.json
  local label="$1" wt="$2" master="$3" rev="$4" out="$STAGE/env-$1.json"
  (cd "$wt" && ORCHESTRATOR_STACK_REEXEC=1 PYTHONPATH=. nice -n 19 timeout 600 "$ORCH_PY" \
     -m scripts.server.autokernel_enrollment --master-registry "$master" --revision "$rev" --instance-mode both \
     >"$out" 2>"$STAGE/env-$label.err.txt")
}

# ---------------------------------------------------------------- verify mode (post-landing, read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$ORCH_LANDED" = yes ]  || { say "  FAIL  orchestrator pin is not on origin/main"; ok=0; }
  [ "$INDEX_LANDED" = yes ] || { say "  FAIL  $INDEX_REL is not on origin/main"; ok=0; }
  [ "$ok" -eq 1 ] || exit 1
  say "== verify: composed launch env on origin/main =="
  add_wt "$ORCH_REPO" "$STAGE/orch" origin/main
  add_wt "$RESEARCH_REPO" "$STAGE/research" origin/main
  RM="$STAGE/research/orchestration/model_registry.yaml"; RREV="$(g "$RESEARCH_REPO" rev-parse origin/main)"
  export_env verify "$STAGE/orch" "$RM" "$RREV" \
    || { refresh_derived verify "$STAGE/orch" "$RM"; export_env verify "$STAGE/orch" "$RM" "$RREV"; } \
    || { tail -10 "$STAGE/env-verify.err.txt" >&2; die "offline production export refused"; }
  compare_env - "$STAGE/env-verify.json" state-only || die "env state check failed (table above)"
  say "VERIFIED: $GATE_ID landed (code + receipt) and origin/main composes $KEY=$VALUE for $TARGET only."
  say "Live: after the owner's reload, tr '\\0' '\\n' < /proc/<pid>/environ on the :8074 pid shows $KEY=$VALUE."
  exit 0
fi

# ---------------------------------------------------------------- 3. stage
say "== staging (scratch $STAGE) =="
ORCH_BASE="$(g "$ORCH_REPO" rev-parse origin/main)"; RES_BASE="$(g "$RESEARCH_REPO" rev-parse origin/main)"
add_wt "$RESEARCH_REPO" "$STAGE/research" "$RES_BASE"     # read-only export input; research is not changed
add_wt "$ORCH_REPO" "$STAGE/orch-base" "$ORCH_BASE"
add_wt "$ORCH_REPO" "$STAGE/orch" "$ORCH_BASE"
if [ "$ORCH_LANDED" = no ]; then
  check_paths orchestrator "$STAGE/orch" "$ORCH_BASE" "$ORCH_PIN" ORCH_ALLOWED
  say "  ok  orchestrator: pinned change touches only: ${ORCH_ALLOWED[*]}"
  land_onto_main orchestrator "$STAGE/orch" "$ORCH_PIN"
fi
STAGED_HEAD="$(g "$STAGE/orch" rev-parse HEAD)"
RM="$STAGE/research/orchestration/model_registry.yaml"

# ---------------------------------------------------------------- 4. env proof
say "== env proof: pre-landing origin/main vs staged (research master ${RES_BASE:0:12}, unchanged) =="
if ! { export_env baseline "$STAGE/orch-base" "$RM" "$RES_BASE" && export_env staged "$STAGE/orch" "$RM" "$RES_BASE"; }; then
  say "  export refused (lean registry stale against the master?); refreshing both scratch trees identically"
  tail -3 "$STAGE"/env-*.err.txt >&2 || true
  refresh_derived baseline "$STAGE/orch-base" "$RM"; refresh_derived staged "$STAGE/orch" "$RM"
  export_env baseline "$STAGE/orch-base" "$RM" "$RES_BASE" || { tail -10 "$STAGE/env-baseline.err.txt" >&2; die "baseline export refused"; }
  export_env staged "$STAGE/orch" "$RM" "$RES_BASE" || { tail -10 "$STAGE/env-staged.err.txt" >&2; die "staged export refused"; }
fi
if ! compare_env "$STAGE/env-baseline.json" "$STAGE/env-staged.json" | tee "$STAGE/env-landing-diff.txt"; then
  die "env proof failed (table above)"
fi
g "$STAGE/orch" checkout -q -- .   # drop any scratch-only derived refresh: only the pinned commits land
[ "$(g "$STAGE/orch" rev-parse HEAD)" = "$STAGED_HEAD" ] && [ -z "$(g "$STAGE/orch" status --porcelain --untracked-files=no)" ] \
  || die "orchestrator scratch tree is not exactly the staged commit"

# ---------------------------------------------------------------- 5. tests
(cd "$STAGE/orch" && nice -n 19 timeout 1800 "$ORCH_PY" -m pytest -q -p no:cacheprovider -o addopts= "${ORCH_TESTS[@]}" \
   >"$STAGE/orch-tests.txt" 2>&1) || { tail -20 "$STAGE/orch-tests.txt" >&2; die "orchestrator file-scoped tests FAILED on the staged tree"; }
TESTS_LINE="$(tail -1 "$STAGE/orch-tests.txt")"
say "  ok  orchestrator tests: $TESTS_LINE"
g "$STAGE/orch" checkout -q -- .

# ---------------------------------------------------------------- root staging
add_wt "$ROOT_REPO" "$ROOT_WT" origin/main
for pin in "${ROOT_PINS[@]}"; do
  want="${pin%% *}"; rel="${pin#* }"
  if [ -e "$ROOT_WT/$rel" ] && [ "$(sha_of "$ROOT_WT/$rel")" != "$want" ]; then
    die "root: origin/main already has a DIFFERENT $rel; refusing to overwrite it"
  fi
  mkdir -p "$(dirname "$ROOT_WT/$rel")"; cp -- "$SRC_ROOT/$rel" "$ROOT_WT/$rel"; ROOT_COPIED+=("$rel")
  [ "$(sha_of "$ROOT_WT/$rel")" = "$want" ] || die "root: $rel changed during the copy"
done
mkdir -p "$(dirname "$ROOT_WT/$SCRIPT_REL")"; cp -- "$SCRIPT_PATH" "$ROOT_WT/$SCRIPT_REL"; ROOT_COPIED+=("$SCRIPT_REL")
[ "$(sha_of "$ROOT_WT/$SCRIPT_REL")" = "$SCRIPT_SHA" ] || die "root: script changed during the copy"
# CH-24 premise fix: an exact, unique fragment replacement on FRESH main (refuses if the row text drifted)
FIX_PATH="$("$SYS_PY" -I - "$ROOT_WT" "$ROOT_WT/$FIX_REL" <<'PY'
import json, sys
root, fx = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
p = f"{root}/{fx['path']}"
s = open(p, encoding="utf-8").read()
if s.count(fx["new"]) == 1 and s.count(fx["old"]) == 0:
    print(fx["path"]); sys.exit(0)          # already applied on main
if s.count(fx["old"]) != 1:
    sys.exit(f"CH-24 premise text occurs {s.count(fx['old'])} times in {fx['path']} (expected 1): the row drifted")
open(p, "w", encoding="utf-8").write(s.replace(fx["old"], fx["new"]))
print(fx["path"])
PY
)" || die "STALE: the CH-24 row in handoffs/active/autokernel-champion-aggregate.md changed; the preparer must regenerate $FIX_REL"
say "  ok  root: CH-24 premise fix applies to $FIX_PATH on fresh main"
cp -- "$STAGE/env-baseline.json" "$ROOT_WT/$EVID_REL/landing_env_before.json"
cp -- "$STAGE/env-staged.json" "$ROOT_WT/$EVID_REL/landing_env_after.json"
cp -- "$STAGE/env-landing-diff.txt" "$ROOT_WT/$EVID_REL/landing_env_diff.txt"
ROOT_COPIED+=("$EVID_REL/landing_env_before.json" "$EVID_REL/landing_env_after.json" "$EVID_REL/landing_env_diff.txt")
PACKAGE_SHA="(absent at signing)"
if [ -f "$PACKAGE_SRC" ]; then
  cp -- "$PACKAGE_SRC" "$ROOT_WT/$EVID_REL/PACKAGE.md"; ROOT_COPIED+=("$EVID_REL/PACKAGE.md")
  PACKAGE_SHA="$(sha_of "$ROOT_WT/$EVID_REL/PACKAGE.md")"
fi
ROOT_COPIED+=("$RECEIPT_REL" "$INDEX_REL")
[ ! -e "$ROOT_WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists on origin/main (token spent)"
[ ! -e "$ROOT_WT/$INDEX_REL" ] || die "$INDEX_REL already exists on origin/main (token spent)"
say "  ok  root: script + evidence + CH-24 fix + landing proof staged on origin/main $(g "$ROOT_WT" rev-parse --short HEAD)"

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN -- nothing was pushed, no receipt was written. --apply would:"
  [ "$ORCH_LANDED" = yes ] || say "  1. push orchestrator $(g "$STAGE/orch" rev-parse --short HEAD) (origin/main + pin ${ORCH_PIN:0:12}) under the push lock"
  say "  2. commit script + evidence + CH-24 fix + PACKAGE.md + $RECEIPT_REL + $INDEX_REL on fresh root origin/main and push it"
  say "  It reloads NOTHING. The scratch worktrees are removed on exit."
  say "DRY-RUN OK: $GATE_ID -- all preconditions hold."
  exit 0
fi

# ---------------------------------------------------------------- 6. push (apply)
push_locked() { # name repo-for-lock worktree
  local name="$1" repo="$2" wt="$3" tokdir tok rc=0
  tokdir="$(mktemp -d "$STAGE_PARENT/ratify-fused-off-push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || { rmdir "$tokdir" 2>/dev/null; die "$name: could not take the push lock"; }
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" git -c safe.directory='*' -C "$wt" push origin HEAD:refs/heads/main || rc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: $name push lock release failed -- check serialized_push.py --status"
  rm -f "$tok"; rmdir "$tokdir" 2>/dev/null || true
  [ "$rc" -eq 0 ] || die "$name: git push rejected (rc=$rc; origin/main probably moved). Nothing after this was pushed; re-run to resume."
  say "  pushed $name $(g "$wt" rev-parse --short HEAD) -> origin/main"
}
say ""; say "== landing =="
ORCH_SHA="(landed before this run)"
if [ "$ORCH_LANDED" = no ]; then push_locked orchestrator "$ORCH_REPO" "$STAGE/orch"; ORCH_SHA="$(g "$STAGE/orch" rev-parse HEAD)"; fi
g "$ORCH_REPO" fetch -q origin main
[ "$(landed "$ORCH_REPO" "$ORCH_PIN")" = yes ] || die "orchestrator pin not on origin/main after the push"

mkdir -p "$ROOT_WT/artifacts/operator/receipts"
RECEIPT_ABS="$ROOT_WT/$RECEIPT_REL" INDEX_ABS="$ROOT_WT/$INDEX_REL" RECEIPT_REL="$RECEIPT_REL" GATE_ID="$GATE_ID" \
OPERATOR="$RATIFY_OPERATOR" O_SHA="$ORCH_SHA" O_PIN="$ORCH_PIN" O_BASE="$ORCH_BASE" R_BASE="$RES_BASE" \
SCRIPT_SHA="$SCRIPT_SHA" PACKAGE_SHA="$PACKAGE_SHA" TESTS_LINE="$TESTS_LINE" TARGET="$TARGET" BRANCH="$BRANCH" \
EVID_REL="$EVID_REL" PINS="$(printf '%s\n' "${ROOT_PINS[@]}")" "$SYS_PY" - <<'PY'
import datetime, json, os
e = os.environ
pins = {line.split(" ", 1)[1]: line.split(" ", 1)[0] for line in e["PINS"].splitlines() if line.strip()}
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": e["GATE_ID"],
    "status": "ratified",
    "human_attestation": e["GATE_ID"],
    "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "signed_by": e["OPERATOR"],
    "signed_by_uid": os.getuid(),
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "package": f"{e['EVID_REL']}/PACKAGE.md",
    "package_sha256": e["PACKAGE_SHA"],
    "decision": ("GGML_FUSED_DECODE_OFF=1 DECLARED for architect_general (:8074 Qwen3.8-Flash-Next UD-IQ4_XS, "
                 "qwen4exp, full CPU) in epyc-orchestrator scripts/server/stack_env.py _ROLE_ENV_BLOCKS. Serves the "
                 "measured graph path instead of the default-ON fused decode (open FD-DIV-1b defect; CH-24 /tmp "
                 "debug writes). Follow-up: measure fused ON vs OFF on Q38FN once FD-DIV-1b is fixed."),
    "launch_target": e["TARGET"],
    "branch": e["BRANCH"],
    "pinned_commits": {"epyc-orchestrator": e["O_PIN"]},
    "pre_landing_origin_main": {"epyc-orchestrator": e["O_BASE"], "epyc-inference-research (read-only input)": e["R_BASE"]},
    "landed": {
        "epyc-orchestrator": {"commit": e["O_SHA"], "ref": "origin/main"},
        "epyc-root": {"commit": "the commit carrying this receipt", "ref": "origin/main"},
    },
    "env_proof": f"{e['EVID_REL']}/landing_env_diff.txt",
    "tests": e["TESTS_LINE"],
    "pinned_sha256": pins,
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "reloads_performed": [],
    "effective": ("at architect_general's next launch, by its owning session: "
                  "python3 scripts/server/orchestrator_stack.py reload architect_general. None performed here. "
                  "Until then a running :8074 fails env attestation on GGML_FUSED_DECODE_OFF (declared, absent live)."),
}
with open(e["RECEIPT_ABS"], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, sort_keys=True); fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
with open(e["INDEX_ABS"], "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "attest", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
PY
ROOT_PATHS=("$SCRIPT_REL" "$RECEIPT_REL" "$INDEX_REL" "$FIX_PATH" "$EVID_REL/landing_env_before.json"
            "$EVID_REL/landing_env_after.json" "$EVID_REL/landing_env_diff.txt")
[ -f "$ROOT_WT/$EVID_REL/PACKAGE.md" ] && ROOT_PATHS+=("$EVID_REL/PACKAGE.md")
for pin in "${ROOT_PINS[@]}"; do ROOT_PATHS+=("${pin#* }"); done
g "$ROOT_WT" add -- "${ROOT_PATHS[@]}"
g "$ROOT_WT" commit -q -m "RATIFIED $GATE_ID: GGML_FUSED_DECODE_OFF=1 declared for architect_general (signed by $RATIFY_OPERATOR)" \
  -m "orchestrator ${ORCH_SHA:0:12} landed; CH-24 premise corrected; receipt $RECEIPT_REL + index $INDEX_REL. Reloads: none (the owner reloads architect_general at its own boundary)." \
  || die "root: commit failed (a pre-commit hook refused it?); the orchestrator is landed, re-run to resume the root step"
push_locked root "$ROOT_REPO" "$ROOT_WT"

cat <<EOF

RATIFIED $GATE_ID by $RATIFY_OPERATOR.
  orchestrator: $ORCH_SHA
  root:         receipt $RECEIPT_REL + $INDEX_REL (in the pushed root commit)
NOTHING WAS RELOADED. A running :8074 still runs the fused path and FAILS env attestation on
$KEY (declared, absent live) until it is relaunched.

OWNER STEP (not part of this signature; the session that owns architect_general's inference, at its own
boundary), from the orchestrator repo:
  python3 scripts/server/orchestrator_stack.py reload architect_general   # :8074
then: tr '\0' '\n' < /proc/<pid>/environ | grep $KEY   shows $KEY=$VALUE on the :8074 pid.

POST-APPLY VERIFICATION (read-only):  bash $SCRIPT_REL --verify
EOF
