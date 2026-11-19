#!/bin/bash
set -euo pipefail
umask 077
ulimit -c 0
D="$(cd "$(dirname "$0")/.." && pwd)"
: "${FILLER_ID:?}" "${FILLER_THREADS:?}" "${FILLER_CPUS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
[[ "$FILLER_ID" == fm2-adamast-20261118 ]]
[ ! -e "$FILLER_STOPFILE" ] || exit 0
source "$D/code/model.env"
source "$D/code/qwen_thinking_lib.sh"
export LD_LIBRARY_PATH="$(dirname "$FM2_SERVER_BIN")"
export ADAMAST_BASE_URL=http://127.0.0.1:18711/v1 OPENAI_API_KEY=local-fm2
export OMP_NUM_THREADS="$FILLER_THREADS" GGML_FUSED_DECODE_OFF=1
if [ -n "${FILLER_DRYRUN_RESULT_PATH:-}" ]; then
  log_dir="$(dirname "$FILLER_DRYRUN_RESULT_PATH")"
else
  log_dir="$D/out"
fi
mkdir -p "$log_dir"
read -r -a reasoning <<< "$(qwen_reasoning_args "$FM2_MODEL_GGUF")"
[[ "${reasoning[*]}" == '--reasoning off' ]]
log="$(mktemp "$log_dir/server.XXXXXX.log")"
taskset -c "$FILLER_CPUS" "$FM2_SERVER_BIN" -m "$FM2_MODEL_GGUF" --alias local-fm2 \
  --host 127.0.0.1 --port 18711 -t "$FILLER_THREADS" -tb "$FILLER_THREADS" \
  -c 16384 -np 1 -ngl 0 --jinja --chat-template-file "$FM2_TEMPLATE" "${reasoning[@]}" >"$log" 2>&1 &
server_pid=$!
cleanup() {
  if ps -p "$server_pid" >/dev/null; then
    kill -TERM "$server_pid" 2>/dev/null || true
    for _ in {1..10}; do
      ps -p "$server_pid" >/dev/null || break
      sleep 1
    done
    if ps -p "$server_pid" >/dev/null; then
      kill -KILL "$server_pid" 2>/dev/null || true
    fi
  fi
  wait "$server_pid" 2>/dev/null || true
  ! ps -p "$server_pid" >/dev/null
}
trap cleanup EXIT
trap 'exit 143' TERM INT
ready_deadline=$((SECONDS + 450))
until /usr/bin/python3 -B "$D/code/pilot.py" health; do
  ps -p "$server_pid" >/dev/null || { echo "Owned server exited. $log"; exit 4; }
  [ ! -e "$FILLER_STOPFILE" ] || exit 0
  (( SECONDS < ready_deadline && $(date +%s) < FILLER_DEADLINE )) || { echo "Server startup timed out. $log"; exit 4; }
  sleep 2
done
/usr/bin/python3 -B "$D/code/own_port_proof.py" owner 18711 "$server_pid" || { echo "Expected own server PID $server_pid. $log"; exit 4; }
FM2_SERVER_PID="$server_pid" FM2_SERVER_LOG="$log" "$FM2_PY" -I -B "$D/code/pilot.py" run
