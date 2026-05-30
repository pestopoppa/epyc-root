# Bug: `llama-bench` always aborts on V4-Flash GGUF — `GGML_ASSERT(n_comp_visible <= n_comp_cache)` at init

**Target repo**: [`antirez/llama.cpp-deepseek-v4-flash`](https://github.com/antirez/llama.cpp-deepseek-v4-flash)
**Tip tested**: `2f2d44052` (Speed up DeepSeek V4 prompt replay)
**Severity**: HIGH — blocks all `llama-bench`-based throughput measurement of V4 models
**Component**: `src/models/deepseek4.cpp` × `src/llama-context.cpp`
**Filed by**: EPYC inference research project, 2026-05-30

## Summary

Running `llama-bench` against any V4-Flash GGUF aborts during `llama_context` construction (before any benchmark iteration runs), inside `llm_build_deepseek4`'s decode-path graph construction. The assert fires because mainstream `llama_context::sched_reserve` calls the decode graph builder with a synthetic worst-case `ubatch` (`ubatch.pos == nullptr`, `n_tokens == ubatch_size`), which computes `n_comp_visible = (ubatch_size - 1) / compress_ratio` — exceeding the compressed-attention cache size for the initial reserve.

This means `llama-bench` cannot be used to measure V4 throughput at any non-trivial `-ub` value. `llama-cli` and `llama-completion` work because their decode-path graph reserves use realistic `pos` vectors that fit `n_comp_cache`.

## Reproduction

```bash
cd build  # release build with -DGGML_NATIVE=ON -DGGML_OPENMP=ON
LD_LIBRARY_PATH=$(pwd)/bin ./bin/llama-bench \
    -m /path/to/DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf \
    -t 96 -fa 1 -mmp 0 -p 0 -n 512 -r 2 -o md
```

(Any `-p`/`-n`/`-r` combination produces the same crash; the assert fires at init before any rep.)

Workaround that survives: add `-ub 1 -b 1`. Throughput is degraded (~50% of ubatch-default) but the run completes.

## Expected behavior

`llama-bench` should complete the two reps and emit a markdown table with `tg512` t/s, matching the workflow used for every other architecture in the codebase.

## Actual behavior

```
| model | size | params | backend | threads | fa | mmap | test | t/s |
|---|---|---|---|---|---|---|---|---|
/path/to/src/models/deepseek4.cpp:1153: GGML_ASSERT(n_comp_visible <= n_comp_cache) failed
libggml-base.so.0(+0x18ae8)
libggml-base.so.0(ggml_print_backtrace+0x231)
libggml-base.so.0(ggml_abort+0x109)
libllama.so.0(_ZN19llm_build_deepseek4C2ERK11llama_modelRK16llm_graph_paramsEnnnRK11llama_modelRK16llm_graph_params+0x28b2)
libllama.so.0(_ZSt11make_uniqueI19llm_build_deepseek4JRK11llama_modelRK16llm_graph_paramsEENSt8__detail9_MakeUniqIT_E15__single_objectEDpOT0_+0x2c)
libllama.so.0(_ZNK11llama_model11build_graphERK16llm_graph_params+0x7f0)
libllama.so.0(_ZN13llama_context13graph_reserveEjjjPK22llama_memory_context_ibPmi+0x275)
libllama.so.0(_ZN13llama_context13sched_reserveEv+0xb85)
libllama.so.0(_ZN13llama_contextC2ERK11llama_model20llama_context_params+0x1634)
libllama.so.0(llama_init_from_model+0x251)
llama-bench(+0x159e8)
Aborted (core dumped)
```

## Root cause

`src/models/deepseek4.cpp:1142-1153` (verbatim):

```cpp
if (!is_prefill) {
    const llama_pos first_pos = ubatch.pos ? ubatch.pos[0] : 0;
    const llama_pos last_pos  = ubatch.pos ? ubatch.pos[n_tokens - 1] : n_tokens - 1;
    const int64_t n_comp_before  = first_pos / compress_ratio;
    const int64_t n_comp_visible = (last_pos + 1) / compress_ratio;
    const int64_t n_comp_cache = mctx_dsv4->get_dsv4_n_comp(il);
    GGML_ASSERT(n_comp_visible <= n_comp_cache);
```

During `llama_context::sched_reserve` (called from the context constructor for every reserve shape — see `src/llama-context.cpp:389`), the decode graph is built with a synthetic `ubatch` that has `ubatch.pos == nullptr` and `n_tokens == ubatch_size` (default 512). The else-branches of the two `?:` then yield:

- `first_pos = 0`
- `last_pos  = n_tokens - 1 = 511`
- `n_comp_visible = 512 / compress_ratio`

At init time, `mctx_dsv4->get_dsv4_n_comp(il)` reflects the cache as sized for the initial context (often smaller than the worst-case-ubatch ratio), so the assert trips.

`llama-cli` / `llama-completion` don't hit this because their decode reserves use realistic `ubatch.pos` vectors bounded by the actual context state — `n_comp_visible` stays within `n_comp_cache`.

## Suggested fixes (any one)

1. **Reserve-mode guard** (least intrusive): in `deepseek4.cpp:1142`, treat `ubatch.pos == nullptr` as the reserve path and either (a) skip the assert during reserve, (b) clamp `n_comp_visible` to `n_comp_cache`, or (c) compute against the cache's worst-case sizing rather than the current allocation.

   ```cpp
   if (!is_prefill) {
       const bool is_reserve = (ubatch.pos == nullptr);
       const llama_pos first_pos = is_reserve ? 0 : ubatch.pos[0];
       const llama_pos last_pos  = is_reserve ? n_tokens - 1 : ubatch.pos[n_tokens - 1];
       const int64_t n_comp_visible = is_reserve
           ? std::min<int64_t>((last_pos + 1) / compress_ratio, n_comp_cache)
           : (last_pos + 1) / compress_ratio;
       GGML_ASSERT(is_reserve || n_comp_visible <= n_comp_cache);
   ```

2. **Cache-sizing fix**: ensure `mctx_dsv4` sizes `n_comp_cache` for the worst-case `ubatch_size / compress_ratio` at init time so the assert holds throughout reserve.

3. **Replace assert with runtime check**: convert `GGML_ASSERT` to a runtime guard that bails out gracefully (return an error from `build_graph`) so `llama-bench` can fall back to a safer reserve shape rather than aborting the process.

Recommend option 1 — it's small, scoped to the reserve path, and preserves the runtime invariant.

## Workaround in use downstream

EPYC inference research project (2026-05-30) bypasses this by using `llama-completion` for throughput measurements instead of `llama-bench`. The amended throughput-gate definition in our handoff explicitly names `llama-completion` as the V4 tool and `eval time ... tokens per second` from `common/sampling.cpp:507` as the metric. Documented at: `handoffs/active/deepseek-v4-flash-cpu-port.md §Throughput gate (Strategy B)`.

Bench script with the workaround: `scripts/benchmark/v4_throughput_gate.sh` in the same project.

## Environment

- Build: `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang-20 -DCMAKE_CXX_COMPILER=clang++-20 -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DLLAMA_CURL=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_EXE_LINKER_FLAGS="-Wl,--disable-new-dtags" -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--disable-new-dtags"`
- Host: AMD EPYC 9655 96-Core, NPS4, 4 NUMA nodes, 1.1 TB DDR5
- Kernel: 6.14.0-37-generic
- Model: `DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf` (153.32 GiB, 284.33 B params, mixed Q4_K/F16/Q8 quant)
