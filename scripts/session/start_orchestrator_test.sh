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

# =============================================================================
# PORT OBSERVATION (OBS-8, 2026-09-15)
# =============================================================================
# THE DEFECT: the port gate probed with `netstat` alone, piped through
# `2>/dev/null`. `netstat` is not installed on this host, so that pipe silently
# swallowed "command not found" as if it meant "no matches" — a MISSING TOOL
# read as an EMPTY PORT. The kill loop that used to sit here iterated zero
# times (nothing to parse), the availability check then printed
# "[✓] Ports 8000 and 8080 available" UNCONDITIONALLY, and the script launched
# a second llama-server and a second uvicorn on top of whatever was already
# listening. bus_supervisor.sh already names this file as the cautionary
# example of assuming a tool is installed.
#
# THREE STATES, matching scripts/coordination/observer_guard.sh's contract: a
# port probe that CANNOT RUN is not evidence the port is free.
#   free           - a real tool looked, and found no listener.
#   occupied       - a real tool looked, and found one.
#   cannot-observe - no port-inspection tool is on PATH. Refuse to launch: this
#                    script has no basis to claim anything about the port.
#
# The functions below are extracted so they can be SOURCED (by
# scripts/session/tests/test_start_orchestrator_test.sh) and driven against
# PATH shims — fake ss/netstat/lsof binaries in a tmp dir — without ever
# reaching the `main` launch logic further down. Nothing above the
# `main`/BASH_SOURCE guard at the bottom of this file may have a side effect:
# sourcing this file must be safe.

# osp_probe_tool - print the first available port-inspection tool (ss, then
# netstat, then lsof), or nothing if none is on PATH.
osp_probe_tool() {
  if command -v ss >/dev/null 2>&1; then printf 'ss\n'; return 0; fi
  if command -v netstat >/dev/null 2>&1; then printf 'netstat\n'; return 0; fi
  if command -v lsof >/dev/null 2>&1; then printf 'lsof\n'; return 0; fi
  return 0
}

# osp_port_pids <tool> <port> - print the pid(s) LISTENing on <port> per <tool>.
#
# READ-ONLY IDENTIFICATION ONLY. ***NOT A KILL TARGET.*** This host is shared;
# CLAUDE.md: "kill only PIDs you captured yourself" — a pid this run merely
# observed on a port is not a pid this run started, so this function's output
# is for the operator refusal message, never for a `kill` this script issues.
osp_port_pids() {
  local tool="$1" port="$2"
  case "$tool" in
    ss)
      ss -tlnp 2>/dev/null | awk -v p=":${port}\$" '$4 ~ p' | grep -oP 'pid=\K[0-9]+' | sort -u
      ;;
    netstat)
      netstat -tlnp 2>/dev/null | awk -v p=":${port}\$" \
        '$4 ~ p { split($7, a, "/"); if (a[1] ~ /^[0-9]+$/) print a[1] }' | sort -u
      ;;
    lsof)
      lsof -t -i "TCP:${port}" -sTCP:LISTEN 2>/dev/null | sort -u
      ;;
    *)
      return 1
      ;;
  esac
}

# osp_port_state <tool> <port> - echoes free|occupied. Caller must already have
# a non-empty <tool> (i.e. have handled cannot-observe) before calling this.
osp_port_state() {
  local tool="$1" port="$2" pids
  pids="$(osp_port_pids "$tool" "$port")"
  if [[ -n "$pids" ]]; then printf 'occupied\n'; else printf 'free\n'; fi
}

main() {
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

# Verify ports 8000 and 8080 are free — refuse otherwise
echo ""
echo "Checking ports 8000 and 8080..."
PORT_TOOL="$(osp_probe_tool)"
if [[ -z "$PORT_TOOL" ]]; then
  echo "ERROR: no port-inspection tool on PATH (checked: ss, netstat, lsof)."
  echo "This script CANNOT OBSERVE whether ports 8000/8080 are free, so it refuses"
  echo "to guess and launch a possible duplicate stack on top of a live one."
  echo "Install one of: ss (iproute2), netstat (net-tools), lsof — then re-run."
  exit 1
fi
echo "[i] Port probe tool: $PORT_TOOL"

OCCUPIED=()
for port in 8000 8080; do
  if [[ "$(osp_port_state "$PORT_TOOL" "$port")" == "occupied" ]]; then
    OCCUPIED+=("$port")
  fi
done

if (( ${#OCCUPIED[@]} > 0 )); then
  echo "ERROR: port(s) ${OCCUPIED[*]} already in use — refusing to launch."
  echo "This script no longer stops occupants on your behalf. Host rule (CLAUDE.md):"
  echo "\"kill only PIDs you captured yourself\" — a pid discovered on a port by THIS"
  echo "run is not a pid THIS run started, and this is a shared host (INC-20260731-"
  echo "broad-process-pattern-kills)."
  for port in "${OCCUPIED[@]}"; do
    echo "  Port $port held by:"
    while read -r pid; do
      [[ -n "$pid" ]] || continue
      echo "    pid $pid: $(ps -p "$pid" -o pid,etime,cmd --no-headers 2>/dev/null || echo '<already gone>')"
    done < <(osp_port_pids "$PORT_TOOL" "$port")
  done
  echo "Verify each pid is really what you think it is, then stop it yourself:"
  echo "  kill <pid>   # then confirm: ps -p <pid>  (escalate to -9 only if it ignores SIGTERM)"
  exit 1
fi
echo "[✓] Ports 8000 and 8080 available (verified with $PORT_TOOL)"

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
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
