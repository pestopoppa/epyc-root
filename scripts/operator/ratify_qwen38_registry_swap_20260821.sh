#!/bin/bash
# Ratify: complete the Qwen3.8-27B swap's COMPILE CHAIN + template provenance + --jinja fallback fix.
#
# v2 (2026-08-21, supersedes the same-day v1 after the operator's first run surfaced the truth):
#   * orchestration/model_registry.yaml in the ORCHESTRATOR repo is AUTO-GENERATED — the
#     "MASTER-COMPILED RUNTIME VIEW" banner is at the top of the file. The true master is
#     /mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml.
#   * THE MASTER WAS ALREADY SWAPPED on 2026-08-20 by commit b376dadd ("registry: swap
#     architect_general + coder_escalation to Qwen3.8-27B; draft_max 4 -> 8") — a LOCAL,
#     UNPUSHED commit in the research repo. The earlier "master registry was never swapped"
#     finding audited the compiled lean view and its commit-resolution check was defeated by
#     the research repo's safe.directory git config. Corrected in the Q38 handoff.
#   * What actually never ran is the RECOMPILE: lean + descriptors + derived stack_priors were
#     all compiled 2026-08-11, nine days pre-swap. The launcher reads the derived file AS-IS
#     (orchestrator_stack.py:252-262 — no recompile at start; only the lean auto-recompiles),
#     so a stack start TODAY still serves Qwen3.6-27B at draft_max 4.
#
# PHASES (each skippable):
#   phase 0             revert v1's hand-edits to the GENERATED lean file (verified byte-exact
#                       against a reproduction before restoring; refuses on any foreign hunk).
#   phase 1 --provenance  add the chat-template provenance block to the qwen38_27b_q8_local row
#                       in the TRUE master (research repo). Additive only. The master file
#                       currently also carries the ORPHANED LFM2.5 uncommitted block, so this
#                       script NEVER commits in the research repo — commit hunk-selectively
#                       after you settle the LFM2.5 finish-vs-revert decision.
#   phase 2 --recompile   stack_change_pipeline.py update --allow-descriptor-model-removal,
#                       with a TARGETED assertion that the ONLY removed model_id is
#                       qwen3.6-27b-mtp-q8_0 (expected: it leaves the compiled set when no live
#                       role references it; the master row survives as rollback anchor). Then
#                       hard-verify the derived layer serves Qwen3.8 at draft_max 8, then run
#                       `check` and require green.
#   phase 3 --jinja-fix   orchestrator_stack.py:1402 — retire the reversed architect_general
#                       --jinja exclusion surviving as a live fallback default (reversed
#                       2026-06-26, f4a8a3ca; J12 probe 0/15).
#
# KNOWN RIDE-ALONGS the recompile will pick up from the master working tree (flagged, not
# blocked): the uncommitted LFM2.5 restoration block (operator decision pending) and the
# qwen3-vl-30b-a3b quality.measured drift. Both are master-side state, not this script's edits.
#
# NOT DONE HERE: no process is started or reloaded. live==config is verified at the next stack
# start via the stack-change checklist (pipeline-green != starts). The research repo's push
# backlog (b376dadd among 9 unpushed commits, 190 behind origin) is the separate reconciliation
# already in the operator queue.
#
# Usage:
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh --dry-run
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh                # all phases
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh --commit      # + commit ORCHESTRATOR repo only
#   (--skip-revert --skip-provenance --skip-recompile --skip-jinja-fix to taste)
set -euo pipefail

ROOT="${ROOT:-/workspace}"
ORCH="${ORCH:-$ROOT/repos/epyc-orchestrator}"
RESEARCH="${RESEARCH:-/mnt/raid0/llm/epyc-inference-research}"
VENVPY="$ORCH/.venv/bin/python"
LEAN="$ORCH/orchestration/model_registry.yaml"
MASTER="$RESEARCH/orchestration/model_registry.yaml"
DESCRIPTORS="$ORCH/orchestration/model_descriptors.yaml"
DERIVED="$ORCH/orchestration/derived/stack_priors.yaml"
SUMMARY="$ORCH/docs/generated/current_stack_summary.md"
LAUNCHER="$ORCH/scripts/server/orchestrator_stack.py"
RECEIPT="$ROOT/artifacts/operator/ratify_qwen38_registry_swap_20260821.json"

DRY_RUN=0; DO_COMMIT=0; DO_REVERT=1; DO_PROV=1; DO_RECOMPILE=1; DO_JINJA=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)         DRY_RUN=1 ;;
    --commit)          DO_COMMIT=1 ;;
    --skip-revert)     DO_REVERT=0 ;;
    --skip-provenance) DO_PROV=0 ;;
    --skip-recompile)  DO_RECOMPILE=0 ;;
    --skip-jinja-fix)  DO_JINJA=0 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

[ -x "$VENVPY" ] || { echo "REFUSING: venv python not found at $VENVPY" >&2; exit 66; }
"$VENVPY" -c 'import yaml' || { echo "REFUSING: venv python lacks PyYAML" >&2; exit 66; }
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# ---------------------------------------------------------------------------------------
# Phase 0 — revert v1's hand-edits to the GENERATED lean file, and nothing else.
# Method: reproduce v1's deterministic edit on a copy of HEAD; only if the working file is
# byte-identical to that reproduction can the dirt be provably ours alone -> git restore.
# ---------------------------------------------------------------------------------------
if [ "$DO_REVERT" -eq 1 ]; then
  echo "== phase 0: revert v1 edits to the generated lean file =="
  if git -C "$ORCH" diff --quiet -- orchestration/model_registry.yaml; then
    echo "lean file is clean in git — nothing to revert."
  elif ! grep -qF 'qwen38_27b_q8_local:' "$LEAN"; then
    echo "REFUSING: lean file is dirty but does NOT carry v1's marker — the dirt is not ours." >&2
    exit 65
  else
    git -C "$ORCH" show HEAD:orchestration/model_registry.yaml > "$WORKDIR/lean.head.yaml"
    if ! grep -qF 'AUTO-GENERATED — MASTER-COMPILED RUNTIME VIEW' "$WORKDIR/lean.head.yaml"; then
      echo "REFUSING: HEAD lean file lacks the generated banner — wrong file?" >&2; exit 65
    fi
    # Exact ownership proof: INVERT v1's deterministic edit on the working file and
    # byte-compare to HEAD. Equal => the dirt is exactly v1's edit and nothing else.
    cat > "$WORKDIR/invert_v1.py" <<'PYINNER'
import sys
work, out = sys.argv[1], sys.argv[2]
lines = open(work, encoding='utf-8').read().split('\n')
# 1. delete the inserted role block: [anchor qwen38 .. before anchor qwen36)
a = [i for i, l in enumerate(lines) if l == '  qwen38_27b_q8_local:']
b = [i for i, l in enumerate(lines) if l == '  qwen36_27b_mtp_q8_local:']
assert len(a) == 1 and len(b) == 1 and a[0] < b[0], 'block anchors not found as expected'
lines = lines[:a[0]] + lines[b[0]:]
t = '\n'.join(lines)
OLDG = '/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf'
NEWG = '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
INV = [
 ('    model_role: qwen38_27b_q8_local', '    model_role: qwen36_27b_mtp_q8_local'),
 ('    model: Qwen3.8-27B-Q8_0.gguf', '    model: Qwen3.6-27B-MTP-Q8_0.gguf'),
 (NEWG, OLDG),
 ('      draft_max: 8', '      draft_max: 4'),
 ('    vram_gib: 37.22', '    vram_gib: 36.7'),
 ('      vram_gib: 37.22', '      vram_gib: 36.7'),
 ('    throughput: 55.46', '    throughput: 47.79'),
 ('Coding escalation — Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; registry swap completed 2026-08-21, was Qwen3.6-27B).',
  'Coding escalation — Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0).'),
 ('System architecture — Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; registry swap completed 2026-08-21, was Qwen3.6-27B).',
  'System architecture — Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0).'),
 ('2026-08-21: Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; was Qwen3.6-27B from 2026-07-31);',
  '2026-07-31: Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0);'),
 ("    previous_model: 'Qwen3.6-27B-MTP-Q8_0.gguf (registry swap completed 2026-08-21). Prior: Qwen3.6-35B-A3B-MTP-Q8_0.gguf'",
  '    previous_model: Qwen3.6-35B-A3B-MTP-Q8_0.gguf'),
 ("    previous_model: 'Qwen3.6-27B-MTP-Q8_0.gguf (registry swap completed 2026-08-21). Prior: Qwen3-235B-A22B-Q4_K_M.gguf'",
  '    previous_model: Qwen3-235B-A22B-Q4_K_M.gguf'),
 ("previous_model: 'Qwen3.6-27B-MTP-Q8_0 (registry swap completed 2026-08-21). Prior: Qwen3.6-35B-A3B-MTP-Q8_0 (2026-07-31:",
  "previous_model: 'Qwen3.6-35B-A3B-MTP-Q8_0 (2026-07-31:"),
 ("previous_model: 'Qwen3.6-27B-MTP-Q8_0 (registry swap completed 2026-08-21). Prior: Qwen3.5-122B-A10B UD-Q4_K_M (2026-07-31:",
  "previous_model: 'Qwen3.5-122B-A10B UD-Q4_K_M (2026-07-31:"),
 ('      name: Qwen3.8-27B-Q8_0\n      path: ' + OLDG, '      name: Qwen3.6-27B-MTP-Q8_0\n      path: ' + OLDG),
]
for old, new in INV:
    t = t.replace(old, new)
open(out, 'w', encoding='utf-8').write(t)
PYINNER
    if "$VENVPY" "$WORKDIR/invert_v1.py" "$LEAN" "$WORKDIR/lean.inverted.yaml" \
        && cmp -s "$WORKDIR/lean.inverted.yaml" "$WORKDIR/lean.head.yaml"; then
      REVERT_PROOF="inverse-edit byte-match to HEAD"
    else
      echo "REFUSING: inverting v1's edit does not reproduce HEAD — a foreign hunk may be present." >&2
      echo "          Inspect: git -C $ORCH diff -- orchestration/model_registry.yaml" >&2
      exit 65
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "[dry-run] would git restore the lean file (proof: $REVERT_PROOF)."
    else
      git -C "$ORCH" checkout -- orchestration/model_registry.yaml
      echo "reverted (proof: $REVERT_PROOF). The recompile in phase 2 regenerates it from the master."
    fi
  fi
fi

# ---------------------------------------------------------------------------------------
# Phase 1 — provenance block into the TRUE master's qwen38_27b_q8_local row
# ---------------------------------------------------------------------------------------
cat > "$WORKDIR/prov.py" <<'PYEOF'
import sys, io, yaml
p = sys.argv[1]
text = open(p, encoding='utf-8').read()
if 'unsloth_patched_not_stock' in text:
    print('already ratified: provenance block present in the master — phase 1 is a no-op.')
    sys.exit(3)
lines = text.split('\n')
anchor = '  qwen38_27b_q8_local:'
idx = [i for i, l in enumerate(lines) if l == anchor]
assert len(idx) == 1, f'expected exactly one {anchor!r} in the master, found {len(idx)}'
s = idx[0]
e = s + 1
while e < len(lines) and (lines[e].startswith('    ') or lines[e].strip() == ''):
    e += 1
block = '\n'.join(lines[s:e])
assert 'Qwen3.8-27B-Q8_0.gguf' in block, 'qwen38 row does not reference the artifact — wrong row?'
prov = '''    chat_template:
      provenance: unsloth_patched_not_stock
      evidence_strength: direct_artifact_digest
      served_template_bytes: 9993
      served_template_sha256_12: 12827f24b742
      upstream_template_bytes: 8952
      upstream_template_sha256_12: c3cf9e34abf4
      upstream_ref: Qwen/Qwen3.8-27B
      trailing_marker: '{#- Unsloth fixes - developer role, merged system messages, tool calling #}'
      evidence: 'Extracted 2026-08-21 from the GGUF header of /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
        without loading the model; 1,041 bytes larger than stock. Divergences that matter: reasoning_effort
        ''high'' is silently coerced to ''xhigh'' (template :60-61) where stock raises; the xhigh default
        injects a 209-char instruction (:59, :66); and the assistant branch (:113-120) reads only
        message.reasoning_content, never inline <think>, so inline-think history yields a duplicated blank
        <think></think>. All three sit inside the enable_thinking gate (:58) and are unreachable while
        chat_template_kwargs.enable_thinking is false. Reachability audit:
        epyc-root handoffs/active/qwen38-27b-replace-qwen36.md -> Research Intake 2026-08-21 (Q38-T1/T3).' '''
lines = lines[:e] + prov.rstrip().split('\n') + lines[e:]
out = '\n'.join(lines)
doc = yaml.safe_load(io.StringIO(out))  # structural verification before writing a byte
def find_role(d):
    if isinstance(d, dict):
        if 'qwen38_27b_q8_local' in d and isinstance(d['qwen38_27b_q8_local'], dict):
            return d['qwen38_27b_q8_local']
        for v in d.values():
            r = find_role(v)
            if r is not None:
                return r
    return None
role = find_role(doc)
assert role and role.get('chat_template', {}).get('provenance') == 'unsloth_patched_not_stock'
open(p, 'w', encoding='utf-8').write(out)
print('phase 1 applied: provenance block added to the master qwen38 row; YAML re-parses clean.')
PYEOF

if [ "$DO_PROV" -eq 1 ]; then
  echo "== phase 1: provenance block -> TRUE master (research repo) =="
  if ! git -C "$RESEARCH" diff --quiet -- orchestration/model_registry.yaml 2>/dev/null; then
    echo "NOTE: the master carries pre-existing uncommitted hunks (the orphaned LFM2.5 block)." >&2
    echo "      This phase is ADDITIVE and does not touch them; this script never commits here." >&2
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    cp "$MASTER" "$WORKDIR/master.preview.yaml"
    if "$VENVPY" "$WORKDIR/prov.py" "$WORKDIR/master.preview.yaml"; then
      diff -u "$MASTER" "$WORKDIR/master.preview.yaml" | head -50 || true
    fi
  else
    rc=0; "$VENVPY" "$WORKDIR/prov.py" "$MASTER" || rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "phase 1 FAILED" >&2; exit "$rc"; fi
  fi
fi

# ---------------------------------------------------------------------------------------
# Phase 2 — recompile (update, not check-then-fail) with a targeted removal assertion
# ---------------------------------------------------------------------------------------
if [ "$DO_RECOMPILE" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "== phase 2: stack_change_pipeline update (regenerates lean + descriptors + derived + summary) =="
  "$VENVPY" - "$DESCRIPTORS" > "$WORKDIR/model_ids.before" <<'PYEOF'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
ids = set()
def walk(x):
    if isinstance(x, dict):
        if 'model_id' in x and isinstance(x['model_id'], str): ids.add(x['model_id'])
        for v in x.values(): walk(v)
    elif isinstance(x, list):
        for v in x: walk(v)
walk(d)
print('\n'.join(sorted(ids)))
PYEOF
  cd "$ORCH"
  "$VENVPY" scripts/registry/stack_change_pipeline.py update --allow-descriptor-model-removal \
    || { echo "pipeline UPDATE failed — read its output above" >&2; exit 70; }
  "$VENVPY" - "$DESCRIPTORS" > "$WORKDIR/model_ids.after" <<'PYEOF'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
ids = set()
def walk(x):
    if isinstance(x, dict):
        if 'model_id' in x and isinstance(x['model_id'], str): ids.add(x['model_id'])
        for v in x.values(): walk(v)
    elif isinstance(x, list):
        for v in x: walk(v)
walk(d)
print('\n'.join(sorted(ids)))
PYEOF
  REMOVED="$(comm -23 "$WORKDIR/model_ids.before" "$WORKDIR/model_ids.after" | tr '\n' ' ' | sed 's/ $//')"
  ADDED="$(comm -13 "$WORKDIR/model_ids.before" "$WORKDIR/model_ids.after" | tr '\n' ' ' | sed 's/ $//')"
  echo "descriptor model_id delta: removed=[$REMOVED] added=[$ADDED]"
  if [ "$REMOVED" != "qwen3.6-27b-mtp-q8_0" ]; then
    echo "ABORTING REVIEW-REQUIRED: expected exactly 'qwen3.6-27b-mtp-q8_0' removed, got [$REMOVED]." >&2
    echo "The regenerated artifacts are on disk but NOT committed — review the removals before committing." >&2
    exit 71
  fi
  echo "== phase 2 verification: what does the derived layer now serve? =="
  "$VENVPY" - "$DERIVED" <<'PYEOF'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
ag = d['roles']['architect_general'] if 'roles' in d else d['architect_general']
blob = yaml.safe_dump(ag)
assert 'Qwen3.8-27B-Q8_0.gguf' in blob, 'DERIVED STILL DOES NOT SERVE QWEN3.8'
assert 'Qwen3.6-27B-MTP-Q8_0.gguf' not in blob, 'derived architect_general still references Qwen3.6'
assert 'draft_max: 8' in blob and 'draft_max: 4' not in blob, 'derived draft_max is not 8'
print('VERIFIED: derived architect_general serves Qwen3.8-27B-Q8_0 at draft_max 8.')
PYEOF
  echo "== phase 2 post-check (must be green now) =="
  "$VENVPY" scripts/registry/stack_change_pipeline.py check || { echo "post-update check NOT green — investigate before committing" >&2; exit 72; }
  cd "$ROOT"
elif [ "$DO_RECOMPILE" -eq 1 ]; then
  echo "== phase 2: [dry-run] would run update --allow-descriptor-model-removal, assert the only removal is qwen3.6-27b-mtp-q8_0, verify derived, then require check green =="
fi

# ---------------------------------------------------------------------------------------
# Phase 3 — retire the reversed --jinja fallback in the launcher
# ---------------------------------------------------------------------------------------
cat > "$WORKDIR/jinja_fix.py" <<'PYEOF'
import sys, py_compile
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
# Idempotency keys on the STALE expression itself: the file has THREE
# flags.get("jinja", ...) sites and two (:975, :1103) already default True.
STALE = 'flags.get("jinja", role_name != "architect_general")'
if STALE not in s:
    if 'the reversed policy surviving' in s:
        print('already ratified: the stale role-conditional fallback is gone — phase 3 is a no-op.')
        sys.exit(3)
    print('REFUSING: neither the stale fallback nor the fix marker is present — file drifted', file=sys.stderr)
    sys.exit(70)
old = '''    # --jinja: model's native chat template (enables thinking on Qwen3/3.5).
    # SKIP for architect_general — Qwen3.5 hybrids enter infinite <think> loops.
    # --reasoning off is insufficient: the jinja template itself primes the model
    # into think mode. Without --jinja, llama-server falls back to generic ChatML
    # which has no thinking scaffolding.
    if flags.get("jinja", role_name != "architect_general") is True:
        cmd.append("--jinja")'''
new = '''    # --jinja: model's native chat template (enables thinking on Qwen3/3.5).
    # 2026-08-21: the architect_general exclusion that used to live here was
    # REVERSED upstream on 2026-06-26 (commit f4a8a3ca; gated on the J12
    # think-loop probe — 0 leaks/loops over n=15,
    # orchestration/reports/j12_think_loop_probe_20260706T143621Z). The compiled
    # priors (stack_priors.py -> derived jinja: true) are authoritative; this
    # default only fires when a role has no compiled prior, and the old
    # `role_name != "architect_general"` default silently dropped --jinja for
    # exactly that role on the no-priors path — the reversed policy surviving
    # as a live fallback. Audit: per-request-reasoning-budget.md PRB-T1.
    if flags.get("jinja", True) is True:
        cmd.append("--jinja")'''
assert s.count(old) == 1, f'expected exactly one fallback site, found {s.count(old)} — file drifted, refusing'
open(p, 'w', encoding='utf-8').write(s.replace(old, new))
py_compile.compile(p, doraise=True)
print('phase 3 applied: --jinja fallback now defaults True; py_compile clean.')
PYEOF

if [ "$DO_JINJA" -eq 1 ]; then
  echo "== phase 3: --jinja fallback fix =="
  if [ "$DRY_RUN" -eq 1 ]; then
    cp "$LAUNCHER" "$WORKDIR/launcher.preview.py"
    if "$VENVPY" "$WORKDIR/jinja_fix.py" "$WORKDIR/launcher.preview.py"; then
      diff -u "$LAUNCHER" "$WORKDIR/launcher.preview.py" || true
    fi
  else
    rc=0; "$VENVPY" "$WORKDIR/jinja_fix.py" "$LAUNCHER" || rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "phase 3 FAILED" >&2; exit "$rc"; fi
  fi
fi

# ---------------------------------------------------------------------------------------
# Receipt + optional commit (ORCHESTRATOR repo only; the research repo is never committed
# here — its master carries the orphaned LFM2.5 hunks pending the operator's decision, and
# its push backlog is a separate reconciliation)
# ---------------------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p "$(dirname "$RECEIPT")"
  {
    echo '{'
    echo '  "ratification": "qwen38-compile-chain-completion-and-template-provenance-and-jinja-fallback",'
    echo '  "version": 2,'
    echo '  "date": "2026-08-21",'
    echo '  "operator_executed": true,'
    echo '  "corrected_finding": "the true master (research repo) was swapped 2026-08-20 by b376dadd (local, unpushed); the gap was the recompile chain, and the earlier never-swapped finding had audited the compiled lean view",'
    echo '  "evidence": ["epyc-root handoffs/active/qwen38-27b-replace-qwen36.md (Q38-T1..T3 + 2026-08-21 correction)",'
    echo '               "epyc-root handoffs/active/per-request-reasoning-budget.md (PRB-T1)",'
    echo '               "epyc-inference-research b376dadd; epyc-orchestrator 1cff5162"],'
    echo '  "files": {'
    echo "    \"master_model_registry.yaml\": \"$(sha256sum "$MASTER" | cut -d' ' -f1)\","
    echo "    \"lean_model_registry.yaml\": \"$(sha256sum "$LEAN" | cut -d' ' -f1)\","
    echo "    \"model_descriptors.yaml\": \"$(sha256sum "$DESCRIPTORS" | cut -d' ' -f1)\","
    echo "    \"stack_priors.yaml\": \"$(sha256sum "$DERIVED" | cut -d' ' -f1)\","
    echo "    \"orchestrator_stack.py\": \"$(sha256sum "$LAUNCHER" | cut -d' ' -f1)\""
    echo '  },'
    echo '  "not_done_here": "no process started; live==config at next stack start; research-repo commit + push left to the operator (LFM2.5 decision pending in the same file)"'
    echo '}'
  } > "$RECEIPT"
  echo "receipt: $RECEIPT"
  echo; echo "== orchestrator diff =="; git -C "$ORCH" diff --stat
  echo "== research diff (yours to commit hunk-selectively after the LFM2.5 decision) =="
  git -C "$RESEARCH" diff --stat -- orchestration/model_registry.yaml 2>/dev/null | grep -v safe.directory || true
  if [ "$DO_COMMIT" -eq 1 ]; then
    git -C "$ORCH" add -- orchestration/model_registry.yaml orchestration/model_descriptors.yaml orchestration/derived/ docs/generated/current_stack_summary.md scripts/server/orchestrator_stack.py
    git -C "$ORCH" commit -m "recompile the registry chain for the Qwen3.8-27B swap + retire reversed --jinja fallback

The master swap (research repo, b376dadd, 2026-08-20) never had its compile
chain run: lean/descriptors/derived were all 2026-08-11 artifacts, and the
launcher reads the derived priors as-is, so a stack start still served
Qwen3.6-27B at draft_max 4. Regenerated via stack_change_pipeline.py update
(--allow-descriptor-model-removal; verified the only removal is
qwen3.6-27b-mtp-q8_0, and that derived architect_general now serves
Qwen3.8-27B-Q8_0 at draft_max 8). Also retires the reversed architect_general
--jinja fallback (orchestrator_stack.py:1402; policy reversed 2026-06-26,
f4a8a3ca). Operator-ratified via
scripts/operator/ratify_qwen38_registry_swap_20260821.sh (v2)."
    echo "committed in $ORCH — push when ready (serialized_push.py if the guard asks)."
  else
    echo "not committed (--commit to commit the ORCHESTRATOR repo after reviewing)."
  fi
else
  echo; echo "[dry-run] no files written."
fi
echo "DONE."
