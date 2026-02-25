# Bug Report: Architect Inference Hangs — Slot Idle but Client Blocked

**Date**: 2026-02-20 15:45
**Reporter**: Claude (investigating session)
**Severity**: High — blocks 3-way eval for minutes per occurrence
**Affected Roles**: architect_general (8083), architect_coding (8084)

## Symptom

During `seed_specialist_routing.py --3way` eval, architect inference requests hang for 4+ minutes. The TUI shows:

```
ROLE=architect_coding
PROMPT: [...]
RESPONSE:
(empty — no tokens streaming)
```

The log panel shows: `still waiting for ARCHITECT (241s elapsed, 26 tokens so far)` — no progress for 120+ seconds.

## Key Findings

### 1. The llama-server slot is NOT stuck — it already finished

```bash
curl -s http://localhost:8084/slots | python3 -m json.tool
```
Returns:
```json
{
  "id": 0,
  "is_processing": false,    // NOT processing
  "id_task": 258,
  "next_token": [{
    "has_next_token": false,  // generation halted
    "n_remain": 166,          // 166 tokens remaining (of n_predict=192)
    "n_decoded": 26           // only 26 decoded
  }]
}
```

The server generated 26 tokens, then stopped. The slot is idle. But the Python client is still blocked waiting for more data.

### 2. Completion requests work fine

```bash
curl -s -X POST http://localhost:8084/completion -d '{"prompt":"hello","n_predict":1}' -H "Content-Type: application/json"
# Returns immediately with 200 OK
```

The server's main loop is operational. It can process new tasks. Only the existing streaming HTTP response to the architect inference request is "orphaned."

### 3. Slot erase via curl hangs due to missing Content-Length

```bash
# HANGS (no Content-Length header → server waits for body):
curl -s -X POST "http://localhost:8084/slots/0?action=erase"

# WORKS:
curl -s -X POST -H "Content-Length: 0" "http://localhost:8084/slots/0?action=erase"
wget -q -O- --post-data='' "http://localhost:8084/slots/0?action=erase"
```

The llama-server HTTP parser blocks reading body when `Content-Length` is missing on POST. Not a bug in our patch — this is a general server behavior. Our Python `httpx.post()` sends `Content-Length: 0` by default, so `_erase_port_slots()` should work correctly.

### 4. The erase endpoint works but there's nothing to erase

When erase succeeds, it returns `{"id_slot":0,"n_erased":0}` — the slot was already idle with 0 cached tokens (cleared after previous erase). The problem isn't that erase fails — it's that the **original streaming HTTP response** is stuck.

### 5. TCP connection state

During the hang:
```
ESTAB 127.0.0.1:8084 → 127.0.0.1:42310  (llama-server)
ESTAB 127.0.0.1:42310 → 127.0.0.1:8084  (python/uvicorn)
```

The TCP connection between the Python client and the server was still established. The server-side socket was idle. Eventually the connection closed (Python timeout), leaving only the erase attempt's connection.

### 6. Server log shows 200 OK for erase but doesn't log the stuck inference

```
srv  log_server_r: request: POST /slots/0 127.0.0.1 200
srv  update_slots: all slots are idle
```

No error log for the original inference that stopped at 26 tokens. The server's `slot release` log at task 860 is for our test completion, not the original stuck request.

### 7. Inference tap records the section but no response content

The tap file contains:
```
[2026-02-20 15:33:19] ROLE=architect_coding
PROMPT: [...]
RESPONSE:
(empty)
```

The tap's `write_chunk` callback was never called — the streaming backend never delivered any chunks to the Python client. Yet the server decoded 26 tokens. This means either:
- The SSE stream was established but tokens were never flushed to the HTTP response, OR
- The SSE connection was never established and a non-streaming path was used (where the response is written all-at-once after completion), OR
- The streaming connection broke silently (server-side write failed, Python-side read never noticed)

## Root Cause Analysis (Confirmed)

### Server-Side: Slot erase force-releases without sending final result

**File:** `llama.cpp/tools/server/server-context.cpp:1858-1887`

The `SERVER_TASK_TYPE_SLOT_ERASE` handler at line 1872-1874:
```cpp
if (slot->is_processing()) {
    SLT_WRN(*slot, "force-releasing processing slot for erase, id_task = %d\n", task.id);
    slot->release();    // <-- sets IDLE, nulls task, but sends NO result
}
```

`slot->release()` (line 348) sets the slot to IDLE and nulls the task pointer, but **does NOT call `send_final_response()`**. The HTTP streaming handler for the original request is still blocking in `rd.next()`, waiting for results that will never arrive. Since `should_stop()` only returns true when the TCP connection closes (client timeout), the handler blocks for the full client timeout duration (600s original, 120s with fix).

**Trigger chain:**
1. Request A starts inference on architect_coding (port 8084)
2. A competing request B times out on the inference lock
3. Lock timeout calls `_erase_port_slots(8084)` (src/inference_lock.py:378)
4. Erase handler force-releases the slot — no final result sent
5. Request A's HTTP handler blocks forever in `rd.next()`
6. Python httpx client blocks in `response.iter_lines()` until read timeout

This explains why 0 chunks were received (erase can happen during prompt eval) and why the slot shows `is_processing: false` while the client is stuck.

**The `send()` function in server-queue.cpp:304-317 also silently drops results if task IDs are missing from `waiting_task_ids` — no logging, no error. This is a separate resilience issue.**

### Client-Side: Read timeout matched overall request timeout (FIXED)

`infer_stream_text()` used `read=overall_timeout` (up to 600s). Fixed to `read=min(overall_timeout, 120)` with graceful `ReadTimeout` recovery.

### Original hypotheses revisited

- **Primary (SSE broken/stuck)**: Partially correct — SSE stream IS broken, but by slot erase, not by stop condition handling
- **Secondary (lock timeout masks issue)**: **CONFIRMED** — the lock timeout's slot erase IS the direct cause
- **Tertiary (read timeout misconfigured)**: **CONFIRMED** — 600s read timeout made the stall catastrophically long

## Reproduction Steps

1. Start orchestrator stack: `orchestrator_stack.py start --hot-only`
2. Run 3-way eval: `python seed_specialist_routing.py --tui --3way --continuous --evolve --debug`
3. Wait for a question that delegates to architect_coding (typically competitive programming / USACO)
4. Observe the TUI — if the architect section shows RESPONSE: with no content for 30+ seconds while the log shows "still waiting for ARCHITECT", it's this bug

## Investigation Commands

```bash
# Check slot state (is_processing should be true during active inference)
curl -s http://localhost:8084/slots | python3 -m json.tool

# Check if streaming is actually being used (look for "stream" in tap)
grep -A5 'ROLE=architect' /mnt/raid0/llm/tmp/inference_tap.log | tail -20

# Check CachingBackend streaming path
# The decision is in inference.py: can_stream = tap_enabled && hasattr(backend, "infer_stream_text") && should_stream_role(role)
# For architect roles, should_stream_role returns True (HEAVY_STREAM_ROLES is empty)

# Check server-side SSE events (if server has debug logging)
tail -f /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8084.log

# Check Python-side streaming read timeout
grep -n 'stream\|timeout\|read_timeout' src/backends/llama_server.py

# Check if the stop condition at 26 tokens was a stop sequence or EOS
# Look for stop_type in the slot's next_token data
```

## Suggested Next Steps

### Server-side fix (llama.cpp patch)

**File:** `llama.cpp/tools/server/server-context.cpp`, `SERVER_TASK_TYPE_SLOT_ERASE` handler (~line 1872)

Before calling `slot->release()`, send an error result to the original task's HTTP handler:

```cpp
if (slot->is_processing()) {
    SLT_WRN(*slot, "force-releasing processing slot for erase, id_task = %d\n", task.id);
    // Send error to the original request's HTTP handler so it doesn't block forever
    if (slot->task) {
        auto err = std::make_unique<server_task_result_error>();
        err->id = slot->task->id;
        err->index = slot->task->index;
        err->error = format_error_response("Slot erased while processing", ERROR_TYPE_SERVER);
        queue_results.send(std::move(err));
    }
    slot->release();
}
```

This unblocks the HTTP handler's `rd.next()` call, which receives an error result, sets `output` to the error JSON, and returns `false` to terminate the stream. The Python client then receives the error and can handle it.

### Also: add logging to `send()` for silent drops

**File:** `llama.cpp/tools/server/server-queue.cpp:304-317`

The `send()` function silently drops results when the task ID isn't in `waiting_task_ids`. Add a warning log:

```cpp
void server_response::send(server_task_result_ptr && result) {
    // ... existing code ...
    }
    // Task ID not found in waiting list — result silently dropped
    RES_DBG("WARNING: result for task id = %d dropped (not in waiting list)\n", result->id);
}
```

## Files to Investigate

| File | What to Check |
|------|---------------|
| `llama.cpp/tools/server/server-context.cpp:1858-1887` | **ROOT CAUSE** — slot erase releases without sending result |
| `llama.cpp/tools/server/server-queue.cpp:304-317` | `send()` silently drops unmatched results |
| `src/backends/llama_server.py` | `infer_stream_text()` — streaming read loop, timeout handling |
| `src/inference_lock.py:368-381` | Lock timeout triggers `_erase_port_slots()` |
| `src/llm_primitives/inference.py:414` | `_call_caching_backend` — streaming path selection and chunk callback |

## Fix Applied

**Root cause**: `infer_stream_text()` in `src/backends/llama_server.py` used the overall request timeout (up to 600s) as the httpx `read` timeout. When the server's SSE stream stalled (slot finished without sending `[DONE]`), `response.iter_lines()` blocked for the full 600s. The client had no way to detect the stall.

**Fix** (commit pending):
1. **Per-read timeout cap**: `read=min(overall_timeout, 120)` — prompt eval for even 480B models completes within 120s. If no SSE data arrives within 120s, the stream is dead.
2. **Graceful `ReadTimeout` recovery**: New `except httpx.ReadTimeout` handler before the generic `TimeoutException`. If partial chunks were received, returns them as `success=True` with `completion_reason="read_timeout_partial"`. If no chunks received (prompt eval timeout), returns `success=False`.
3. **`chunks` scoping fix**: Moved `chunks` list initialization outside the `with` block so the `ReadTimeout` handler can always access it.

**File**: `src/backends/llama_server.py` — `infer_stream_text()` method.

**Additional finding**: `curl -X POST` without `-d ''` or `-H "Content-Length: 0"` hangs against llama-server because the HTTP parser waits for a body. Python's `httpx.post()` sends `Content-Length: 0` by default so this doesn't affect production code, but manual testing with curl requires the explicit header.

## Environment

- llama-server: production-consolidated branch (patched 2026-02-20 14:27)
- Model: Qwen3-Coder-480B-A35B-Instruct Q4_K_M, 8192 ctx, 1 slot, spec decode K=16
- Draft: Qwen3-Coder-Instruct-DRAFT-0.75B-32k Q4_0
- Server launched with: `-np 1 -c 8192 -t 96 --flash-attn on --cache-type-k q8_0 --draft-max 16`
