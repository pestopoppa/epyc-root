#!/bin/bash
# trash-sweep.sh — permanently remove trash entries older than N days.
#
# Usage: trash-sweep.sh --older-than DAYS|Nh|now [--dry-run]
#   --older-than 24h   hours granularity (trash_reap_tick.sh, operator 2026-11-21); a bare number is days
#   --older-than now   operator force-clear: removes EVERY trash entry, including ones trashed today
#                      (operator 2026-11-05). Always preview with --dry-run first.
# Only ever deletes inside $TRASH_ROOT. Never run on a live path.
set -euo pipefail

TRASH_ROOT="${TRASH_ROOT:-/mnt/raid0/llm/.trash}"
AUDIT_LOG="${SAFETY_AUDIT_LOG:-/workspace/logs/safety_audit.log}"

days=0; dry=0
while [ $# -gt 0 ]; do
    case "$1" in
        --older-than) [ "$#" -ge 2 ] || { echo "--older-than requires a value" >&2; exit 2; }; days="$2"; shift 2 ;;
        --dry-run) dry=1; shift ;;
        *) echo "usage: trash-sweep.sh --older-than DAYS|now [--dry-run]" >&2; exit 2 ;;
    esac
done

[ -d "$TRASH_ROOT" ] || { echo "trash root missing: $TRASH_ROOT" >&2; exit 1; }
TRASH_ROOT="$(realpath -e -- "$TRASH_ROOT")"
[ "$TRASH_ROOT" != / ] || { echo "refusing filesystem root as trash" >&2; exit 1; }
if [ "$days" = now ]; then
    cutoff=$(( $(date +%s) + 1 ))   # everything trashed up to this second
elif [[ "$days" =~ ^([0-9]+)h$ ]] && [ "${BASH_REMATCH[1]}" -gt 0 ]; then
    cutoff=$(( $(date +%s) - BASH_REMATCH[1] * 3600 ))
else
    [[ "$days" =~ ^[0-9]+$ ]] && [ "$days" -gt 0 ] || { echo "days required (positive integer, 'Nh' hours, or 'now')" >&2; exit 2; }
    cutoff=$(( $(date +%s) - days * 86400 ))
fi
# Age = the TRASH time, read from the YYYYMMDD-HHMMSS prefix guarded_rm.sh gives every entry —
# never the entry's mtime: `mv` preserves mtime, so a month-old scratch dir trashed today would
# otherwise be swept on the next run and the recoverable window would not exist. Files and dirs
# alike (guarded_rm.sh trashes both; a `-type d` filter leaked every trashed file forever).
# An entry without the prefix falls back to its ctime (set by the mv into the trash).
# Materialize the list so traversal errors are not hidden by a pipeline subshell.
entries=$(mktemp)
links=$(mktemp)
trap 'rm -f -- "$entries" "$links"' EXIT
find -P "$TRASH_ROOT" -mindepth 1 -maxdepth 1 \( -type d -o -type f -o -type l \) -print0 | sort -z > "$entries"
skipped=0
while IFS= read -r -d '' p; do
    ctime="$(stat -c %Z -- "$p")"
    name="${p##*/}"
    if [[ "$name" =~ ^([0-9]{8})-([0-9]{2})([0-9]{2})([0-9]{2})- ]]; then
        age="$(date -d "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}:${BASH_REMATCH[3]}:${BASH_REMATCH[4]}" +%s 2>/dev/null || echo "$ctime")"
    else
        age="$ctime"
    fi
    [ "$age" -lt "$cutoff" ] || continue
    owner="$(stat -c '%U (%u)' -- "$p" 2>/dev/null || echo unknown)"
    reason=""
    resolved="$(realpath -m -- "$p")"
    case "$resolved" in "$TRASH_ROOT"/*) ;; *) reason="path resolves outside trash root" ;; esac
    # Recursive chmod and rm must never follow links outside the root. Refuse
    # the whole entry if it contains such a link, including a top-level link.
    if [ -z "$reason" ]; then
        if find -P "$p" -type l -print0 > "$links"; then
            while IFS= read -r -d '' link; do
                resolved="$(realpath -m -- "$link")"
                case "$resolved" in "$TRASH_ROOT"/*) ;; *) reason="symlink resolves outside trash root"; break ;; esac
            done < "$links"
        else
            reason="cannot inspect entry for symlinks"
        fi
    fi
    if [ -n "$reason" ]; then
        printf 'skipped %q owner=%q reason=%q\n' "$p" "$owner" "$reason"
        skipped=$((skipped + 1))
        continue
    fi
    if [ "$dry" = 1 ]; then
        echo "[dry-run] would remove $p ($(( ( $(date +%s) - age ) / 86400 ))d old)"
    else
        size="$(du -sb "$p" 2>/dev/null | cut -f1 || echo unknown)"
        if ! rm -rf -- "$p" 2>/dev/null; then
            # Never let chmod dereference a command-line symlink.
            if [ ! -L "$p" ]; then
                chmod -R u+rwX -- "$p" 2>/dev/null || true
            fi
            if reason="$(rm -rf -- "$p" 2>&1)"; then
                reason=""
            else
                reason="${reason:-removal failed after chmod retry}"
                reason="${reason//$'\n'/; }"
                printf 'skipped %q owner=%q reason=%q\n' "$p" "$owner" "$reason"
                skipped=$((skipped + 1))
                continue
            fi
        fi
        printf '{"ts":"%s","session":"safety-guard","level":"INFO","cat":"TRASH_SWEEP","msg":"removed %s size=%s"}\n' \
            "$(date +%Y-%m-%dT%H:%M:%S%z)" "$p" "$size" >> "$AUDIT_LOG"
        echo "removed $p"
    fi
done < "$entries"
echo "skipped entries: $skipped"
