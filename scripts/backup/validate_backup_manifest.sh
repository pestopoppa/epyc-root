#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_PATH="$SCRIPT_DIR/MANIFEST.yaml"
EXTRA_ARGS=()

if [[ $# -gt 0 ]]; then
  if [[ "${1:-}" == --* ]]; then
    EXTRA_ARGS=("$@")
  else
    MANIFEST_PATH="$1"
    shift
    EXTRA_ARGS=("$@")
  fi
fi

if [[ ! -f "$MANIFEST_PATH" ]]; then
  echo "ERROR: manifest missing: $MANIFEST_PATH" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/continuity_backup.py" validate --manifest "$MANIFEST_PATH" "${EXTRA_ARGS[@]}"
