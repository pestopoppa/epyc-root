#!/bin/bash
# apply_v2.sh — OPERATOR-RUN ratification apply for the MEASUREMENT v2 bundle.
#
# This script performs the human-only writes an agent cannot: replacing
# /workspace/MEASUREMENT.md, installing the measurement/protocols/ annexes,
# patching the MEASUREMENT_POLICY.md digest (region-lock line), and extending
# the human-only path list + sha256 pin to cover the new annex dir.
#
# Default is DRY-RUN (prints every action, writes nothing). Run with --apply
# after auditing RATIFICATION_LEDGER.md. Backups are taken before every write;
# nothing is destroyed (prime directive).
set -euo pipefail

ROOT=/workspace
DRAFT="$ROOT/artifacts/operator/measurement-v2-draft"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/artifacts/operator/measurement-v1-backup-$TS"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

run() { if [[ $APPLY -eq 1 ]]; then "$@"; else echo "DRY-RUN: $*"; fi; }

# --- 0. Preconditions -------------------------------------------------------
for f in MEASUREMENT.md RATIFICATION_LEDGER.md \
         protocols/bench-cpu.md protocols/quality-eval.md protocols/gpu-cross-device.md; do
  [[ -f "$DRAFT/$f" ]] || { echo "FATAL: missing draft file $f" >&2; exit 1; }
done
grep -q 'DRAFT v2 — NOT RATIFIED' "$DRAFT/MEASUREMENT.md" || {
  echo "FATAL: draft banner missing — wrong file?" >&2; exit 1; }

# --- 1. Backup v1 (never destroy) ------------------------------------------
run mkdir -p "$BACKUP_DIR"
run cp -a "$ROOT/MEASUREMENT.md" "$BACKUP_DIR/MEASUREMENT.v1.md"
run cp -a "$ROOT/agents/shared/MEASUREMENT_POLICY.md" "$BACKUP_DIR/MEASUREMENT_POLICY.v1.md"

# --- 2. Install core + annexes (strip the draft banner, stamp ratification) --
install_core() {
  sed 's/⚠️ DRAFT v2 — NOT RATIFIED\. Proposed rewrite of \/workspace\/MEASUREMENT\.md (2026-07-30)\./RATIFIED by operator '"$TS"' — see RATIFICATION_LEDGER in the apply bundle./' \
    "$DRAFT/MEASUREMENT.md" > "$ROOT/MEASUREMENT.md"
}
install_annex() { # $1 = name
  sed 's/⚠️ DRAFT v2 — NOT RATIFIED\. /RATIFIED '"$TS"'. /' \
    "$DRAFT/protocols/$1" > "$ROOT/measurement/protocols/$1"
}
run mkdir -p "$ROOT/measurement/protocols"
if [[ $APPLY -eq 1 ]]; then
  install_core
  for a in bench-cpu.md quality-eval.md gpu-cross-device.md; do install_annex "$a"; done
else
  echo "DRY-RUN: install core -> $ROOT/MEASUREMENT.md (banner -> RATIFIED $TS)"
  echo "DRY-RUN: install annexes -> $ROOT/measurement/protocols/{bench-cpu,quality-eval,gpu-cross-device}.md"
fi

# --- 3. Digest fix (ledger L13 / audit D1): region-lock replaces per-bench approval
PATCH_OLD='- **Before any bench**: explicit operator approval (another agent may be benchmarking; concurrent runs silently poison both); host-health preflight (uptime ≤1wk → drop_caches + NUMA-interleave rewarm; ≥1wk → reboot required); `pgrep` zombie check.'
PATCH_NEW='- **Before any bench**: hold the region claim for the run'"'"'s footprint via `region-lock` (`bench_canonical.sh` acquires it automatically and refuses to run unlocked). Concurrency alone is never grounds for a human gate — operator approval only where `operator_gates[]` names a trust boundary (`OPERATING_CONSTRAINTS.md` → Inference and Benchmarks, amended 2026-07-27). Host-health preflight (uptime ≤1wk → drop_caches + NUMA-interleave rewarm; ≥1wk → reboot required); `pgrep` zombie check.'
if [[ $APPLY -eq 1 ]]; then
  python3 - "$ROOT/agents/shared/MEASUREMENT_POLICY.md" <<PYEOF
import sys
p = sys.argv[1]
old = '''$PATCH_OLD'''
new = '''$PATCH_NEW'''
s = open(p, encoding='utf-8').read()
assert s.count(old) == 1, 'digest patch anchor not found exactly once'
open(p, 'w', encoding='utf-8').write(s.replace(old, new))
print('digest patched:', p)
PYEOF
else
  grep -qF -- "$PATCH_OLD" "$ROOT/agents/shared/MEASUREMENT_POLICY.md" \
    && echo "DRY-RUN: digest patch anchor found — will replace approval line with region-lock rule" \
    || { echo "FATAL: digest patch anchor NOT found" >&2; exit 1; }
fi

# --- 4. Extend the trust boundary to the annexes + re-pin -------------------
HOP="$ROOT/coordination/session-bus/human_only_paths.yaml"
if ! grep -q 'measurement/protocols' "$HOP"; then
  if [[ $APPLY -eq 1 ]]; then
    python3 - "$HOP" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
anchor = '''  - repo: epyc-root
    glob: "agents/shared/MEASUREMENT_POLICY.md"'''
assert anchor in s
add = '''  - repo: epyc-root
    glob: "measurement/protocols/*.md"
    why: "MEASUREMENT v2 protocol annexes — same trust boundary as the core constitution"
'''
# insert after the why-line following the digest entry
idx = s.index(anchor)
end = s.index('\n', s.index('why:', idx)) + 1
open(p, 'w', encoding='utf-8').write(s[:end] + add + s[end:])
print('human_only_paths.yaml extended')
PYEOF
    sha256sum "$HOP" | awk '{print $1}' > "$ROOT/coordination/session-bus/human_only_paths.sha256"
    echo "sha256 pin rewritten"
  else
    echo "DRY-RUN: add measurement/protocols/*.md to human_only_paths.yaml + re-pin sha256"
  fi
fi

# --- 5. Post-apply validation ----------------------------------------------
if [[ $APPLY -eq 1 ]]; then
  python3 "$ROOT/scripts/validate/validate_agents_references.py"
  python3 "$ROOT/scripts/validate/validate_claude_md_matrix.py"
  "$ROOT/scripts/validate/check_claims_grammar.sh"
  echo "APPLY COMPLETE. v1 backup: $BACKUP_DIR"
  echo "Remaining human step: none — this script was the consolidated apply."
else
  echo "DRY-RUN COMPLETE. Re-run with --apply to execute."
fi
