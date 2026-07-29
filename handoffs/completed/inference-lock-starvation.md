# Inference Lock Starvation — Bug Report

**Status**: COMPLETE — PrefixRouter slot mismatch, fix applied and validated 40/40 OK (6 workers)
**Created**: 2026-03-04
**Updated**: 2026-03-05
**Priority**: HIGH — blocks reliable seeding and all REPL-dependent validation
**Source**: Validation sweep Item 3 (session log seeding run)

## Symptoms

1. **Lock held after request completion**: REPL pipeline's exclusive lock on `/mnt/raid0/llm/tmp/heavy_model.lock` is not released when the client-side HTTP request times out. The uvicorn worker holds the lock indefinitely until the server-side coroutine finishes or is killed.

2. **Lock starvation in seeding**: ~40% of requests hang with 0 tokens generated, holding the inference lock for the full timeout duration.

3. **Cascading failures**: Once the lock is stuck, all subsequent requests queue behind it, hit the exclusive lock timeout, and fail with infrastructure errors.

## Root Cause — CONFIRMED (2026-03-05)

**The PrefixRouter assigns `id_slot` values (2, 3) that exceed llama-server's actual slot count (`-np 2`, slots 0-1).** When llama-server receives `id_slot=2` or `id_slot=3`, it waits indefinitely for those non-existent slots to become available, never returning HTTP response headers.

### How it happens

1. `LLMPrimitives` default `num_slots=4` (hardcoded in `primitives.py:67`)
2. `PrefixRouter(num_slots=4)` creates virtual slots 0-3
3. Sequential requests fill slots: Q1→slot 0, Q2→slot 1, Q3→slot 2, Q4→slot 3
4. llama-server (`-np 2`) only has slots 0 and 1
5. Requests with `id_slot=2` or `id_slot=3` hang: the server accepts the TCP connection and HTTP request but blocks internally waiting for the requested slot
6. httpx blocks in `_receive_response_headers()` — no headers are ever sent back
7. The inference lock is held throughout, blocking all subsequent requests

### Definitive evidence

**Orchestrator log with slot diagnostics** — perfectly periodic 2-OK, 2-HANG pattern:
```
Q1:  id_slot=0 → headers received in 106ms → OK (4.2s, 277 tok)
Q2:  id_slot=1 → headers received in 46ms  → OK (2.0s, 343 tok)
Q3:  id_slot=2 → NO headers received       → Lock held 59.1s → 504 timeout
Q4:  id_slot=3 → NO headers received       → Lock held 59.0s → 504 timeout
Q5:  id_slot=0 → headers received in 68ms  → OK (22.6s, 707 tok)
Q6:  id_slot=1 → headers received in 51ms  → OK (27.1s, 1241 tok)
Q7:  id_slot=2 → NO headers received       → Lock held 59.0s → 504 timeout
Q8:  id_slot=3 → NO headers received       → Lock held 59.0s → 504 timeout
Q9:  id_slot=0 → headers received in 69ms  → OK (31.6s, 949 tok)
Q10: id_slot=1 → headers received in 57ms  → OK (25.9s, 1181 tok)
```

The pattern repeats with 100% consistency: slots 0,1 succeed, slots 2,3 hang.

### Isolation testing methodology (2026-03-05)

Extensive isolation tests ruled out all other hypotheses before identifying the slot mismatch:

| Test | Hypothesis tested | Result | Conclusion |
|------|-------------------|--------|------------|
| A1: Direct batch to llama-server | Server batch hang | 20/20 OK | Not server batch bug |
| A2: Direct streaming to llama-server | Server streaming hang | 20/20 OK | Not server streaming bug |
| C: Direct with keep-alive persistent client | Connection reuse | 20/20 OK | Not keep-alive bug |
| D: Direct with large prompts + keep-alive | Large payload | 20/20 OK | Not payload size |
| E1-E5: Client leak, slot routing, GC patterns | httpx.Client lifecycle | 50/50 OK | Not client management |
| F1-F5: asyncio.to_thread + flock + per-request client | Threading/lock interaction | 50/50 OK | Not asyncio/flock bug |
| H1-H5: Exact orchestrator payload (direct) | Payload content/params | 25/25 OK | Not payload-specific |
| G1-G3: Through orchestrator (1 worker) | Multi-worker contention | Reproduce 40% hang | Not multiprocessing |
| G4: Ephemeral httpx.Client per stream | Shared client state | Reproduce 40% hang | Not shared client |
| B1-B4: Keep-alive disabled | Connection pool | Reproduce 40% hang | Not keep-alive |

**Key breakthrough**: Adding `id_slot` logging to the streaming path revealed the slot mismatch pattern.

### Previous hypothesis (superseded)

~~llama-server completes inference but never sends the HTTP response.~~ This was a red herring. The server never starts processing because it's waiting for a non-existent slot. The TCP connection is established and headers are never sent — the symptoms look identical to a server-side response delivery bug, but the cause is purely client-side (bad slot ID in request).

## Fix Applied (2026-03-05)

### Primary fix: Correct slot count

Changed `num_slots` default from 4 to 2 across all configuration layers:

1. **`src/config/__init__.py`** line 130: `ServerSettings.num_slots: int = 4` → `2`
2. **`src/config/__init__.py`** line 421: `_env_int("ORCHESTRATOR_SERVER_NUM_SLOTS", 4)` → `2`
3. **`src/config/models.py`** line 154: `ServerConfigData.num_slots: int = 4` → `2`
4. **`src/llm_primitives/primitives.py`** line 67: `LLMPrimitives.__init__(num_slots=4)` → `2`
5. **`src/api/routes/chat_pipeline/routing.py`** line 235: Now explicitly passes `num_slots=get_config().server.num_slots` to `LLMPrimitives`

### Mitigations (retained as defense-in-depth)

These were developed before the root cause was found. They remain useful as safety nets:

1. **Lock hold watchdog** (`inference_lock.py`): Daemon thread force-releases flock after `ORCHESTRATOR_MAX_LOCK_HOLD_S` (default 130s).
2. **Streaming fallback for all paths** (`inference.py`): Non-tap inference now uses `infer_stream_text` — per-chunk cancel check can abort on client disconnect.
3. **Cancel check in streaming** (`inference.py`): `_on_chunk_guarded()` checks `get_request_cancel_check()` on every chunk.
4. **Tighter httpx timeouts** (`llama_server.py`): Explicit `httpx.Timeout(read=min(overall, 120), pool=30)`.
5. **Dead code removal** (`primitives.py`): Removed `llm_call_stream()` (generator-in-lock anti-pattern).

Unit tests: 7/7 pass including two new watchdog tests.

### Cleanup (completed after validation)

- Reverted ephemeral `httpx.Client` per streaming call → back to `self.client.stream()`
- Reverted WARNING-level diagnostic logs → INFO-level with `id_slot` retained for ongoing monitoring
- Re-enabled keep-alive connections (`max_keepalive_connections=10`) — root cause was slot mismatch, not connection reuse

## Verification Results (2026-03-05)

### Test G7: 60s timeout, 10 questions
- **Result**: 9/10 OK, 1 timeout (Q3: 18700 chars / 84.8s generation, exceeds 60s test timeout)
- All slot assignments confirmed in range 0-1
- Baseline (pre-fix): 6/10 OK with periodic 2-OK, 2-HANG pattern

### Test G8: 120s timeout, 10 questions — PASS
- **Result**: 10/10 OK, 0 hangs
- Q3 completed in 84.8s (previously timed out at 60s — legitimate long generation, not a hang)
- Average OK elapsed: 22.9s
- All slot assignments confirmed in range 0-1

### Test G9: 40-question stress test, 6 workers — PASS
- **Result**: 40/40 OK, 0 hangs
- Average OK elapsed: 15.0s
- Full production config (6 uvicorn workers, `-np 2` frontdoor)
- Previously this would fail at ~question 3 with cascading lock starvation

**Fix fully validated under production conditions.**

## Remaining Risk

The config environment variable `ORCHESTRATOR_SERVER_NUM_SLOTS` must match the llama-server `-np` value. If servers are started with different slot counts, the mismatch will recur. Consider:
1. Auto-detecting slot count via `GET /slots` on startup
2. Per-role `num_slots` config (frontdoor has `-np 2`, others have `-np 1`)

## Resolution

Fix complete. All next steps executed:
1. Restarted orchestrator with 6 workers — healthy
2. 40-question stress test — 40/40 OK, 0 hangs
3. Progress file updated (`progress/2026-03/2026-03-05.md`)
