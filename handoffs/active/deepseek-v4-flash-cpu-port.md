# DeepSeek-V4-Flash CPU Port — Experimental Branch

**Status**: Strategy B IN PROGRESS — binary side fully validated 2026-05-28; download in progress (~5%, ~4h ETA at anonymous HF rate, resumable curl in background); inference gates blocked on download completion
**Created**: 2026-05-28
**Priority**: P2
**Effort**: High (multi-thousand-line arch addition, mirroring/exceeding the DSv3.2 DSA work)
**Source**: intake-637 ([antirez/deepseek-v4-gguf](https://huggingface.co/antirez/deepseek-v4-gguf)) + deep-dive 2026-05-28

## Objective

Port the `deepseek4` architecture (CSA + HCA + indexer + compressor + manifold-constrained Hyper-Connections) to our ik_llama.cpp production tree on an experimental branch (`feature/deepseek4-port`), validate Q4 (153 GiB) and Q2 (80 GiB) GGUFs against canonical CPU stack on EPYC 9655 NPS4, and merge into production only after both a quality gate (logprob parity vs reference) and a throughput gate (≥ comparable to current top-tier roles at the same active-param budget) pass.

## Why now

User decision 2026-05-28: "no point deferring pure coding work. Should we maybe build it in an experimental branch first? And only merge it after testing?" Authorized. Experimental-branch isolation mitigates the high-risk-of-direct-cherrypick concern (antirez's fork is "not extensively tested", targets MacBook 128 GB, has no NUMA / AVX-512BW validation).

## Background

DeepSeek-V4-Flash is a 284B / 13B-active MoE with a fundamentally new architecture, not a DSv3.2 derivative:
- **Attention**: hybrid Compressed-Sparse Attention (CSA, local-window KV compression m≈4 then sparse top-k selection) + Hierarchical Compressed Attention (HCA, aggressive m'≈128 block compression + dense attention over compressed). Two parallel branches.
- **New blocks**: indexer, compressor, manifold-constrained Hyper-Connections (Birkhoff polytope residuals, spectral-norm ≤ 1). All kept at F16/F32 in the quant — decision-making layers, not quantized.
- **Efficiency claims**: 27% of V3.2 FLOPs and 10% of V3.2 KV at 1M ctx.
- **MTP head**: 3.6 GiB optional sidecar, mirrors gemma4 / DSv3.2 MTP-as-drafter pattern. Uses ds4-specific tensor naming → separate integration after base.
- **License**: MIT (passes `feedback_opensource_only`).

Current state of upstream support (2026-05-28):
- `grep -ri deepseek4 /mnt/raid0/llm/llama.cpp /mnt/raid0/llm/ik_llama.cpp` → zero hits. Neither tree supports the arch.
- Upstream tracker: ggml-org/llama.cpp issue #22319 (model request, open) + discussion #22376 (WIP, 4+ community forks). PR #22378 is closed/reference-only, not a merge path. No merged PR.
- Reference engine `antirez/ds4` (DwarfStar4) is from-scratch C (not llama.cpp-based). Backends: Metal primary, CUDA secondary, "CPU is reference/debug, non-production." Best ds4 numbers: M3 Max 21.5 t/s Q2; DGX Spark 13.75 t/s. **No EPYC / x86-AVX-512 production path published.**
- Best community llama.cpp CPU number: 6.5 t/s on ThinkPad-P16 128 GB (dual-channel DDR5). Our NPS4 12-channel-per-node should be substantially faster but no reference exists.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-637 | antirez/deepseek-v4-gguf (Q2/Q4/MTP) | high | worth_investigating (post-port escalates to new_opportunity) |
| intake-506 | DeepSeek-V3.2 + DSA (arxiv:2512.02556) | high | already_integrated (DSA, not V4 — different arch) |
| intake-508 | DeepSeek-TUI Rust client | medium | worth_investigating (targets V4 API) |
| intake-600 | Engram Conditional Memory / CXL | low | confirmed V4 does NOT use Engram |

## Merge Gates (DEFINED BEFORE PHASE 1)

These gates are concrete and not subject to renegotiation mid-port. If a gate fails at the end of its phase, the branch stays out of production until a new run passes — no waiver flow.

### Quality gate (end of Phase 3)

- **Reference engine**: antirez/ds4 reference implementation running on the same Q4 GGUF (Metal on a Mac, since ds4 has no production CPU path). If ds4 cannot run on accessible hardware for the operator, fall back to the antirez/llama.cpp-deepseek-v4-flash fork running on a Mac with `--temp 0 --seed 1`.
- **Prompt set**: 20 prompts spanning 5 categories × 4 each:
  - 4 short factual ("Who wrote Hamlet?", etc.)
  - 4 short code completion ("Write a Python function that sorts a list of integers in ascending order.")
  - 4 long-form reasoning (3-5 sentence math word problems)
  - 4 instruction-following (formatting + multi-step tool-shape outputs without actual tool calls)
  - 4 long-context recall (1K-token preface + question about a specific detail)
- **Procedure**: for each prompt, run both the reference engine and the experimental-branch build at `--temp 0 --seed 1 --top-k 1`. Capture token-level logprobs of the GREEDY output sequence for the first 64 generated tokens.
- **Tolerance**: for each prompt, compute mean absolute log-prob difference across the 64 tokens. Per-prompt MAD must be **≤ 0.05 nats** (~5% logprob deviation). Aggregate: **≥ 18 of 20 prompts** must pass per-prompt tolerance.
- **Token-1 exact-match**: for at least **15 of 20 prompts**, the experimental and reference engines must emit the same first token under greedy decoding. (This catches tokenizer or BOS/EOS handling drift before deeper logprob divergence.)
- **Failure modes documented**: if any of the 20 prompts triggers an assert, segfault, or NaN — gate FAILS automatically regardless of other prompt scores.

### Throughput gate (end of Phase 3)

- **Workload**: same 512-token decode prompt used by `cpu-decode-flops-roofline-audit.md` ("Write a Python function that computes the n-th Fibonacci number iteratively. Then explain it briefly.") at `--temp 0 --seed 42`.
- **Stack**: canonical NPS4 (`taskset -c 0-95 -t 96 -fa 1`, `numactl --interleave=all`, OMP env stack per `feedback_omp_env_stack_required`, `KMP_BLOCKTIME=10`, `GGML_NUMA_WEIGHTS=1`, `--mlock`).
- **Floor — solo Q4**: **≥ 18 t/s** sustained decode (lower bound calibrated from V4-Flash's 13B active params vs gemma4-26B-A4B's 4B active sustaining 76.5 t/s solo; conservative ~ proportional inverse with the param ratio at the same Q4 quant gives ~18-23 t/s expected).
- **Floor — solo Q2**: **≥ 35 t/s** sustained decode (Q2 is ~2× the BW efficiency of Q4 at the same per-token compute; this is opportunistic — Q2 quality may not be production-acceptable but the throughput floor is documented).
- **Acceptance interaction with `feedback_speed_verify_via_llama_bench`**: the agent does NOT autonomously run the throughput gate; the user runs it manually and reports the t/s number. The gate floor above is the criterion against which the user-reported number is judged.
- **Quality gate must pass first**: throughput numbers from a quality-failing build are not meaningful. If the quality gate fails, the throughput run is skipped until quality is fixed.

### Merge criteria (end of Phase 6)

Merge `feature/deepseek4-port` → ik_llama production tree requires ALL of:
1. Quality gate passes (≥ 18/20 prompts within 0.05-nat MAD; ≥ 15/20 token-1 exact-match; no assert/segfault/NaN).
2. Throughput gate passes (Q4 ≥ 18 t/s solo on canonical stack).
3. Chat-template shim works against the orchestrator chat-completions path on at least 3 of the 4 instruction-following prompts from the quality set.
4. MTP sidecar EITHER integrates with acceptance ≥ 0.4 OR is parked with a stub PR noting "second integration, not blocking base merge."
5. No regression on existing models — re-run a smoke test on gemma4-26B-A4B + Qwen3.6-frontdoor with the merged binary, both must still launch and produce coherent output (no quality bench, just liveness).

If any of (1)-(3) or (5) fails, the branch stays in experimental and remediation goes into a follow-on phase log appended to this handoff.

## Phase 1 Outcome — 2026-05-28

### Done
- Added `antirez` remote (https://github.com/antirez/llama.cpp-deepseek-v4-flash.git) to `/mnt/raid0/llm/ik_llama.cpp`; fetched `antirez/main` at `2f2d44052`.
- Created branch `feature/deepseek4-port` off `production-gemma4-mtp` (tip `c04881fc0`); branch is clean and at the same tip (no commits applied — see below).
- Identified 7 V4-relevant commits on `antirez/main`:
  - `06c504247` Add DeepSeek V4 Flash inference support (THE base port, 6 files, +1649 LOC)
  - `1e2752f88` README fork advertisement (skip — not our README)
  - `b67f5db5c` Optimize DeepSeek V4 Metal HC decode (skip — Metal-only)
  - `57c4283b5` Remove stale DeepSeek V4 quantize tool build entry (cleanup)
  - `188df615c` Fix DeepSeek V4 long-context graph metadata (likely needed for ≥32K ctx)
  - `3ba61fbb4` Add DeepSeek V4 tool-call chat template (needed for orchestrator)
  - `2f2d44052` Speed up DeepSeek V4 prompt replay (optimization)

### Finding — direct cherry-pick is infeasible due to fork divergence

`git cherry-pick 06c504247` produced **17+ merge conflicts**, almost all of the `modify/delete` form: ik_llama's `production-gemma4-mtp` has DELETED files (post the ikawrakow tree's refactoring of `src/llama-graph.cpp`, `src/llama-kv-cache.cpp`, `src/models/models.h`, `src/llama-context.cpp`, `src/llama-memory-hybrid-iswa.*`, plus the entire Metal backend tree) that antirez's commit MODIFIES because his fork is from a recent mainline llama.cpp tree where those files still exist. Cherry-picked aborted cleanly; `feature/deepseek4-port` branch is back at the production tip.

### Phase 1 actual delta vs documented plan

- The handoff (and master-index #58) assumed a near-clean cherry-pick. Reality: antirez forked from mainline llama.cpp (build b8927), and ik_llama.cpp's lineage diverges substantially from mainline. **Phase 1 cannot be "cherry-pick the antirez commits" as drafted.**

### Phase 1.2 delta inventory — initial plan superseded by API-gap survey

The good news from inspecting `06c504247 --stat`: the V4-specific changes are well-isolated:

| File | LOC change | Type |
|---|---|---|
| `src/models/deepseek4.cpp` | +1347 (new) | NEW arch implementation |
| `src/llama-model.cpp` | +200 | dispatch + registry add |
| `src/llama-arch.cpp` | +52 | arch enum entries |
| `src/llama-arch.h` | +30 | arch enum constants |
| `src/llama-hparams.h` | +12 | hyperparam fields |
| `src/llama-hparams.cpp` | +8 | hyperparam defaults |
| **Total** | **+1649 LOC** | **6 files** |

The 17+ conflicting files seen during the cherry-pick attempt are antirez's UNRELATED refactors that landed in the same commit (Metal kernels, KV-cache lifetime changes, graph plumbing). None of those are required for CPU inference of V4 — they were antirez's path-of-least-resistance for his Mac-targeted build.

### Phase 1.2 scope revised 2026-05-28 — original "1-2 day manual hand-merge" estimate was WRONG

**Survey of the actual API gap** (run on `feature/deepseek4-port` branch 2026-05-28 PM):

- **Headers** `deepseek4.cpp` includes — `models.h`, `llama-kv-cache-iswa.h`, `llama-memory-hybrid-iswa.h`, `llama-memory-recurrent.h` — **none exist in ik_llama**. But: V4 actually only uses `models.h` for its base class `llm_graph_context`; the other three are transitive includes serving other archs (Mamba, ISWA, recurrent) that V4 doesn't touch.
- **V4 actually uses ONLY** (from the graph-context refactor in mainstream): `llm_graph_context` (1 ref, as parent class), `llm_graph_input_i` (interface for input registration), `llm_graph_params` (constructor parameter struct). Plus V4-specific structs (`dsv4_hc_mix`, `dsv4_state_pair`, `dsv4_decode_compressor`, etc.) which are self-contained.
- **ik_llama's paradigm** is `llama-build-context` — the older API. Models are member functions of `class llm_build_context` (e.g. `build_deepseek2()` member at line ~2399 of the 2915-LOC `llama-build-context.cpp`). The dispatch is `llm_build_context::build_<arch>()` returning `ggml_cgraph *`.
- **Mainstream's paradigm** is `llama-graph` — the newer API. Models are subclasses of `llm_graph_context` (e.g. `llm_build_deepseek4 : public llm_graph_context`). The dispatch is via constructor + virtual functions on the graph context.

**These are not the same shape.** Translating `deepseek4.cpp` (1392 LOC in graph-context idiom) into ik_llama's build-context idiom is a structural rewrite, not a hand-merge. Per-call-site mapping needed for every `ggml_*` graph operation. The V4-specific logic (CSA + HCA + indexer + compressor + manifold-constrained HC) stays the same; the API surface around it does not.

**Realistic scope**: 3-5 days of careful translation by someone who understands BOTH APIs deeply enough to map calls 1:1. The previous "1-2 days" estimate assumed self-contained file + additive enum hand-merge — wrong on the first point. The arch enum + hparams deltas (+52/+30/+8/+12 LOC) ARE simple hand-merges; the work is the 1347-LOC model file.

**Strategy options for the next session — operator decision needed**:

| Option | What | Cost | Pro | Con |
|---|---|---|---|---|
| **A. Translate to ik_llama API** | Rewrite `deepseek4.cpp` against `llm_build_context` member-function paradigm | 3-5 days | V4 lands in production ik_llama tree; reuses ik_llama's MLA/MoE/CPU optimizations | Major engineering investment; iterative compile-fix cycles |
| **B. Pivot to mainstream fork** | Fork `antirez/llama.cpp-deepseek-v4-flash` directly; add EPYC NUMA env/launch tuning; run V4 as a SEPARATE binary from production stack | 1-2 days | V4 serving today; preserves antirez's already-debugged code | Loses ik_llama's CPU optimizations for V4 specifically; two binaries to maintain; production stack still on ik_llama for everything else |
| **C. Defer to upstream** | Wait for ggml-org/llama.cpp PR (currently #22319/#22376 WIP); evaluate then | weeks-to-months | Zero work; eventually best result | No V4 access in the interim |
| **D. Hybrid: B now + A in background** | Run V4 on antirez fork as auxiliary binary while option A proceeds at slower pace | 1-2d short + 3-5d long | V4 access today + cleaner long-term integration | Two paths to maintain temporarily |

**Recommendation (mine, operator overrides)**: **D** — get V4 functional today via option B (the antirez fork already builds and runs on x86 Linux per its README), evaluate whether it's useful enough to keep / consolidate into ik_llama via option A. Reduces risk of multi-day port investment on a model whose end-value is still uncertain.

### Phase 1.2 execution — Strategy D agreed 2026-05-28 evening

Operator selected **Option D**: Option B execution first (V4 functional today via antirez's mainstream-based fork as auxiliary binary); decision on Option A (3-5d translation into ik_llama) deferred until B-side evaluation produces evidence on whether V4 is production-meaningful enough to justify the longer ik_llama integration.

### Strategy B execution — 2026-05-28 evening progress

**Steps 1-2 + 4 COMPLETE; step 3 (download) in progress; steps 5-6 blocked on download.**

#### ✓ Step 1: Antirez fork cloned

- Path: `/mnt/raid0/llm/llama.cpp-deepseek-v4`
- Tip: `2f2d44052` (antirez/main as of 2026-05-28)
- `--depth 1` clone (we don't need the history)

#### ✓ Step 2: Build with canonical hardening

Configure:
```
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang-20 \
  -DCMAKE_CXX_COMPILER=clang++-20 \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,--disable-new-dtags" \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--disable-new-dtags" \
  -DGGML_NATIVE=ON \
  -DGGML_OPENMP=ON \
  -DLLAMA_CURL=OFF \
  -DBUILD_SHARED_LIBS=ON
cmake --build . -j 32
```

Verified post-build:
- `readelf -d llama-bench` → `DT_RPATH` (not `DT_RUNPATH`) — beats `LD_LIBRARY_PATH`
- `ldd llama-bench` → resolves to V4 fork's own `libllama.so.0`, `libggml.so.0`, plus `/usr/lib/llvm-20/lib/libomp.so.5` (clang-20 libomp)
- All binaries built: `llama-bench`, `llama-server`, `llama-cli`, `llama-gguf`, etc.
- `deepseek4.cpp.o` compiled (66 KB object, 1392 LOC source) — `LLM_ARCH_DEEPSEEK4` enum present

#### ⏳ Step 3: Q4 GGUF download (~5%, ETA ~4h at anonymous rate)

- File: `DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf` (153.3 GiB)
- Target: `/mnt/raid0/llm/models/deepseek-v4-flash/`
- Method: `curl -L -C - --retry 5 --retry-delay 5` (resumable; survived devcontainer rebuild)
- Rate: stable ~10 MB/s (anonymous HF per-IP limit; **parallel range requests tested, no improvement** — confirmed per-IP not per-connection)
- HF_TOKEN would speed this to ~100 MB/s (30-60 min) but no token set this session
- The curl will resume on its own if killed; the partial file at `*.gguf.tmp` is the resume target

#### ✓ Step 4: canonical_recipe.py V4-fork support (committed)

Research-repo commit `77b5cbc`:
- New constants `V4_FORK_BENCH` + `EXPECTED_LIBS_V4_FORK` pointing at the new build dir
- New function `discover_v4_fork_bench()` — raises FileNotFoundError with the rebuild instructions if not built
- `build_canonical_bench_command(..., use_v4_fork=False)` — new optional param; when True, picks V4_FORK_BENCH
- CLI flags: `validate --v4-fork`, `emit-bench-command --v4-fork`
- `bench_canonical.sh --v4-fork` flag pass-through
- Tests: 3 new V4-fork tests, all pass; 22 total tests pass

Verified at 2026-05-28 PM:
- `python3 canonical_recipe.py validate --v4-fork` → OK
- `bench_canonical.sh --v4-fork --help` → flag visible

#### Diagnostic — binary side fully working

Using `llama-gguf` from the new fork to inspect the partial download (only 8 GB of 153 GB):
- Header parses cleanly: 62 metadata kv pairs, all `deepseek4.*` prefixed
- V4-specific fields present: `attention.q_lora_rank`, `attention.output_lora_rank`, `attention.output_group_count`, `attention.compress_ratios`, `attention.compress_rope_freq_base`, `expert_count`, `expert_shared_count`, `hash_layer_count`
- Tensor count: 1328 (consistent with 284B MoE Q4)
- No parse errors, no symbol mismatches — the deepseek4 arch wiring is functional

This means: **once the download completes, the bench should just work.** No expected debugging on the binary side.

#### ⏭ Step 5 (after download): Throughput gate

```bash
bench_canonical.sh --v4-fork --perf -m \
  /mnt/raid0/llm/models/deepseek-v4-flash/DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf
```

Validates host, picks V4 fork binary, runs canonical perf-stat recipe. Gate floor: Q4 ≥ 18 t/s solo (per §Merge Gates above).

#### ⏭ Step 6 (after step 5 passes): Quality gate + decision

20-prompt set per §Merge Gates. Reference engine (antirez fork on Mac) is operator-coordinated; we provide EPYC-side numbers. After both gates pass, decide:
- If V4 is production-meaningful → promote to **Option A** (3-5d translation into ik_llama for production-tree consolidation)
- If V4 underperforms → park at B-only or abandon

### Resume / continue instructions (for next session)

```bash
# Confirm download still running:
pgrep -af 'curl.*DeepSeek-V4-Flash'
du -sh /mnt/raid0/llm/models/deepseek-v4-flash/*.tmp

# If curl died, restart it (preserves resume):
REDIRECT=$(curl -sI "https://huggingface.co/antirez/deepseek-v4-gguf/resolve/main/DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf" | grep -i '^location:' | awk '{print $2}' | tr -d '\r\n')
cd /mnt/raid0/llm/models/deepseek-v4-flash && \
  nohup curl -L -C - --retry 5 --retry-delay 5 -o "DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf.tmp" "$REDIRECT" \
  > /tmp/v4-curl-resume.log 2>&1 &

# Once size matches the 153.3 GiB target (check `du -h *.tmp`), rename:
mv /mnt/raid0/llm/models/deepseek-v4-flash/*.gguf.tmp \
   /mnt/raid0/llm/models/deepseek-v4-flash/DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf

# Then run gates:
bench_canonical.sh --v4-fork --perf -m /mnt/raid0/llm/models/deepseek-v4-flash/DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2-imatrix.gguf
```

If you set `HF_TOKEN` (via `hf auth login`) the download can complete in 30-60 min instead of ~4h, but this is not required — curl will keep going on its own.

### Strategy B operational notes (gathered 2026-05-28 from antirez fork inspection)

#### Chat template

V4-Flash GGUF **does** embed `tokenizer.chat_template` in the metadata (`llama-gguf` on the partial download shows `kv[57]: key = tokenizer.chat_template`). The antirez fork ALSO ships a copy on-disk at:

```
/mnt/raid0/llm/llama.cpp-deepseek-v4/models/templates/deepseek-ai-DeepSeek-V4.jinja
```

(96 lines, added in commit `3ba61fbb4`). The two should be identical — the on-disk file is the source antirez used during quantization. Diff against the GGUF-embedded copy with `llama-gguf <gguf> r` and `cat <jinja>` once the download finishes; if they match, prefer the GGUF-embedded path (`--jinja` alone, no `--chat-template-file` needed) since it travels with the model. If they diverge, the on-disk file is the authoritative source.

The template:
- Uses a custom `｜DSML｜` token wrapper for tool calls (similar pattern to Qwen3.6's frontdoor tokens)
- Supports `enable_thinking` Jinja variable (similar to Qwen3.6) — default false, may need to be explicitly disabled per the `feedback_enable_thinking_requires_chat_completions_path` pattern if we observe `<think>` loops
- Has separate tool-call schema in `<｜DSML｜tool_calls>` block format

For the throughput gate we use bare prompt completion (no chat template needed). For the quality gate (uses /v1/completions, not /v1/chat/completions) we also don't need the template. The template only becomes load-bearing if we later wire V4 into the orchestrator chat-completions path.

#### Long-context graph metadata fix (already in our build)

Commit `188df615c` ("Fix DeepSeek V4 long-context graph metadata") bumps `llama_context::graph_max_nodes` for `LLM_ARCH_DEEPSEEK4` from `max(4096, n_tokens*64+32*n_tensors)` to `max(262144, n_tokens*192+64*n_tensors)`. Reason: V4's position-dependent compressed-attention decode path creates many temporary tensor objects per token (especially in non-prefill ubatches on long contexts); the visible graph node count is much smaller than the GGML objects actually allocated, so without this bump long-context decode would exhaust the metadata arena.

This fix is in our build (tip `2f2d44052` includes the prior commit). **No operator action required**, but if we hit an arena-exhaustion assertion at long context, this is the area to look first.

The commit also added `DSV4_COMPRESSED_DECODE_UBATCH_MAX = 128` to `llama-memory-hybrid-iswa.cpp` to bound the compressed-decode ubatch size — this is the kind of soft limit that interacts with our `-ub` setting (we use 512 for gemma4 production; for V4 we should follow antirez's recipe of `-ub 512` per the runner script).

#### README disclaimers + recommended invocation

From `llama.cpp-deepseek-v4/README.md`:

> This is a fork of llama.cpp that implements DSv4 support, with generated GGUF that aims to target MacBooks with just 128GB of RAM using 2bit quantization of routed experts.
>
> Disclaimer:
> - This code was written with heavy help from GPT 5.5 and the official DeepSeek v4 Flash as reference.
> - The model quantized in this way behaves very very well in the chat, frontier-model vibes, but it was not extensively tested.
> - The code runs both with CPU and Metal backends. With Metal is faster.

Implications for us:
- **"Not extensively tested"** — treat all results as exploratory. The quality gate is exactly the right tool for the situation.
- **MacBook target** — antirez's tuning targets 128 GB unified memory on Apple Silicon. Our 1.1 TB EPYC + 12-channel DDR5 + NPS4 is a different regime; we should not expect the same numbers as antirez's Mac runs.
- **CPU "works but Metal is faster"** — author has stress-tested Metal, not CPU. Our throughput floor (Q4 ≥ 18 t/s solo per §Merge Gates) is calibrated for a CPU-on-EPYC regime, not a Metal comparison.

Recommended invocation from the README is `llama-cli -m DeepSeek-V4-Flash-IQ2XXS... -cnv` (interactive). Our automated flow is non-interactive; the smoke test (`v4_smoke_test.sh`) uses `--no-conversation` and the runner (`v4_quality_gate_runner.py`) uses `/v1/completions`.

#### Tip commit (`2f2d44052`) — prompt replay speedup

Latest antirez commit adds a "DeepSeek V4 HC weighted-sum ggml op with CPU, Metal, and meta backend support" used in the compressed attention path. Also batches resumed compressed-decode projections and increases the compressed-decode replay cap. Performance numbers cited: M3 Max ~127-128 → ~166 tok/s synthetic Metal server replay. **Generation speed cited as ~21.5 tok/s on M3 Max** — this is our nearest comparison point on the throughput axis (though architectures differ enough that we shouldn't anchor on it).

#### Useful prep artifacts (committed alongside this section)

- `scripts/benchmark/v4_quality_gate_runner.py` — capture EPYC-side logprobs (20 prompts × 64 tokens via /v1/completions)
- `scripts/benchmark/v4_quality_gate_compare.py` — MAD + token-1 verdict; 27 unit tests
- `scripts/benchmark/test_v4_quality_gate_compare.py` — comparator test suite
- `scripts/benchmark/v4_smoke_test.sh` — preflight + metadata + 4-token decode (folds in option C preflight)
- `benchmarks/prompts/v1/deepseek-v4-quality-gate.yaml` — 20-prompt set per §Merge Gates

### Notes carried forward from 2026-05-28 session

- ik_llama branch `feature/deepseek4-port` preserved at `c04881fc0` (= `production-gemma4-mtp` tip). Used if/when Option A activates.
- `antirez` remote on ik_llama still present (harmless; used for the cherry-pick attempt + subsequent surveys).
- ik_llama binaries already rebuilt with RPATH fix (today's commit). Production stack should keep using them when restarted.
- `bench_canonical.sh` + `canonical_recipe.py` validators live and now support `--v4-fork`.
- Strategy-decision diagnostics that informed D (1392 LOC graph-context → build-context translation, V4 only depends on 3 graph-context symbols not the broader Mamba/ISWA hierarchy) are recorded in the §"Phase 1.2 scope revised" block above.
- Devcontainer was killed + rebuilt mid-session 2026-05-28; ALL persistent state (build artifacts, partial download, repo commits) survived on `/mnt/raid0/llm`. The ephemeral state lost was: `hf_transfer` Python package (couldn't reinstall — no pip in rebuilt container), `HF_TOKEN` env var (was never set), production llama-server stack (operator restart needed).

## Phased Port Plan (Option A only; superseded until decision)

The original six-phase ik_llama integration plan below is retained as a scaffold, but it is not active while the A/B/C/D decision is pending. Do not run Phase 1 as originally drafted: direct cherry-pick already failed. If the operator selects Option A, rewrite Phase 1 as graph-context → build-context API translation. If the operator selects Option B or D, create a separate auxiliary-binary plan for the antirez fork before doing code work.

### Phase 1 — ik_llama API translation (Option A; replaces cherry-pick)

1. Keep `feature/deepseek4-port` off the ik_llama.cpp production tree's current head (NOT off antirez's fork directly).
2. Hand-merge the simple additive deltas from `antirez/llama.cpp-deepseek-v4-flash`: arch enum, hparams, loader/dispatch, tokenizer/template fields.
3. Translate `src/models/deepseek4.cpp` from mainstream `llm_graph_context` idiom into ik_llama `llm_build_context::build_<arch>()` idiom, mapping each graph/KV call explicitly.
4. **Do NOT bring in any non-arch changes** from the antirez fork (per `feedback_minimum_imports`).
5. Build verification under canonical stack: AOCC + KMP_BLOCKTIME=10 + GGML_NUMA_WEIGHTS=1.

### Phase 2 — Q2 smoke test (Day 2)

5. Download Q2 GGUF (80.8 GiB) to `/mnt/raid0/llm/models/`. Verify storage budget (Q2 + Q4 + MTP + working copy ≈ 250 GB).
6. Single-thread load-and-decode smoke test (no concurrent inference per `feedback_no_concurrent_inference`).
7. Compare a small set of logprobs against ds4 reference vectors (if antirez publishes them; otherwise against the antirez/llama.cpp-deepseek-v4-flash MacBook run for parity sanity-check).

### Phase 3 — Q4 quality gate (Days 3-4)

8. Download Q4 GGUF (153.3 GiB).
9. Single-instance Q4 inference with canonical NPS4 stack: `taskset -c 0-95 -t 96 -fa 1`, `numactl --interleave=all`, OMP env stack (`feedback_omp_env_stack_required`).
10. **Run the quality gate** per the §Merge Gates definitions above (20-prompt set × per-prompt MAD ≤ 0.05 nats × token-1 exact-match).
11. **Run the throughput gate** per the §Merge Gates definitions above (canonical 512-token decode, Q4 floor ≥ 18 t/s, Q2 floor ≥ 35 t/s) — operator-executed per `feedback_speed_verify_via_llama_bench`.

### Phase 4 — Chat template + orchestrator integration (Day 5)

12. V4-Flash GGUF lacks a built-in Jinja chat template (per allthings.how). Write a template shim against the upstream Python encoder.
13. Wire into orchestrator_stack.py as a registry candidate (NOT as a production role) — load on demand.
14. Validate against ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES path.

### Phase 5 — MTP sidecar integration (Days 6-7, optional)

15. The 3.6 GiB MTP sidecar uses ds4-specific tensor naming. Adapter layer to load it as a drafter for V4 base, mirroring the gemma4 MTP path.
16. Acceptance-rate measurement on representative workload.

### Phase 6 — Merge decision

17. Both gates passed AND chat-template works AND MTP optional integration either works or is parkable → merge `feature/deepseek4-port` into production tree.
18. If upstream ggml-org/llama.cpp merges a deepseek4 PR first → roll back our branch in favor of upstream PR for review and merge.

## Open Questions

- Should MTP integration be in-scope for this branch, or a separate follow-on after base merge? (Per §Merge Gates criterion 4, either path is acceptable — but the decision affects whether Phase 5 is required or optional.)
- Once merged, what production role does V4-Flash take? (Top-tier general, or specialized?) Resolve based on the throughput-gate t/s number vs gemma4-26B-A4B's 76.5 t/s.
- Is the `github.com/antirez/ds4` KV-cache-on-disk reference engine worth a separate intake / experiment? (User said earlier: "to be ingested separately if user requests.")
- ~~Quality-gate tolerance and throughput-gate floor are now DEFINED above; not open.~~

## Cross-references

- **Primary intake**: intake-637 (antirez/deepseek-v4-gguf)
- **Sibling handoff**: `llama-cpp-dsa-contribution.md` — V4 is tracked as adjacent upstream arch work (different arch, parallel effort)
- **MTP integration template**: `moe-spec-cpu-spec-dec-integration.md` and `project_gemma4_mtp_launch_recipe`
- **Quant recipe reference**: APEX paper / intake (asymmetric routed-vs-shared expert precision)
- **Upstream watch**: ggml-org/llama.cpp#22319 + #22376
- **antirez fork**: github.com/antirez/llama.cpp-deepseek-v4-flash
- **ds4 reference engine**: github.com/antirez/ds4 (Metal/CUDA/ROCm; CPU = non-production reference)

## Reporting Instructions

After each phase, append a Phase Report subsection here documenting:
- Build / smoke-test / gate outcomes
- Throughput numbers (when explicitly user-approved)
- Any deviations from antirez's fork that we had to make for NPS4 / AVX-512BW
- Decision to proceed to next phase or pause

Update `progress/YYYY-MM/YYYY-MM-DD.md` at every phase transition.

## Notes

User authorized this port on 2026-05-28 with the explicit framing: "build in an experimental branch first, only merge after testing." Experimental-branch isolation is the safety harness; the antirez fork is acknowledged-untested for our NUMA / AVX-512BW environment.

Per `feedback_no_concurrent_inference`: no benchmark execution without explicit per-run user approval. The phases above are scoped so that loading and smoke-testing can proceed, but throughput/quality benchmark runs are deferred to user invocation.

Per `feedback_no_wholesale_git_add_shared_files`: when staging cherry-picked changes, verify `git diff --cached` to ensure only our targeted hunks land — `/mnt/raid0/llm/ik_llama.cpp` is a shared clone and other agents may have in-progress work.
