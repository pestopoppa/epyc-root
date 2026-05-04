# Qwen3.6 Benchmark Fixes — Session Handoff

**Date**: 2026-05-02
**Status**: Partial — Qwen3.6 works, compiler optimization failed

## What Was Accomplished

### 1. Qwen3.6 model output fixed (VERIFIED WORKING)

**Problem**: Qwen3.6-35B-A3B and Qwen3.6-27B produced garbled output (TemplateName, TargetException, WidgetItem, etc.) on non-trivial prompts.

**Root causes found and fixed**:

1. **TIDE dynamic early exit unconditionally active** (commit `0a9e8e5bc`): The server decode loop activated layer reduction for ALL models after 5 warmup tokens with 3 consecutive >80% confidence tokens. Qwen3.6's qwen35moe builder doesn't wire `n_layer_exit` into its layer loop or recurrent state management, causing corrupted output.

   **Fix**: Gate `slot.tide_step = ...` on `params_base.n_layer_exit > 0` in `tools/server/server-context.cpp` (committed as `2ffbdbbba` on `production-consolidated-v5`).

2. **Unsloth Dynamic 2.0 quant replaced with bartowski**: The Unsloth Q8_0 quant produced identical garbage to bartowski on the broken binary, but after the TIDE fix, the garbage was confirmed to be a compute bug, not a quantization issue. Switched to bartowski `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` for broader llama.cpp compatibility.

3. **Registry fixes applied to all 3 Qwen3.6 entries** (`qwen36_q8_0`, `qwen36_27b_q8`, `qwen36_27b_q4km`):
   - Removed `chat_template: chatml` and `no_jinja: true` — embedded Jinja template works correctly
   - Set `use_chat_api: true`, `reasoning: auto`, `disable_thinking: true`
   - Added `env_vars:` with canonical OMP stack (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false`)
   - Updated paths to bartowski GGUF files

4. **YAML boolean bug fixed**: `reasoning: off` was parsed as boolean `False` by YAML 1.1 — `--reasoning off` never passed. Quoted all 7 entries as `"off"`. Fixed `if reasoning:` to `if reasoning is not None and reasoning is not False:` in executor.py.

5. **Server restart paths fixed**: 6 restart paths (MoE expert change, draft model change, crash recovery, etc.) lost all model-specific flags. Refactored to `_ServerState._start_server()` with cached `_model_flags` dict.

6. **`disable_thinking: true` added to all 3 Qwen3.6 entries + minimax**: Sends `chat_template_kwargs: {"enable_thinking": false}` in API requests — the Unsloth-recommended way to suppress thinking on Qwen3.6.

7. **All 9 models audited for launch flags**: None have model-specific binary overrides. All now have proper `use_chat_api`, `reasoning`, `kv_cache`, and `disable_thinking` settings. All have `env_vars:` with canonical OMP stack.

### 2. Benchmark infrastructure improvements

- `env_vars` support wired through `ServerManager.start()` → `subprocess.Popen` → `os.environ.copy()` merge
- Benchmark reads `model.env_vars` from registry, caches in `_model_flags`, passes through all restart paths

## What Failed

### Compiler optimization for throughput

**Goal**: Reproduce the ~58 t/s Coder-30B throughput from `data/cpu_optimization/2026-04-28-cpu11-pgo/decision.md`.

The April 28 PGO report documented:
```
| gcc + libgomp + no-march | 48.28 | reference |
| + -march=znver5          | 50.06 | +3.7% codegen |
| + libomp runtime          | 56.84 | +13.5% runtime |
| + PGO codegen             | 58.65 | +3.2% codegen |
```

Multiple attempts to reproduce these numbers failed:

1. **GCC build (baseline)**: Produced ~24 t/s on server mode (~28 t/s with OMP env vars)
2. **clang + libomp + znver5**: Linked against AMD AOCC libomp — ~23 t/s on llama-bench tg32
3. **clang + system libomp-20**: Forced `/lib/x86_64-linux-gnu/libomp.so.5` — ~24 t/s on llama-bench tg32
4. **clang + libomp + znver5 + PGO**: Profile from `llama.cpp-experimental/build_v5_pgo_gen/profraw/` (30 profraw files, 2.0 MB merged) — `llama.cpp` code differs from `llama.cpp-experimental`, causing `[-Wprofile-instr-unprofiled]` warnings. ~24 t/s.
5. **clang + libomp + znver5 + mtune**: Added `-mtune=znver5` — ~23 t/s.

None approached the documented 48+ t/s baseline.

### Unresolved questions

1. **Why is llama-bench tg32 showing 24 t/s when the report claims 48+?** The measurements were done on `llama.cpp-experimental` which had CPU optimization code paths present (CPU1 through CPU22, NUMA_WEIGHTS, etc.) that were env-gated but compiled in. The v5 consolidation stripped these. The report says they were "net-negative" or "no current effect" — but the 50% throughput gap suggests otherwise.

2. **LD_LIBRARY_PATH contamination**: `/opt/AMD/aocc-compiler-5.0.0/lib` appears in the system `LD_LIBRARY_PATH` and `ld.so.conf`, causing any binary linked against libomp to load the AMD AOCC runtime instead of clang-20's libomp. The AMD AOCC libomp may have different thread pinning behavior.

3. **The existing PGO binary** (`llama.cpp-experimental/build_v5_pgo_gen/bin/llama-server` at `0c8d05597`) is from an older codebase (April 28, b8941) and produces 2.4 t/s — likely incompatible with current GGUF files or hardware.

## Current State

### Binary
- **Path**: `/mnt/raid0/llm/llama.cpp/build/bin/llama-server`
- **Version**: 8957 (2ffbdbbba) — production-consolidated-v5 with TIDE fix
- **Compiler**: Clang 20.1.2, `-march=znver5 -mtune=znver5`, `-O3`, `-fopenmp=libomp`
- **OpenMP**: Links against `/opt/AMD/aocc-compiler-5.0.0/lib/libomp.so` (AMD AOCC)

### Registry
- All 9 models have correct `use_chat_api`, `reasoning`, `kv_cache`, `disable_thinking`
- All have `env_vars:` with canonical OMP stack
- Qwen3.6 paths point to bartowski GGUF files
- Qwen3.6-27B-Q4_K_M download still in progress (path exists but file may not be fully downloaded)

### Downloads
- ✅ Qwen3.6-35B-A3B Q8_0 (bartowski, 35 GB) — ready
- ✅ Qwen3.6-27B Q8_0 (bartowski, 27 GB) — ready
- ⏳ Qwen3.6-27B Q4_K_M (bartowski, ~16 GB) — downloading

### Benchmark
- Currently running with old binary (launched before compiler rebuilds)
- Needs kill and re-launch to pick up Clang + libomp binary
- Server mode shows ~28-30 t/s on Coder-30B; llama-bench tg32 shows ~24 t/s
- Expected based on reports: 48-58 t/s

## Next Steps for Another Agent

1. **Resolve the throughput gap**: The 50% difference between documented and actual throughput is the key open issue. Check if the CPU optimization strips (`GGML_RMS_NORM_PARALLEL`, `GGML_GDN_K_PER_HEAD`, `NUMA_WEIGHTS`, `CPU15`, etc.) were truly no-effect or if they removed performance-critical code paths. The progress reports claim "net-negative" and "no current effect" but the evidence contradicts.

2. **Fix LD_LIBRARY_PATH**: Remove `/opt/AMD/aocc-compiler-5.0.0/lib` from the builder session or use `LD_PRELOAD=/usr/lib/llvm-20/lib/libomp.so.5` to force the correct libomp.

3. **Rebuild with PGO on current codebase**: The existing profdata was collected on `llama.cpp-experimental` (different code). Re-run training with `-fprofile-instr-generate` on the current codebase, collect new .profraw files, merge, and rebuild with `-fprofile-instr-use`.

4. **Test with the canonical measurement recipe**: `taskset -c 0-95` + `OMP_PROC_BIND=spread OMP_PLACES=cores` + `numactl --interleave=all` — the benchmark already applies numactl but not taskset.

## Files Modified

- `orchestration/model_registry.yaml` — Qwen3.6 entries, env_vars, YAML boolean quoting
- `scripts/lib/executor.py` — `_build_env()`, `if reasoning:` fix, `env_vars` parameter
- `scripts/benchmark/run_benchmark.py` — `_model_flags` cache, `_start_server()`, read `env_vars`
- `tools/server/server-context.cpp` (llama.cpp) — TIDE gate fix

---

## 2026-05-04 update — most original problems resolved; one new variant found

### Resolved this session (May-2 → May-4)

1. **Throughput restored under canonical recipe**: After reboot + `taskset -c 0-95` wrapping in `executor.py` + LLVM-20 libomp override via LD_LIBRARY_PATH in `canonical_recipe.py`, Coder-30B-A3B Q4_K_M now hits **45-48 t/s** under standalone llama-bench + preflight. The original "28 t/s vs 48 t/s" gap was the multi-day uptime CPU-throttle hysteresis (per `feedback_host_throttle_check.md`).

2. **Canonical recipe single-source-of-truth**: New `scripts/lib/canonical_recipe.py` defines `CANONICAL_PREFIX = ["taskset", "-c", "0-95", "numactl", "--interleave=all"]`, `CANONICAL_OMP_ENV` stack, and LLVM-20 LD_LIBRARY_PATH override. All 3 cmd-construction sites in `executor.py` use it.

3. **Preflight gate `scripts/preflight_canonical.py`** runs 5 checks before any sweep: uptime warn / libomp resolution / canonical_cmd dry-run / tripwire bench (Coder-30B Q4_K_M tg128 r=2 ≥45 t/s) / freq sample mid-tripwire (≥80/96 cores >2.5 GHz). Auto-invoked by `run_benchmark.py`; bypass with `--skip-preflight`.

### NEW variant found 2026-05-04 evening — bimodal throughput

After ~6 hours of full-sweep benchmark activity, system entered a state where the SAME canonical recipe produces 29 t/s (60% of baseline) instead of 47 t/s. Ruled out: freq throttle, libomp, wrapping, subprocess invocation, page-cache fragmentation, THP fallback, NUMA imbalance. Reboot recommended (matches `feedback_host_throttle_check.md` reset behavior). Tracked as deferred work in `progress/2026-05/2026-05-04.md` § "Evening session" — instrument preflight on FAIL to capture full process state next time.

### Status: this handoff is now MOSTLY DONE

Original throughput gap: ✅ resolved.
Original AOCC libomp issue: ✅ overridden via LD_LIBRARY_PATH at recipe layer.
Original missing taskset: ✅ wrapped in canonical recipe.
PGO rebuild: deferred — not blocking; canonical recipe already at 45-48 t/s without PGO.

Recommend MOVE TO `handoffs/completed/` after the next session confirms post-reboot reproducibility (one more good bench run). Current open thread (bimodal regression) belongs in a fresh handoff if it reappears.
