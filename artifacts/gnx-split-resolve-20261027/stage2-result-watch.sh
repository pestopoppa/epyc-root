#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
id=codex-ni-gnx-split-resolve-20261027
grants=/mnt/raid0/llm/tmp/compute-flags/grants
exec 9>"$root/stage2-result-watch.lock"
flock -n 9 || exit 75
printf '%s\n' "$$" > "$root/stage2-result-watch.pid"
for ((i=0;i<4320;i++)); do
  if [[ -f "$grants/$id.complete" || -f "$grants/$id.ended" ]]; then
    tmp="$root/STAGE2-RESULT-AVAILABLE.txt.tmp.$$"
    { printf 'id=%s observed=%s\n' "$id" "$(date -u +%FT%TZ)"; for suffix in complete ended; do
        if [[ -f "$grants/$id.$suffix" && ! -L "$grants/$id.$suffix" ]]; then printf '%s: ' "$suffix"; cat "$grants/$id.$suffix"; fi
      done; } > "$tmp"
    mv "$tmp" "$root/STAGE2-RESULT-AVAILABLE.txt"
    touch "$root/STAGE2-RESULT-AVAILABLE.flag"
    exit 0
  fi
  sleep 10
done
printf 'watch expired without terminal marker\n' > "$root/STAGE2-RESULT-WATCH-EXPIRED.txt"
touch "$root/STAGE2-RESULT-WATCH-EXPIRED.flag"
exit 75
