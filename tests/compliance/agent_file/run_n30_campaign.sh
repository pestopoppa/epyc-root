#!/bin/bash
# AFC-P5.E3 — n=30 compliance campaign (suite v2), sequential bench-style servers.
# Usage: region-lock run --cpu-list 0-95 -- bash tests/compliance/agent_file/run_n30_campaign.sh
# Incremental persistence: one JSON per (model, level); campaign.log per step.
set -euo pipefail

ROOT=/workspace
BIN=/mnt/raid0/llm/llama.cpp/build/bin/llama-server
PORT=18099
URL="http://127.0.0.1:${PORT}"
OUT="$ROOT/data/compliance/2026-07-30-n30-curve"
LOG="$OUT/campaign.log"
mkdir -p "$OUT"

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

declare -A MODELS=(
  [worker_general-gemma4-26B-A4B-Q4KM]="/mnt/raid0/llm/models/gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf"
  [frontdoor-Qwen3.6-35B-A3B-Q8]="/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
  [ingest-Qwen3-Next-80B-Q4KM]="/mnt/raid0/llm/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
  [architect-Qwen3.5-122B-UD-Q4KM]="/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf"
)
# Deterministic order: small->large so early results land fast.
ORDER=(worker_general-gemma4-26B-A4B-Q4KM frontdoor-Qwen3.6-35B-A3B-Q8 ingest-Qwen3-Next-80B-Q4KM architect-Qwen3.5-122B-UD-Q4KM)

LEVELS=(none mild medium aggressive)

# SMOKE=1: config probe (first model, level=none, 2 tasks/pool) per
# feedback_bench_max_opt_and_config_probe_first — validate end-to-end before the long run.
EXTRA_ARGS=()
if [[ "${SMOKE:-0}" == "1" ]]; then
  ORDER=("${ORDER[0]}")
  LEVELS=(none)
  EXTRA_ARGS=(--max-tasks 2)
  OUT="$OUT/smoke"
  LOG="$OUT/campaign.log"
  mkdir -p "$OUT"
fi
declare -A FILES=(
  [none]="agents/shared/ENGINEERING_STANDARDS.md"
  [mild]="agents/shared/ENGINEERING_STANDARDS.compressed-mild.md"
  [medium]="agents/shared/ENGINEERING_STANDARDS.compressed-medium.md"
  [aggressive]="agents/shared/ENGINEERING_STANDARDS.compressed-aggressive.md"
)

SERVER_PID=""
teardown() {
  if [[ -n "$SERVER_PID" ]] && ps -p "$SERVER_PID" >/dev/null 2>&1; then
    log "teardown: killing server pid=$SERVER_PID"
    kill "$SERVER_PID" 2>/dev/null || true
    for _ in $(seq 1 20); do ps -p "$SERVER_PID" >/dev/null 2>&1 || break; sleep 1; done
    if ps -p "$SERVER_PID" >/dev/null 2>&1; then kill -9 "$SERVER_PID"; sleep 2; fi
    ps -p "$SERVER_PID" >/dev/null 2>&1 && log "ERROR: pid $SERVER_PID survived SIGKILL" || log "teardown: dead"
  fi
  SERVER_PID=""
}
trap teardown EXIT

wait_health() { # $1 = max seconds
  local deadline=$(( $(date +%s) + $1 ))
  while (( $(date +%s) < deadline )); do
    if curl -sf -m 3 "$URL/health" >/dev/null 2>&1; then return 0; fi
    ps -p "$SERVER_PID" >/dev/null 2>&1 || { log "ERROR: server died during load"; return 1; }
    sleep 5
  done
  return 1
}

log "=== n30 campaign start (suite v2, binary $($BIN --version 2>&1 | head -1)) ==="
cd "$ROOT"

for model in "${ORDER[@]}"; do
  path="${MODELS[$model]}"
  log "--- model $model : loading $path"
  taskset -c 0-95 "$BIN" -m "$path" --port "$PORT" -t 96 -c 32768 -fa 1 -np 8 \
    --jinja --no-webui >> "$OUT/$model.server.log" 2>&1 &
  SERVER_PID=$!
  if ! wait_health 1800; then log "ERROR: $model failed to become healthy; skipping"; teardown; continue; fi
  log "$model healthy (pid=$SERVER_PID)"

  # Per-model config probe: 2 tasks/pool at level=none; a broken serving config
  # (template, np, ctx) must fail HERE, not after 360 wasted calls.
  if ! python3 tests/compliance/agent_file/live_runner.py \
      --base-url "$URL" --model-id "$model-probe" \
      --agent-file "${FILES[none]}" --level none \
      --max-tokens 512 --temperature 0.0 --timeout 600 \
      --max-tasks 2 --concurrency 2 \
      --output "$OUT/${model}.probe.json" >> "$LOG" 2>&1; then
    log "ERROR: $model config probe FAILED; skipping model"; teardown; continue
  fi
  log "$model probe ok"

  for level in "${LEVELS[@]}"; do
    outfile="$OUT/${model}-${level}.json"
    if [[ -s "$outfile" ]]; then log "skip existing $outfile"; continue; fi
    log "run $model level=$level"
    if python3 tests/compliance/agent_file/live_runner.py \
        --base-url "$URL" --model-id "$model" \
        --agent-file "${FILES[$level]}" --level "$level" \
        --max-tokens 512 --temperature 0.0 --timeout 600 \
        --concurrency 8 \
        "${EXTRA_ARGS[@]}" \
        --output "$outfile" >> "$LOG" 2>&1; then
      log "done $model/$level"
    else
      log "ERROR: live_runner failed for $model/$level (continuing)"
    fi
  done
  teardown
done

log "=== campaign complete ==="
python3 - "$OUT" <<'EOF'
import json, sys
from pathlib import Path
rows = []
for f in sorted(Path(sys.argv[1]).glob('*-*.json')):
    if f.name.endswith('.probe.json'):
        continue
    d = json.load(open(f))
    rows.append((d['model_id'], d['level'], d['token_count'],
                 d['compliance_pass_rate'], d['procedure_pass_rate'], d['recall_pass_rate']))
print(f"{'model':42} {'level':10} {'tok':>6} {'compl':>6} {'proc':>6} {'recall':>6}")
for r in rows:
    print(f"{r[0]:42} {r[1]:10} {r[2]:>6} {r[3]:>6} {r[4]:>6} {r[5]:>6}")
EOF
