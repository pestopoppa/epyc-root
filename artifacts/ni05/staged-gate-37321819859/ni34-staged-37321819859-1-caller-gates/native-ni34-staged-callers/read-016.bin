#!/bin/bash
set -euo pipefail
# Git pre-commit hook: Hermes skill docs vs orchestrator x_* request overrides.
# Runs only when staged files touch the Hermes skill docs or OpenAIChatRequest.

CURRENT_REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EPYC_ROOT="/mnt/raid0/llm/epyc-root"
ORCHESTRATOR_ROOT="/mnt/raid0/llm/epyc-orchestrator"
CHECKER="$EPYC_ROOT/scripts/hermes/skills/check_drift.py"
SCHEMA="$ORCHESTRATOR_ROOT/src/api/models/openai.py"
SKILLS_DIR="$EPYC_ROOT/scripts/hermes/skills"

if [[ ! -x "$CHECKER" ]]; then
  echo "[hermes_drift] missing checker: $CHECKER" >&2
  exit 1
fi

mapfile -d '' -t STAGED_FILES < <(git diff --cached --name-only -z --diff-filter=ACM 2>/dev/null || true)
if [[ ${#STAGED_FILES[@]} -eq 0 ]]; then
  exit 0
fi

should_run=0
case "$CURRENT_REPO" in
  "$EPYC_ROOT")
    for path in "${STAGED_FILES[@]}"; do
      if [[ "$path" == scripts/hermes/skills/* ]]; then
        should_run=1
        break
      fi
    done
    ;;
  "$ORCHESTRATOR_ROOT")
    for path in "${STAGED_FILES[@]}"; do
      if [[ "$path" == src/api/models/openai.py ]]; then
        should_run=1
        break
      fi
    done
    ;;
  *)
    exit 0
    ;;
esac

if [[ $should_run -eq 0 ]]; then
  exit 0
fi

python3 "$CHECKER" --schema "$SCHEMA" --skills-dir "$SKILLS_DIR"
