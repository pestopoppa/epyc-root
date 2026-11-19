#!/bin/bash
set -euo pipefail
out=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf41-direct-evidence-20261102
export LD_LIBRARY_PATH=/dev/shm/kpf41-direct-20261102/bin:/opt/rocm/lib
/dev/shm/kpf41-direct-20261102/bin/test-kv-rows-vec-direct > "$out/program.log" 2>&1 &
pid=$!
printf 'pid=%s\n' "$pid" > "$out/residency.log"
while kill -0 "$pid" 2>/dev/null; do
  if [ -d "/sys/class/kfd/kfd/proc/$pid" ]; then
    printf 'utc=%s kfd=present\n' "$(date -u +%FT%TZ)" >> "$out/residency.log"
    ls -R "/sys/class/kfd/kfd/proc/$pid" > "$out/kfd-tree.txt" 2>/dev/null || :
    for f in /sys/class/kfd/kfd/proc/"$pid"/vram_*; do
      if [ -f "$f" ]; then printf '%s=' "$f" >> "$out/residency.log"; cat "$f" >> "$out/residency.log"; fi
    done
    cat "/proc/$pid/maps" > "$out/process.maps" 2>/dev/null || :
  fi
  sleep 0.2
done
rc=0
wait "$pid" || rc=$?
printf 'exit=%s\n' "$rc" >> "$out/residency.log"
exit "$rc"
