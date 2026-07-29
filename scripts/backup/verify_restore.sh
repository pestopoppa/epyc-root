#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'EOF'
Usage:
  scripts/backup/verify_restore.sh --snapshot-root /path/to/snapshot [options]

Common options:
  --manifest scripts/backup/MANIFEST.yaml
  --tiers T0_irreplaceable
  --restore-root /tmp/restore-dir
  --max-age-days 7
EOF
  exit 1
fi

python3 "$SCRIPT_DIR/continuity_backup.py" verify-restore "$@"
