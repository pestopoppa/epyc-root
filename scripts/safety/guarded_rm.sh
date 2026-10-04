#!/bin/bash
# guarded_rm.sh — trash-first deletion guard for data roots.
#
# NEVER rm -rf data directly. This wrapper is the only sanctioned path for
# recursive deletes of data, and even it does not delete: it MOVES the target
# into the trash root and records a manifest, so every deletion is recoverable
# until trash-sweep.sh explicitly ages it out.
#
# Usage:
#   guarded_rm.sh <path>...            move each path to trash + manifest
#   guarded_rm.sh --list               show trash contents + ages
#   trash-sweep.sh --older-than DAYS   permanently remove aged trash entries
#
# Guarded roots (refused outright unless --bypass-guard is passed, which logs
# a CRITICAL audit line): anything under /mnt/raid0/llm/models or
# /mnt/raid0/llm/lmstudio is a data root; the trash root itself is guarded.
#
# Audit: every operation appends a JSON line to /workspace/logs/safety_audit.log
# (same shard convention as agent_audit.log; readers merge via agent_log_read.sh).
set -euo pipefail

TRASH_ROOT="${TRASH_ROOT:-/mnt/raid0/llm/.trash}"
AUDIT_LOG="${SAFETY_AUDIT_LOG:-/workspace/logs/safety_audit.log}"
GUARDED_ROOTS=("/mnt/raid0/llm/models" "/mnt/raid0/llm/lmstudio" "$TRASH_ROOT")

ts() { date +%Y-%m-%dT%H:%M:%S%z; }
audit() {
    local level="$1" msg="$2"
    printf '{"ts":"%s","session":"safety-guard","level":"%s","cat":"%s","msg":"%s"}\n' \
        "$(ts)" "$level" "GUARDED_RM" "$msg" >> "$AUDIT_LOG"
}

resolve_real() { realpath -m "$1" 2>/dev/null || echo "$1"; }

is_guarded() {
    local p; p="$(resolve_real "$1")"
    for root in "${GUARDED_ROOTS[@]}"; do
        local r; r="$(resolve_real "$root")"
        case "$p" in
            "$r"|"$r"/*) return 0 ;;
        esac
    done
    return 1
}

if [ "${1:-}" = "--list" ]; then
    [ -d "$TRASH_ROOT" ] || { echo "trash empty"; exit 0; }
    find "$TRASH_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -n |
        while read -r age p; do
            echo "$(( ($(date +%s) - ${age%.*}) / 86400 ))d old  $(du -sh "$p" 2>/dev/null | cut -f1)  $(basename "$p")"
        done
    exit 0
fi

[ $# -ge 1 ] || { echo "usage: guarded_rm.sh <path>... | --list" >&2; exit 2; }

BY="safety-guard"
if [ "${1:-}" = "--bypass-guard" ]; then
    shift
    BY="safety-guard(BYPASS)"
    audit "CRITICAL" "guard bypassed for: $*"
fi

mkdir -p "$TRASH_ROOT"
for target in "$@"; do
    [ -e "$target" ] || { echo "missing: $target" >&2; audit "WARN" "missing: $target"; continue; }
    if is_guarded "$target" && [ "$BY" = "safety-guard" ]; then
        echo "REFUSED: $target is under a guarded data root. Use --bypass-guard only with operator approval." >&2
        audit "CRITICAL" "refused guarded delete: $target"
        exit 1
    fi
    dest="$TRASH_ROOT/$(date +%Y%m%d-%H%M%S)-$(basename "$target")"
    size="$(du -sb "$target" 2>/dev/null | cut -f1 || echo unknown)"
    if mv "$target" "$dest"; then
        echo "trashed: $target -> $dest ($size bytes)"
        audit "INFO" "trashed $target -> $dest size=$size"
    else
        echo "FAILED to trash: $target" >&2
        audit "ERROR" "trash failed: $target"
        exit 1
    fi
done
