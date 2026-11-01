#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/inf70-cls-rect-live-20261101
BIN=/mnt/raid0/llm/kernels/production/cpu
BIN_REAL=$(readlink -f "$BIN")
SERVER=$BIN/llama-server
MODEL_DIR=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS
MODEL=$MODEL_DIR/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
RESULT=$D/results/CLS-RECT-1a.jsonl
PORT=${PORT:-18499}
SPID=
mkdir -p "$D/results" "$D/evidence"
cleanup() {
  local rc=$?
  if [ -n "$SPID" ] && kill -0 "$SPID" 2>/dev/null; then
    kill -TERM "$SPID" 2>/dev/null || true
    for _ in $(seq 1 120); do
      kill -0 "$SPID" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$SPID" 2>/dev/null; then
      kill -KILL "$SPID" 2>/dev/null || true
      sleep 1
    fi
    if ps -p "$SPID" >/dev/null 2>&1; then
      echo "FATAL: server pid $SPID survived SIGKILL" >&2
      rc=70
    else
      echo "server pid $SPID confirmed dead"
    fi
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

[[ -x "$SERVER" ]] || { echo "missing server: $SERVER" >&2; exit 65; }
[[ -f "$MODEL" ]] || { echo "missing model shard: $MODEL" >&2; exit 65; }
actual_sha=$(sha256sum "$SERVER" | awk '{print $1}')
expected_sha=4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c
[[ "$actual_sha" == "$expected_sha" ]] || { echo "server hash mismatch: $actual_sha" >&2; exit 65; }
version=$(env LD_LIBRARY_PATH="$BIN" LANG=C LC_ALL=C "$SERVER" --version 2>&1 | head -1)
[[ "$version" == "version: 10303 (ffc1bac82)" ]] || { echo "server version mismatch: $version" >&2; exit 65; }
ss -ltn "sport = :$PORT" | grep -q LISTEN && { echo "port $PORT already listening" >&2; exit 64; }

for shard in "$MODEL_DIR"/Qwen3.8-Flash-Next-UD-IQ4_XS-0000{1,2,3}-of-00003.gguf; do
  [[ -f "$shard" ]] || { echo "missing model shard: $shard" >&2; exit 65; }
done
(cd "$MODEL_DIR" && sha256sum -c ./*.sha256) > "$D/evidence/model-sha256.txt"
{
  echo "server=$SERVER"
  echo "server_sha256=$actual_sha"
  echo "server_version=$version"
  echo "model_shard1=$MODEL"
  printf 'model_shards='; printf '%s ' "$MODEL_DIR"/Qwen3.8-Flash-Next-UD-IQ4_XS-0000{1,2,3}-of-00003.gguf; echo
  for sidecar in "$MODEL_DIR"/*.sha256; do [[ -f "$sidecar" ]] && cat "$sidecar"; done
  echo "model_sha256_check=$(tr '\n' ';' < "$D/evidence/model-sha256.txt")"
  echo "port=$PORT"
  echo "taskset=0-95"
  echo "numa=interleave=all"
  echo "threads=48"
  echo "start_utc=$(date -u +%FT%TZ)"
  env | sort | rg '^(GGML_|OMP_|FILLER_)' || true
} > "$D/evidence/launch.txt"

env LD_LIBRARY_PATH="$BIN" \
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false \
  GGML_IQK=1 GGML_FA_SPLIT_KV=0 \
  taskset -c 0-95 numactl --interleave=all "$SERVER" \
    --no-webui -np 1 -c 8192 -t 48 --no-mmap -lv 4 \
    --host 127.0.0.1 --port "$PORT" -m "$MODEL" \
    -fa on -ctk f16 -ctv f16 \
    > "$D/evidence/server.log" 2>&1 &
SPID=$!
echo "server_pid=$SPID" >> "$D/evidence/launch.txt"

source /mnt/raid0/llm/epyc-root/scripts/coordination/rowflow/filler_lib.sh
fl_register_pid "$SPID"
fl_wait_own_port "$PORT" "$SPID" 1200 | tee "$D/evidence/health.txt"
grep -q "pid=$SPID," <(ss -ltnp "sport = :$PORT") || { echo "port owner mismatch" >&2; exit 66; }
grep -oE '/[^ ]*libggml-cpu\.so[^ ]*' "/proc/$SPID/maps" | sort -u > "$D/evidence/ggml-maps.txt"
grep -q "$BIN_REAL/" "$D/evidence/ggml-maps.txt" || { echo "production ggml linkage not mapped from $BIN_REAL" >&2; exit 66; }
numastat -p "$SPID" > "$D/evidence/numastat.txt"
cat "/proc/$SPID/smaps_rollup" > "$D/evidence/smaps_rollup.txt"

if [ -e "${FILLER_STOPFILE:?}" ] || [ "$(date -u +%s)" -ge "${FILLER_DEADLINE:?}" ]; then
  echo "stop requested before client start"
  exit 0
fi
CLIENT_OUT="$D/results" python3 "$D/live_arm.py" CLS-RECT-1a "$PORT" "$RESULT"
