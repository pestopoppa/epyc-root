#!/bin/bash
set -euo pipefail

# Git pre-commit hook: stack-fact migration discipline.
# Blocks staged stack topology reader/source changes unless the same commit also
# updates a reader-agreement or parity contract test.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" "$ROOT_DIR/scripts/validate/check_stack_fact_migration_discipline.py" \
  --repo-root "$REPO_ROOT"
