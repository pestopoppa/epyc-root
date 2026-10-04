#!/bin/bash
# path_identity.sh — pre-flight identity check before ANY destructive action
# (rm -rf, mv, kill). Prints evidence that two paths are the same physical file
# vs. a true duplicate, and flags bind mounts / symlinks that alias paths.
#
# Usage: path_identity.sh <path>...
set -euo pipefail

for p in "$@"; do
    [ -e "$p" ] || { echo "$p: MISSING"; continue; }
    echo "== $p"
    echo "  realpath : $(realpath -m "$p")"
    echo "  inode    : $(stat -c %i "$p")"
    echo "  device   : $(stat -c %d "$p")"
    echo "  type     : $(stat -c %F "$p")"
    echo "  mount    : $(findmnt -T "$p" -o TARGET,SOURCE,FSTYPE -n 2>/dev/null || echo n/a)"
    if stat -c %F "$p" | grep -q symbolic; then
        echo "  LINK     : $(readlink "$p")"
    fi
done

echo
echo "== alias check (same inode reachable via other mounts/symlinks):"
for p in "$@"; do
    [ -e "$p" ] || continue
    ino=$(stat -c %i "$p")
    # find other paths on this host that resolve to the same inode/device
    findmnt -o TARGET -n 2>/dev/null | while read -r mnt; do
        case "$mnt" in
            /proc*|/sys*|/dev*|/run*) continue ;;
        esac
        find "$mnt" -xdev -maxdepth 8 -inum "$ino" 2>/dev/null | head -3 |
            while read -r hit; do echo "  ALIAS: $hit"; done
    done | sort -u
done
echo "(no ALIAS lines = this path is the only reachable copy)"
