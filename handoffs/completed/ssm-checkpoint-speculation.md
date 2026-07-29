# SSM State Checkpointing for Speculative Decoding

**Status**: CONDITIONAL GO — Benchmark complete, works for code tasks
**Created**: 2026-03-03
**Priority**: MEDIUM
**Workstream**: WS1 (independent — does not block WS2/WS3)
**Branch**: `llama.cpp-experimental` (based on `origin/master` at `137435ff1`)

## Goal

Enable speculative decoding for hybrid SSM+Attention models (e.g., Qwen3.5-35B-A3B) by checkpointing recurrent state before speculation and restoring on rejection.

**Blocker**: Current llama.cpp can't do speculation with SSM models because rejected draft tokens corrupt the recurrent state — `seq_rm` on recurrent memory fails for partial ranges. The root cause is in `common_speculative_is_compat()` which tests `seq_rm(mem, 0, 1, -1)` — this partial removal is inherently invalid for recurrent state.

## Implementation Summary (DONE)

8 files modified, +312 lines. All changes on `llama.cpp-experimental` branch.

### 1. Checkpoint/Restore Core (`llama-memory-recurrent.h/cpp`)
- `llama_memory_recurrent_checkpoint` struct: holds cell metadata + raw tensor data (CPU-side `std::vector<uint8_t>` per layer)
- `checkpoint()`: saves cell pos/src/src0/tail/seq_id + `ggml_backend_tensor_get()` for all r_l/s_l tensors
- `restore()`: restores all metadata + `ggml_backend_tensor_set()` for tensor data

### 2. Hybrid Memory Integration (`llama-memory-hybrid.h/cpp`)
- `checkpoint_recurrent()`/`restore_recurrent()` delegate to recurrent sub-memory
- **Critical change**: `seq_rm()` no longer bails early when recurrent partial removal fails — KV cache cleanup proceeds regardless, allowing the caller to handle recurrent state via checkpoint/restore

### 3. C API (`llama.h`, `llama-context.cpp`)
- `llama_memory_has_recurrent()` — queries if memory supports checkpointing
- `llama_memory_checkpoint_save/restore/free()` — opaque handle API
- Internal: `dynamic_cast` to detect `llama_memory_hybrid` or `llama_memory_recurrent`

### 4. Speculation Compat Fix (`common/speculative.cpp`)
- `common_speculative_is_compat()`: when partial `seq_rm` fails but `llama_memory_has_recurrent()` is true, allows speculation instead of rejecting

### 5. Server Integration (`tools/server/server-context.cpp`)
- `spec_checkpoint` member on `server_slot`
- Before speculation batch: saves checkpoint via `llama_memory_checkpoint_save()`
- On partial rejection: restores checkpoint, does `seq_rm` (KV cache only), then re-decodes accepted tokens via small `llama_decode()` batch
- On full acceptance: no restore needed (state already correct)
- Checkpoint freed after each speculation round; also cleaned up in `reset()` and `destroy()`

## Build & Test Status

- **Build**: Succeeds (`cmake -DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON`, 96 threads)
- **Model loads**: Qwen3.5-35B-A3B detected as hybrid (30 recurrent + 10 attention layers, 62.81 MiB RS buffer)
- **Baseline generation**: 9.5 t/s (llama-cli), 5.0-6.6 t/s (server single slot)
- **Draft model loads**: Qwen3.5-0.8B-Q8_0 (24 layers, 19.27 MiB RS buffer)
- **Spec init**: "speculative decoding context initialized" confirmed in logs

### Open Issue — RESOLVED
- Draft stats were always working — fields are `timings.draft_n` and `timings.draft_n_accepted` in JSON response (not top-level). Previous session was looking at wrong JSON path.

## Feasibility Numbers (Qwen3.5-35B-A3B)

| Metric | Value |
|--------|-------|
| Total layers | 40 |
| Recurrent layers | 30 (75%) |
| Attention layers | 10 (25%) |
| **RS buffer size** | **62.81 MiB** (measured) |
| R state | 2.81 MiB |
| S state | 60.00 MiB |
| Checkpoint time (memcpy @ 30 GB/s) | ~2.2 ms |
| Restore time | ~2.2 ms |

## Go/No-Go Gate — CONDITIONAL GO

### Benchmark Results (Qwen3.5-35B-A3B + Qwen3.5-0.8B-Q8_0 draft, --draft-max 8)

| Task | Baseline | Spec Decode | Accept% | Speedup |
|------|----------|-------------|---------|---------|
| Summarize (256 tok) | 6.6 t/s | 5.9 t/s | 51.9% | 0.89x |
| Code (256 tok) | 7.8 t/s | 12.2 t/s | 92.0% | **1.56x** |
| Edit (128 tok) | 7.3 t/s | 7.4 t/s | 69.0% | 1.01x |

### Assessment
- **Acceptance rate >30%**: PASS (all 3 tests: 51.9%, 92.0%, 69.0%)
- **Output correctness**: PASS (temperature=0, deterministic, matches baseline)
- **>1.2x speedup**: PASS for code (1.56x), FAIL for general text (0.89x–1.01x)
- **Verdict**: CONDITIONAL GO — enable spec decode for code generation tasks only
- **Recommendation**: Cherry-pick into WS2 (`production-consolidated-v2`), but configure as opt-in for code/REPL roles

## Resume Commands

```bash
cd /mnt/raid0/llm/llama.cpp
git checkout llama.cpp-experimental  # branch already exists

# Build (already done, but if needed)
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON
cmake --build build -j96

# Check all modified files
git diff --stat HEAD

# Test server with spec decode
./build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-UD-Q4_K_M.gguf \
  -md /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf \
  -t 96 -c 4096 --port 9999 --draft-max 8 -np 1

# Debug: check if draft tokens are generated (look for "draft" in verbose output)
# Key investigation: why draft_n_accepted shows N/A in response JSON
```

## Closeout

- [x] Implementation complete on `llama.cpp-experimental` branch
- [x] Build succeeds, model loads, baseline generation works
- [x] **Debug draft token generation** — resolved (stats in `timings.draft_n/draft_n_accepted`)
- [x] Preliminary benchmark run — CONDITIONAL GO (1.56x for code, neutral for text)
- [ ] Update research docs (Chapter 07 SSM warning section)
- [x] Update `logs/agent_audit.log`
- [x] Update `progress/2026-03/2026-03-03.md`
- [x] Move to completed (conditional Go — cherry-pick into WS2 for code roles)
