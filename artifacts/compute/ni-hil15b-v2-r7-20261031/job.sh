#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-hil15b-v2-inference-prep-20261031
MODE=${1:?mode}
: "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}"
MODEL=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf
APP=/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator
SERVER=/mnt/raid0/llm/kernels/production/cpu/llama-server
LIB=/mnt/raid0/llm/kernels/production/cpu
PORT=18983
if [[ "$MODE" == smoke ]]; then THREADS=1; OUT="$D/qualification-${SMOKE_RUN_ID:-native-r7}"; else THREADS=24; OUT="$D/out"; fi
mkdir -p "$OUT"
if [[ "$MODE" == full && -f "$OUT/COHORT-EXPOSED.json" ]]; then
  echo 'frozen cohort already exposed; preserving terminal result without another native call'
  test -f "$OUT/ASSESSMENT.json"
  exit 0
fi
[[ $(stat -c %s "$MODEL") == 37801097504 ]] || { echo 'model size drift'; exit 2; }
python3 "$D/verify_source.py" > "$OUT/app-runtime-head.txt" || { echo 'APP functional source drift'; exit 2; }
[[ $(sha256sum "$APP/scripts/trace/hil15a_flagon_run.py" | cut -d' ' -f1) == 75abff0842a550051b3a25f3bf079a505044120a9ee57e80cc08ef2661bb4c63 ]] || { echo 'native driver drift'; exit 2; }
[[ $(sha256sum "$D/hil15b_v2_tasks.json" | cut -d' ' -f1) == 0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312 ]] || { echo 'taskset drift'; exit 2; }
[[ $(sha256sum /mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030/scripts/vidya/adapters/l2_scan_capture.py | cut -d' ' -f1) == abf418f5825fd520e1ce38ad49a4a961bbd72546b3b416f4370bfb220bc0bc81 ]] || { echo 'ROOT L2 adapter drift'; exit 2; }
[[ $(sha256sum /mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030/scripts/vidya/adapters/hil15a_auc.py | cut -d' ' -f1) == c8a133eb0e38038892b8a830d598c01e7a0f76817914ff90414648faa8250c7f ]] || { echo 'ROOT AUC adapter drift'; exit 2; }
python3 - <<'PY' || { echo 'model edge pin drift'; exit 2; }
import hashlib
p='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'; n=64*1024*1024
with open(p,'rb') as f:
    a=f.read(n); f.seek(-n,2); b=f.read(n)
assert hashlib.sha256(a+b).hexdigest() == '07b181eed5d3b8c0317427faea571256f2f6bb3d97265bf6ccc096f5e9dac6a9'
PY
LD_LIBRARY_PATH="$LIB" /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$SERVER" "$LIB" > "$OUT/linkage.log" 2>&1
if ss -H -ltn "sport = :$PORT" | grep -q LISTEN; then echo "private port $PORT occupied"; exit 4; fi
export LD_LIBRARY_PATH="$LIB" OMP_NUM_THREADS=1 PYTHONHASHSEED=0
export ORCHESTRATOR_CONTENT_CACHE=0 ORCHESTRATOR_FEATURE_CONTENT_CACHE=0
PYTHONPATH="$APP" /workspace/repos/epyc-orchestrator/.venv/bin/python -c 'from src.features import features; assert features().content_cache is False; print("content_cache=False")' > "$OUT/client-feature-proof.log"
setsid taskset -c "$FILLER_CPUS" "$SERVER" -m "$MODEL" -t "$THREADS" -np 1 -c 16384 --reasoning off --jinja --host 127.0.0.1 --port "$PORT" --no-webui -ngl 0 > "$OUT/server.log" 2>&1 &
SPID=$!
echo "$SPID" > "$OUT/server.pid"
cleanup() {
  if [[ "$MODE" == full && ! -f "$OUT/ASSESSMENT.json" ]]; then
    /usr/bin/python3 -c "import sys,pathlib; sys.path.insert(0, '$D'); import native_once; native_once.account(pathlib.Path('$OUT'),'full',75,'shell exit before native assessment',0)" || true
  fi
  if ps -p "$SPID" -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z'; then
    kill -TERM -- "-$SPID" 2>/dev/null || kill -TERM "$SPID" 2>/dev/null || true
    for _ in $(seq 1 30); do ps -p "$SPID" -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z' || break; sleep 1; done
    if ps -p "$SPID" -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z'; then kill -KILL -- "-$SPID" 2>/dev/null || kill -KILL "$SPID" 2>/dev/null || true; fi
  fi
  wait "$SPID" 2>/dev/null || true
  if ps -p "$SPID" -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z'; then echo "server $SPID STILL ALIVE"; else echo "server $SPID dead verified"; fi
}
trap cleanup EXIT
trap 'exit 75' TERM INT
READY=0
for _ in $(seq 1 240); do
  if [[ $(date +%s) -ge $((FILLER_DEADLINE - 20)) ]]; then break; fi
  if ! ps -p "$SPID" > /dev/null; then break; fi
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" > "$OUT/health.json" 2>/dev/null; then READY=1; break; fi
  sleep 1
done
[[ $READY == 1 ]] || { echo 'private server did not become healthy in window'; exit 75; }
if [[ "$MODE" == smoke ]]; then ENTRY=qualification; else ENTRY=full; fi
taskset -c "$FILLER_CPUS" /usr/bin/python3 "$D/native_once.py" "$ENTRY" --out-dir "$OUT" --server-url "http://127.0.0.1:$PORT" --server-pid "$SPID" --deadline-epoch "$FILLER_DEADLINE"
