#!/bin/bash
# Ratify the Qwen3.8-27B registry swap + template-provenance block + --jinja fallback fix.
#
# WHY THIS SCRIPT EXISTS (evidence: handoffs/active/qwen38-27b-replace-qwen36.md → Q38-T1..T3,
# and handoffs/active/per-request-reasoning-budget.md → PRB-T1, both 2026-08-21):
#   * The 2026-08-20 "registry swap" landed ONLY in stack_templates/default.yaml (1cff5162).
#     The MASTER registry (orchestration/model_registry.yaml) was never touched — git log -S
#     'Qwen3.8' on it is EMPTY — and the launcher takes -m from the DERIVED
#     orchestration/derived/stack_priors.yaml (compiled 2026-08-11), so a stack start serves
#     Qwen3.6-27B at draft_max 4 regardless of the stack template.
#   * The registry is operator-frozen and the launcher script is classifier-protected, so an
#     agent cannot apply these edits. This script is the pre-validated command: the operator
#     runs it, reviews the diff, and commits.
#
# WHAT IT DOES (each phase skippable):
#   phase 1 --swap        master-registry swap: new qwen38_27b_q8_local role (with the
#                         chat-template provenance block nested), repoint architect_general +
#                         coder_escalation in BOTH the server_mode map and the roles map,
#                         draft_max 4→8, measured figures 47.79/36.7 → 55.46/37.22.
#                         qwen36_27b_mtp_q8_local is left byte-untouched as rollback anchor.
#   phase 2 --recompile   stack_change_pipeline.py check + update → regenerates the derived
#                         priors, then HARD-VERIFIES the derived output actually serves
#                         Qwen3.8 at draft_max 8 (the step the 2026-08-20 swap never had).
#   phase 3 --jinja-fix   scripts/server/orchestrator_stack.py:1402 — retire the reversed
#                         architect_general --jinja exclusion surviving as a live fallback
#                         default (policy reversed 2026-06-26, f4a8a3ca; J12 probe 0/15).
#   receipt               sha256 receipt → artifacts/operator/ratify_qwen38_registry_swap_20260821.json
#
# WHAT IT DOES **NOT** DO: start, reload, or touch any process. live==config verification
# happens at the next stack start via the stack-change checklist (pipeline-green ≠ starts).
#
# Usage:
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh --dry-run      # diff only, no writes
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh                # apply all three phases
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh --skip-jinja-fix
#   bash scripts/operator/ratify_qwen38_registry_swap_20260821.sh --commit       # apply + commit in orchestrator repo
#
# Idempotent: a phase whose end-state is already present is skipped with a note, not an error.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
ORCH="${ORCH:-$ROOT/repos/epyc-orchestrator}"
VENVPY="$ORCH/.venv/bin/python"
REG="$ORCH/orchestration/model_registry.yaml"
DERIVED="$ORCH/orchestration/derived/stack_priors.yaml"
LAUNCHER="$ORCH/scripts/server/orchestrator_stack.py"
RECEIPT="$ROOT/artifacts/operator/ratify_qwen38_registry_swap_20260821.json"

DRY_RUN=0; DO_COMMIT=0; DO_SWAP=1; DO_RECOMPILE=1; DO_JINJA=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)          DRY_RUN=1 ;;
    --commit)           DO_COMMIT=1 ;;
    --skip-swap)        DO_SWAP=0 ;;
    --skip-recompile)   DO_RECOMPILE=0 ;;
    --skip-jinja-fix)   DO_JINJA=0 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

[ -x "$VENVPY" ] || { echo "REFUSING: venv python not found at $VENVPY" >&2; exit 66; }
[ -f "$REG" ]    || { echo "REFUSING: $REG not found" >&2; exit 66; }
"$VENVPY" -c 'import yaml' || { echo "REFUSING: venv python lacks PyYAML" >&2; exit 66; }

# Shared-clone safety: the target files must be clean in git before we touch them, so the
# review surface is exactly this script's diff and `git checkout --` restores cleanly.
cd "$ORCH"
git fetch origin --quiet || echo "WARN: git fetch failed (offline?); continuing"
for f in orchestration/model_registry.yaml scripts/server/orchestrator_stack.py; do
  if ! git diff --quiet -- "$f"; then
    echo "REFUSING: $f already has uncommitted changes — reconcile those first" >&2
    echo "          (git diff -- $f to see whose hunks they are)" >&2
    exit 65
  fi
done

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# ---------------------------------------------------------------------------------------
# The new role block (Q38 prepared edits 1+2, figures transcribed from the owning handoff)
# ---------------------------------------------------------------------------------------
cat > "$WORKDIR/qwen38_role_block.yaml" <<'ROLEBLOCK'
  qwen38_27b_q8_local:
    tier: A
    description: 'Qwen3.8-27B Q8_0 exact local artifact (unsloth GGUF, MTP-embedded blk.64.nextn.*).
      2026-08-21: role created to COMPLETE the 2026-08-20 swap that landed only in stack_templates/default.yaml
      (1cff5162) — the master registry was never updated (Q38-T2 audit, handoffs/active/qwen38-27b-replace-qwen36.md).
      Backs architect_general (:8083, MI210 ROCm0) and its coder_escalation alias. qwen36_27b_mtp_q8_local
      is preserved unmodified as the rollback anchor.'
    production_throughput:
      optimized_tps: 55.46
      optimized_tps_long_context: null
      baseline_tps: 27.78
      contended_tps: null
      vram_gib: 37.22
      attest: 'handoffs/active/qwen38-27b-replace-qwen36.md — MI210 draft-depth sweep on production-consolidated-v9
        (0db32c06e, binary 10125), np=1, 12 real olympiadbench prompts; vram_gib sampled DURING residency
        at n_slots=4, n_ctx 262144, q8_0 KV, kv_unified=true.'
      attest_grade: 'observation-grade. Figures transcribed 2026-08-21 from the owning handoff by the
        operator-directed ratification script (scripts/operator/ratify_qwen38_registry_swap_20260821.sh).
        optimized_tps_long_context and contended_tps are explicitly null — NOT yet measured on this
        artifact; do not inherit the Qwen3.6 cells.'
    model:
      name: Qwen3.8-27B-Q8_0
      path: /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
      quant: Q8_0
      size_gb: 27.05
      architecture: qwen35
      mtp_capable: true
    artifact_status:
      download: present
      observed_date: 2026-08-14
      file_bytes: 29047086048
      provenance: 'unsloth Qwen3.8-27B Q8_0 GGUF with embedded NextN/MTP tensors (blk.64.nextn.*,
        qwen35.nextn_predict_layers) — same-file draft-mtp self-draft; header-verified 2026-08-14
        and re-verified 2026-08-21 (866 tensors).'
    candidate_roles:
    - architect_general
    - coder_escalation
    acceleration:
      type: speculative_decoding
      spec_type: native_mtp_candidate
      optimal_gpu_serving:
        date: 2026-08-20
        kernel: production-consolidated-v9
        binary: /mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server
        device: MI210 (ROCm0)
        spec_type: draft-mtp
        spec_draft_n_max: 8
        decode_t_s: 55.46
        grade: observation
      gpu_spec_depth_sweep_observation: '2026-08-14..20 MI210 draft-depth sweep on production-consolidated-v9
        (0db32c06e/10125), np=1, 12 real olympiadbench prompts: plain 27.78; n2 39.77 / n3 46.61 /
        n4 51.03 / n6 55.22 / n8 55.46 (optimum) / n12 51.14 t/s; acceptance declines 0.842 -> 0.482
        with depth. Depth is PER-MODEL, not inherited — Qwen3.6-27B''s measured optimum is 4. Keep in
        step with stack_templates/default.yaml spec_overrides.draft_max (8 since 1cff5162).'
    chat_template:
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
        server_mode.<role>.chat_template_kwargs.enable_thinking is false. Reachability audit:
        handoffs/active/qwen38-27b-replace-qwen36.md -> Research Intake 2026-08-21 (Q38-T1/T3).'
    memory:
      residency: cold
      pinned: false
      cpu_only_candidate: false
      gpu_only_candidate: true
      hybrid_candidate: false
ROLEBLOCK

# ---------------------------------------------------------------------------------------
# Phase 1 — the master-registry swap (block-scoped, every replacement count-asserted)
# ---------------------------------------------------------------------------------------
cat > "$WORKDIR/swap.py" <<'PYEOF'
import sys, io

reg_path, role_block_path = sys.argv[1], sys.argv[2]
text = open(reg_path, encoding='utf-8').read()

if 'qwen38_27b_q8_local:' in text:
    print('already ratified: qwen38_27b_q8_local role present — phase 1 is a no-op.')
    sys.exit(3)  # sentinel: already done

lines = text.split('\n')

def block_span(header, fingerprint):
    """Span of a 2-space-indented block whose body contains `fingerprint`."""
    starts = [i for i, l in enumerate(lines) if l == header]
    assert starts, f'header not found: {header!r}'
    for s in starts:
        e = s + 1
        while e < len(lines) and (lines[e].startswith('    ') or lines[e].strip() == ''):
            e += 1
        body = '\n'.join(lines[s:e])
        if fingerprint in body:
            return s, e, body
    raise AssertionError(f'no block {header!r} containing {fingerprint!r}')

def edit_block(header, fingerprint, replacements):
    global lines
    s, e, body = block_span(header, fingerprint)
    for old, new, want in replacements:
        got = body.count(old)
        assert got == want, f'{header!r}: {old!r} count {got} != {want}'
        body = body.replace(old, new)
    lines = lines[:s] + body.split('\n') + lines[e:]

OLD_GGUF = '/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf'
NEW_GGUF = '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'

# -- server_mode.coder_escalation (fingerprint: alias_of) --
edit_block('  coder_escalation:', 'alias_of: architect_general', [
    ('    model_role: qwen36_27b_mtp_q8_local', '    model_role: qwen38_27b_q8_local', 1),
    ('    model: Qwen3.6-27B-MTP-Q8_0.gguf', '    model: Qwen3.8-27B-Q8_0.gguf', 1),
    ('    model_path: ' + OLD_GGUF, '    model_path: ' + NEW_GGUF, 1),
    ('    vram_gib: 36.7', '    vram_gib: 37.22', 1),
    ('    throughput: 47.79', '    throughput: 55.46', 1),
    ('Coding escalation — Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0).',
     'Coding escalation — Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; registry swap completed 2026-08-21, was Qwen3.6-27B).', 1),
    ('    previous_model: Qwen3.6-35B-A3B-MTP-Q8_0.gguf',
     "    previous_model: 'Qwen3.6-27B-MTP-Q8_0.gguf (registry swap completed 2026-08-21). Prior: Qwen3.6-35B-A3B-MTP-Q8_0.gguf'", 1),
])

# -- server_mode.architect_general (fingerprint: shared_with) --
edit_block('  architect_general:', 'shared_with:', [
    ('    model_role: qwen36_27b_mtp_q8_local', '    model_role: qwen38_27b_q8_local', 1),
    (OLD_GGUF, NEW_GGUF, 3),          # model:, draft_model:, acceleration.draft_model:
    ('      draft_max: 4', '      draft_max: 8', 1),
    ('    vram_gib: 36.7', '    vram_gib: 37.22', 1),
    ('    throughput: 47.79', '    throughput: 55.46', 1),
    ('System architecture — Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0).',
     'System architecture — Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; registry swap completed 2026-08-21, was Qwen3.6-27B).', 1),
    ('    previous_model: Qwen3-235B-A22B-Q4_K_M.gguf',
     "    previous_model: 'Qwen3.6-27B-MTP-Q8_0.gguf (registry swap completed 2026-08-21). Prior: Qwen3-235B-A22B-Q4_K_M.gguf'", 1),
])

# -- roles.coder_escalation (fingerprint: tier: B) --
edit_block('  coder_escalation:', 'tier: B', [
    ('      name: Qwen3.6-27B-MTP-Q8_0\n      path: ' + OLD_GGUF,
     '      name: Qwen3.8-27B-Q8_0\n      path: ' + NEW_GGUF, 1),
    ('Coding escalation — Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0).',
     'Coding escalation — Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; registry swap completed 2026-08-21, was Qwen3.6-27B).', 1),
    ("previous_model: 'Qwen3.6-35B-A3B-MTP-Q8_0 (2026-07-31:",
     "previous_model: 'Qwen3.6-27B-MTP-Q8_0 (registry swap completed 2026-08-21). Prior: Qwen3.6-35B-A3B-MTP-Q8_0 (2026-07-31:", 1),
])

# -- roles.architect_general (fingerprint: superseded_model_history) --
edit_block('  architect_general:', 'superseded_model_history', [
    ('      name: Qwen3.6-27B-MTP-Q8_0\n      path: ' + OLD_GGUF,
     '      name: Qwen3.8-27B-Q8_0\n      path: ' + NEW_GGUF, 1),
    ('      draft_model: ' + OLD_GGUF, '      draft_model: ' + NEW_GGUF, 1),
    ('      draft_max: 4', '      draft_max: 8', 1),
    ('      vram_gib: 36.7', '      vram_gib: 37.22', 1),
    ('2026-07-31: Qwen3.6-27B dense Q8 MTP on MI210 (ROCm0);',
     '2026-08-21: Qwen3.8-27B Q8_0 MTP on MI210 (ROCm0; was Qwen3.6-27B from 2026-07-31);', 1),
    ("previous_model: 'Qwen3.5-122B-A10B UD-Q4_K_M (2026-07-31:",
     "previous_model: 'Qwen3.6-27B-MTP-Q8_0 (registry swap completed 2026-08-21). Prior: Qwen3.5-122B-A10B UD-Q4_K_M (2026-07-31:", 1),
])

# -- insert the new role block immediately before its rollback anchor --
anchor = '  qwen36_27b_mtp_q8_local:'
idx = [i for i, l in enumerate(lines) if l == anchor]
assert len(idx) == 1, f'expected exactly one {anchor!r}, found {len(idx)}'
role_block = open(role_block_path, encoding='utf-8').read().rstrip('\n').split('\n')
lines = lines[:idx[0]] + role_block + lines[idx[0]:]

out = '\n'.join(lines)

# structural verification before writing a byte
import yaml
doc = yaml.safe_load(io.StringIO(out))
roles = doc['roles']
assert 'qwen38_27b_q8_local' in roles, 'new role missing after insert'
assert roles['qwen38_27b_q8_local']['model']['path'] == NEW_GGUF
assert roles['qwen38_27b_q8_local']['chat_template']['provenance'] == 'unsloth_patched_not_stock'
assert roles['qwen38_27b_q8_local']['acceleration']['optimal_gpu_serving']['spec_draft_n_max'] == 8
assert roles['architect_general']['model']['path'] == NEW_GGUF
assert roles['architect_general']['acceleration']['draft_max'] == 8
assert roles['coder_escalation']['model']['path'] == NEW_GGUF
sm = doc['server_mode']
assert sm['architect_general']['model_role'] == 'qwen38_27b_q8_local'
assert sm['architect_general']['model'] == NEW_GGUF
assert sm['architect_general']['acceleration']['draft_max'] == 8
assert sm['architect_general']['chat_template_kwargs']['enable_thinking'] is False
assert sm['coder_escalation']['model_role'] == 'qwen38_27b_q8_local'
assert sm['coder_escalation']['model_path'] == NEW_GGUF
assert sm['coder_escalation']['chat_template_kwargs']['enable_thinking'] is False
# rollback anchor byte-untouched
assert 'qwen36_27b_mtp_q8_local' in roles and roles['qwen36_27b_mtp_q8_local']['model']['path'] == OLD_GGUF

open(reg_path, 'w', encoding='utf-8').write(out)
print('phase 1 applied: registry swap + provenance block; structural verification passed.')
PYEOF

if [ "$DO_SWAP" -eq 1 ]; then
  echo "== phase 1: master-registry swap =="
  if [ "$DRY_RUN" -eq 1 ]; then
    cp "$REG" "$WORKDIR/reg.preview.yaml"
    if "$VENVPY" "$WORKDIR/swap.py" "$WORKDIR/reg.preview.yaml" "$WORKDIR/qwen38_role_block.yaml"; then
      diff -u "$REG" "$WORKDIR/reg.preview.yaml" | head -200 || true
      echo "  [dry-run] full diff: diff -u $REG $WORKDIR/reg.preview.yaml"
    fi
  else
    rc=0; "$VENVPY" "$WORKDIR/swap.py" "$REG" "$WORKDIR/qwen38_role_block.yaml" || rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "phase 1 FAILED (registry untouched or restored via git)" >&2; exit "$rc"; fi
  fi
fi

# ---------------------------------------------------------------------------------------
# Phase 2 — recompile derived priors, then hard-verify what the launcher would serve
# ---------------------------------------------------------------------------------------
if [ "$DO_RECOMPILE" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "== phase 2: stack_change_pipeline check + update =="
  "$VENVPY" scripts/registry/stack_change_pipeline.py check  || { echo "pipeline CHECK failed — read its output; registry edits are applied but derived is NOT regenerated" >&2; exit 70; }
  "$VENVPY" scripts/registry/stack_change_pipeline.py update || { echo "pipeline UPDATE failed" >&2; exit 70; }
  echo "== phase 2 verification: what does the derived layer now serve? =="
  "$VENVPY" - "$DERIVED" <<'PYEOF'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
ag = d['roles']['architect_general'] if 'roles' in d else d['architect_general']
blob = yaml.safe_dump(ag)
assert 'Qwen3.8-27B-Q8_0.gguf' in blob, 'DERIVED STILL DOES NOT SERVE QWEN3.8 — do not start the stack believing the swap is live'
assert 'Qwen3.6-27B-MTP-Q8_0.gguf' not in blob, 'derived architect_general still references the Qwen3.6 artifact'
assert 'draft_max: 8' in blob and 'draft_max: 4' not in blob, 'derived draft_max is not 8'
print('VERIFIED: derived architect_general serves Qwen3.8-27B-Q8_0 at draft_max 8.')
PYEOF
elif [ "$DO_RECOMPILE" -eq 1 ]; then
  echo "== phase 2: [dry-run] would run stack_change_pipeline.py check + update, then verify derived =="
fi

# ---------------------------------------------------------------------------------------
# Phase 3 — retire the reversed --jinja fallback in the launcher
# ---------------------------------------------------------------------------------------
cat > "$WORKDIR/jinja_fix.py" <<'PYEOF'
import sys, py_compile
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
# Idempotency keys on the STALE expression itself, not on the fixed form: the file
# has THREE flags.get("jinja", ...) sites and two (:975, :1103) already default True,
# so probing for the fixed form false-passes while :1402 still carries the stale
# role-conditional default (caught in dry-run validation, 2026-08-21).
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
# Receipt + optional commit
# ---------------------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p "$(dirname "$RECEIPT")"
  {
    echo '{'
    echo '  "ratification": "qwen38-registry-swap-and-template-provenance-and-jinja-fallback",'
    echo '  "date": "2026-08-21",'
    echo '  "operator_executed": true,'
    echo '  "evidence": ["handoffs/active/qwen38-27b-replace-qwen36.md (Q38-T1..T3, 2026-08-21)",'
    echo '               "handoffs/active/per-request-reasoning-budget.md (PRB-T1, 2026-08-21)",'
    echo '               "stack_templates/default.yaml @ 1cff5162"],'
    echo '  "files": {'
    echo "    \"model_registry.yaml\": \"$(sha256sum "$REG" | cut -d' ' -f1)\","
    echo "    \"stack_priors.yaml\": \"$(sha256sum "$DERIVED" | cut -d' ' -f1)\","
    echo "    \"orchestrator_stack.py\": \"$(sha256sum "$LAUNCHER" | cut -d' ' -f1)\""
    echo '  },'
    echo '  "not_done_here": "no process started or reloaded; live==config is verified at the next stack start via the stack-change checklist"'
    echo '}'
  } > "$RECEIPT"
  echo "receipt: $RECEIPT"
  echo; echo "== review the diff =="; git -C "$ORCH" diff --stat
  if [ "$DO_COMMIT" -eq 1 ]; then
    git -C "$ORCH" add -- orchestration/model_registry.yaml orchestration/derived/ scripts/server/orchestrator_stack.py
    git -C "$ORCH" commit -m "registry: complete the Qwen3.8-27B swap (role qwen38_27b_q8_local, draft_max 8) + chat-template provenance + retire reversed --jinja fallback

The 2026-08-20 swap landed only in stack_templates/default.yaml (1cff5162); the
master registry and the derived priors the launcher actually reads still served
Qwen3.6-27B at draft_max 4. Evidence: qwen38-27b-replace-qwen36.md Q38-T1..T3
and per-request-reasoning-budget.md PRB-T1 (2026-08-21). Operator-ratified via
scripts/operator/ratify_qwen38_registry_swap_20260821.sh."
    echo "committed in $ORCH — push when ready (serialized_push.py if the guard asks)."
  else
    echo "not committed (--commit to do so after reviewing the diff)."
  fi
else
  echo; echo "[dry-run] no files written."
fi
echo "DONE."
