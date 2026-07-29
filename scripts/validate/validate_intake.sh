#!/bin/bash
set -euo pipefail
# Wrapper for the research-intake index validator.
#
# WHY: the devcontainer's default `python3` lacks PyYAML, so a bare
# `python3 validate_intake.py` exits 1 with an ImportError BEFORE validating —
# silently defeating the intake skill's Phase-5 gate. This wrapper selects the
# first Python that actually has PyYAML (the orchestrator venv has it) and runs
# the validator with it. Baseline established green (0 errors) on 2026-07-14.
#
# Usage: bash scripts/validate/validate_intake.sh
# Exit: passes through the validator's exit code (0 = valid).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATOR="$ROOT/.claude/skills/research-intake/scripts/validate_intake.py"

for PY in \
  "$ROOT/repos/epyc-orchestrator/.venv/bin/python" \
  /workspace/repos/epyc-orchestrator/.venv/bin/python \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
  python3; do
  if [[ -x "$PY" || "$PY" == "python3" ]] && "$PY" -c 'import yaml' 2>/dev/null; then
    exec "$PY" "$VALIDATOR" "$@"
  fi
done

echo "ERROR: no Python with PyYAML found (tried orchestrator venv + python3)." >&2
echo "Fix: pip install pyyaml, or point at a venv that has it." >&2
exit 1
