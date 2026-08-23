#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/backup/backup_critical.sh --target-root /path/to/offhost-or-offarray-target [options]

Backends (--backend):
  restic   (default) create the timestamped snapshot directory (verify_restore.sh-
           compatible layout; live SQLite via the sqlite3 .backup API), then
           restic init (once) + restic backup + restic check of that directory
           into <target-root>/restic-repo, tagged f4-t0.
  snapshot create the timestamped snapshot directory only (fallback path).

The snapshot-first ordering means restic never touches live sources, so live
SQLite files are copied through the .backup API (never a torn `cp`), and the
manifest's excluded patterns are already applied before restic sees any byte.

Common options:
  --manifest scripts/backup/MANIFEST.yaml
  --tiers T0_irreplaceable
  --snapshot-name 20260614T000000Z
  --report-json /path/to/report.json
  --password-file /path/to/restic-password.txt
           restic repo password; default <target-root>/restic-password.txt

The target root must be a different filesystem device than the source repos.
Same-array snapshots are intentionally refused.
EOF
}

backend="restic"
password_file=""
target_root=""
declare -a passthrough=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend)
      [[ $# -lt 2 ]] && { usage; exit 1; }
      backend="$2"
      shift 2
      ;;
    --password-file)
      [[ $# -lt 2 ]] && { usage; exit 1; }
      password_file="$2"
      shift 2
      ;;
    --target-root)
      [[ $# -lt 2 ]] && { usage; exit 1; }
      target_root="$2"
      passthrough+=("--target-root" "$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      passthrough+=("$1")
      shift
      ;;
  esac
done

[[ -n "$target_root" ]] || { usage; exit 1; }

case "$backend" in
  snapshot)
    exec python3 "$SCRIPT_DIR/continuity_backup.py" create-snapshot "${passthrough[@]}"
    ;;
  restic)
    command -v restic >/dev/null 2>&1 || { echo "error: restic is not installed" >&2; exit 1; }
    [[ -n "$password_file" ]] || password_file="$target_root/restic-password.txt"
    [[ -r "$password_file" ]] || { echo "error: restic password file not readable: $password_file" >&2; exit 1; }

    repo="$target_root/restic-repo"
    export RESTIC_REPOSITORY="$repo"
    export RESTIC_PASSWORD_FILE="$password_file"

    echo "==> [1/3] snapshot via continuity_backup.py (sqlite .backup API, manifest exclusions)"
    python3 "$SCRIPT_DIR/continuity_backup.py" create-snapshot "${passthrough[@]}"

    snapshot_dir=$(python3 - "$target_root" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
candidates = sorted(
    (p for p in root.iterdir() if p.is_dir() and (p / "SNAPSHOT.json").is_file()),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
print(candidates[0] if candidates else "")
PY
)
    [[ -n "$snapshot_dir" ]] || { echo "error: no snapshot dir found under $target_root" >&2; exit 1; }
    echo "restic: snapshot_dir=$snapshot_dir"

    if ! restic cat config >/dev/null 2>&1; then
      echo "==> [2/3] restic init: $repo"
      restic init
    else
      echo "==> [2/3] restic repo already initialized: $repo"
    fi

    echo "restic: backup $snapshot_dir (tag f4-t0)"
    restic backup "$snapshot_dir" --json --tag f4-t0

    echo "==> [3/3] restic check"
    restic check
    ;;
  *)
    echo "error: unknown --backend '$backend' (expected 'restic' or 'snapshot')" >&2
    exit 1
    ;;
esac
