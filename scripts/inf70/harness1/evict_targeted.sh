#!/bin/bash
# INF-70 HARNESS-1: targeted page-cache eviction.
#
# evict_nodes_force.sh reaches the same end state by allocating TARGET+2 GiB of anonymous memory
# under membind on every short node, forcing the kernel to reclaim page cache: ~140 s per arm.
# What the arm actually needs evicted is the read cache of the GGUF it is about to re-read with
# --no-mmap. posix_fadvise(POSIX_FADV_DONTNEED) drops exactly that, in seconds.
#
# fadvise is ADVISORY and only evicts CLEAN pages, so the tool re-measures residency with
# mincore(2) afterwards -- the syscall's return value is not evidence. And because the page
# cache may hold OTHER files this script knows nothing about, the per-node free target is still
# verified, with the old allocation-pressure path kept as the fallback when it is not met.
#
#   usage: evict_targeted.sh <target_gib> <file>...
set -u
TARGET_GIB=$1; shift
H=/mnt/raid0/llm/tmp/inf70/agents/harness1
free_mb() { numactl -H | awk -v n="$1" '$1=="node" && $2==n && $3=="free:" {print $4}'; }
pernode() { for n in 0 1 2 3; do printf "%d " $(( $(free_mb "$n") / 1024 )); done; }
T0=$(date +%s)
echo "$(date -u +%T) free/node GiB before: $(pernode)"
"$H/tools/pagecache" drop "$@"
echo "$(date -u +%T) free/node GiB after targeted drop: $(pernode)"
short=0; for n in 0 1 2 3; do [ $(( $(free_mb "$n") / 1024 )) -ge "$TARGET_GIB" ] || short=1; done
if [ "$short" = 1 ]; then
  echo "$(date -u +%T) FALLBACK: a node is still under ${TARGET_GIB} GiB -> allocation pressure"
  bash /mnt/raid0/llm/tmp/inf70/evict_nodes_force.sh "$TARGET_GIB"
  echo "$(date -u +%T) free/node GiB after fallback: $(pernode)"
  echo "EVICT_MODE=targeted+fallback"
else
  echo "EVICT_MODE=targeted"
fi
ok=1; for n in 0 1 2 3; do [ $(( $(free_mb "$n") / 1024 )) -ge "$TARGET_GIB" ] || ok=0; done
echo "EVICT_ELAPSED=$(( $(date +%s)-T0 ))s EVICT_OK=$ok"
[ "$ok" = 1 ]
