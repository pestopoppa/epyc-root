# Handoff: Orchestrator Live Testing & Debugging

**Created:** 2026-01-14
**Updated:** 2026-01-28
**Priority:** High
**Status:** **STACK FIXED** - Use `launch_production.sh` for deterministic startup

---

## 🚀 QUICK START (2026-01-28 FIX)

The orchestrator stack has been fixed. All model paths validated, 41 tools initialized at startup.

```bash
# Launch full production stack (~510GB, 45% RAM)
./scripts/server/launch_production.sh --full

# Or minimal for testing (~45GB)
./scripts/server/launch_production.sh --minimal

# Check status
./scripts/server/launch_production.sh --status

# Stop all
./scripts/server/launch_production.sh --stop
```

**What was fixed:**
- `WORKER_POOL_MODELS` paths corrected to use existing files
- Added `EXPLORE_DRAFT_MODEL` for spec decode on worker_explore (46 t/s)
- Removed redundant `worker_code` (8092) - all code routes to 32B coder (faster)
- Added architects to HOT tier (510GB = 45% of 1130GB RAM)
- Added startup validation (`validate_model_paths()`) to fail fast
- Added `init_memrl_and_tools()` for 41 deterministic tools

---

## ⛔ CRITICAL MEMORY GUARDRAILS ⛔

**READ THIS BEFORE DOING ANYTHING**

### Hard Limits

1. **NEVER run `pytest -n auto`** - Will spawn ~192 workers and crash the machine
2. **NEVER enable `real_mode=True` without llama-server running** - Will try to load 0.5B TaskEmbedder
3. **Check memory before each major operation:**
   ```bash
   free -h | head -2
   # Must have > 100GB free before any model loading
   ```
4. **If memory goes below 100GB free, STOP and clean up:**
   ```bash
   pkill -9 -f "llama-server"
   pkill -9 -f "uvicorn"
   ```

### Safe Operations

| Operation | RAM Impact | Safe? |
|-----------|-----------|-------|
| `uvicorn src.api:app` (mock_mode) | ~500MB | ✅ Yes |
| `llama-server` with 0.5B model | ~2GB | ✅ Yes |
| `llama-server` with 7B model | ~8GB | ✅ Yes |
| `pytest tests/ -n 4` | ~2GB | ✅ Yes |
| `real_mode=True` API call | +1GB (TaskEmbedder) | ⚠️ Only with llama-server |
| `pytest -n auto` | ~200GB+ | ❌ NEVER |

---

## Objective

Get the orchestrator stack working end-to-end:
1. llama-server running on correct ports
2. Orchestrator API responding to requests
3. Real-mode inference working
4. Escalation behavior verified

---

## Current State

### What's Working (Verified 2026-01-14)

| Component | Status | Test Command |
|-----------|--------|--------------|
| Orchestrator API | ✅ Running on port 8000 | `curl http://localhost:8000/health` |
| Mock mode chat | ✅ Works | `curl -X POST http://localhost:8000/chat -d '{"prompt":"test","mock_mode":true}'` |
| Gates endpoint | ✅ Works | `curl -X POST http://localhost:8000/gates -d '{"gate_names":["schema"]}'` |
| OpenAI-compat endpoint | ✅ Works | `curl -X POST http://localhost:8000/v1/chat/completions -d '{"model":"frontdoor","messages":[{"role":"user","content":"test"}]}'` |
| Role routing | ✅ Works | Different roles (frontdoor/coder/worker) return distinct responses |
| Unit tests | ✅ 459 tests pass | `uv run pytest tests/unit/ -v` |
| FailureRouter | ✅ Works | 51 tests pass, escalation chains verified |
| Progress logging | ✅ Works | Fallback to /workspace/logs/ in devcontainer |

### What Needs Debugging (Production Env Only)

| Component | Status | Issue |
|-----------|--------|-------|
| llama-server startup | ⬜ Not in devcontainer | Requires `/mnt/raid0/` mount and llama.cpp binary |
| Real-mode inference | ⬜ Not in devcontainer | Requires llama-server + models |
| Live escalation | ⬜ Not in devcontainer | Requires real-mode with errors |

**Note:** These can only be tested on the production Beelzebub system with RAID mount.

---

## 🚀 PRODUCTION TESTING GUIDE (Copy-Paste Ready)

**Run these commands on Beelzebub with `/mnt/raid0/` mounted.**

### Phase 1: Environment Setup

```bash
# 1. Verify RAID is mounted
ls /mnt/raid0/llm/models/*.gguf | head -5
# Should list model files

# 2. Set environment variables
export HF_HOME=/mnt/raid0/llm/cache/huggingface
export TRANSFORMERS_CACHE=/mnt/raid0/llm/cache/huggingface
export TMPDIR=/mnt/raid0/llm/tmp
export XDG_CACHE_HOME=/mnt/raid0/llm/claude/cache

# 3. Check memory (need >100GB free)
free -h | head -2

# 4. Kill any stale processes
pkill -9 -f "llama-server" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
sleep 5

# 5. Verify ports are free
netstat -tlnp 2>/dev/null | grep -E "8000|8080" && echo "PORTS IN USE - wait or kill" || echo "Ports free ✓"
```

### Phase 2: Start llama-server (Frontdoor Model)

```bash
# Use small model for testing (0.5B = ~1GB RAM)
cd /mnt/raid0/llm

# Check the model exists
ls -lh models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf

# Start llama-server
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 4096 \
  --parallel 2 \
  --threads 8 \
  > /tmp/llama-server-8080.log 2>&1 &

# Wait for startup (watch the log)
sleep 10
tail -20 /tmp/llama-server-8080.log

# Verify it's running
curl -s http://localhost:8080/health
# Expected: {"status":"ok"}
```

**If port 8080 fails to bind:**
```bash
# Check what's using the port
netstat -tlnp | grep 8080

# Wait for TIME_WAIT to clear
sleep 60

# Or use alternate port
--port 8085
```

### Phase 3: Start Orchestrator API

```bash
cd /mnt/raid0/llm/claude

# Activate environment
source /path/to/pace-env/bin/activate  # or use uv

# Start orchestrator
python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000 > /tmp/orchestrator.log 2>&1 &

# Wait and verify
sleep 5
curl -s http://localhost:8000/health
# Expected: {"status":"ok","models_loaded":0,"mock_mode_available":true,"version":"0.1.0"}
```

### Phase 4: Test Real-Mode Inference

```bash
# Check memory before enabling real mode
free -h | head -2

# Test real-mode chat (will load TaskEmbedder ~1GB)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is 2+2? Answer briefly.",
    "real_mode": true,
    "role": "frontdoor",
    "max_turns": 1
  }'

# Expected: actual LLM response, not [MOCK]

# Check memory after
free -h | head -2
```

### Phase 5: Test Role Routing (Real Mode)

```bash
# Test frontdoor role
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "frontdoor",
    "messages": [{"role": "user", "content": "Hello, who are you?"}],
    "max_tokens": 100
  }'

# Test with different roles (requires those servers running)
# For now, all roles route to port 8080 unless you start more servers
```

### Phase 6: Test Escalation Behavior

To trigger escalation, you need an error. Options:

**Option A: Simulate error via invalid prompt**
```bash
# Send prompt that might cause parsing error
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "```python\nimport sys; sys.exit(1)\n```\nExecute this code.",
    "real_mode": true,
    "role": "worker",
    "max_turns": 3
  }'
# Watch logs for escalation: worker -> coder_primary
```

**Option B: Programmatic test**
```python
# Run in Python REPL
import requests

# First request as worker
resp = requests.post("http://localhost:8000/chat", json={
    "prompt": "Write code with a syntax error",
    "real_mode": True,
    "role": "worker",
    "max_turns": 5
})
print(resp.json())

# Check if escalation occurred in logs
```

**Option C: Direct FailureRouter test**
```python
from src.failure_router import FailureRouter, FailureContext, ErrorCategory

router = FailureRouter()
context = FailureContext(
    role="worker",
    failure_count=2,  # Exhausted retries
    error_category=ErrorCategory.CODE,
    error_message="SyntaxError in generated code"
)
decision = router.route_failure(context)
print(f"Action: {decision.action}, Next: {decision.next_role}")
# Expected: Action: escalate, Next: coder_primary
```

### Phase 7: Multi-Server Setup (Full Stack)

For complete testing with multiple models:

```bash
# Terminal 1: Frontdoor (0.5B)
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf \
  --host 0.0.0.0 --port 8080 --ctx-size 4096 --parallel 2 --threads 8

# Terminal 2: Coder (32B with speculative decoding)
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-Coder-32B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8081 --ctx-size 8192 --parallel 2 --threads 48

# Terminal 3: Worker (7B)
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8082 --ctx-size 4096 --parallel 4 --threads 24

# Check all servers
for port in 8080 8081 8082; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health || echo "DOWN"
done
```

### Monitoring Commands

```bash
# Watch memory usage
watch -n 5 'free -h | head -2'

# Watch orchestrator log
tail -f /tmp/orchestrator.log

# Watch llama-server log
tail -f /tmp/llama-server-8080.log

# Check all processes
ps aux | grep -E "llama-server|uvicorn" | grep -v grep

# GPU/CPU usage (if nvidia-smi available)
watch -n 1 nvidia-smi  # For GPU
htop  # For CPU
```

### Cleanup Commands

```bash
# Graceful shutdown
pkill -f "uvicorn"
pkill -f "llama-server"

# Force kill if needed
pkill -9 -f "uvicorn"
pkill -9 -f "llama-server"

# Clear memory
sync && echo 3 > /proc/sys/vm/drop_caches  # Requires sudo

# Verify cleanup
free -h
netstat -tlnp | grep -E "8000|808"
```

### Expected Results Checklist

| Test | Expected Result | Actual |
|------|-----------------|--------|
| `curl localhost:8080/health` | `{"status":"ok"}` | ⬜ |
| `curl localhost:8000/health` | `{"status":"ok",...}` | ⬜ |
| Real-mode chat | Actual LLM response (not [MOCK]) | ⬜ |
| Role routing | Different responses per role | ⬜ |
| Escalation trigger | worker → coder_primary on failure | ⬜ |
| Memory stable | <50GB used during testing | ⬜ |
| No crashes | All processes stay running | ⬜ |

### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Port binding fails | Socket in TIME_WAIT | Wait 60s or use different port |
| "Model not found" | Wrong path | Check `ls /mnt/raid0/llm/models/` |
| OOM crash | Model too large | Use smaller model or kill other processes |
| Slow responses | Too few threads | Increase `--threads` |
| Empty responses | Context too small | Increase `--ctx-size` |
| "Connection refused" | Server not started | Check `ps aux \| grep llama` |
| TaskEmbedder load fail | No real_mode server | Start llama-server first |

### Quick-Start Script (All-in-One)

**Script created:** `scripts/session/start_orchestrator_test.sh`

```bash
# On Beelzebub:
cd /mnt/raid0/llm/claude
./scripts/session/start_orchestrator_test.sh --dev-mode  # 0.5B model
./scripts/session/start_orchestrator_test.sh             # Production model
```

Full script contents (or copy to `/mnt/raid0/llm/claude/scripts/start_orchestrator_test.sh`):

```bash
#!/bin/bash
set -euo pipefail

echo "=== Orchestrator Test Stack Startup ==="

# Check RAID
if [[ ! -d /mnt/raid0/llm/models ]]; then
    echo "ERROR: /mnt/raid0/llm/models not found. Is RAID mounted?"
    exit 1
fi

# Check memory
FREE_GB=$(free -g | awk '/^Mem:/{print $4}')
if [[ $FREE_GB -lt 100 ]]; then
    echo "WARNING: Only ${FREE_GB}GB free. Recommend >100GB."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Kill existing
echo "Killing existing processes..."
pkill -9 -f "llama-server" 2>/dev/null || true
pkill -9 -f "uvicorn.*src.api" 2>/dev/null || true
sleep 3

# Set environment
export HF_HOME=/mnt/raid0/llm/cache/huggingface
export TMPDIR=/mnt/raid0/llm/tmp
export XDG_CACHE_HOME=/mnt/raid0/llm/claude/cache

# Start llama-server
echo "Starting llama-server on :8080..."
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf \
  --host 0.0.0.0 --port 8080 --ctx-size 4096 --parallel 2 --threads 8 \
  > /tmp/llama-server-8080.log 2>&1 &
LLAMA_PID=$!
echo "  PID: $LLAMA_PID"

# Wait for llama-server
echo "Waiting for llama-server..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "  llama-server ready ✓"
        break
    fi
    sleep 1
done

# Check if llama-server started
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "ERROR: llama-server failed to start. Check /tmp/llama-server-8080.log"
    tail -20 /tmp/llama-server-8080.log
    exit 1
fi

# Start orchestrator
echo "Starting orchestrator API on :8000..."
cd /mnt/raid0/llm/claude
python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000 > /tmp/orchestrator.log 2>&1 &
ORCH_PID=$!
echo "  PID: $ORCH_PID"

# Wait for orchestrator
sleep 5
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: Orchestrator failed to start. Check /tmp/orchestrator.log"
    tail -20 /tmp/orchestrator.log
    exit 1
fi
echo "  Orchestrator ready ✓"

# Summary
echo ""
echo "=== Stack Running ==="
echo "llama-server: http://localhost:8080 (PID $LLAMA_PID)"
echo "orchestrator: http://localhost:8000 (PID $ORCH_PID)"
echo ""
echo "Logs:"
echo "  tail -f /tmp/llama-server-8080.log"
echo "  tail -f /tmp/orchestrator.log"
echo ""
echo "Test commands:"
echo "  curl http://localhost:8000/health"
echo "  curl -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{\"prompt\":\"Hello\",\"real_mode\":true}'"
echo ""
echo "To stop: pkill -f 'llama-server|uvicorn'"
```

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Request statistics |
| POST | `/stats/reset` | Reset statistics |
| POST | `/chat` | Chat endpoint (main) |
| POST | `/chat/stream` | Streaming chat |
| GET | `/gates` | List available gates |
| POST | `/gates` | Run validation gates |
| GET | `/v1/models` | List models (OpenAI-compat) |
| POST | `/v1/chat/completions` | Chat completions (OpenAI-compat) |
| GET | `/sessions` | List sessions |
| POST | `/sessions/{id}/resume` | Resume session |

### `/chat` Request Body

```json
{
  "prompt": "Your question here",
  "role": "frontdoor",           // frontdoor|coder|worker|architect
  "mock_mode": false,            // true = no LLM call
  "real_mode": true,             // true = use llama-server
  "max_turns": 5,                // Max REPL iterations
  "context": "Optional context",
  "server_urls": {               // Override server URLs
    "frontdoor": "http://localhost:8080"
  }
}
```

### `/chat` Response

```json
{
  "answer": "LLM response...",
  "turns": 1,
  "tokens_used": 150,
  "elapsed_seconds": 2.5,
  "mock_mode": false,
  "real_mode": true,
  "cache_stats": {...}
}
```

### `/v1/chat/completions` (OpenAI-Compatible)

```json
{
  "model": "frontdoor",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 100,
  "temperature": 0.7
}
```

### `/gates` Request

```json
{
  "gate_names": ["schema", "format", "lint"],
  "artifact_path": "/path/to/file.json"
}
```

### Error Responses

```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "escalation": {
    "from_role": "worker",
    "to_role": "coder_primary",
    "reason": "Max retries exceeded"
  }
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator API                         │
│                   (uvicorn src.api:app)                     │
│                      Port: 8000                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │ Mock Mode   │   │ Real Mode   │   │ Gates       │      │
│   │ (default)   │   │ (llama-srv) │   │ (validators)│      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │
│                            │                                │
│                            ▼                                │
│                     ┌─────────────┐                         │
│                     │ LLMPrimitives│                        │
│                     │ CachingBackend│                       │
│                     └─────────────┘                         │
│                            │                                │
│                            ▼                                │
│   ┌─────────────────────────────────────────────────────┐  │
│   │               llama-server instances                │  │
│   │  Port 8080: frontdoor    Port 8081: coder          │  │
│   │  Port 8082: worker       (per model_registry.yaml) │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                     Escalation Path                         │
│                                                             │
│   Error → _classify_error() → FailureRouter.route_failure() │
│                                      │                      │
│                            ┌─────────┴─────────┐            │
│                            ▼                   ▼            │
│                        "retry"             "escalate"       │
│                            │                   │            │
│                            ▼                   ▼            │
│                     Same role            worker → coder     │
│                                          coder → architect  │
└─────────────────────────────────────────────────────────────┘
```

---

## Debugging Methodology

### Step 1: Verify Orchestrator API (DONE)

```bash
# Check if already running
curl http://localhost:8000/health

# If not running:
cd /mnt/raid0/llm/claude
python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000 &
sleep 3
curl http://localhost:8000/health
```

**Expected:** `{"status": "ok", "mock_mode_available": true, ...}`

### Step 2: Start llama-server

The model registry specifies servers on ports 8080-8082. For testing, start ONE small model:

```bash
# Check memory first!
free -h

# Kill any existing servers
pkill -9 -f "llama-server" 2>/dev/null

# Wait for ports to clear
sleep 2

# Start with a small model (0.5B = ~1GB RAM)
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 4096 \
  --parallel 2 \
  --threads 8 \
  > /tmp/llama-server.log 2>&1 &

# Wait for startup
sleep 10

# Verify
curl http://localhost:8080/health
```

**Known Issue:** Port 8080 binding sometimes fails. Try:
1. Wait longer (socket may be in TIME_WAIT)
2. Use different port (8085, 8090)
3. Check `netstat -tlnp | grep 808`

### Step 3: Test Real-Mode Chat

Once llama-server is running:

```bash
# Check memory before enabling real mode
free -h

# Test real-mode (will load TaskEmbedder ~1GB)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is 2+2?",
    "real_mode": true,
    "server_urls": {"frontdoor": "http://localhost:8080"}
  }'
```

### Step 4: Test Escalation

Escalation requires:
1. Real-mode enabled
2. An error to trigger escalation
3. FailureRouter to decide on escalation

To trigger escalation manually, you'd need an error in REPL execution. One way:
- Send a prompt that causes the model to generate invalid Python
- The REPL will fail to execute it
- FailureRouter should escalate

---

## File Locations

| File | Purpose |
|------|---------|
| `src/api.py` | Main orchestrator API |
| `src/failure_router.py` | Escalation logic |
| `src/llm_primitives.py` | LLM call abstraction |
| `orchestration/model_registry.yaml` | Server ports, model paths |
| `/tmp/orchestrator.log` | Orchestrator API log |
| `/tmp/llama-server.log` | llama-server log |

---

## llama.cpp Branch

**MUST USE:** `production-consolidated` branch

```bash
cd /mnt/raid0/llm/llama.cpp
git checkout production-consolidated
```

**Includes all optimizations:**
- Parallel tensor repack (fast model loading)
- CPU paged attention (+76% gen speed on 70B+)
- MoE expert override (`--moe-n-expert`)
- Layer skip / early exit for speculative decoding
- SWA cell reuse fixes
- Lookahead crash fixes

---

## Model Registry Server Config

From `orchestration/model_registry.yaml`:

```yaml
server_mode:
  frontdoor:
    url: http://localhost:8080
    slots: 4
    model_role: frontdoor
  coder:
    url: http://localhost:8081
    slots: 4
    model_role: coder_primary
  worker:
    url: http://localhost:8082
    slots: 8
    model_role: worker_general
  dev:
    frontdoor:
      url: http://localhost:8080
      slots: 4
      model: Qwen2.5-Coder-0.5B-Q8_0.gguf
```

---

## Test Models (Small, Safe)

| Model | Path | Size | Good For |
|-------|------|------|----------|
| Qwen2.5-0.5B | `/mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf` | ~1GB | Dev testing |
| Llama-3.2-1B | `/mnt/raid0/llm/models/Llama-3.2-1B-Instruct-f16.gguf` | ~2.5GB | Dev testing |

---

## Success Criteria

1. ✅ `curl http://localhost:8000/health` returns OK
2. ⬜ `curl http://localhost:8080/health` returns OK (llama-server) - **Requires production env**
3. ⬜ Real-mode chat completes without crash - **Requires production env**
4. ⬜ Memory stays under 50GB during testing - **Requires production env**
5. ⬜ Escalation path triggers on error - **Requires production env**

---

## Devcontainer Testing Results (2026-01-14)

### Mock Mode - All Verified Working

| Endpoint | Status | Evidence |
|----------|--------|----------|
| `/health` | ✅ PASS | Returns `{"status":"ok","mock_mode_available":true}` |
| `/chat` (mock) | ✅ PASS | Returns `[MOCK] Processed prompt: ...` |
| `/gates` | ✅ PASS | Schema validation passes |
| `/v1/chat/completions` | ✅ PASS | OpenAI-format response |
| Role routing | ✅ PASS | frontdoor/coder/worker return distinct responses |

### Unit Tests

| Test Suite | Result | Notes |
|------------|--------|-------|
| test_failure_router.py | ✅ 51/51 pass | Escalation chains work |
| test_llm_primitives.py | ✅ 31/31 pass | Mock mode, logging, stats |
| test_api.py | ✅ 21/21 pass | (excluding gates timeout) |
| test_generation_monitor.py | ✅ All pass | (after role fix) |
| All unit tests | ✅ 459 pass | 4.56s execution |

### Bug Fixed: Role Name Mismatch

**Issue:** `test_early_abort_routing` expected `next_role == "coder"` but got `"coder_primary"`

**Root Cause:** FailureRouter now correctly translates generic chain names to specific role names via `CHAIN_TO_ROLE` mapping.

**Fix:** Updated test to expect `"coder_primary"` (the correct specific role name)

### Devcontainer Limitations

Cannot test in devcontainer:
- Real-mode inference (no RAID mount, no models)
- llama-server startup (no binary)
- Live escalation behavior (requires real LLM)

### Code Fix Applied

`orchestration/repl_memory/progress_logger.py`: Added fallback path for devcontainer environment:
```python
# Use RAID path if available, otherwise fallback to workspace
DEFAULT_LOG_PATH = _RAID_LOG_PATH if _RAID_LOG_PATH.parent.exists() else _WORKSPACE_LOG_PATH
```

---

## Recovery Commands

If things go wrong:

```bash
# Kill everything
pkill -9 -f "uvicorn"
pkill -9 -f "llama-server"

# Check memory
free -h

# Clear any stuck sockets
sleep 30  # Wait for TIME_WAIT to expire

# Restart from scratch
cd /mnt/raid0/llm/claude
python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000 &
```

---

## What Was Built (Context)

Recent work completed:

1. **RLM Phase 2 Enhancements**
   - Forced exploration validation
   - Async `llm_batch_async()`
   - Recursion depth limiting
   - Per-query cost tracking

2. **RLM Phase 3 Escalation Integration**
   - `_classify_error()` function
   - FailureRouter wired into Root LM loop
   - Role switching on escalation
   - Escalation prompts

3. **MemRL Integration**
   - Lazy loading (TaskEmbedder only loads on real_mode)
   - Progress logging
   - Q-scoring integration

4. **Role Mapping Fix**
   - `ROLE_TO_CHAIN` and `CHAIN_TO_ROLE` maps
   - Specific role names (worker_general) ↔ generic chains (worker)

---

## Do NOT Do

1. ❌ `pytest -n auto` (crashes machine)
2. ❌ Load multiple large models simultaneously
3. ❌ Enable real_mode without checking memory first
4. ❌ Run long benchmarks without monitoring RAM
