#!/bin/bash
# Read-only path identity check. Alias discovery is limited to depth 8 and
# does not follow symlinks; realpath reports the supplied path's resolution.
set -euo pipefail

(($# > 0)) || { echo 'Usage: path_identity.sh <path>...' >&2; exit 2; }
declare -A device_inodes=()
for p in "$@"; do
    [[ -e "$p" ]] || { echo "$p: MISSING" >&2; exit 1; }
    ino=$(stat -c %i "$p")
    dev=$(stat -c %d "$p")
    printf '== %s\n' "$p"
    printf '  realpath : %s\n' "$(realpath -m "$p")"
    printf '  inode    : %s\n' "$ino"
    printf '  device   : %s\n' "$dev"
    printf '  type     : %s\n' "$(stat -c %F "$p")"
    mount=$(findmnt -T "$p" -o TARGET,SOURCE,FSTYPE -n) || { echo "Cannot resolve mount for $p" >&2; exit 1; }
    printf '  mount    : %s\n' "$mount"
    if [[ -L "$p" ]]; then printf '  LINK     : %s\n' "$(readlink "$p")"; fi
    device_inodes["$dev"]+=" $ino"
done

# --raw removes findmnt's tree decoration and escapes mount path whitespace.
# Capture its status before reading; a broken mount list cannot mean no aliases.
mounts=$(findmnt -rn -o TARGET) || { echo 'Cannot enumerate mounts' >&2; exit 1; }
printf '\n== same-device inode matches (depth <= 8; symlinks not followed):\n'
while IFS= read -r encoded; do
    [[ -n "$encoded" ]] || continue
    printf -v mnt '%b' "$encoded"
    case "$mnt" in /proc*|/sys*|/dev*|/run*) continue ;; esac
    dev=$(stat -c %d "$mnt") || { echo "Cannot stat mount $mnt" >&2; exit 1; }
    [[ -v 'device_inodes[$dev]' ]] || continue
    read -r -a inodes <<< "${device_inodes[$dev]}"
    expr=()
    for ino in "${inodes[@]}"; do
        ((${#expr[@]} == 0)) || expr+=(-o)
        expr+=(-inum "$ino")
    done
    # No pipe/head: traversal errors or truncation must never look like success.
    find "$mnt" -xdev -maxdepth 8 \( "${expr[@]}" \) -printf '  ALIAS: %p\n' || {
        echo "Alias traversal failed for $mnt" >&2; exit 1;
    }
done <<< "$mounts"
printf '(Search is limited to depth 8 and does not follow symlinks.)\n'
