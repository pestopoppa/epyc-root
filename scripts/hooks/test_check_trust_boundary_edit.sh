#!/bin/bash
set -euo pipefail
# Regression test for check_trust_boundary_edit.sh's gate-list matcher.
#
# WHY THIS EXISTS
# ---------------
# On 2026-08-03 the matcher was found comparing the target path against each
# gate-list entry with a QUOTED right-hand side, i.e. literal string equality.
# Literal entries (MEASUREMENT.md, instrument_eras.yaml) matched fine, so the
# guard looked healthy. Every WILDCARD entry silently matched nothing:
# `measurement/protocols/*.md` was compared against the literal path
# `.../protocols/*.md`, which no real file equals. Annex B, Q and G — which
# MEASUREMENT.md:17-19 states carry the SAME trust boundary and amendment rules
# as the constitution itself — were therefore agent-writable, and layer 1 of the
# three-layer enforcement reported success while doing nothing for them.
#
# The whole defect was two quote characters, and nothing tested the matcher.
# This test asserts both directions: protected paths block, unrelated paths do
# not. It reads the live gate list, so adding an entry there extends coverage
# automatically.
#
# Run: bash scripts/hooks/test_check_trust_boundary_edit.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE_LIST="${REPO_ROOT}/coordination/session-bus/human_only_paths.yaml"
ROOTS=("$REPO_ROOT" "/mnt/raid0/llm/epyc-orchestrator" "/mnt/raid0/llm/epyc-inference-research")

FAILURES=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s — %s\n' "$1" "$2"; FAILURES=$((FAILURES + 1)); }

globs=$(grep -oE '^[[:space:]]*glob:[[:space:]]*"[^"]+"' "$GATE_LIST" \
        | sed -E 's/.*"([^"]+)".*/\1/')

if [[ -z "$globs" ]]; then
  echo "FAIL: could not parse any glob from $GATE_LIST — the matcher would fail open." >&2
  exit 1
fi

# Mirrors the matcher in check_trust_boundary_edit.sh. Keep in sync: the RHS of
# the comparison must stay unquoted so it is a pattern, not a literal.
matches_gate_list() {
  local target="$1" g root candidate
  while IFS= read -r g; do
    [[ -z "$g" ]] && continue
    for root in "${ROOTS[@]}"; do
      candidate=$(realpath -m "${root}/${g}" 2>/dev/null || printf '%s' "${root}/${g}")
      if [[ "$target" == $candidate ]]; then
        return 0
      fi
    done
  done <<< "$globs"
  return 1
}

echo "MUST BLOCK (on the trust boundary):"
# Literal entries — these matched even with the bug, so they are the control
# that proves the test itself is not vacuous.
for t in \
  "${REPO_ROOT}/MEASUREMENT.md" \
  "${REPO_ROOT}/agents/shared/MEASUREMENT_POLICY.md" \
  "/mnt/raid0/llm/epyc-orchestrator/orchestration/instrument_eras.yaml" \
  "/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_baseline.yaml"
do
  if matches_gate_list "$t"; then pass "${t#$REPO_ROOT/}"; else fail "${t#$REPO_ROOT/}" "not matched"; fi
done

# Wildcard entry — the regression. Every ratified annex must block.
for t in "${REPO_ROOT}"/measurement/protocols/*.md; do
  [[ -e "$t" ]] || continue
  if matches_gate_list "$t"; then pass "${t#$REPO_ROOT/}"; else fail "${t#$REPO_ROOT/}" "WILDCARD ENTRY NOT ENFORCED — the 2026-08-03 defect has regressed"; fi
done

echo "MUST NOT BLOCK (ordinary agent-writable files):"
for t in \
  "${REPO_ROOT}/CLAUDE.md" \
  "${REPO_ROOT}/scripts/hooks/check_trust_boundary_edit.sh" \
  "${REPO_ROOT}/handoffs/active/autokernel-research-loop.md" \
  "${REPO_ROOT}/measurement/protocols/not-a-real-annex.txt"
do
  if matches_gate_list "$t"; then fail "${t#$REPO_ROOT/}" "over-blocked"; else pass "${t#$REPO_ROOT/}"; fi
done

if [[ "$FAILURES" -gt 0 ]]; then
  echo "FAILED: $FAILURES assertion(s)." >&2
  exit 1
fi
echo "All assertions passed."
