#!/bin/bash
# STEP 8: prove the fleet SERVES the promoted kernel. A process list is not evidence.
set -uo pipefail
K=/mnt/raid0/llm/kernels; RC=0
CPU=""; GPU=""
[ -L "$K/production/cpu" ] && CPU=$(readlink -f "$K/production/cpu")
[ -L "$K/production/gpu" ] && GPU=$(readlink -f "$K/production/gpu")
PIDS=$(ps -eo pid,args | grep 'llama-server -m' | grep -v grep | awk '{print $1}')
[ -n "$PIDS" ] || { echo "no llama-server processes running"; exit 1; }
n=0; bad=0
for pid in $PIDS; do
  n=$((n+1))
  exe=$(readlink /proc/$pid/exe 2>/dev/null)
  case "$exe" in
    "$CPU"/*|"$GPU"/*) ;;
    *) echo "  pid $pid exe NOT from the store: $exe"; bad=$((bad+1)); continue ;;
  esac
  # THE LOAD-BEARING CHECK. Three ggml generations live on this host (llama.cpp 0.16.0,
  # whisper.cpp 0.18.0, qwentts.cpp 0.17.0). A binary that inherits the wrong tree's ggml
  # answers normally and computes wrong. ldd cannot settle it either: llama.cpp DLOPENS
  # libggml-hip.so, so the executable shows no HIP linkage whichever tree it ends up using.
  out=$(grep -oE "/[^ ]*libggml[^ ]*\.so[^ ]*" /proc/$pid/maps 2>/dev/null | sort -u \
        | { [ -n "$CPU" ] && grep -v "^$CPU/" || cat; } \
        | { [ -n "$GPU" ] && grep -v "^$GPU/" || cat; } || true)
  if [ -n "$out" ]; then
    echo "  pid $pid maps ggml OUTSIDE the store:"; echo "$out" | sed 's/^/     /'; bad=$((bad+1))
  fi
done
echo "$n servers checked, $bad with a binary or ggml outside the store"
[ "$bad" = 0 ] || RC=1
[ "$RC" = 0 ] && echo "SERVING VERIFIED" || echo "SERVING VERIFICATION FAILED"
exit $RC
