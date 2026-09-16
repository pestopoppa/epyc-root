#!/bin/bash
# Force >= TARGET GiB free on every NUMA node. Unlike evict_nodes.sh (which allocates TARGET-free and therefore
# reclaims nothing when that is smaller than what is already free), this allocates TARGET+2 GiB under membind
# whenever free < TARGET, so the kernel must reclaim (TARGET - free) of page cache on that node. Verifies, 2 passes.
set -u
TARGET_GIB=${1:-40}
B=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)   # where_pages.py lives beside this script
free_mb() { numactl -H | awk -v n="$1" '$1=="node" && $2==n && $3=="free:" {print $4}'; }
for pass in 1 2; do
  for n in 0 1 2 3; do
    f=$(( $(free_mb "$n") / 1024 ))
    if [ "$f" -lt "$TARGET_GIB" ]; then
      echo "$(date -u +%T) pass $pass node $n free ${f} GiB -> allocating $((TARGET_GIB + 2)) GiB under membind to force reclaim"
      numactl --membind="$n" python3 "$B/where_pages.py" "$((TARGET_GIB + 2))"
    fi
  done
  echo "$(date -u +%T) pass $pass free per node now: $(numactl -H | grep free | tr '\n' ' ')"
  ok=1; for n in 0 1 2 3; do [ $(( $(free_mb "$n") / 1024 )) -ge "$TARGET_GIB" ] || ok=0; done
  [ "$ok" = 1 ] && break
done
[ "$ok" = 1 ] && echo "EVICT OK (>= ${TARGET_GIB} GiB free on every node)" || echo "EVICT SHORT"
