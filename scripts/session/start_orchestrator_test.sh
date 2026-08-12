#!/bin/bash
# Orchestrator Test Stack Startup Script
# Usage: ./start_orchestrator_test.sh [--dev-mode]
#
# Run this on Beelzebub with /mnt/raid0/ mounted.
# Creates a minimal test stack with 0.5B model for development.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source environment library for path variables
# shellcheck source=../lib/env.sh
source "${SCRIPT_DIR}/../lib/env.sh"

DEV_MODE=false
if [[ "${1:-}" == "--dev-mode" ]]; then
  DEV_MODE=true
fi

echo "=== Orchestrator Test Stack Startup ==="
echo "Mode: $([ "$DEV_MODE" = true ] && echo 'Development (0.5B model)' || echo 'Production')"
echo ""

# Check RAID
if [[ ! -d "${MODELS_DIR}" ]]; then
  echo "ERROR: ${MODELS_DIR} not found."
  echo "Is this the Beelzebub host with RAID mounted?"
  exit 1
fi
echo "[✓] RAID mounted"

# Check llama.cpp binary
LLAMA_SERVER="${LLAMA_CPP_BIN}/llama-server"
if [[ ! -x "$LLAMA_SERVER" ]]; then
  echo "ERROR: llama-server not found at $LLAMA_SERVER"
  echo "Build llama.cpp first: cd ${LLM_ROOT}/llama.cpp && make -j"
  exit 1
fi
echo "[✓] llama-server binary found"

# Check memory
FREE_GB=$(free -g | awk '/^Mem:/{print $4}')
echo "[i] Free memory: ${FREE_GB}GB"
if [[ $FREE_GB -lt 100 ]]; then
  echo "WARNING: Only ${FREE_GB}GB free. Recommend >100GB for safety."
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Select model
if [ "$DEV_MODE" = true ]; then
  MODEL_PATH="${MODELS_DIR}/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf"
  THREADS=8
  PARALLEL=2
  CTX_SIZE=4096
else
  MODEL_PATH="${MODELS_DIR}/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
  THREADS=48
  PARALLEL=4
  CTX_SIZE=8192
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "ERROR: Model not found: $MODEL_PATH"
  echo "Available models:"
  ls -lh "${MODELS_DIR}"/*.gguf | head -10
  exit 1
fi
echo "[✓] Model found: $(basename $MODEL_PATH)"

# Kill existing processes
echo ""
echo "Stopping existing processes..."
# Resolve what to stop by LISTENING PORT, never by name pattern.
#
# This host is shared. `pkill -f "llama-server"` is a wildcard over every session's
# processes, not just this script's — it killed another agent's server twice
# (INC-20260731, docs/reference/agent-config/INCIDENT_LOG.md). A port is a precise
# identity: only one process can hold it, and it is the one actually in our way.
for port in 8000 8080; do
  for pid in $(netstat -tlnp 2>/dev/null | awk -v p=":${port}\$" '$4 ~ p { split($7, a, "/"); if (a[1] ~ /^[0-9]+$/) print a[1] }' | sort -u); do
    echo "  Port $port held by PID $pid — stopping it"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do ps -p "$pid" >/dev/null 2>&1 || break; sleep 1; done
    if ps -p "$pid" >/dev/null 2>&1; then
      echo "  PID $pid ignored SIGTERM; escalating to SIGKILL"
      kill -9 "$pid" 2>/dev/null || true
      sleep 1
    fi
    if ps -p "$pid" >/dev/null 2>&1; then
      echo "ERROR: PID $pid is still alive after SIGKILL — refusing to continue"
      exit 1
    fi
    echo "  PID $pid confirmed stopped"
  done
done
sleep 1

# Check ports
for port in 8000 8080; do
  if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
    echo "ERROR: Port $port still in use after cleanup"
    netstat -tlnp 2>/dev/null | grep ":$port "
    echo "Wait 60s for TIME_WAIT or kill the process manually"
    exit 1
  fi
done
echo "[✓] Ports 8000 and 8080 available"

# Set environment (already sourced from env.sh, but export for subprocesses)
export HF_HOME="${CACHE_DIR}/huggingface"
export TRANSFORMERS_CACHE="${CACHE_DIR}/huggingface"
export TMPDIR="${TMP_DIR}"
export XDG_CACHE_HOME="${PROJECT_ROOT}/cache"

# Ensure directories exist
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"

# Start llama-server
echo ""
echo "Starting llama-server..."
echo "  Model: $(basename $MODEL_PATH)"
echo "  Port: 8080"
echo "  Threads: $THREADS"
echo "  Context: $CTX_SIZE"

$LLAMA_SERVER \
  --model "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size $CTX_SIZE \
  --parallel $PARALLEL \
  --threads $THREADS \
  >/tmp/llama-server-8080.log 2>&1 &
LLAMA_PID=$!
echo "  PID: $LLAMA_PID"

# Wait for llama-server to be ready
echo "  Waiting for startup..."
for i in {1..60}; do
  if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo "  [✓] llama-server ready"
    break
  fi
  if ! kill -0 $LLAMA_PID 2>/dev/null; then
    echo "  [✗] llama-server crashed!"
    tail -30 /tmp/llama-server-8080.log
    exit 1
  fi
  sleep 1
done

if ! curl -s http://localhost:8080/health >/dev/null 2>&1; then
  echo "  [✗] llama-server failed to start (timeout)"
  tail -30 /tmp/llama-server-8080.log
  exit 1
fi

# Start orchestrator API
echo ""
echo "Starting orchestrator API..."
cd "${PROJECT_ROOT}"

# Try to activate pace-env if it exists
if [[ -f "${LLM_ROOT}/pace-env/bin/activate" ]]; then
  source "${LLM_ROOT}/pace-env/bin/activate"
fi

python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000 >/tmp/orchestrator.log 2>&1 &
ORCH_PID=$!
echo "  PID: $ORCH_PID"

# Wait for orchestrator
echo "  Waiting for startup..."
sleep 5
for i in {1..30}; do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "  [✓] Orchestrator ready"
    break
  fi
  if ! kill -0 $ORCH_PID 2>/dev/null; then
    echo "  [✗] Orchestrator crashed!"
    tail -30 /tmp/orchestrator.log
    exit 1
  fi
  sleep 1
done

if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
  echo "  [✗] Orchestrator failed to start"
  tail -30 /tmp/orchestrator.log
  exit 1
fi

# Final status
echo ""
echo "=========================================="
echo "         STACK READY"
echo "=========================================="
echo ""
echo "Services:"
echo "  llama-server: http://localhost:8080 (PID $LLAMA_PID)"
echo "  orchestrator: http://localhost:8000 (PID $ORCH_PID)"
echo ""
echo "Logs:"
echo "  tail -f /tmp/llama-server-8080.log"
echo "  tail -f /tmp/orchestrator.log"
echo ""
echo "Test commands:"
echo ""
echo "  # Health check"
echo "  curl http://localhost:8000/health"
echo ""
echo "  # Mock mode (no LLM)"
echo "  curl -X POST http://localhost:8000/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\":\"Hello\",\"mock_mode\":true}'"
echo ""
echo "  # Real mode (uses llama-server)"
echo "  curl -X POST http://localhost:8000/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\":\"What is 2+2?\",\"real_mode\":true}'"
echo ""
echo "  # OpenAI-compatible"
echo "  curl -X POST http://localhost:8000/v1/chat/completions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\":\"frontdoor\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo ""
echo "To stop:"
# The stop ADVICE must not teach the command the stop CODE was fixed to remove.
# Until 2026-08-12 this printed a name-pattern kill over llama-server|uvicorn, so an
# operator following the script's own closing output ran, by hand, exactly the
# wildcard INC-20260731 is about — laundered as official instructions. The executed
# commands and the recommended one had different universes, and the recommended one
# is arguably worse: a human runs it deliberately, on a shared host, at the moment a
# stack is being torn down. This script CAPTURES both pids (LLAMA_PID, ORCH_PID), so
# the compliant form was available the whole time.
echo "  kill $LLAMA_PID $ORCH_PID     # the pids this run started"
echo "  ps -p $LLAMA_PID -p $ORCH_PID  # confirm they are gone; escalate to -9 only if not"
echo ""
echo "Memory usage:"
free -h | head -2
