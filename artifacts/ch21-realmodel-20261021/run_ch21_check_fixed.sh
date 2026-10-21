#!/bin/bash
# Copy of /mnt/raid0/llm/tmp/ch21-realmodel-check/run_ch21_check.sh (CH-21, another session's script; the
# original is left untouched) with two harness defects fixed, nothing else changed in what it starts/kills:
#  1. the binary check ran `strings | grep -q` under `set -o pipefail`: grep -q exits on the first match, strings
#     dies of SIGPIPE (141) and the pipeline reports failure, so a binary that HAS the message was refused
#     ("binary lacks the disable message"). Now: grep -c on the captured strings of each file.
#  2. this server's generation_settings does not serialize n_cache_reuse (it is a request-schema field only),
#     so `generation_settings.n_cache_reuse == 0` could never hold. The verdict is the disable log line; the
#     echoed value is recorded as 0 / absent. A second request that ASKS for n_cache_reuse=256 with a shared
#     prefix must still be served (and is logged as ignored if the reuse path is reached).
# Same models, same port 18921, starts and kills only its own server PID.
set -euo pipefail
[ "${WINDOW_CONFIRMED:-}" = "1" ] || { echo "REFUSED: set WINDOW_CONFIRMED=1 (window scheduled by main)" >&2; exit 3; }
BIN="${1:?llama-server path}"; OUT="${2:?outdir}"
mkdir -p "$OUT"; LIB="$(dirname "$BIN")"; export LD_LIBRARY_PATH="$LIB"
found=0
for f in "$BIN" "$LIB"/*.so; do
  c=$(strings "$f" 2>/dev/null | grep -c "cache_reuse is not supported by this context" || true)
  [ "$c" -gt 0 ] && { echo "disable message in $(basename "$f")"; found=1; }
done
[ "$found" = 1 ] || { echo "binary lacks the disable message" >&2; exit 4; }
PORT=18921; rc=0
for M in /mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf; do
  tag=$(basename "$M" .gguf); log="$OUT/$tag.log"
  "$BIN" -m "$M" -c 2048 -np 1 --cache-reuse 256 --port $PORT --no-warmup -t 24 >"$log" 2>&1 & pid=$!
  echo "$tag server pid=$pid"
  for i in $(seq 1 600); do curl -sf localhost:$PORT/health >/dev/null 2>&1 && break; kill -0 $pid 2>/dev/null || break; sleep 2; done
  curl -s localhost:$PORT/completion -d '{"prompt":"Hello world, this is a test.","n_predict":4,"temperature":0}' >"$OUT/$tag.resp.json" || true
  curl -s localhost:$PORT/completion -d '{"prompt":"Hello world, this is a test. And a second sentence follows here.","n_predict":4,"temperature":0,"n_cache_reuse":256,"cache_prompt":true}' >"$OUT/$tag.resp2.json" || true
  kill $pid; for i in 1 2 3 4 5 6; do kill -0 $pid 2>/dev/null || break; sleep 5; done; kill -9 $pid 2>/dev/null || true; wait $pid 2>/dev/null || true
  if kill -0 $pid 2>/dev/null; then echo "server $pid STILL ALIVE"; rc=1; else echo "server $pid verified dead"; fi
  n=$(python3 -c "import json;print(json.load(open('$OUT/$tag.resp.json'))['generation_settings'].get('n_cache_reuse','absent'))" 2>/dev/null || echo NA)
  ok2=$(python3 -c "import json;print('served' if 'content' in json.load(open('$OUT/$tag.resp2.json')) else 'error')" 2>/dev/null || echo NA)
  ign=$(grep -c "cache reuse is not supported - ignoring n_cache_reuse" "$log" || true)
  if grep -q "cache_reuse is not supported by this context, it will be disabled" "$log" && { [ "$n" = "0" ] || [ "$n" = "absent" ]; } && [ "$ok2" = "served" ]; then
    echo "PASS $tag (disable line present; generation_settings.n_cache_reuse=$n; reuse-request $ok2; per-request ignore lines=$ign)"
  else
    echo "FAIL $tag (n_cache_reuse=$n, reuse-request=$ok2)"; rc=1
  fi
done
exit $rc
