#!/bin/bash
# usage: run.sh <slot> <iterations> <tag> [gdb]
set -uo pipefail
ulimit -c 0
W=/mnt/raid0/llm/tmp/gitnexus-doublefree-20261105
slot=$1; n=$2; tag=$3; mode=${4:-plain}
G=/usr/local/share/npm-global/lib/node_modules/gitnexus/dist/cli/index.js
mkdir -p "$W/logs/$tag" "$W/home$slot"
export GITNEXUS_HOME="$W/home$slot" GITNEXUS_REPO_NAME="dfrepro$slot" GITNEXUS_VERBOSE=1 \
  GITNEXUS_WORKER_POOL_SIZE=1 GITNEXUS_PARSE_CHUNK_CONCURRENCY=1 \
  GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS=120000 GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS=600000 \
  GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES=131072 \
  NODE_OPTIONS="--max-old-space-size=65536 --max-semi-space-size=64"
cd "$W/src$slot"
for it in $(seq 1 "$n"); do
  o="$W/logs/$tag/s${slot}-i${it}"
  if [[ $mode == gdb ]]; then
    gdb -batch -nx -ex 'set pagination off' -ex 'handle SIGPIPE SIGUSR1 SIGUSR2 nostop noprint pass' \
      -ex run -ex 'bt 60' -ex 'info threads' -ex 'thread apply all bt 25' \
      --args node --stack-size=4096 "$G" analyze --skip-agents-md --skip-skills --workers 1 --force >"$o.out" 2>"$o.err"
    rc=$?
  else
    node --stack-size=4096 "$G" analyze --skip-agents-md --skip-skills --workers 1 --force >"$o.out" 2>"$o.err"
    rc=$?
  fi
  ok=$(grep -c 'indexed successfully' "$o.out")
  df=$(grep -cE 'double free|corruption|SIGSEGV|SIGABRT|free\(\)' "$o.out" "$o.err" | awk -F: '{s+=$2} END{print s}')
  echo "{\"tag\":\"$tag\",\"slot\":$slot,\"iter\":$it,\"rc\":$rc,\"success\":$ok,\"crash_markers\":$df}" >> "$W/logs/$tag/results.jsonl"
done
