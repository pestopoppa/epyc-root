#!/bin/bash
# trash-sweep.sh — permanently remove trash entries older than N days.
#
# Usage: trash-sweep.sh --older-than DAYS [--dry-run]
# Only ever deletes inside $TRASH_ROOT. Never run on a live path.
set -euo pipefail

TRASH_ROOT="${TRASH_ROOT:-/mnt/raid0/llm/.trash}"
AUDIT_LOG="${SAFETY_AUDIT_LOG:-/workspace/logs/safety_audit.log}"

days=0; dry=0
while [ $# -gt 0 ]; do
    case "$1" in
        --older-than) days="$2"; shift 2 ;;
        --dry-run) dry=1; shift ;;
        *) echo "usage: trash-sweep.sh --older-than DAYS [--dry-run]" >&2; exit 2 ;;
    esac
done

[ "$days" -gt 0 ] || { echo "days required" >&2; exit 2; }
[ -d "$TRASH_ROOT" ] || { echo "no trash"; exit 0; }

cutoff=$(( $(date +%s) - days * 86400 ))
# Age = the TRASH time, read from the YYYYMMDD-HHMMSS prefix guarded_rm.sh gives every entry —
# never the entry's mtime: `mv` preserves mtime, so a month-old scratch dir trashed today would
# otherwise be swept on the next run and the recoverable window would not exist. Files and dirs
# alike (guarded_rm.sh trashes both; a `-type d` filter leaked every trashed file forever).
# An entry without the prefix falls back to its ctime (set by the mv into the trash).
find "$TRASH_ROOT" -mindepth 1 -maxdepth 1 \( -type d -o -type f -o -type l \) -printf '%C@ %p\n' | sort -n |
    while read -r ctime p; do
        name="$(basename "$p")"
        if [[ "$name" =~ ^([0-9]{8})-([0-9]{2})([0-9]{2})([0-9]{2})- ]]; then
            age="$(date -d "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}:${BASH_REMATCH[3]}:${BASH_REMATCH[4]}" +%s 2>/dev/null || echo "${ctime%.*}")"
        else
            age="${ctime%.*}"
        fi
        [ "${age%.*}" -lt "$cutoff" ] || continue
        if [ "$dry" = 1 ]; then
            echo "[dry-run] would remove $p ($(( ( $(date +%s) - ${age%.*} ) / 86400 ))d old)"
        else
            size="$(du -sb "$p" 2>/dev/null | cut -f1 || echo unknown)"
            rm -rf -- "$p"
            printf '{"ts":"%s","session":"safety-guard","level":"INFO","cat":"TRASH_SWEEP","msg":"removed %s size=%s"}\n' \
                "$(date +%Y-%m-%dT%H:%M:%S%z)" "$p" "$size" >> "$AUDIT_LOG"
            echo "removed $p"
        fi
    done
