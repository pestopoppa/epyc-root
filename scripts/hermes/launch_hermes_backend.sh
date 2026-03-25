#!/bin/bash
set -euo pipefail
# Launch llama-server for Hermes Agent frontend — standalone mode
# Port 8099: avoids conflict with orchestrator ports 8080-8095
#
# Model: Qwen3-Coder-30B-A3B-Instruct Q4_K_M (18.5GB, ~39 t/s)
# Usage: ./launch_hermes_backend.sh
# Stop:  kill $(cat /tmp/hermes-llama-server.pid)
#
# Phase 2: Stop this, start orchestrator on :8000, change ~/.hermes/config.yaml base_url

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
LLAMA_SERVER="/mnt/raid0/llm/llama.cpp/build/bin/llama-server"
CHAT_TEMPLATE="${SCRIPT_DIR}/chat-template-no-think.jinja"
HOST="127.0.0.1"
PORT=8099
THREADS=48
CONTEXT=32768
# Single slot: Hermes CLI is single-user, no need to split context.
# -np 2 would halve per-slot context (32K→16K) with no benefit.
# Delegation subagents queue — they don't need parallel slots.
SLOTS=1

if [[ ! -f "$MODEL" ]]; then
    echo "ERROR: Model not found at $MODEL"
    exit 1
fi

if [[ ! -x "$LLAMA_SERVER" ]]; then
    echo "ERROR: llama-server not found at $LLAMA_SERVER"
    exit 1
fi

# Check if port is already in use
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "WARNING: Port $PORT already in use. Kill existing process first."
    echo "  ss -tlnp | grep :${PORT}"
    exit 1
fi

echo "Starting llama-server on ${HOST}:${PORT}..."
echo "Model: $(basename "$MODEL")"
echo "Context: ${CONTEXT}, Slots: ${SLOTS}, Threads: ${THREADS}"

taskset -c 0-47,96-143 \
    "$LLAMA_SERVER" \
    -m "$MODEL" \
    --host "$HOST" --port "$PORT" \
    -t "$THREADS" -c "$CONTEXT" --jinja \
    --chat-template-file "$CHAT_TEMPLATE" \
    --override-kv qwen3moe.expert_used_count=int:4 \
    -np "$SLOTS" --mlock &

SERVER_PID=$!
echo "$SERVER_PID" > /tmp/hermes-llama-server.pid
echo "Server PID: $SERVER_PID (saved to /tmp/hermes-llama-server.pid)"

# Wait for server to be ready
echo -n "Waiting for server..."
for i in $(seq 1 30); do
    if curl -sf "http://${HOST}:${PORT}/health" > /dev/null 2>&1; then
        echo " ready!"
        echo ""
        echo "Hermes backend is live at http://${HOST}:${PORT}/v1"
        echo "Run 'hermes' or 'python /mnt/raid0/llm/hermes-agent/cli.py' to start chatting."
        wait "$SERVER_PID"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo " timeout!"
echo "Server may still be loading. Check: curl http://${HOST}:${PORT}/health"
wait "$SERVER_PID"
