# K28 — Fused Chunked GDN Recurrence Kernel: Research Handoff

**Status**: RESEARCH/DESIGN — Phase 0 ceiling + pinned verbose trace + direct HIP-event timing gate run 2026-07-20; no fused recurrence kernel written. A default-off timing hook was added on the post-candidate experimental line only. Design + SOTA deep-dive gates a possible post-v7 default-off kernel effort.
**Created**: 2026-07-20. **Scope**: GPU (MI210 / gfx90a / CDNA2, ROCm/HIP). **Owner task**: `mi210-big-model-and-acceleration-roadmap.md` K28 (`- [ ]`, `gated_delta_net.cu:191` TODO).
**Related (distinct)**: [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) (a different, monitoring-only *log-linear* GDN tracker — not this kernel effort).
**For**: the parallel agent working the K28 / GDN long-prefill thread.

---

## Context — why this handoff exists

The parallel agent closed the two *cheap* K28 win-paths on 2026-07-20 and concluded:

> "Do not spend more time on graph-vs-fused switching or BF16-for-speed. If K28 remains worth pursuing, it needs a real fused recurrence kernel improvement or a separate residency/memory argument."

This handoff answers **what that "real fused kernel" is**, grounds it in the actual SOTA (equations, reference kernels, CDNA2 feasibility, upstream prior art — all in the appendices), and pairs the design with a **cheap decision gate to run before committing weeks**.

The single most important framing: **the MI210 A/B is not evidence against chunking — it is evidence against llama.cpp's *generic-ggml decomposition* of the chunked algorithm.** The chunked *algorithm* is what every SOTA engine ships (FLA→vLLM/SGLang, FlashQLA, TFLA). What loses on MI210 is how llama.cpp expresses it — as ~150+ separate ggml ops, each round-tripping intermediates through HBM. A real fused kernel keeps chunk-local tensors on-chip.

## 2026-07-20 Phase 0 gate result

Phase 0 was run only to decide whether K28 should delay v7 promotion. It should
not. Direct ROCm attribution could not run because `rocprofv2`, `rocprof`, and
`omniperf` are absent, so the gate used a fresh `GATED_DELTA_NET` MI210 op rerun
plus the existing Qwen3.6-35B-A3B Q8 full-model prefill rows. The op rerun
reproduced the serial-dependency signature (`51.20 GB/s` at 64 tokens falling
to `26.84 GB/s` at 1024), but the modeled full-model ceiling is bounded:
estimated GDN prefill share is `15.31%` at p2048 and `14.54%` at p8192; a 4x
op kernel would map to about `11.48%` / `10.91%` full-model prompt gain.

The follow-up `LLAMA_QWEN35_PREFILL_TRACE=2` run used the pinned experimental
v7 libraries (`LD_LIBRARY_PATH=build-hip/bin`) and `llama-bench -v` because
non-verbose `llama-bench` suppresses model logs. It confirmed the trace scaffold
is active, but it emits structural graph-node deltas rather than wall-clock
timings. Across the emitted graph groups, `gated_delta_net` accounted for
`24.50%` of `linear_attn_total` graph-node deltas and `12.22%` of
`linear_attn_total+ffn_total` deltas. That sanity-checks that GDN is material
inside linear attention, but it does not replace direct profiler attribution or
raise the Phase 0 full-model ceiling.

Evidence:
`/mnt/raid0/llm/epyc-inference-research/data/k28_gdn_perf/k28-phase0-op-rerun-20260720T102526Z/`
and
`/mnt/raid0/llm/epyc-inference-research/data/k28_gdn_perf/k28-phase0-ceiling-20260720T102644Z/summary.json`;
trace follow-up
`/mnt/raid0/llm/epyc-inference-research/data/k28_gdn_perf/k28-qwen35moe-gpu-trace-verbose-pinned-20260720T112158Z/summary.json`.

Verdict: keep K28 open as a plausible post-promotion/default-off fused-kernel
project, but do not delay frozen-v7 promotion for Phase 1 unless a direct
profiler rerun or throwaway prototype shows a materially higher full-model
ceiling.

## 2026-07-20 direct GDN timing hook follow-up

Direct ROCm profilers were unavailable, so the follow-up added a **default-off
op timing hook** to `llama.cpp-experimental` commit `8bb53c520` (`Add
default-off GDN timing hook`). This is post-candidate research, not part of the
frozen promotable v7 tip `6ad45fa3ff`.

Runtime contract:
- `GGML_CUDA_GDN_TIMING=1` requests HIP/CUDA event timing around
  `GGML_OP_GATED_DELTA_NET`.
- The hook requires `GGML_CUDA_DISABLE_GRAPHS=1`; otherwise it emits one warning
  and disables timing to avoid synchronizing inside graph capture.
- Log rows include wall-clock `ms`, shape (`S_v`, `H`, `n_tokens`, `n_seqs`,
  `K`), `kda`, `keep_rs`, dtype, and fused-cache status.

Validation:
- `git diff --check` passed on the touched experimental files.
- `cmake --build build-hip --target test-backend-ops -j 32` passed.
- `GGML_CUDA_DISABLE_GRAPHS=1 GGML_CUDA_GDN_TIMING=1
  test-backend-ops test -o GATED_DELTA_NET -b ROCm0 -j 8` passed `38/38` and
  emitted timing rows for both K==1 and snapshot/KDA fallback cases.

Full-model timing evidence is in inference-research commit `2c2b94b7`, pushed to
`origin/main`:
`data/k28_gdn_perf/k28-gdn-op-timing-hook-qwen35-20260720Tcurrent/summary.json`.
The Qwen3.6-35B-A3B Q8 MI210 run used `llama-bench -v -p 2048,8192 -n 1 -r 1`
with graphs disabled for timing.

| Prompt | Prompt t/s | Direct measured GDN share | 4x GDN-op full-model ceiling |
|---:|---:|---:|---:|
| p2048 | `2073.75 t/s` | `15.45%` | `11.59%` |
| p8192 | `1975.94 t/s` | `14.64%` | `10.98%` |

Verdict: direct HIP-event timing validates the Phase 0 modeled ceiling instead
of raising it. K28 remains an interesting **post-promotion/default-off fused
recurrence** project, but it should not delay frozen-v7 promotion. If reopened,
the smallest defensible prototype is a constrained GDA-only/F32/K==1,
`S_v=128`, `n_seqs=1`, long-prefill path; broader GDA+KDA+snapshots+MFMA support
is multi-day to multi-week work.

---

## TL;DR recommendation

1. **The "real fused kernel" = a single fused chunked-recurrence kernel** computing one chunk's WY/UT-transform, intra-chunk masked matmul, and inter-chunk state carry **in one launch with chunk-local tensors resident in registers/LDS**, one block per `(head, seq)`. This is the `//TODO: Add chunked kernel` at `gated_delta_net.cu:191`. Structure it after FLA's 5-kernel split (Appendix 2), collapsed into one launch.
2. **The win is fusion, not "chunking per se."** The generic-ggml chunked graph *already* dispatches its matmuls to matrix cores (rocBLAS/mmq) and still loses to the serial kernel by ~6% — so the bottleneck is op-dispatch + HBM round-trips, not matmul throughput.
3. **Do NOT lead with an MFMA rewrite.** Lead with a **fusion-only FP32 kernel** (keep the existing warp-reduce math, just process a whole chunk on-chip per launch). Lower-risk, and likely already beats both current paths. MFMA/bf16 (Appendix 4) is a separable Phase 2.
4. **Gate it first.** K28 is lever **#7 of 11**; the GPU raw-speed frontier is called "structurally exhausted"; MI210 is **not live production**; the GDN model (Qwen3.6-35B-A3B) is served on **CPU**. Any result is **observation-grade** until v7 promotes and `P-GPU-1` reruns. **Run Phase 0 (attribution + throwaway prototype) before Phase 1.** If the modeled full-model prefill ceiling is < ~10% and stays observation-grade, defer behind the higher-EV levers in Part G.
5. **Heed the AMD register-pressure landmine.** Upstream issue #20354 shows the existing hipified GDN kernel runs at ~11.8 t/s on ROCm (RDNA3.5), root-caused to per-thread state register spilling + a warp-32 tiling assumption. On CDNA2 (Wave64) the tiling must be re-derived and the VGPR budget watched (Appendix 4).

---

## Part A — Audit of the current GDN kernel stack

### Three code paths (chooser: `build_delta_net`, `src/models/delta-net-base.cpp:425`)

| Path | Function | Used when | Implementation |
|---|---|---|---|
| Fused (custom kernel) | `build_delta_net_fused` (:373) → `ggml_gated_delta_net` op → `ggml/src/ggml-cuda/gated_delta_net.cu` | decode (`FGDN_AR`) and prefill (`FGDN_CH`) when `cparams.fused_gdn_ch`/`fused_gdn_ar` set | **Sequential** token loop (`gated_delta_net.cu:74` `for t < n_tokens`), warp-per-column rank-1 updates, **FP32, no matrix cores** |
| Chunked (generic graph) | `build_delta_net_chunking` (:16) | prefill when fused disabled | Real FLA-style chunked algorithm from `ggml_mul_mat` + `ggml_solve_tri` (:166, the UT-transform) + `ggml_cumsum` + `ggml_tri` + `ggml_exp` + a **per-chunk C-loop** (:235-274) |
| Autoregressive (generic graph) | `build_delta_net_autoregressive` (:289) | decode when fused disabled | Generic-ggml single-token recurrence |

- Chunk sizes **already match SOTA**: `const int CS = kda ? 16 : 64;` (`delta-net-base.cpp:61`). GDN (scalar gate) = 64; KDA (Kimi, per-channel gate) = 16 (FLA's supported set is exactly 16/32/64 — Appendix 2).
- GDN dims for Qwen3.6-35B-A3B: `S_v = ssm_d_state = 128`, `H_v = ssm_dt_rank = 32` v-heads, `H_k = ssm_n_group = 16` k-heads (`src/models/qwen35moe.cpp:93-96`). State `[S_v × S_v × H_v × n_seqs]`, transposed (`M[col][i]=S[i][col]`, `gated_delta_net.cu:65`).
- A CPU GDN op path exists too (`ggml-cpu.c` `GGML_OP_GATED_DELTA_NET`) — but GDN is only ~1-2% of CPU prefill wall-clock (Part D), so CPU is not the target.

### The bottleneck, quantified (K28.1 op microbench, `test-backend-ops -o GATED_DELTA_NET`, MI210, head_count=32/head_size=128)

| Prompt tokens | Op time | Effective BW |
|---:|---:|---:|
| 64 | 152.99 µs | **51.17 GB/s** |
| 256 | 625.04 µs | 31.36 GB/s |
| 512 | 1254.23 µs | 28.15 GB/s |
| 1024 | 2485.09 µs | **26.87 GB/s** |

MI210 HBM2e peak ≈ 1.6 TB/s → **~1.7% of peak**, and effective BW **falls** as prompt grows. That declining curve is the fingerprint of a **serial-dependency-bound** kernel (the token loop dominates; per-token overhead can't amortize) — the opposite of a chunked matmul kernel (rising efficiency with length). **Strongest single signal that a fused chunked kernel has real headroom.** Prior gate ("build a chunked kernel only if recurrence latency, not memory traffic, dominates") is thereby **satisfied**.

### Tried / falsified ledger (do not re-tread)

**Banked in v7** (`gemma-challenge-kernel-techniques-v7.md:26-31`):
- `nwarps 2→4` (`5dc116130`) **+4.6%** — hence `num_warps = 4` (`gated_delta_net.cu:193`). Occupancy already tuned.
- async prefetch (`7c28056b7`) +3.3%.
- **bf16 GDN recurrent-state** (`496e2f098`) **+21.5% @B=32** (frontdoor 35B-A3B +17.7%, architect 122B +16.4%).

**Falsified** (`mi210-big-model-and-acceleration-roadmap.md:61-64` + K28.2/K28.3):
- Further **GDN-occupancy rewrite** ✗ (consistent with serial-dependency-bound: occupancy is not the limit).
- compact-LDS ✗.
- **graph-vs-fused policy switch** ✗ — generic chunked graph *loses* to the serial kernel −6.30% to −6.69% on full-model prompt (p64→p8192), Qwen3.6-35B-A3B Q8 (`data/k28_gdn_perf/k28-fused-vs-graph-qwen36-35b-summary-20260720.json`).
- **single-stream BF16 state** ✗ (neutral: −0.76%/−0.79% prompt, +0.74% decode).

**Reconciliation of the BF16-state result** (don't mis-file it): the banked **+21.5% @B=32** and the neutral single-stream probe are the *same* `GGML_CUDA_GDN_STATE_BF16` mechanism in two regimes. State bandwidth only dominates at **batch**; single-stream is dependency-bound. So "BF16-for-speed is dead" is only true single-stream — it is a **live batched-decode lever** across the GDN family (35B frontdoor + 122B architect). See Part G.

**Only untried lever left:** the algorithmic restructure to a fused chunked-matmul kernel.

### Upstream prior art this builds on (Appendix 4 for detail)

- `#19504` added the fused op (`GGML_OP_GATED_DELTA_NET`; CPU ref + **CUDA autoregressive** kernel). `#20340` **enabled the chunked fused prefill path** (feeds multi-token chunks to the op; big Kimi-linear prefill gains) with CUDA (`#20391`) / Metal (`#20361`) kernels. `#19375` only restructured the *generic graph* (fewer copies/concats, ~1.2–1.37× on M2 Ultra) — **not a fused chunked kernel.**
- **No CDNA2/ROCm-tuned GDN kernel exists.** HIP just runs the hipified CUDA kernel. The one AMD data point — **issue #20354** (RDNA3.5) — shows it at ~11.8 t/s (vs 50–80 expected) from register spilling + warp-32 assumptions. **That gap is precisely what an MI210 fused chunked HIP kernel would fill; it's genuinely open territory (and a candidate upstream contribution).**

---

## Part B — The direct answer: what "real fused kernel" improvement to make

Restructure prefill from a per-token serial scan into a **fused chunked recurrence** in one custom HIP kernel. Per chunk of `C` tokens (C=64 GDN / 16 KDA), inside one launch with tensors resident in registers/LDS (full equations in Appendix 1; FLA's kernel split to mirror in Appendix 2):

1. **WY / UT-transform** (removes the per-token dependency inside a chunk): form the strict-lower `A = strictLower(diag(β)·KKᵀ)` (gated: `strictLower(diag(β)·(Γ⊙KKᵀ))` for the value side), then `T = (I + A)⁻¹·diag(β)` — a **C×C unit-lower-triangular solve** by forward substitution (the only serial step *within* a chunk, O(C); parallel *across* chunks). **Note the sign: `(I + strictLower(...))⁻¹`** (this is `ggml_solve_tri` at `delta-net-base.cpp:166`, done in-kernel in LDS).
2. **WY factors:** `W = T·K`, `U = T·V` (matmuls, token-parallel).
3. **Inter-chunk state carry** (the only cross-chunk serial dependency, O(L/C) steps, not O(L)): `S_[t+1] = →S_[t] + (Ũ − ←W·Sᵀ)ᵀ·→K` with the gated decay `γ` folded via the `←/→` arrow scalings.
4. **Output:** `O = ←Q·Sᵀ + (Q·Kᵀ ⊙ Γ)·(Ũ − ←W·Sᵀ)` — inter-chunk (decayed, unmasked) + intra-chunk (decay-masked) terms.

**Gated asymmetry to implement (Appendix 1 §5):** the **W (key-side) solve uses plain `KKᵀ`**; the **Ũ (value-side) solve uses `Γ⊙KKᵀ`** (decay mask inside the inverse). The per-chunk cumulative decay `γ = exp(cumsum(log α))` re-enters at output/state-carry via the arrow factors. FLA computes this in **log2 space** (`cumsum` scaled by `1/ln2`, then `exp2`).

**Why this is the lever (evidence-backed):**
- Cuts the serial dependency from **`n_tokens` → `n_tokens/C`** (16× fewer at C=64) and exposes the rest as dense, token-parallel matmuls.
- Keeps the C×C decay mask, `KKᵀ`, the triangular-solve result, `W`, `U`, per-chunk output **on-chip**, round-tripping only the `d×d` state per chunk — eliminating the ~150+ op-launch / HBM-round-trip overhead that sinks the generic-ggml graph (`delta-net-base.cpp:235-274`: at 1024 tokens / C=64 = 16 chunks × ~9 ops ≈ 144 launches + ~20 setup ops).

**The critical sequencing insight:** the generic graph already uses matrix cores and *still* loses → the bottleneck is **fusion/launch/IO, not matmul throughput.** Therefore:
- **Phase 1 = fusion-only, FP32.** Keep the current warp-reduce math; process a full chunk on-chip in one launch (fewer, longer-lived blocks; state in LDS/registers across the chunk loop). Likely beats both current paths, low-risk.
- **Phase 2 = MFMA/bf16.** Convert chunk matmuls to matrix-core ops for the ceiling. Separable, larger.

Do **not** invert this order.

---

## Part C — SOTA cross-reference (summary; full deep-dives in appendices)

- **Algorithm** — DeltaNet chunked/UT-transform (Yang et al., NeurIPS 2024, arXiv:2406.06484 §3.2–3.3) + Gated DeltaNet (ICLR 2025, arXiv:2412.06464 §3.1–3.4). Chunked-vs-recurrent speedup **grows with L and d_head, up to ~30×** at L≈16K/d_head=256 (Appendix 1 §6). d_head=128 is our case.
- **FLA (`fla-org/flash-linear-attention`)** — de-facto reference; 5-kernel Triton split, chunk ∈ {16,32,64}, bf16 in / fp32 accum, tri-solve forced IEEE fp32, memory-bound `fused_recurrent` decode path. **Runs on ROCm** (`[rocm]` extra) but not reusable in llama.cpp (no Triton runtime). Appendix 2.
- **vLLM & SGLang** — both drive Qwen3-Next GDN through FLA's Triton kernels. **Nobody uses a per-op decomposed graph like llama.cpp's** — that's the unique thing losing on MI210.
- **FlashQLA (`QwenLM/FlashQLA`)** — TileLang, **2–3× fwd vs FLA** (measured 3.17× @32k) — but **SM90/SM100 only**, prefill-only. Its warpgroup-specialization + TMA + wgmma **do not port to CDNA2**; its *algorithmic* wins (single-launch fusion, algebraic reformulation, gate-decay context-parallel splitting) do. Appendix 2.
- **TFLA (arXiv:2503.14376)** — identifies FLA's chunk-≤64 low-arithmetic-intensity problem (many HBM-materialized inter-chunk states), fixes it with a **second level of intra-chunk parallelism** → **runtime-optimal chunk 128–256** (`L_opt ∝ √(d·I)`; **re-sweep for CDNA2's lower ridge point**). Optimize wall-clock, not FLOP utilization. This is the Phase-3/"beyond" direction, not the first kernel. Appendix 3.
- **AttentionEngine (arXiv:2502.15349)** — TileLang compiler, **MI250 (CDNA2, ROCm 6.2.4), avg 3.3× fwd / 2.0× bwd** — proof CDNA2 codegen for gated linear recurrences is competitive. **Caveat: it does NOT cover DeltaNet/GDN** (only Mamba2/RetNet/gated-retention); the delta-rule correction term is the un-templated part, and it documents no wave64/LDS/MFMA specifics. Use as design/autotune oracle, not a code source. Appendix 3.
- **Upstream llama.cpp** — no fused matmul-chunked GDN kernel; issue #20354 is the open AMD-perf gap. Appendix 4.

**Convergence targets:** chunk **64 GDN / 16 KDA** to start (SOTA + already the fork's values); **bf16/fp16 matmul + fp32 accumulate**, **triangular solve in fp32** (IEEE on MI210 — no TF32); **MFMA 16×16×16 bf16_1k for chunk matmuls**; **one block per (head, seq)** to keep the inter-chunk scan on-chip (avoids CDNA2's slow cross-block scans/atomics).

---

## Part D — ROI reality check + the decision gate (read before building)

- **K28 is lever #7 of 11** (`inference-acceleration-index.md:50-93`) — below every CPU lever, residency/teleport, and the cheaper stream-K residual. GPU raw-speed frontier is "structurally exhausted" (`mi210-...:61`).
- **MI210 is not live production.** Ratified `P-GPU-1` requires a **production-named** kernel → every MI210 result stays **observation-grade** until v7 promotes and Gate-R/AXA rerun on `production-consolidated-v7` (`v7-promotion.md:30`).
- **The GDN model is served on CPU.** Qwen3.6-35B-A3B is the live frontdoor + coder_escalation, **CPU Q8** — K28 accelerates **GPU prefill of a model not served on GPU**.
- **On CPU, GDN is ~1-2% of prefill wall-clock** (PC-4d: "do not prototype recurrent GDN first while GDN/SSM/RMS stay at about 1-2%"). High node count ≠ high time. CPU is not a fallback justification.
- **Full-model prefill ceiling is bounded.** The entire serial-vs-generic-chunked gap is only ~6% of full-model prompt t/s — GDN is a meaningful but not dominant share of GPU prefill; a large op speedup dilutes at the model level.
- **Highest-EV action by every audit is promoting the already-banked v7 kernel** (operator-gated), not opening a new post-v7 GPU kernel project.

### Phase 0 — the cheap gate (run FIRST; ~1 operator bench window, no kernel authoring)

1. **GDN share of GPU prefill.** Via the `LLAMA_QWEN35_PREFILL_TRACE` scaffold (`cpu-prefill-compute-large-models.md` PC-4a) or rocprof op-attribution, measure the fraction of Qwen3.6-35B-A3B Q8 **GPU** prefill wall-clock the GDN op(s) consume at 2K/8K/32K.
2. **Ceiling model.** `full_model_gain ≈ gdn_prefill_share × (1 − 1/op_speedup)`. Optimistic op-level 3–5× (DeltaNet Fig. 1 range for d_head=128). E.g. share 25% × 4× → ~19% ceiling; share 8% → ~6%.
3. **Throwaway prototype signal (cheap).** Force `fused_gdn_ch` off and hand-fuse *just the per-chunk C-loop* (`delta-net-base.cpp:235-274`) into one small HIP kernel that keeps `S` in LDS across the loop, leaving the rest of the graph intact. Isolates the "fusion, not matmul" hypothesis at a fraction of the effort and predicts Phase 1's payoff.

**Gate decision:** proceed to Phase 1 **only if** the modeled ceiling is materially above the Part G alternatives *and* there is a concrete post-promotion path to decision-grade. Otherwise record Phase 0 as the K28 closeout ("headroom exists but bounded/observation-grade; deferred behind X") and stop.

---

## Part E — Staged implementation plan (if Phase 0 passes)

All work in **`/mnt/raid0/llm/llama.cpp-experimental`** (`experimental-v7-refresh-20260716`) — **never** touch `production-consolidated-v6`. The tree is currently dirty with the parallel agent's working state; coordinate before building. Gate the new kernel behind a runtime flag (mirror `GGML_CUDA_GDN_STATE_BF16` / `LLAMA_DISABLE_FUSED_GDN_CH`) so it is default-off and A/B-able.

**Phase 1 — fusion-only FP32 chunked kernel (primary deliverable).**
- New kernel in `gated_delta_net.cu` (the `//TODO` at :191): grid = one block per `(head, seq)`; loop over chunks; hold `S` (S_v×S_v tile) + the chunk's Q/K/V/g/β + C×C decay mask + triangular-solve scratch in LDS/registers.
- Reuse the existing FP32 warp-reduce math; the change is **locality and launch count**, not arithmetic. Wave64-correct (use `warpSize`/`ggml_cuda_get_physical_warp_size()`; do **not** assume 32).
- **Watch the VGPR budget** (issue #20354 landmine): the current kernel already shards state (`s_shard[rows_per_lane]`, rows_per_lane = S_v/64 = 2 on CDNA2), which is good — but adding chunk tiles + solve scratch can spill. Keep occupancy above the cliff; prefer 16×16 tiles over 32×32 in Phase 2 (16 accum-VGPR/lane) if register-limited.
- Keep the serial kernel as decode (`FGDN_AR`) and very-short-prefill path — mirror FLA's chunk/fused-recurrent split. Add a token-count threshold in `build_delta_net`.
- Target: rising (not falling) GB/s vs length on the K28.1 op microbench; full-model p2048/p8192/p32768 beating both current paths.

**Phase 2 — MFMA/bf16 (upside, separable).**
- Convert chunk matmuls (`KKᵀ`, `W=TK`, `U=TV`, `QKᵀ`, `QSᵀ`, output) to matrix-core ops via the **existing `ggml/src/ggml-cuda/mma.cuh`** abstraction — it has full `AMD_MFMA_AVAILABLE` support (16×16×16 bf16/fp16, 16×16×4 fp32) and is consumed by `fattn-mma-f16.cuh` (`using namespace ggml_cuda_mma;`). **Follow that template.**
- **Do NOT** copy `lightning-indexer.cu` — raw `nvcuda::wmma`, NVIDIA-only (`// TODO add support for AMD cards via rocWMMA`). That is the trap.
- **bf16 → use the `_1k` MFMA variants** (`mfma_f32_16x16x16bf16_1k`); the non-`_1k` gfx908 carryovers are half-rate. **fp32 accumulate; keep the triangular solve in fp32** (IEEE on MI210 — no TF32). Appendix 4 for the intrinsic table and per-lane VGPR layout.
- CDNA2 constraints: LDS ~64 KB/CU (C=64,d=128 working set is tight but fits — why FLA caps at 64); **no async-copy/TMA** → manual software-pipeline + LDS double-buffer behind `s_barrier`; keep the inter-chunk scan **inside one block** (no cross-block hipCUB scans/atomics — slow on CDNA2). Use `amd_matrix_instruction_calculator` (`--architecture cdna2`) for authoritative fragment↔lane maps.

**Phase 3 — (only if Phase 2 saturates and more is wanted) TFLA-style large chunks.** Add the second level of intra-chunk parallelism to grow C into the 128–256 band; re-sweep `L_opt` for CDNA2. High effort; do not attempt before Phase 2 lands.

---

## Part F — Correctness invariants + validation recipe (hard requirements)

Any kernel **must preserve** (`gemma-challenge-kernel-techniques-v7.md:390`, `mi210-...:161`):
- **GDA and KDA** behavior (scalar vs per-channel gate; `g->ne[0]==1` vs `==S_v`).
- **Transposed recurrent-state layout** (`M[col][i]=S[i][col]`, `gated_delta_net.cu:65`).
- **`K > 1` snapshot semantics** and the **fused-cache bridge** (`ggml_cuda_op_gated_delta_net_fused_cache`).

**The MTP-snapshot gotcha (fork-specific; not in any FLA/FlashQLA reference — design it in):** the current kernel writes **per-token** state snapshots for spec-dec rollback (`keep_rs_t`, K slots, `gated_delta_net.cu:156-168`). A chunked kernel naturally produces **per-chunk-boundary** states. Two options:
- (a) **Restrict the chunked path to `K==1`** (final-state-only prefill), fall back to the serial kernel when snapshots are requested — simplest; or
- (b) re-derive intra-chunk per-token states on demand (more work; only if (a)'s fallback is hot).
Boundary tests already lock this: `231db22c7` (GDA 65-token/K=4 across the chunk boundary) and `41ae83402` (KDA 65-token/K=4 + fused-cache K≤1 skip). The kernel must pass them.

**Validation (all must pass before any promotion claim):**
1. `test-backend-ops test -o GATED_DELTA_NET -b ROCm0 -j 8` **and** `-b CPU -j 8` — incl. the 65-token/K=4 GDA+KDA overflow cases.
2. **Long-prefill PPL parity** vs the serial kernel on Qwen3.6-35B-A3B (and a Qwen3-Next / Qwen3.5 GDN checkpoint if available) — match within noise. Pair every speed number with a correctness/garbage check.
3. **Prefill t/s** via `llama-bench` on the experimental (v7-candidate) binary — the K28.1 op microbench (expect rising GB/s vs length) and full-model p2048/p8192/p32768, vs the serial-kernel baseline in `data/k28_gdn_perf/`.
4. Sampling-sensitive checks use **production temp + seed 42**, no-think.

All results stay **observation-grade** until v7 is operator-promoted and rerun under production-named `P-GPU-1` — state this explicitly; never present MI210 numbers as decision-grade.

---

## Part G — Adjacent levers to weigh against K28 (may be higher-EV)

- **Batched-decode state bandwidth (live, partly banked).** BF16 GDN state gives **+21.5% @B=32** across the GDN family. Single-stream is neutral, but serving is batched. A batched-decode-optimized GDN kernel (fold B sequences' rank-1 updates into a matmul; further state-precision narrowing) targets the *serving-critical* path, is grounded in a measured win, and is lever #10 territory — likely closer to production value than prefill. NB the decode path is the memory-bound `fused_recurrent` shape (no `tl.dot`; Appendix 2 §5) — sized to saturate HBM.
- **Residency/footprint (not speed).** BF16 (or lower) state halves the `[S_v²·H·n_seqs·K-snapshots]` cache — relevant to how many sequences / how deep an MTP snapshot horizon fits in VRAM at high batch. The pure "residency/memory argument"; needs a separate quality/coherence gate.
- **Deprioritize:** CPU GDN (~1-2% of prefill), and jumping straight to TFLA chunk-128–256 (needs the second-level parallelism scheme; Phase 3 only).

---

## Part H — Key references

**Local source (`/mnt/raid0/llm/llama.cpp-experimental/`):** `ggml/src/ggml-cuda/gated_delta_net.cu` (`:74` loop, `:156-168` snapshots, `:191` TODO) + `.cuh`; `src/models/delta-net-base.cpp` (`:16`/`:166`/`:235-274`/`:289`/`:373`/`:425`); `ggml/src/ggml-cuda/mma.cuh` (reuse), `fattn-mma-f16.cuh`, `solve_tri.cu`, `cumsum.cu`, `tri.cu`; `src/models/qwen35moe.cpp:93-96`.
**Local evidence:** `data/k28_gdn_perf/` (K28.1 op profile, K28.2 fused-vs-graph, K28.3 BF16 state).
**Handoffs:** `mi210-big-model-and-acceleration-roadmap.md` (:161-199), `gemma-challenge-kernel-techniques-v7.md` (:60-78, :390), `inference-acceleration-index.md` (:50-93), `v7-promotion.md`, `cpu-prefill-compute-large-models.md` (PC-4d).

---

# Appendix 1 — The chunked algorithm (DeltaNet + Gated DeltaNet equations)

Notation: `L`=seq len, `C`=chunk, `d_k/d_v`=head dims, `S∈ℝ^{d_v×d_k}`, chunk matrices `Q_[t],K_[t],V_[t],U_[t],W_[t]∈ℝ^{C×d}`. `⊙`=elementwise, `strictLower(·)`=strict lower triangle. `[DN-n]`=DeltaNet arXiv:2406.06484v4; `[GDN-n]`=Gated DeltaNet arXiv:2412.06464v3.

**Per-token recurrence.**
- Ungated `[DN-3]`: `S_t = S_{t-1}(I − β_t k_t k_tᵀ) + β_t v_t k_tᵀ`. `β_t=σ(W_β x_t)∈(0,1)` write strength; `q,k = SiLU(Wx)/‖·‖₂` (L2-normed); `o_t = S_t q_t`. `I − β_t k_t k_tᵀ` is a generalized Householder (rank-1). Online-learning view: delta/Widrow-Hoff step on `½‖S k_t − v_t‖²`.
- Gated `[GDN-10]`: `S_t = S_{t-1}(α_t(I − β_t k_t k_tᵀ)) + β_t v_t k_tᵀ`. `α_t∈(0,1)` scalar decay (Mamba2 parameterization). α=1 → DeltaNet; drop the `kkᵀ` erase term → Mamba2. Optional `β_t∈(0,2)` for negative eigenvalues/state-tracking.

**WY / UT transform (the triangular solve).** Reparameterize state as `S_t = Σ_{i≤t} u_i k_iᵀ`, `u_t := β_t(v_t − Σ_{i<t} u_i (k_iᵀk_t))` `[DN-3]` (O(d) memory, no d×d state materialized). Within a chunk:
```
T_[t] = ( I + strictLower(diag(β_[t]) K_[t] K_[t]ᵀ) )⁻¹ diag(β_[t])   ∈ ℝ^{C×C}   [DN-10]/[GDN-6]
W_[t] = T_[t] K_[t] ,   U_[t] = T_[t] V_[t]                          ∈ ℝ^{C×d}   [DN-11]/[GDN-7]
```
**SIGN: it is `(I + strictLower(...))⁻¹` (PLUS).** `I + strictLower(...)` is unit-lower-triangular → inverse is **exact by forward substitution** ("UT transform", refs Joffrain 2006 / Bischof–Van Loan 1985 compact-WY). FLA sub-blocks this C×C solve into 4× 16×16 matmul blocks (Appendix 2). Fully-parallel form `A=(QKᵀ⊙M)T` is avoided in training because forming `T` cubically per full sequence is too costly — chunking bounds it to C.

**Chunkwise decomposition + serial/parallel split.**
- Inter-chunk state carry `[DN-8]` (**the O(L/C) SERIAL scan**): `S_[t+1] = S_[t] + (U_[t] − W_[t] S_[t]ᵀ)ᵀ K_[t]`.
- **Serial:** (a) inter-chunk scan (O(L/C) steps carrying S); (b) the C×C forward-substitution solve (O(C) per chunk, but all chunks' solves run in parallel).
- **Parallel matmuls (tensor-core), within and across chunks:** `KKᵀ`, `QKᵀ` (C×C), `TK`, `TV` `[DN-11]`, `(U−WSᵀ)ᵀK` `[DN-8]`, and outputs `[DN-9]`.
- Complexity `O(LCd + Ld²)` FLOPs, `O(L/C)` sequential steps. C=L → fully parallel; C=1 → pure recurrent.

**Output `[DN-9]`:** `O_[t] = Q_[t] S_[t]ᵀ + (Q_[t] K_[t]ᵀ ⊙ M)(U_[t] − W_[t] S_[t]ᵀ)`. Inter term `Q S_[t]ᵀ` (queries vs carried state, **no mask**); intra term causal-masked (`M` lower-tri inclusive) over **corrected pseudo-values** `U − W S_[t]ᵀ` (the `−W S_[t]ᵀ` prevents double-counting the inherited state).

**Gated cumulative decay (GDN §2.1–3.3).** `γ_[t]^r = ∏_{j=tC+1}^{tC+r} α_j` (cumulative product within chunk, reset per chunk) = `exp(cumsum(log α))`. Decay-aware mask `(Γ_[t])_{ij} = γ_[t]^i/γ_[t]^j` for `i≥j` else 0. Arrow scalings `[GDN-2]`: `←q^r=γ^r q^r` (to chunk start), `→k^r=(γ^C/γ^r)k^r`, `→v^r=(γ^C/γ^r)v^r`, `→S=γ^C S` (to chunk end).
- **Value-side UT solve carries the decay mask:** `Ũ_[t] = [ I + strictLower(diag(β)(Γ_[t] ⊙ K K ᵀ)) ]⁻¹ diag(β) V_[t]`.
- **KEY ASYMMETRY:** the **W (key-side) solve keeps plain `KKᵀ`** (`W=TK`, no Γ); only the **Ũ (value-side) solve uses `Γ⊙KKᵀ`**. γ re-enters at output/carry via the arrows.
- Gated carry: `S_[t+1] = →S_[t] + (Ũ_[t] − ←W_[t] S_[t]ᵀ)ᵀ →K_[t] = γ^C S_[t] + (Ũ − Diag(γ)W Sᵀ)ᵀ Diag(γ^C/γ) K`.
- Gated output: `O_[t] = ←Q_[t] S_[t]ᵀ + (Q_[t] K_[t]ᵀ ⊙ Γ_[t])(Ũ_[t] − ←W_[t] S_[t]ᵀ)`.

**Speedups.** DeltaNet Fig. 1 (Triton chunk-vs-recurrent, d=2048): speedup **grows with L and d_head**, approaching **~30×** at L≈16K/d_head=256, low single digits at L≈0.5–1K/d_head=64 (over a recurrent baseline already 2× the original Schlag CUDA kernel). Gated DeltaNet Fig. 3 (1.3B, H100 training throughput): GDN ≈ DeltaNet ≈ 45K tok/s, ~2–3K slower than Mamba2 — the gated transition matrix adds only marginal overhead.

**Chunk size + stability.** DeltaNet: C "usually 64 or 128". GDN: C a multiple of 16, **64 in FLA**. Stability guarantee is paper-grounded: L2-normalizing q,k bounds eigenvalues of `I − β kkᵀ` ≤ 1 (at β=1, unit k, it's a projection). **fp32 caveat:** "keep the tri-solve/cumsum in fp32" is a **FLA implementation practice**, not a paper claim — validate against the reference kernel; the paper's stability lever is the L2-norm eigenvalue bound.

---

# Appendix 2 — FLA reference kernel decomposition + FlashQLA port map

**FLA chunked forward** (`fla/ops/gated_delta_rule/chunk.py`, entry `chunk_gated_delta_rule` / alias `chunk_gdn`) — 5 kernels to mirror, collapsed into one fused launch on MI210:

| Stage | Kernel | Computes | Grid / parallelism | `tl.dot` |
|---|---|---|---|---|
| Gate prepass | `gdn_gate_chunk_cumsum_scalar_kernel` (`gate.py`) / `chunk_local_cumsum` | log-space per-chunk gate cumsum (`b_gate=-exp(b_A)*softplus(b_g)`, `cumsum`) | B·H·chunks | no |
| WY / intra solve | `chunk_gated_delta_rule_fwd_kkt_solve_kernel` (`chunk_fwd.py`, aka `..._fwd_intra`) | strict-lower `A=β·(KKᵀ)` with gate `exp2(g_i−g_j)`, then **in-register `(I+A)⁻¹` via 4×[16×16] block decomposition** | `(NT, B·HV)`, K serial | **yes** |
| Inter-chunk state scan | `chunk_gated_delta_rule_fwd_kernel_h_blockdim64` (`common/chunk_delta_h.py`, aka `..._fwd_h`) | carries d×d state `h` across chunks; per-chunk `h` snapshots + `v_new` | `(cdiv(V,BV), N·HV)`, **serial `for i_t in NT`** | **yes** |
| WY recompute w,u | `recompute_w_u_fwd_kernel` (`wy_fast.py`) | `w=A@(β·k·exp2(g))`, `u=A@(β·v)` | B·HV·chunks | **yes** |
| Output | `chunk_fwd_kernel_o` (`common/chunk_o.py`, aka `chunk_fwd_o`) | `o=(q@h_inter)·scale + tril(q@kᵀ)@v·scale` | `(cdiv(V,BV), NT, B·HV)` fully parallel | **yes** |

Dependency order: gate-cumsum → kkt_solve (A) → recompute_w_u (w needed by h) → fwd_h (state scan) → fwd_o.

- **Chunk-size assertion:** `if chunk_size not in (16,32,64): raise ValueError(...)`. Default 64. Cap = SRAM/`BT`: the intra kernel materializes a `[BT,BT]` fp32 inverse and does the WY inverse as **4 blocks of `BC=16`** (4×16=64). Larger BT blows the register/SRAM budget.
- **Precision:** matmul inputs native bf16/fp16; **all accumulators fp32** (`b_A`,`b_o`,`b_h1`). Triangular solve is **fp32-mandatory** — `SOLVE_TRIL_DOT_PRECISION = 'tf32' if IS_TF32_SUPPORTED else 'ieee'`; the u-projection forces `allow_tf32=False`. **On MI210 there is no TF32 → the solve runs true IEEE fp32** (numerically ideal, full-rate fp32 cost).
- **In-kernel options:** `use_qk_l2norm_in_kernel` (L2-norm q,k inline), `use_beta_sigmoid_in_kernel` (+`allow_neg_eigval` needs the sigmoid), **log2-space gate** (`chunk_local_cumsum(g, scale=RCP_LN2)` → `exp2(g_i−g_j)` instead of `exp`, faster + overflow-safe).
- **Inter-chunk scan occupancy limiter:** concurrency = `N·HV·cdiv(V,BV)` blocks; the d×d state lives in registers/SRAM across the whole serial chunk loop → cannot parallelize across chunks. On MI210 provide enough (head, V-block) tiles to fill 104 CUs. `state_v_first` toggles `(K,V)` vs `(V,K)` layout — pick the MFMA-friendly transpose.
- **Decode path** `fused_recurrent_gated_delta_rule` (`fused_recurrent.py`): **no `tl.dot`** — pure elementwise (`tl.sum(b_h*b_k[None,:],1)`, decay `b_h*=exp(b_g)`), one d×d state HBM round-trip per token, **memory-bound**. Chunking buys nothing at T=1. Prefill→decode state layout is compatible. **MI210 decode wants this kernel, sized to saturate HBM** (matches the project's decode-BW-bound intuition).
- **ROCm:** FLA ships a `rocm` extra ("platform-agnostic, verified on NVIDIA/AMD/Intel"). CDNA2 caveats: TF32 paths → IEEE fp32; NVIDIA-keyed `check_shared_mem('ampere'/'ada')` autotune branches fall to conservative defaults → **re-autotune `BV`/`num_stages`/`num_warps`**; `num_stages` = LDS double-buffering (not hardware async-copy) → prefer 1–2; verify `tl.dot` shapes (BK 32/64, BT≤64) lower to MFMA cleanly.

**FlashQLA (`QwenLM/FlashQLA`, TileLang).** Hardware: **SM90 (Hopper) / SM100 (Blackwell)**, CUDA ≥12.8; arch-partitioned (`chunk/hopper|blackwell|blackwell_sm120/{kkt_solve,prepare_h,fused_fwd,fused_bwd,cp_fwd,cp_bwd}.py`) — **same decomposition as FLA**; prefill/training-only (no decode kernel), sm120 has no backward. Speedup vs FLA: **2–3× fwd** (measured H200: 32k 3.17×, 16k 2.77×, 8k 2.20×), **~2–4.5× bwd**. Tiles: `chunk_size=64`, `DK=DV=128`.

| FlashQLA technique | Win via | Ports to MI210/CDNA2? |
|---|---|---|
| 4-way warpgroup specialization (producer + S/V/O consumers), `set_max_nreg` | overlap TMA / Tensor-Core / CUDA-Core | **No** — CDNA2 has no HW warp-specialization / dynamic register realloc; emulate with multi-wavefront occupancy + manual LDS staging |
| `T.tma_copy` (TMA async bulk) + `mbarrier` double-buffer | async HBM→SMEM, zero register cost | **No** — no TMA/mbarrier; use `buffer_load`/`ds_read` + LDS double-buffer + `s_barrier` |
| `T.gemm` = `wgmma` (async warpgroup MMA), fp32 accum | tensor-core throughput | **Partially** — replace with **MFMA** (`v_mfma_f32_16x16x16_bf16`); synchronous, no async-MMA overlap |
| Single-launch fusion, algebraic reformulation, gate-decay context-parallel splitting | fewer launches, less HBM round-trip, more SM utilization | **Yes** — algorithm-level, hardware-agnostic; **lift these** |

**Net port guidance:** take FLA's Triton decomposition as the ROCm-runnable baseline (kkt_solve → fwd_h → w/u → fwd_o; chunk 64, BC=16, fp32 tri-solve, log2 gate); adopt FlashQLA's *algorithmic* wins (single-launch fusion, algebraic reformulation, gate-decay context-parallel splitting); **drop its TMA/warpgroup/wgmma machinery** — replace with occupancy-based overlap, LDS double-buffering behind `s_barrier`, and MFMA. Even NVIDIA needed per-arch rewrites (SM90 vs SM100 vs sm120-no-backward), so an MI210 kernel is a legitimate third arch target.

---

# Appendix 3 — TFLA chunk-size theory + AttentionEngine CDNA2 feasibility

**TFLA (arXiv:2503.14376, NeurIPS 2025; code `NX-AI/mlstm_kernels`).**
- **Problem with chunk≤64:** "chunk size of FLA is limited (typically L=64) by physical SRAM size … we have to materialize many states in HBM, where the number of states is Nc=⌈T/L⌉ … low arithmetic intensity and high GPU memory consumption." Small L → large Nc inter-chunk states, each written/re-read from HBM → IO-bound, low FLOP:byte.
- **Fix:** a **second level of sequence parallelism within a chunk** — tile the intra-chunk attention matrix along block dims `B_Lhq, B_Lkv, B_dqk, B_dhv` (parallelize some, accumulate others in an in-kernel loop). Decouples chunk size from SRAM → arbitrarily large chunks → smaller Nc → less HBM state traffic. **This is the transferable idea: two nested parallel levels (inter-chunk recurrence + intra-chunk tiled matmuls), not FLA's single chunk-parallel level.**
- **Runtime-optimal chunk = 128–256** ("there exists an optimal chunk size (between 128 and 256) at which runtime is minimized"). Scaling: **`L_opt ∝ √(d · I)`** (d=head dim, I=accelerator computational intensity / roofline ridge point). **MI210's ridge point differs from H100 (lower matrix-core FLOPs, ~1.6 TB/s HBM) → re-sweep L_opt; start the search in 128–256 but expect it to sit lower.** Optimize **wall-clock, not FLOP utilization** ("FLOPs/s alone can be misleading").
- **Numbers (H100):** >2× vs Mamba2 kernels at all lengths; faster than FlashAttention-3 for long sequences; mLSTMsig 30% faster fwd than mLSTMexp (dropping the max/normalizer state removes cross-tile reductions → better fusion — relevant if GDN gating avoids a running-max reduction).
- **Precision:** bf16 in / fp32 accum is the reference-code + Triton convention (not an explicit paper sentence). Backward stores max/normalizer states in fwd and reuses (no heavy recompute).
- *Uncertain:* the closed-form arithmetic-intensity `AI(L)` (Appendix G, Eq. 109) and exact ridge-point numbers were MathML the fetch couldn't extract — read the PDF Appendix G if the closed form is needed.

**AttentionEngine (arXiv:2502.15349).**
- **AMD stack:** MI250 (CDNA2, same gfx90a family), **ROCm 6.2.4, Triton 3.1.0**. **Avg 3.3× fwd / 2.0× bwd** over baselines on MI250. MI210 = 1 GCD of MI250 → single-GCD numbers transfer.
- **Coverage caveat (important):** generates kernels for softmax/sigmoid/ReLU/multi-scale-retention (parallel) and Mamba2/RFA/retention-recurrent/gated-retention (recurrent). **DeltaNet/GDN are NOT covered — not on NVIDIA, not on AMD.** So it proves the **CDNA2 codegen path for gated linear recurrences is competitive**, and gives a gated-retention/Mamba2 template, but **not a GDN kernel**; the delta-rule outer-product correction is the un-templated part.
- **Codegen:** TileLang (+CuTe), explicit mem-location control (global/shared/registers), "chunk parallelism to fully exploit tensor cores" for recurrent attention, targets AMD Matrix Cores + ALUs + async-copy units. **Not standalone** — integrated into PyTorch; use as design/autotune oracle, not a code source.
- **Silent on CDNA2 microarch:** no wave64, LDS size, MFMA tile shapes, or async-copy-vs-TMA detail. Those must come from Appendix 4 + your own benches.

---

# Appendix 4 — Upstream llama.cpp GDN prior art + gfx90a MFMA reference

**Upstream GDN PR/issue chain:**

| PR/Issue | Substance | Relevance |
|---|---|---|
| **#19504** (am17an, merged) | Adds `GGML_OP_GATED_DELTA_NET`: CPU vector ref + **CUDA autoregressive** (token-by-token) kernel; GDA+KDA; chunked path deferred. RTX 5090 83.9→106 t/s (no graphs). | The op + serial kernel we have. |
| **#20340** (ggerganov, merged) | Enables the **chunked fused prefill path** (feeds token chunks to the op). DGX Spark Kimi-linear 48B Q4_K_M: pp512 **1.79×**, pp2048 **2.11×**. Qwen3.5 smaller (1.07–1.15×). | "Chunked" = multi-token batching to the *serial* kernel, not a chunk-parallel matmul kernel — consistent with our audit. |
| **#20391 / #20361** | CUDA AR kernel improvements / Metal GDN kernel. | Backend coverage. |
| **#19375** (ggerganov, merged) | **Graph-builder only** — removes copies/concats (`ggml_concat`→`ggml_set_inplace`), redundant masks (`ggml_tri`/`ggml_diag`), transpose→sum_rows→transpose collapse. M2 Ultra qwen3next 80B Q4_0: pp1 1.37×, pp512 1.21×, tg32 1.33×. `ggml-cuda.cu` +2/−1 (a name-prefix branch, **no kernel change**). | **Not** a fused chunked kernel; the `//TODO` is still open. |
| **#20354** (nsyring, closed dup) | **The AMD-perf gap.** Fused GDN kernel ~**11.8 t/s** on ROCm/HIP (RDNA3.5 gfx1151) vs 50–80 expected. Root causes: (a) **register pressure** — `float s[S_v]` per thread (~512 B) → **spilling to VRAM/LDS**; (b) `hipMemcpyWithStream` = 92–95% of decode time (>15 GB models); (c) "tuned for CUDA's warp architecture, not RDNA's Wave32". | **The landmine.** RDNA3.5/Wave32, but the register-pressure caution applies to any AMD part. An MI210/CDNA2 (Wave64) fused chunked kernel is the missing piece. |
| **#24712** | `sched_reserve` device-placement warning (layer CPU, fused GDN tensor CUDA0). | Correctness/scheduling, not perf. |

**gfx90a MFMA intrinsics (`__builtin_amdgcn_mfma_*`; Wave64, 64-lane fragments):**

*FP16 in → FP32 out (1024 FLOP/cyc/CU — throughput tiles):* `mfma_f32_16x16x16f16` (M16 N16 K16, 1 blk, 32 cyc), `mfma_f32_32x32x8f16` (M32 N32 K8, 1 blk, 64 cyc), plus K4 multi-block variants.
*BF16 in → FP32 out — **use `_1k` on CDNA2** (full-rate, K matches f16):* `mfma_f32_16x16x16bf16_1k`, `mfma_f32_32x32x8bf16_1k`. **Avoid** non-`_1k` gfx908 carryovers (`16x16x8bf16`, `32x32x4bf16`) — half-rate CDNA1.
*FP32 in → FP32 out (256 FLOP/cyc/CU — for the tri-solve/accum):* `mfma_f32_16x16x4f32` (K4), `mfma_f32_32x32x2f32` (K2).
*INT8 → INT32 (quantized paths):* `mfma_i32_16x16x16i8`, `mfma_i32_32x32x8i8` (CDNA2 int8 K is 4× smaller than CDNA3).

Per-lane VGPR fragment cost (elements/lane = rows×cols/64; fp16/bf16 packed 2/VGPR, accum 1 fp32/VGPR):

| Tile | A/lane | B/lane | C/D accum/lane |
|---|---|---|---|
| 16×16×16 f16/bf16 | 2 VGPR | 2 VGPR | **4 VGPR** |
| 32×32×8 f16/bf16 | 2 VGPR | 2 VGPR | **16 VGPR** |
| 16×16×4 f32 | 1 VGPR | 1 VGPR | 4 VGPR |

**→ 32×32 tiles cost 16 accum VGPR/lane; combined with GDN state that risks the #20354 spill. Prefer 16×16 tiles or partition state to keep VGPR live-count under the occupancy cliff.**

**CDNA2 platform facts:** Wave64 (use `warpSize`/`__AMDGCN_WAVEFRONT_SIZE__`, never assume 32); LDS **64 KB/CU** (spec-sourced — verify via `rocminfo`), read BW ~128 B/clk/CU; VGPR file 512/SIMD (512 KB/CU); **NO async-copy/TMA/cp.async** (`global_load_lds` moves only 1 dword/lane on gfx90a) → **manual software-pipelined double-buffering** (prefetch next tile before consuming current, rely on occupancy to hide latency). Access paths: **raw `__builtin_amdgcn_mfma_*`** (max control; needed for small-K tiles), **rocWMMA** (16×16×16 / 32×32×8 only — **missing** small-K 16×16×4/4×4×4 per issue #509 closed-unimplemented → drop to raw intrinsics), Composable Kernel (heavyweight, poor fit). Authoritative fragment↔lane maps: **`github.com/ROCm/amd_matrix_instruction_calculator`** — `./matrix_calculator.py --architecture cdna2 --instruction v_mfma_f32_16x16x16f16 --detail-instruction`.

**External sources:** DeltaNet arXiv:2406.06484v4 §2.1–3.3; Gated DeltaNet arXiv:2412.06464v3 §2.1–3.4; FLA `fla/ops/gated_delta_rule/{chunk,chunk_fwd,fused_recurrent,wy_fast,gate}.py` + `common/{chunk_delta_h,chunk_o}.py`; FlashQLA `github.com/QwenLM/FlashQLA`; TFLA arXiv:2503.14376 (Appendix G for AI closed form); AttentionEngine arXiv:2502.15349; llama.cpp PRs #19504/#20340/#20391/#20361/#19375, issues #20354/#24712, rocWMMA #509; AMD MFMA lab notes (gpuopen.com/learn/amd-lab-notes matrix-cores) + `ROCm/amd_matrix_instruction_calculator`.

---

## Verification of this handoff (how the receiving agent confirms the framing before acting)
- Re-run the K28.1 op microbench; confirm the **falling GB/s vs length** curve (serial-dependency signature) before assuming headroom.
- Confirm `solve_tri`/`tri`/`cumsum` have live ROCm impls (they do — so the generic graph's loss is dispatch/IO, not CPU fallback): `test-backend-ops -o SOLVE_TRI -b ROCm0`.
- Confirm `mma.cuh` compiles the `AMD_MFMA_AVAILABLE` path in the current `build-hip` before committing to Phase 2.
- Verify the UT-transform sign against the reference kernel: `(I + strictLower(...))⁻¹` (Appendix 1).
- Run **Phase 0 attribution first** and let the modeled ceiling — not this document — decide whether Phase 1 proceeds.
