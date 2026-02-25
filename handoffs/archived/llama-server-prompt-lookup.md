# Handoff: Implement Prompt Lookup in llama-server

## Status: COMPLETE - Merged to Production

**Experimental Branch:** `feature/server-prompt-lookup` in `/mnt/raid0/llm/llama.cpp-experimental/`
**Production Commit:** `8e35dbc01` on `production-consolidated` in `/mnt/raid0/llm/llama.cpp/`
**Implemented:** 2026-01-28 Session 9
**Tested & Merged:** 2026-01-28 Session 10

---

## Problem (Solved)

`--lookup-ngram-min` (prompt lookup decoding) was only available in `llama-cli`, not `llama-server`:
- llama-cli: 95 t/s with prompt lookup on summarization tasks (12.7x speedup)
- llama-server: 33 t/s with spec decode only

## Solution Implemented

Added n-gram prompt lookup as alternative/complementary draft source in llama-server. Spec decode is tried first (higher acceptance rate), lookup is used as fallback when draft model unavailable or insufficient.

### Files Modified (94 insertions, 9 deletions)

| File | Changes |
|------|---------|
| `common/common.h` | `bool lookup = false` in `common_params` |
| `common/arg.cpp` | `--lookup` CLI flag for SERVER + LOOKUP examples |
| `tools/server/server-task.h` | `bool lookup = false` in `task_params` |
| `tools/server/server-task.cpp` | JSON parsing (`"lookup": true`), serialization, defaults |
| `tools/server/server-context.cpp` | Ngram cache per slot, combined spec+lookup draft generation |

### Key Design Decisions

1. **Spec-first priority**: Try draft model first (higher acceptance) -> fall back to lookup -> shared verification
2. **Per-request toggle**: `"lookup": true` in request JSON; `--lookup` CLI flag sets default
3. **Context-only cache**: Built from prompt tokens, no `-lcs`/`-lcd` file I/O
4. **Incremental updates**: Cache updated after each accepted token batch
5. **Slot-isolated**: Each slot has own `common_ngram_cache`, cleared on `reset()`

### Bugs Found & Fixed During Testing

1. **Missing sampled token in ngram context**: `common_ngram_cache_draft` needs `slot.sampled` appended to `inp` so n-grams include the current token. Without this fix, acceptance was 0.4%.
2. **Wrong draft priority**: Original implementation tried lookup first, but lookup has much lower acceptance (13%) than spec decode (72-90%). Reversed to spec-first, lookup-fallback.

### Implementation Flow (server-context.cpp)

```
server_slot {
    common_ngram_cache ngram_cache_context;  // per-slot ngram cache
    bool lookup_enabled = false;
}

Task assignment -> set lookup_enabled from params
DONE_PROMPT -> GENERATING -> build ngram cache from prompt tokens
update_slots() draft generation:
    Step 1: common_speculative_gen_draft() -> draft tokens (if spec available)
    Step 2: common_ngram_cache_draft() -> draft tokens (if lookup_enabled && !draft_found)
    Step 3: Feed draft into i_batch_dft pipeline (shared, draft-source agnostic)
After acceptance -> common_ngram_cache_update() with new tokens
reset() -> ngram_cache_context.clear()
```

---

## Benchmark Results (Qwen2.5-Coder-32B-Q4_K_M, summarization prompt)

| Mode | Speed (t/s) | Acceptance | vs Baseline |
|------|------------|-----------|-------------|
| Baseline (no spec/lookup) | 7.28 | N/A | 1.0x |
| Lookup only (no draft model) | 10.75 | 13.2% | 1.48x |
| Spec only (0.5B draft) | 37.84 | 89.7% | 5.2x |
| **Combined (spec + lookup fallback)** | **39.44** | **83.2%** | **5.4x** |

### Concurrent Test
Two simultaneous requests with different prompts (AMD EPYC + Python). Both completed correctly with no cross-slot interference. Speeds: 18.8 t/s and 15.3 t/s respectively (shared resources).

### Note on 12.7x Claim
The 12.7x (95 t/s) figure from llama-cli uses `--lookup-ngram-min 3` with highly repetitive prompts (code editing with source material). Server lookup with summarization prompts shows more modest 1.48x standalone, but combines well with spec decode for a net 5.4x.

---

## Acceptance Criteria

1. [x] `--lookup` CLI flag enables prompt lookup in llama-server
2. [x] `"lookup": true` per-request parameter works
3. [x] Lookup + spec decode coexist (spec first, lookup fallback)
4. [x] Build succeeds on host (both experimental and production)
5. [x] Speedup verified: 5.4x combined, 1.48x lookup-only
6. [x] Concurrent requests don't interfere with each other's lookup tables
7. [x] Response includes draft stats (`timings.draft_n`, `timings.draft_n_accepted`)

## Remaining Work

- [x] Update `orchestrator_stack.py` to pass `--lookup` flag for port 8081 (coder_escalation/worker_summarize)
- [x] Update `orchestrator_stack.py` to pass `--lookup` flag for port 8082 (worker_explore)
- [x] Update `model_registry.yaml` with combined spec+lookup performance numbers
- [x] Update `launch_production.sh` speed claims
- [x] Update `CLAUDE.md` server topology
- [ ] Test with longer code-editing prompts (higher n-gram overlap expected)

## Created

2026-01-28 - Session 8 (identified problem)
2026-01-28 - Session 9 (implementation complete)
2026-01-28 - Session 10 (bugs fixed, tested, merged to production)
