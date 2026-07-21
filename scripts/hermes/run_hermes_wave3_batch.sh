#!/bin/bash
set -euo pipefail

# Batch wrapper for BULK-hermes-smokes.
# Starts the standalone Hermes llama-server only when it is not already live,
# runs the live smoke harness with the manifest-declared JSONL output, and
# cleans up only the backend process this wrapper started.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TARGET_TAG="${HERMES_WAVE3_TARGET_TAG:-v2026.4.23}"
OUT="${HERMES_SMOKE_OUT:-logs/hermes/hermes_wave3_smokes.jsonl}"
BACKEND_LOG="${HERMES_BACKEND_LOG:-logs/hermes/hermes_backend_8099.log}"
HEALTH_URL="${HERMES_HEALTH_URL:-http://127.0.0.1:8099/health}"

usage() {
    cat <<'EOF'
Usage: bash scripts/hermes/run_hermes_wave3_batch.sh [--target-tag TAG]

Runs the Hermes pin audit and live Wave-3 smoke legs for the inference-batch
loop. Environment overrides:
  HERMES_SMOKE_OUT       JSONL output path (default logs/hermes/hermes_wave3_smokes.jsonl)
  HERMES_BACKEND_LOG     backend launcher log path (default logs/hermes/hermes_backend_8099.log)
  HERMES_HEALTH_URL      backend health URL (default http://127.0.0.1:8099/health)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-tag)
            TARGET_TAG="${2:?--target-tag needs a value}"
            shift
            ;;
        --target-tag=*)
            TARGET_TAG="${1#*=}"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

cd "$ROOT"
mkdir -p "$(dirname "$OUT")" "$(dirname "$BACKEND_LOG")"
: >"$OUT"
: >"$BACKEND_LOG"

backend_started=0
launcher_pid=""
server_pid=""

pid_alive() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

terminate_pid() {
    local pid="$1" label="$2"
    [[ -n "$pid" ]] || return 0
    if ! pid_alive "$pid"; then
        return 0
    fi
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
        if ! pid_alive "$pid"; then
            return 0
        fi
        sleep 1
    done
    echo "WARN: ${label} pid ${pid} ignored TERM; sending KILL" >&2
    kill -9 "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
        if ! pid_alive "$pid"; then
            return 0
        fi
        sleep 1
    done
    echo "WARN: ${label} pid ${pid} still visible after KILL" >&2
    return 1
}

cleanup() {
    local rc=$?
    if [[ "$backend_started" == "1" ]]; then
        if [[ -f /tmp/hermes-llama-server.pid ]]; then
            server_pid="$(cat /tmp/hermes-llama-server.pid 2>/dev/null || true)"
        fi
        terminate_pid "$server_pid" "Hermes llama-server" || true
        terminate_pid "$launcher_pid" "Hermes launcher" || true
        rm -f /tmp/hermes-llama-server.pid
    fi
    exit "$rc"
}
trap cleanup EXIT

python3 scripts/hermes/hermes_pin_audit.py --target-tag "$TARGET_TAG"

if curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "Hermes backend already healthy at ${HEALTH_URL}; not starting a new one."
else
    echo "Starting Hermes backend via scripts/hermes/launch_hermes_backend.sh"
    bash scripts/hermes/launch_hermes_backend.sh >"$BACKEND_LOG" 2>&1 &
    launcher_pid=$!
    backend_started=1

    for _ in $(seq 1 180); do
        if curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
            echo "Hermes backend healthy at ${HEALTH_URL}"
            break
        fi
        if ! pid_alive "$launcher_pid"; then
            echo "ERROR: Hermes backend launcher exited before health check passed" >&2
            tail -n 80 "$BACKEND_LOG" >&2 || true
            exit 1
        fi
        sleep 2
    done

    if ! curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        echo "ERROR: Hermes backend did not become healthy at ${HEALTH_URL}" >&2
        tail -n 80 "$BACKEND_LOG" >&2 || true
        exit 1
    fi
fi

HERMES_SMOKE_OUT="$OUT" HERMES_SMOKE_LIVE=1 \
    bash scripts/hermes/run_hermes_smokes.sh \
        --target-tag "$TARGET_TAG" \
        --chat --tooluse --streaming --override --multiturn --reference-client --subagent
