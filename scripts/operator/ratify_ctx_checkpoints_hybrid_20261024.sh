#!/bin/bash
# ratify_ctx_checkpoints_hybrid_20261024.sh -- operator signature AND landing for RATIFY-CTXCKPT-HYBRID-20261024:
# `--ctx-checkpoints 32` DECLARED (not inherited from the kernel default) on every HYBRID serving role.
#
#   Review / dry run (default; pushes nothing, writes no receipt):
#     bash scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh --dry-run
#   Sign and land (the OPERATOR runs this, from a terminal):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh --apply --attest RATIFY-CTXCKPT-HYBRID-20261024
#   Verify the post-state (read-only apart from scratch worktrees it removes):
#     bash scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh --verify
#
# Run it from a checkout of epyc-root branch ratify/ctx-checkpoints-hybrid-20261024 (it holds the pinned evidence).
# Package summary: /mnt/raid0/llm/tmp/ratify-ctxckpt-20261024/PACKAGE.md (copied into the landing commit).
#
# WHY: on a hybrid model (gated-delta-net / SSM layers) context checkpoints are the only partial-restore point;
# KPF-64.4 measured checkpoints-off at -3.9 pp prefix-hit share and ~1,400 extra uncached tok/req on frontdoor.
# Every role gets 32 from llama-server's built-in default today and nothing declares it, so a kernel-default
# change would silently change production. 32 == the v10 default (common/common.h:633): behaviour is UNCHANGED.
#
# WHAT IT CHANGES (pinned branch tips, both pushed, neither merged):
#   epyc-inference-research  orchestration/model_registry.yaml (the MASTER): server_mode.{frontdoor,
#                            architect_critic,architect_general}.ctx_checkpoints: 32
#   epyc-orchestrator        compile (src/registry/stack_priors.py), emit (scripts/server/orchestrator_stack.py
#                            _RUNTIME_SERVING_FLAG_ARGS), attest (scripts/server/stack_commands.py, resolved value),
#                            tests/unit/test_ratify_ctxckpt_hybrid.py, and the derived regen (lean registry,
#                            descriptors, stack priors, generated summary)
#   epyc-root                this script, the evidence dir, PACKAGE.md, the receipt + keyed receipt index
#
# WHAT IT DOES (--apply), in order, each step refusing on any mismatch:
#   1. checks the signer (typed --attest token; RATIFY_OPERATOR set, not a default/system/agent name);
#   2. verifies the sha256 of every pinned evidence file, and that origin/<branch> of research and orchestrator
#      is EXACTLY the pinned commit (a moved branch is a different package: refuse);
#   3. stages, in scratch worktrees at a FRESH origin/main of each repo: a fast-forward to the pin when possible,
#      else a clean --no-ff merge (a conflict refuses: the package is STALE and its preparer regenerates it);
#      a path allow-list check of the pinned change; then `stack_change_pipeline.py update` (stack-change skill
#      phase 7) against the merged master -- a substantive derived change is committed in the scratch tree,
#      volatile fingerprint/timestamp churn is discarded;
#   4. PROVES THE ARGV: the offline production export (scripts.server.autokernel_enrollment, which calls the real
#      build_server_command with prepare_runtime_dirs=False and launches nothing) on the pre-landing origin/main
#      pair (re-derived the same way) and on the staged pair; every hybrid target must gain exactly
#      `--ctx-checkpoints 32`, every other target must be byte-identical, and the hybrid set must equal the set of
#      targets whose GGUF general.architecture is hybrid (llm_arch_is_hybrid in the frozen v10 tree);
#   5. runs the file-scoped orchestrator tests on the staged tree;
#   6. pushes research, then orchestrator, each as a fast-forward of origin/main from the scratch worktree
#      through scripts/coordination/serialized_push.py's push lock; then ONE root commit (script + evidence +
#      landing argv proof + PACKAGE.md + receipt + keyed index) the same way.
#
# WHAT IT DOES NOT DO: reload, start, stop or signal ANY process; set the stack-change-pending marker (there is no
# bring-up: behaviour is unchanged). RELOAD NEEDED? Not for behaviour (32 is what every server already runs) and
# not for attestation (the attestation compares the RESOLVED value, so a pre-reload server on the default is
# clean). The flag APPEARS in a server's live argv at its next ordinary reload, done by the session that owns that
# role's inference at its own boundary (CLAUDE.md, Process Management) -- printed at the end, never run here.
# No production kernel tree or kernel-store file is touched.
#
# IDEMPOTENT / RESUMABLE: a repo whose pin is already an ancestor of origin/main is skipped; a rejected push stops
# everything after it and a re-run resumes. Both pins landed + receipt index on root origin/main -> "ALREADY
# RATIFIED", exit 0.
#
# ROLLBACK: `git revert -m 1 <merge>` (or `git revert <A>..<tip>` after a fast-forward) in orchestrator and
# research -- the landed commits are in the receipt -- then the owners reload frontdoor, architect_general,
# architect_critic at their own boundary. Rolling back restores "inherit the kernel default", i.e. the same 32.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SRC_ROOT="${SRC_ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"   # the checkout holding the evidence

GATE_ID="RATIFY-CTXCKPT-HYBRID-20261024"
BRANCH="ratify/ctx-checkpoints-hybrid-20261024"
EVID_REL="artifacts/operator/ratify-ctxckpt-hybrid-20261024"
SCRIPT_REL="scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh"
RECEIPT_REL="artifacts/operator/ratify_ctx_checkpoints_hybrid_20261024.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
PACKAGE_SRC="${PACKAGE_SRC:-/mnt/raid0/llm/tmp/ratify-ctxckpt-20261024/PACKAGE.md}"

ORCH_REPO="${ORCH_REPO:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH_REPO="${RESEARCH_REPO:-/mnt/raid0/llm/epyc-inference-research}"
ROOT_REPO="${ROOT_REPO:-/mnt/raid0/llm/epyc-root}"
ORCH_PY="${ORCH_PY:-/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python}"
SYS_PY="/usr/bin/python3"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-ctxckpt-hybrid"

# ---- pins (filled by the preparing agent; the operator verifies by reading them) ----
ORCH_PIN="aeb077cda08ce7ba6d9a92ce5a2717c9ae78fd03"
RESEARCH_PIN="7e201b50efd66899a55aac98149e7238c5eed5a8"
ROOT_PINS=(
  "36de55dc85e275ca69db2945a33e64103ad469f183060ef46a51a71cbb0b618e $EVID_REL/argv_before.json"
  "2edc2c1df296cde7170ccd656d9f97aadaffce398e08fc466f96959fce8524b6 $EVID_REL/argv_after.json"
  "14e0d478ebcffce46f8616320c1ad9a91f1f4dde86f7da5cf9b71682b0387d7f $EVID_REL/argv_diff.txt"
  "2ba83d6d482abaf500ac86dee265c84ad1465bd52b6c798f4661a9ca0fd8fa3b $EVID_REL/gguf_arch.txt"
)
# the launch targets that must gain `--ctx-checkpoints 32` (and nothing else may change anywhere)
HYBRID_TARGETS="frontdoor@8070 frontdoor@8080 frontdoor@8180 architect_general@8074 architect_critic@8083"
# paths the pinned change may touch (anything else is refused)
ORCH_ALLOWED=(src/registry/stack_priors.py scripts/server/orchestrator_stack.py scripts/server/stack_commands.py
              tests/unit/test_ratify_ctxckpt_hybrid.py orchestration/model_registry.yaml
              orchestration/derived/stack_priors.yaml orchestration/model_descriptors.yaml
              docs/generated/current_stack_summary.md)
RESEARCH_ALLOWED=(orchestration/model_registry.yaml)
DERIVED=(orchestration/model_registry.yaml orchestration/derived/stack_priors.yaml orchestration/model_descriptors.yaml
         docs/generated/current_stack_summary.md orchestration/procedures/add_model_to_registry.yaml
         orchestration/procedure.schema.json)
ORCH_TESTS=(tests/unit/test_ratify_ctxckpt_hybrid.py tests/unit/test_stackchg_8083_idle_slots.py
            tests/unit/test_stackchg_8083_batch.py tests/unit/test_orchestrator_stack_reload.py
            tests/unit/test_build_server_command_helpers.py tests/unit/test_autokernel_enrollment.py
            tests/unit/test_prefix_cache_policy.py tests/unit/test_external_drafter_launch.py)
# lines of a derived file that change on every compile and carry no launch fact
VOLATILE_RE='^[+-](compiled_at: |# Compiled at: |# Cache key: |# noncanonical master input at |# with drafter selection from |[[:space:]]*(sha256: [0-9a-f]{64}|repo_commit: [0-9a-f]+|path: /.*/orchestration/model_registry[.]yaml)$|- [a-z_/]+[.](yaml|md): `[0-9a-f]{64}`$)'

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
g() { local repo="$1"; shift; git -c safe.directory='*' -C "$repo" "$@"; }
sha_of() { sha256sum -- "$1" | awk '{print $1}'; }

for tool in git sha256sum awk timeout "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -x "$ORCH_PY" ] || die "orchestrator interpreter $ORCH_PY missing"
PUSHER="$ROOT_REPO/scripts/coordination/serialized_push.py"
[ -f "$PUSHER" ] || die "$PUSHER not found"
case "${ROOT_PINS[*]}" in *@@*) die "script was not finalised (unfilled pin)";; esac

# ---------------------------------------------------------------- 1. signer
if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply requires the typed confirmation --attest $GATE_ID"
  # shellcheck source=/dev/null
  source "$ROOT_REPO/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator   # exits 65 on an unset/default/system/login/agent name
  say "signer: $RATIFY_OPERATOR"
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
for pair in "$ORCH_REPO|$ORCH_PIN" "$RESEARCH_REPO|$RESEARCH_PIN"; do
  r="${pair%%|*}"; want="${pair#*|}"
  g "$r" cat-file -e "$want^{commit}" 2>/dev/null || g "$r" fetch -q origin "refs/heads/$BRANCH" \
    || die "$r: pinned commit $want absent and origin/$BRANCH not fetchable"
  g "$r" cat-file -e "$want^{commit}" 2>/dev/null || die "$r: pinned commit $want not present after fetch"
  if g "$r" merge-base --is-ancestor "$want" origin/main; then
    say "  ok  $(basename "$r"): pin ${want:0:12} already on origin/main"
  else
    tip="$(g "$r" ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
    [ "$tip" = "$want" ] || die "$(basename "$r"): origin/$BRANCH is '${tip:-absent}', not the pinned $want"
    say "  ok  $(basename "$r"): origin/$BRANCH == pin ${want:0:12}"
  fi
done

landed() { g "$1" merge-base --is-ancestor "$2" origin/main && echo yes || echo no; }
ORCH_LANDED="$(landed "$ORCH_REPO" "$ORCH_PIN")"
RES_LANDED="$(landed "$RESEARCH_REPO" "$RESEARCH_PIN")"
INDEX_LANDED=no
g "$ROOT_REPO" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && INDEX_LANDED=yes
say "  orchestrator on origin/main: $ORCH_LANDED; research: $RES_LANDED; receipt index: $INDEX_LANDED"

if [ "$MODE" != "verify" ]; then
  if [ "$ORCH_LANDED$RES_LANDED$INDEX_LANDED" = "yesyesyes" ]; then
    say "ALREADY RATIFIED: both pins and $INDEX_REL are on origin/main. Nothing to do (--verify re-proves the argv)."
    exit 0
  fi
  [ "$INDEX_LANDED" = no ] || die "$INDEX_REL is on origin/main but the code is not fully landed. Resolve by hand."
  # push locks free (read-only)
  for r in "$ORCH_REPO" "$RESEARCH_REPO" "$ROOT_REPO"; do
    st="$("$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$r" --lock-name push --status 2>&1 || true)"
    case "$st" in *FREE*) say "  ok  push lock FREE for $r" ;; *) die "push lock for $r is not free: $st" ;; esac
  done
fi

# ---------------------------------------------------------------- scratch worktrees
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ctxckpt-land.XXXXXX")"
WT_ADDED=()
ROOT_COPIED=()
ROOT_WT="$STAGE/root"
cleanup() {
  local wt rel
  for wt in "${WT_ADDED[@]}"; do
    local repo="${wt%%|*}" path="${wt#*|}"
    [ -d "$path" ] || continue
    g "$path" merge --abort >/dev/null 2>&1 || true        # only ever inside OUR scratch worktree
    if [ "$path" = "$ROOT_WT" ]; then
      g "$path" reset -q >/dev/null 2>&1 || true
      for rel in "${ROOT_COPIED[@]}"; do
        g "$path" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 || rm -f -- "$path/$rel"
      done
      find "$path/$EVID_REL" -depth -type d -empty -delete 2>/dev/null || true
    else
      g "$path" checkout -q -- . >/dev/null 2>&1 || true     # scratch-only: derived files `update` rewrote
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

derive() { # label orch-wt research-master-file -> runs `update`; refuses unless only live-drift errors
  local label="$1" wt="$2" master="$3" out="$STAGE/update-$1.txt" bad
  (cd "$wt" && nice -n 19 timeout 900 "$ORCH_PY" scripts/registry/stack_change_pipeline.py update \
     --research-registry "$master" >"$out" 2>&1) || true
  for step in lean_registry guard guard_strict stack_manifest_registry serving_shape_capacity; do
    awk -v s="$step:" '$1==s {print $2}' "$out" | awk '$1=="ok"{f=1} END{exit !f}' \
      || { tail -30 "$out" >&2; die "$label: stack_change_pipeline step $step is not ok"; }
  done
  awk '$1=="stack_priors:" {print $2}' "$out" | awk '$1=="ok"||$1=="updated"{f=1} END{exit !f}' \
    || { tail -30 "$out" >&2; die "$label: stack_priors did not compile"; }
  bad="$(awk '/^[[:space:]]*error:/ && !/live process drift/' "$out")"
  [ -z "$bad" ] || { printf '%s\n' "$bad" >&2; die "$label: stack_change_pipeline reported errors other than lane-worktree live drift"; }
  say "  ok  $label: stack_change_pipeline update compiled clean (live-drift errors only: a scratch tree has no state file)"
}

substantive_derived_change() { # wt -> yes|no
  local wt="$1" lines
  lines="$(g "$wt" diff -U0 -- "${DERIVED[@]}" | awk '/^[+-]/ && !/^(\+\+\+|---)/' | { grep -E -v -- "$VOLATILE_RE" || true; })"
  [ -n "$lines" ] && echo yes || echo no
}

export_argv() { # label orch-wt research-master revision -> $STAGE/argv-<label>.json
  local label="$1" wt="$2" master="$3" rev="$4" out="$STAGE/argv-$1.json"
  (cd "$wt" && ORCHESTRATOR_STACK_REEXEC=1 PYTHONPATH=. nice -n 19 timeout 600 "$ORCH_PY" \
     -m scripts.server.autokernel_enrollment --master-registry "$master" --revision "$rev" --instance-mode both \
     >"$out" 2>"$STAGE/argv-$label.err.txt") \
    || { tail -10 "$STAGE/argv-$label.err.txt" >&2; die "$label: offline production export refused"; }
}

compare_argv() { # before after [state-only] -> prints the table; exits 65 on any violation
  HYBRID_TARGETS="$HYBRID_TARGETS" "$SYS_PY" -I - "$@" <<'PY'
import json, os, struct, sys

# llm_arch_is_hybrid() in the frozen v10 tree (src/llama-arch.cpp:1040-1060), GGUF arch strings
HYBRID = {"jamba", "falcon-h1", "plamo2", "granitehybrid", "lfm2", "lfm2moe", "nemotron_h", "nemotron_h_moe",
          "qwen3next", "kimi-linear", "qwen35", "qwen35moe", "qwen4exp", "deepseek4"}
T = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}

def gguf_arch(path):  # KV header only; never reads tensor data
    def rd(f, fmt): return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
    def rs(f): return f.read(rd(f, "<Q")).decode("utf-8", "replace")
    def rv(f, t):
        if t in T: return rd(f, T[t])
        if t == 8: return rs(f)
        if t == 9:
            et, n = rd(f, "<I"), rd(f, "<Q")
            for _ in range(n): rv(f, et)
            return None
        raise ValueError(t)
    with open(path, "rb") as f:
        if f.read(4) != b"GGUF": return None
        rd(f, "<I"); rd(f, "<Q"); n = rd(f, "<Q")
        for _ in range(n):
            k = rs(f); v = rv(f, rd(f, "<I"))
            if k == "general.architecture": return v
    return None

expected = set(os.environ["HYBRID_TARGETS"].split())
state_only = len(sys.argv) > 3 and sys.argv[3] == "state-only"
after = {t["target_id"]: t for t in json.load(open(sys.argv[2]))["targets"]}
before = {} if state_only else {t["target_id"]: t for t in json.load(open(sys.argv[1]))["targets"]}
bad = []
if not state_only and set(before) != set(after):
    bad.append(f"target set changed: {sorted(set(before) ^ set(after))}")
gguf_hybrid = set()
for tid, t in sorted(after.items()):
    a = t.get("command_argv") or []
    arch = gguf_arch(a[a.index("-m") + 1]) if "-m" in a else None
    if arch in HYBRID: gguf_hybrid.add(tid)
    n = a.count("--ctx-checkpoints")
    if tid in expected:
        i = a.index("--ctx-checkpoints") if n else -1
        ok = n == 1 and a[i + 1] == "32"
        if ok and not state_only:
            for key in ("command_argv", "argv"):
                x = t.get(key) or []
                j = x.index("--ctx-checkpoints") if "--ctx-checkpoints" in x else -1
                ok = ok and j >= 0 and x[:j] + x[j + 2:] == (before[tid].get(key) or [])
        verdict = "+ --ctx-checkpoints 32 ONLY" if ok else "VIOLATION"
    else:
        ok = n == 0 and (state_only or (t.get("command_argv") == before[tid].get("command_argv")
                                         and t.get("argv") == before[tid].get("argv")))
        verdict = ("no flag" if state_only else "byte-identical") if ok else "VIOLATION"
    if not state_only:
        for key in ("environment", "environment_unsets", "topology", "workload", "aliases", "backend", "device"):
            if t.get(key) != before[tid].get(key):
                ok = False; verdict = f"VIOLATION ({key} changed)"
    if not ok: bad.append(f"{tid}: {verdict}")
    print(f"  {verdict:28} {tid:36} arch={arch}")
if gguf_hybrid != expected:
    bad.append(f"hybrid-by-GGUF targets {sorted(gguf_hybrid)} != declared {sorted(expected)}")
if bad:
    print("ARGV CHECK FAILED:\n  " + "\n  ".join(bad)); sys.exit(65)
print(f"ARGV CHECK OK: {len(expected)} hybrid targets gain exactly --ctx-checkpoints 32; "
      + ("no other target carries it" if state_only else "every other target byte-identical")
      + "; hybrid set == GGUF-hybrid set")
PY
}

# ---------------------------------------------------------------- verify mode (post-landing, read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$ORCH_LANDED" = yes ] || { say "  FAIL  orchestrator pin is not on origin/main"; ok=0; }
  [ "$RES_LANDED" = yes ]  || { say "  FAIL  research pin is not on origin/main"; ok=0; }
  [ "$INDEX_LANDED" = yes ] || { say "  FAIL  $INDEX_REL is not on origin/main"; ok=0; }
  [ "$ok" -eq 1 ] || exit 1
  say "== verify: compiled argv on origin/main =="
  add_wt "$ORCH_REPO" "$STAGE/orch" origin/main
  add_wt "$RESEARCH_REPO" "$STAGE/research" origin/main
  derive verify "$STAGE/orch" "$STAGE/research/orchestration/model_registry.yaml"
  export_argv verify "$STAGE/orch" "$STAGE/research/orchestration/model_registry.yaml" "$(g "$RESEARCH_REPO" rev-parse origin/main)"
  compare_argv - "$STAGE/argv-verify.json" state-only || die "argv state check failed (table above)"
  say "VERIFIED: $GATE_ID landed (code + receipt) and origin/main compiles --ctx-checkpoints 32 for every hybrid target only."
  say "Live argv carries it after each owner's next reload (see the end of --apply's output)."
  exit 0
fi

# ---------------------------------------------------------------- 3. stage
say "== staging (scratch $STAGE) =="
ORCH_BASE="$(g "$ORCH_REPO" rev-parse origin/main)"; RES_BASE="$(g "$RESEARCH_REPO" rev-parse origin/main)"
# Resume fix (2026-10-24, 3c4ca599): when a pin already landed, origin/main already carries the change, so the argv proof
# must compare against the PRE-LANDING main recorded by the first --apply run (its push log: orchestrator 26affbf8..aeb077cd,
# research d3db98e28..7e201b50e), not today's main. The staging trees below still build on current origin/main.
PROOF_ORCH_BASE="$ORCH_BASE"; PROOF_RES_BASE="$RES_BASE"
[ "$ORCH_LANDED" = yes ] && PROOF_ORCH_BASE="$(g "$ORCH_REPO" rev-parse 26affbf8)"
[ "$RES_LANDED" = yes ] && PROOF_RES_BASE="$(g "$RESEARCH_REPO" rev-parse d3db98e28)"
add_wt "$RESEARCH_REPO" "$STAGE/research-base" "$PROOF_RES_BASE"
add_wt "$ORCH_REPO" "$STAGE/orch-base" "$PROOF_ORCH_BASE"
add_wt "$RESEARCH_REPO" "$STAGE/research" "$RES_BASE"
add_wt "$ORCH_REPO" "$STAGE/orch" "$ORCH_BASE"
if [ "$RES_LANDED" = no ]; then
  check_paths research "$STAGE/research" "$RES_BASE" "$RESEARCH_PIN" RESEARCH_ALLOWED
  land_onto_main research "$STAGE/research" "$RESEARCH_PIN"
fi
if [ "$ORCH_LANDED" = no ]; then
  check_paths orchestrator "$STAGE/orch" "$ORCH_BASE" "$ORCH_PIN" ORCH_ALLOWED
  land_onto_main orchestrator "$STAGE/orch" "$ORCH_PIN"
fi
RES_MASTER="$STAGE/research/orchestration/model_registry.yaml"

derive staged "$STAGE/orch" "$RES_MASTER"
REGEN_SHA=""
if [ "$(substantive_derived_change "$STAGE/orch")" = yes ]; then
  g "$STAGE/orch" add -- "${DERIVED[@]}"
  g "$STAGE/orch" commit -q \
    -m "derived($GATE_ID): regen at landing against research $(g "$STAGE/research" rev-parse --short HEAD)" \
    -m "stack_change_pipeline update after merging $BRANCH onto a moved origin/main (stack-change phase 7)." \
    || die "orchestrator: could not commit the landing regen"
  REGEN_SHA="$(g "$STAGE/orch" rev-parse HEAD)"
  say "  ok  orchestrator: substantive derived change after the merge committed as ${REGEN_SHA:0:12}"
else
  g "$STAGE/orch" checkout -q -- .
  say "  ok  orchestrator: derived files already match the merged master (fingerprint churn discarded)"
fi
[ -z "$(g "$STAGE/orch" status --porcelain --untracked-files=no)" ] || die "orchestrator scratch tree is dirty after staging"

# ---------------------------------------------------------------- 4. argv proof
say "== argv proof: pre-landing origin/main vs staged =="
derive baseline "$STAGE/orch-base" "$STAGE/research-base/orchestration/model_registry.yaml"
export_argv baseline "$STAGE/orch-base" "$STAGE/research-base/orchestration/model_registry.yaml" "$PROOF_RES_BASE"
export_argv staged "$STAGE/orch" "$RES_MASTER" "$(g "$STAGE/research" rev-parse HEAD)"
if ! compare_argv "$STAGE/argv-baseline.json" "$STAGE/argv-staged.json" | tee "$STAGE/argv-landing-diff.txt"; then
  die "argv proof failed (table above)"
fi

# ---------------------------------------------------------------- 5. tests
(cd "$STAGE/orch" && nice -n 19 timeout 1800 "$ORCH_PY" -m pytest -q -p no:cacheprovider -o addopts= "${ORCH_TESTS[@]}" \
   >"$STAGE/orch-tests.txt" 2>&1) || { tail -20 "$STAGE/orch-tests.txt" >&2; die "orchestrator file-scoped tests FAILED on the staged tree"; }
TESTS_LINE="$(tail -1 "$STAGE/orch-tests.txt")"
say "  ok  orchestrator tests: $TESTS_LINE"

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
cp -- "$STAGE/argv-baseline.json" "$ROOT_WT/$EVID_REL/landing_argv_before.json"
cp -- "$STAGE/argv-staged.json" "$ROOT_WT/$EVID_REL/landing_argv_after.json"
cp -- "$STAGE/argv-landing-diff.txt" "$ROOT_WT/$EVID_REL/landing_argv_diff.txt"
ROOT_COPIED+=("$EVID_REL/landing_argv_before.json" "$EVID_REL/landing_argv_after.json" "$EVID_REL/landing_argv_diff.txt")
PACKAGE_SHA="(absent at signing)"
if [ -f "$PACKAGE_SRC" ]; then
  cp -- "$PACKAGE_SRC" "$ROOT_WT/$EVID_REL/PACKAGE.md"; ROOT_COPIED+=("$EVID_REL/PACKAGE.md")
  PACKAGE_SHA="$(sha_of "$ROOT_WT/$EVID_REL/PACKAGE.md")"
fi
ROOT_COPIED+=("$RECEIPT_REL" "$INDEX_REL")
[ ! -e "$ROOT_WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists on origin/main (token spent)"
[ ! -e "$ROOT_WT/$INDEX_REL" ] || die "$INDEX_REL already exists on origin/main (token spent)"
say "  ok  root: script + evidence + landing proof staged on origin/main $(g "$ROOT_WT" rev-parse --short HEAD)"

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN -- nothing was pushed, no receipt was written. --apply would:"
  [ "$RES_LANDED" = yes ]  || say "  1. push research $(g "$STAGE/research" rev-parse --short HEAD) (origin/main + pin ${RESEARCH_PIN:0:12}) under the push lock"
  [ "$ORCH_LANDED" = yes ] || say "  2. push orchestrator $(g "$STAGE/orch" rev-parse --short HEAD) (origin/main + pin ${ORCH_PIN:0:12}${REGEN_SHA:+ + landing regen}) under the push lock"
  say "  3. commit script + evidence + PACKAGE.md + $RECEIPT_REL + $INDEX_REL on fresh root origin/main and push it"
  say "  It reloads NOTHING. The scratch worktrees are removed on exit."
  say "DRY-RUN OK: $GATE_ID -- all preconditions hold."
  exit 0
fi

# ---------------------------------------------------------------- 6. push (apply)
push_locked() { # name repo-for-lock worktree
  local name="$1" repo="$2" wt="$3" tokdir tok rc=0
  tokdir="$(mktemp -d "$STAGE_PARENT/ratify-ctxckpt-push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
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
RES_SHA="(landed before this run)"; ORCH_SHA="(landed before this run)"
if [ "$RES_LANDED" = no ]; then push_locked research "$RESEARCH_REPO" "$STAGE/research"; RES_SHA="$(g "$STAGE/research" rev-parse HEAD)"; fi
if [ "$ORCH_LANDED" = no ]; then push_locked orchestrator "$ORCH_REPO" "$STAGE/orch"; ORCH_SHA="$(g "$STAGE/orch" rev-parse HEAD)"; fi
g "$ORCH_REPO" fetch -q origin main; g "$RESEARCH_REPO" fetch -q origin main
[ "$(landed "$RESEARCH_REPO" "$RESEARCH_PIN")" = yes ] || die "research pin not on origin/main after the push"
[ "$(landed "$ORCH_REPO" "$ORCH_PIN")" = yes ] || die "orchestrator pin not on origin/main after the push"

mkdir -p "$ROOT_WT/artifacts/operator/receipts"
RECEIPT_ABS="$ROOT_WT/$RECEIPT_REL" INDEX_ABS="$ROOT_WT/$INDEX_REL" RECEIPT_REL="$RECEIPT_REL" GATE_ID="$GATE_ID" \
OPERATOR="$RATIFY_OPERATOR" O_SHA="$ORCH_SHA" R_SHA="$RES_SHA" O_PIN="$ORCH_PIN" R_PIN="$RESEARCH_PIN" \
O_BASE="$ORCH_BASE" R_BASE="$RES_BASE" REGEN_SHA="$REGEN_SHA" SCRIPT_SHA="$SCRIPT_SHA" PACKAGE_SHA="$PACKAGE_SHA" \
TESTS_LINE="$TESTS_LINE" HYBRID_TARGETS="$HYBRID_TARGETS" BRANCH="$BRANCH" EVID_REL="$EVID_REL" \
PINS="$(printf '%s\n' "${ROOT_PINS[@]}")" "$SYS_PY" - <<'PY'
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
    "decision": ("--ctx-checkpoints 32 DECLARED on every hybrid serving role (server_mode.frontdoor, "
                 "architect_critic, architect_general; gated-delta-net/SSM models) instead of inherited from the "
                 "llama-server default. Equals the v10 default: behaviour unchanged. Evidence KPF-64.4; policy "
                 "docs/design/ufh14-b4-prefix-cache-policy-20261003.md section 3.7."),
    "hybrid_launch_targets": e["HYBRID_TARGETS"].split(),
    "branch": e["BRANCH"],
    "pinned_commits": {"epyc-orchestrator": e["O_PIN"], "epyc-inference-research": e["R_PIN"]},
    "pre_landing_origin_main": {"epyc-orchestrator": e["O_BASE"], "epyc-inference-research": e["R_BASE"]},
    "landed": {
        "epyc-orchestrator": {"commit": e["O_SHA"], "ref": "origin/main",
                              "landing_regen_commit": e["REGEN_SHA"] or None},
        "epyc-inference-research": {"commit": e["R_SHA"], "ref": "origin/main"},
        "epyc-root": {"commit": "the commit carrying this receipt", "ref": "origin/main"},
    },
    "argv_proof": f"{e['EVID_REL']}/landing_argv_diff.txt",
    "tests": e["TESTS_LINE"],
    "pinned_sha256": pins,
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "reloads_performed": [],
    "effective": ("behaviour: unchanged (32 == kernel default). Flag appears in each hybrid server's live argv at its "
                  "next ordinary reload by its owning session; none performed by this script."),
}
with open(e["RECEIPT_ABS"], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, sort_keys=True); fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
with open(e["INDEX_ABS"], "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "attest", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
PY
ROOT_PATHS=("$SCRIPT_REL" "$RECEIPT_REL" "$INDEX_REL" "$EVID_REL/landing_argv_before.json" "$EVID_REL/landing_argv_after.json"
            "$EVID_REL/landing_argv_diff.txt")
[ -f "$ROOT_WT/$EVID_REL/PACKAGE.md" ] && ROOT_PATHS+=("$EVID_REL/PACKAGE.md")
for pin in "${ROOT_PINS[@]}"; do ROOT_PATHS+=("${pin#* }"); done
g "$ROOT_WT" add -- "${ROOT_PATHS[@]}"
g "$ROOT_WT" commit -q -m "RATIFIED $GATE_ID: --ctx-checkpoints 32 declared on every hybrid serving role (signed by $RATIFY_OPERATOR)" \
  -m "orchestrator ${ORCH_SHA:0:12}, research ${RES_SHA:0:12} landed; receipt $RECEIPT_REL + index $INDEX_REL. Reloads: none (owners reload at their own boundary)." \
  || die "root: commit failed (a pre-commit hook refused it?); orchestrator/research are landed, re-run to resume the root step"
push_locked root "$ROOT_REPO" "$ROOT_WT"

cat <<EOF

RATIFIED $GATE_ID by $RATIFY_OPERATOR.
  research:     $RES_SHA
  orchestrator: $ORCH_SHA${REGEN_SHA:+ (incl. landing regen $REGEN_SHA)}
  root:         receipt $RECEIPT_REL + $INDEX_REL (in the pushed root commit)
NOTHING WAS RELOADED. Behaviour is unchanged (32 is the v10 default), and runtime attestation compares the
resolved value, so running servers attest clean now.

LATER, OWNER STEP (not part of this signature; the session that owns each role's inference, at its own boundary):
the flag appears in live argv at each server's next ordinary reload, from the orchestrator repo:
  python3 scripts/server/orchestrator_stack.py reload frontdoor           # :8070 / :8080 / :8180
  python3 scripts/server/orchestrator_stack.py reload architect_general   # :8074
  python3 scripts/server/orchestrator_stack.py reload architect_critic    # :8083 (GPU)
then: tr '\0' ' ' < /proc/<pid>/cmdline   shows "--ctx-checkpoints 32" for each of those pids.

POST-APPLY VERIFICATION (read-only):  bash $SCRIPT_REL --verify
EOF
