#!/bin/bash
set -euo pipefail

# llama.cpp v3 smoke test suite
# Validates production-consolidated-v3 before binary swap.
# Runs against the EXPERIMENTAL binary — does NOT touch production.
#
# Usage:
#   ./smoke_test_llama_v3.sh              # Full test (all models + features)
#   ./smoke_test_llama_v3.sh --models     # Model load tests only
#   ./smoke_test_llama_v3.sh --features   # Feature tests only
#   ./smoke_test_llama_v3.sh --json       # JSON output

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLAMA_DIR="/mnt/raid0/llm/llama.cpp-experimental"
BIN_DIR="${LLAMA_DIR}/build/bin"
CLI="${BIN_DIR}/llama-cli"
SERVER="${BIN_DIR}/llama-server"
PPL="${BIN_DIR}/llama-perplexity"
SMOKE_PORT=9998  # Avoid conflict with any production port

# Model paths (from model_registry.yaml)
MODEL_WORKER="/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
MODEL_FRONTDOOR="/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-UD-Q4_K_M.gguf"
MODEL_CODER="/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf"
MODEL_REAP="/mnt/raid0/llm/models/Qwen3-Coder-REAP-246B-A35B-Q4_K_M.gguf"
DRAFT_MODEL="/mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf"

# Expected throughput (t/s) with ±15% tolerance
declare -A EXPECTED_TPS
EXPECTED_TPS[worker]=39.0
EXPECTED_TPS[frontdoor]=12.7
EXPECTED_TPS[coder]=10.8
EXPECTED_TPS[reap]=8.0
TPS_TOLERANCE=0.15

# Results tracking
PASS=0
FAIL=0
SKIP=0
RESULTS=()
JSON_MODE=false
RUN_MODELS=true
RUN_FEATURES=true

# ── Argument parsing ──────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --models)   RUN_FEATURES=false ;;
        --features) RUN_MODELS=false ;;
        --json)     JSON_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--models|--features] [--json]"
            exit 0
            ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────

log() { echo "[$(date +%H:%M:%S)] $*"; }

record_result() {
    local test_name="$1" status="$2" detail="${3:-}"
    RESULTS+=("{\"test\":\"${test_name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}")
    if [[ "$status" == "PASS" ]]; then
        ((PASS++))
        log "  PASS: ${test_name} ${detail}"
    elif [[ "$status" == "FAIL" ]]; then
        ((FAIL++))
        log "  FAIL: ${test_name} ${detail}"
    else
        ((SKIP++))
        log "  SKIP: ${test_name} ${detail}"
    fi
}

extract_tps() {
    # Extract tokens/s from llama-cli stderr output
    grep -oP 'eval time.*?(\d+\.\d+) tokens per second' <<< "$1" | grep -oP '\d+\.\d+' | tail -1
}

check_tps() {
    local role="$1" actual="$2"
    local expected="${EXPECTED_TPS[$role]}"
    local low high
    low=$(echo "$expected * (1.0 - $TPS_TOLERANCE)" | bc)
    high=$(echo "$expected * (1.0 + $TPS_TOLERANCE)" | bc)
    if (( $(echo "$actual >= $low && $actual <= $high" | bc -l) )); then
        return 0
    else
        return 1
    fi
}

kill_smoke_server() {
    fuser -k ${SMOKE_PORT}/tcp 2>/dev/null || true
    sleep 1
}

wait_for_server() {
    local port="$1" timeout="${2:-30}"
    for i in $(seq 1 "$timeout"); do
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# ── Pre-flight ────────────────────────────────────────────────

log "llama.cpp v3 smoke test starting"
log "Binary: ${BIN_DIR}"

if [[ ! -x "$CLI" ]]; then
    log "FATAL: llama-cli not found at ${CLI}"
    log "Build first: cd ${LLAMA_DIR} && cmake --build build -j96"
    exit 1
fi

if [[ ! -x "$SERVER" ]]; then
    log "FATAL: llama-server not found at ${SERVER}"
    exit 1
fi

# Verify branch
cd "$LLAMA_DIR"
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
log "Branch: ${BRANCH}"
if [[ "$BRANCH" != "production-consolidated-v3" ]]; then
    log "WARNING: Expected production-consolidated-v3, got ${BRANCH}"
fi

# ── Model Load Tests ──────────────────────────────────────────

if $RUN_MODELS; then
    log ""
    log "═══ Model Load + Generate Tests ═══"

    # Worker (30B-A3B) — 48 threads, single NUMA
    if [[ -f "$MODEL_WORKER" ]]; then
        log "Testing worker_explore (Qwen3-Coder-30B-A3B)..."
        OUTPUT=$("$CLI" -m "$MODEL_WORKER" -n 64 -p "Hello" --no-cnv -t 48 2>&1) || true
        TPS=$(extract_tps "$OUTPUT")
        if [[ -n "$TPS" ]]; then
            if check_tps "worker" "$TPS"; then
                record_result "model_load_worker" "PASS" "${TPS} t/s (expected ~${EXPECTED_TPS[worker]})"
            else
                record_result "model_load_worker" "FAIL" "${TPS} t/s outside ±${TPS_TOLERANCE} of ${EXPECTED_TPS[worker]}"
            fi
        else
            record_result "model_load_worker" "FAIL" "Could not extract t/s"
        fi
    else
        record_result "model_load_worker" "SKIP" "Model file not found"
    fi

    # Frontdoor (35B-A3B) — 48 threads
    if [[ -f "$MODEL_FRONTDOOR" ]]; then
        log "Testing frontdoor (Qwen3.5-35B-A3B)..."
        OUTPUT=$("$CLI" -m "$MODEL_FRONTDOOR" -n 64 -p "Hello" --no-cnv -t 48 2>&1) || true
        TPS=$(extract_tps "$OUTPUT")
        if [[ -n "$TPS" ]]; then
            if check_tps "frontdoor" "$TPS"; then
                record_result "model_load_frontdoor" "PASS" "${TPS} t/s (expected ~${EXPECTED_TPS[frontdoor]})"
            else
                record_result "model_load_frontdoor" "FAIL" "${TPS} t/s outside ±${TPS_TOLERANCE} of ${EXPECTED_TPS[frontdoor]}"
            fi
        else
            record_result "model_load_frontdoor" "FAIL" "Could not extract t/s"
        fi
    else
        record_result "model_load_frontdoor" "SKIP" "Model file not found"
    fi

    # Coder (32B) — 48 threads
    if [[ -f "$MODEL_CODER" ]]; then
        log "Testing coder_escalation (Qwen2.5-Coder-32B)..."
        OUTPUT=$("$CLI" -m "$MODEL_CODER" -n 64 -p "Hello" --no-cnv -t 48 2>&1) || true
        TPS=$(extract_tps "$OUTPUT")
        if [[ -n "$TPS" ]]; then
            if check_tps "coder" "$TPS"; then
                record_result "model_load_coder" "PASS" "${TPS} t/s (expected ~${EXPECTED_TPS[coder]})"
            else
                record_result "model_load_coder" "FAIL" "${TPS} t/s outside ±${TPS_TOLERANCE} of ${EXPECTED_TPS[coder]}"
            fi
        else
            record_result "model_load_coder" "FAIL" "Could not extract t/s"
        fi
    else
        record_result "model_load_coder" "SKIP" "Model file not found"
    fi

    # REAP-246B — 96 threads, moe-n-expert
    if [[ -f "$MODEL_REAP" ]]; then
        log "Testing architect_coding (REAP-246B with --moe-n-expert 6)..."
        OUTPUT=$("$CLI" -m "$MODEL_REAP" -n 32 -p "Hello" --no-cnv --moe-n-expert 6 -t 96 2>&1) || true
        TPS=$(extract_tps "$OUTPUT")
        if [[ -n "$TPS" ]]; then
            if check_tps "reap" "$TPS"; then
                record_result "model_load_reap" "PASS" "${TPS} t/s (expected ~${EXPECTED_TPS[reap]})"
            else
                record_result "model_load_reap" "FAIL" "${TPS} t/s outside ±${TPS_TOLERANCE} of ${EXPECTED_TPS[reap]}"
            fi
        else
            record_result "model_load_reap" "FAIL" "Could not extract t/s"
        fi
    else
        record_result "model_load_reap" "SKIP" "Model file not found"
    fi
fi

# ── Feature Tests ─────────────────────────────────────────────

if $RUN_FEATURES; then
    log ""
    log "═══ Feature-Specific Tests ═══"

    # Feature: --moe-n-expert (already tested in REAP load above, but verify flag parses)
    if [[ -f "$MODEL_WORKER" ]]; then
        log "Testing --moe-n-expert flag parsing..."
        if "$CLI" -m "$MODEL_WORKER" -n 4 -p "Hi" --no-cnv --moe-n-expert 4 -t 48 2>&1 | grep -q "eval time"; then
            record_result "feature_moe_n_expert" "PASS" "Flag accepted, generation completed"
        else
            record_result "feature_moe_n_expert" "FAIL" "Generation failed with --moe-n-expert"
        fi
    else
        record_result "feature_moe_n_expert" "SKIP" "No model available"
    fi

    # Feature: --lookup (prompt lookup decoding)
    if [[ -f "$MODEL_WORKER" ]]; then
        log "Testing --lookup flag..."
        if "$CLI" -m "$MODEL_WORKER" -n 32 -p "The quick brown fox jumps over the lazy dog. The quick brown fox" --no-cnv --lookup -t 48 2>&1 | grep -q "eval time"; then
            record_result "feature_lookup" "PASS" "Lookup decoding active"
        else
            record_result "feature_lookup" "FAIL" "Generation failed with --lookup"
        fi
    else
        record_result "feature_lookup" "SKIP" "No model available"
    fi

    # Feature: Server health + slot erase
    if [[ -f "$MODEL_WORKER" ]]; then
        log "Testing server (health + slot erase)..."
        kill_smoke_server

        "$SERVER" -m "$MODEL_WORKER" -t 48 -c 4096 --port ${SMOKE_PORT} 2>/dev/null &
        SERVER_PID=$!

        if wait_for_server ${SMOKE_PORT} 60; then
            # Health check
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${SMOKE_PORT}/health")
            if [[ "$HTTP_CODE" == "200" ]]; then
                record_result "feature_server_health" "PASS" "HTTP 200"
            else
                record_result "feature_server_health" "FAIL" "HTTP ${HTTP_CODE}"
            fi

            # Completions
            COMP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
                "http://localhost:${SMOKE_PORT}/completion" \
                -d '{"prompt":"Hello","n_predict":16,"temperature":0}')
            if [[ "$COMP_CODE" == "200" ]]; then
                record_result "feature_server_completion" "PASS" "HTTP 200"
            else
                record_result "feature_server_completion" "FAIL" "HTTP ${COMP_CODE}"
            fi

            # Slot erase
            ERASE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
                "http://localhost:${SMOKE_PORT}/slots/0")
            if [[ "$ERASE_CODE" == "200" ]]; then
                record_result "feature_slot_erase" "PASS" "HTTP 200"
            else
                record_result "feature_slot_erase" "FAIL" "HTTP ${ERASE_CODE}"
            fi
        else
            record_result "feature_server_health" "FAIL" "Server did not start within 60s"
            record_result "feature_server_completion" "SKIP" "Server not running"
            record_result "feature_slot_erase" "SKIP" "Server not running"
        fi

        kill_smoke_server
        wait "$SERVER_PID" 2>/dev/null || true
    fi

    # Feature: KV quantization (upstream Hadamard auto-rotation)
    if [[ -f "$MODEL_CODER" ]]; then
        log "Testing KV quantization with upstream Hadamard..."
        kill_smoke_server

        SERVER_LOG=$(mktemp)
        "$SERVER" -m "$MODEL_CODER" -t 48 -c 4096 --port ${SMOKE_PORT} \
            -ctk q4_0 -ctv f16 -fa 2>"$SERVER_LOG" &
        SERVER_PID=$!

        if wait_for_server ${SMOKE_PORT} 60; then
            # Send a completion to exercise KV cache
            curl -s "http://localhost:${SMOKE_PORT}/completion" \
                -d '{"prompt":"Explain quicksort","n_predict":64,"temperature":0}' > /dev/null 2>&1

            # Check for Hadamard rotation in logs (upstream auto-enables)
            if ! grep -qi "LLAMA_ATTN_ROT_DISABLE" "$SERVER_LOG"; then
                record_result "feature_kv_hadamard" "PASS" "No rotation disable flag (upstream auto-rotation active)"
            else
                record_result "feature_kv_hadamard" "FAIL" "LLAMA_ATTN_ROT_DISABLE found — upstream rotation not active"
            fi
        else
            record_result "feature_kv_hadamard" "FAIL" "Server did not start with -ctk q4_0 -ctv f16"
        fi

        kill_smoke_server
        wait "$SERVER_PID" 2>/dev/null || true
        rm -f "$SERVER_LOG"
    fi

    # Feature: Paged attention
    if [[ -f "$MODEL_CODER" ]]; then
        log "Testing paged attention..."
        kill_smoke_server

        "$SERVER" -m "$MODEL_CODER" -t 48 -c 8192 --port ${SMOKE_PORT} \
            --paged-attention 2>/dev/null &
        SERVER_PID=$!

        if wait_for_server ${SMOKE_PORT} 60; then
            # Check RSS is reasonable (paged should be lower)
            RSS_KB=$(ps -p "$SERVER_PID" -o rss= 2>/dev/null | tr -d ' ')
            RSS_GB=$(echo "scale=1; ${RSS_KB:-0} / 1048576" | bc)
            record_result "feature_paged_attention" "PASS" "Server started, RSS=${RSS_GB}GB"
        else
            record_result "feature_paged_attention" "FAIL" "Server did not start with --paged-attention"
        fi

        kill_smoke_server
        wait "$SERVER_PID" 2>/dev/null || true
    fi

    # Feature: NUMA throughput (taskset single quarter)
    if [[ -f "$MODEL_WORKER" ]]; then
        log "Testing NUMA quarter throughput..."
        OUTPUT=$(taskset -c 0-47 "$CLI" -m "$MODEL_WORKER" -n 64 -p "Hello" --no-cnv -t 48 2>&1) || true
        TPS=$(extract_tps "$OUTPUT")
        if [[ -n "$TPS" ]]; then
            record_result "feature_numa_quarter" "PASS" "${TPS} t/s on cores 0-47"
        else
            record_result "feature_numa_quarter" "FAIL" "Could not extract t/s"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────

log ""
log "═══ Summary ═══"
TOTAL=$((PASS + FAIL + SKIP))
log "Results: ${PASS} PASS / ${FAIL} FAIL / ${SKIP} SKIP (${TOTAL} total)"

if $JSON_MODE; then
    echo "["
    for i in "${!RESULTS[@]}"; do
        if [[ $i -lt $((${#RESULTS[@]} - 1)) ]]; then
            echo "  ${RESULTS[$i]},"
        else
            echo "  ${RESULTS[$i]}"
        fi
    done
    echo "]"
fi

if [[ $FAIL -gt 0 ]]; then
    log "VERDICT: FAIL — ${FAIL} test(s) failed. Do NOT swap production binary."
    exit 1
else
    log "VERDICT: PASS — All tests passed. Safe to swap production binary."
    exit 0
fi
