#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'EOF'
Usage:
  scripts/backup/backup_critical.sh --target-root /path/to/offhost-or-offarray-target [options]

Common options:
  --manifest scripts/backup/MANIFEST.yaml
  --tiers T0_irreplaceable
  --snapshot-name 20260614T000000Z
  --report-json /path/to/report.json

The target root must be a different filesystem device than the source repos.
Same-array snapshots are intentionally refused.
EOF
  exit 1
fi

python3 "$SCRIPT_DIR/continuity_backup.py" create-snapshot "$@"
