#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  scripts/backup/check_latest_backup.sh --target-root /path/to/offhost-or-offarray-target --max-age-days N [options]

Options pass through to continuity_backup.py check-latest, including:
  --manifest scripts/backup/MANIFEST.yaml
  --tiers T0_irreplaceable
  --restore-root /tmp/restore-dir
  --report-json /path/to/report.json
USAGE
}

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

python3 "$SCRIPT_DIR/continuity_backup.py" check-latest "$@"
