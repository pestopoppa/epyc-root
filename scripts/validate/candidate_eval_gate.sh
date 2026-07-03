#!/bin/bash
set -euo pipefail

# Root governance candidate gate.
#
# This is intentionally no-inference and non-authority. It bundles deterministic
# checks that are appropriate before committing root governance or handoff
# changes. Project-wiki source-manifest drift is useful but currently noisy, so
# it is opt-in via --strict-doc-drift until the wiki refresh lane is clean.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
STRICT_DOC_DRIFT=0

usage() {
  cat <<'USAGE'
Usage: scripts/validate/candidate_eval_gate.sh [--strict-doc-drift]

Runs deterministic root governance checks:
  - Python syntax compile for root validators and their focused tests
  - agent file structure validation
  - agent reference validation
  - CLAUDE.md matrix validation
  - registry operating-point validation
  - held-out PII fixture validation
  - repo-readiness scorer regeneration into a temp directory

Options:
  --strict-doc-drift  Also fail on project-wiki/doc source manifest drift.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict-doc-drift)
      STRICT_DOC_DRIFT=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "$ROOT_DIR"

echo "== py_compile =="
"$PYTHON_BIN" -m py_compile \
  scripts/validate/repo_readiness_scorer.py \
  tests/validate/test_repo_readiness_scorer.py \
  scripts/validate/validate_agents_structure.py \
  scripts/validate/validate_agents_references.py \
  scripts/validate/validate_claude_md_matrix.py \
  scripts/validate/validate_doc_drift.py \
  scripts/validate/validate_registry.py

echo "== agent governance =="
"$PYTHON_BIN" scripts/validate/validate_agents_structure.py
"$PYTHON_BIN" scripts/validate/validate_agents_references.py
"$PYTHON_BIN" scripts/validate/validate_claude_md_matrix.py

echo "== registry validation =="
if command -v uv >/dev/null 2>&1; then
  uv run --with pyyaml python scripts/validate/validate_registry.py
else
  echo "uv unavailable; skipped registry validation that requires pyyaml"
fi

echo "== pii fixture =="
"$PYTHON_BIN" scripts/validate/pii_fixture_eval.py

if [[ "$STRICT_DOC_DRIFT" -eq 1 ]]; then
  echo "== doc drift =="
  "$PYTHON_BIN" scripts/validate/validate_doc_drift.py
else
  echo "== doc drift =="
  echo "skipped by default; rerun with --strict-doc-drift to enforce wiki/source-manifest freshness"
fi

echo "== repo readiness =="
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
"$PYTHON_BIN" scripts/validate/repo_readiness_scorer.py \
  --min-portfolio-level 4 \
  --output-json "$TMP_DIR/repo_readiness.json" \
  --output-md "$TMP_DIR/repo_readiness.md" \
  --output-remediation-json "$TMP_DIR/repo_readiness_remediation_queue.json" \
  --output-autopilot-remediation-json "$TMP_DIR/repo_readiness_autopilot_pickup.json"

if command -v uv >/dev/null 2>&1; then
  echo "== focused tests =="
  uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py
else
  echo "== focused tests =="
  echo "uv unavailable; skipped pytest slice"
fi

echo "candidate eval gate passed"
