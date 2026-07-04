# 2026-07-03 — MI210 GPU-only speed campaign: Qwen3.6-27B-MTP-Q8_0 (LIVING CHECKPOINT)

**Goal (operator):** make `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` run as fast as possible on the MI210, GPU-only. Track **both single-stream and aggregate-concurrent** throughput. Kernel work → `llama.cpp-experimental` (never production-consolidated-v6). Explore vLLM / close llama.cpp↔vLLM gaps. Runs in parallel with a separate CPU-only session (no CPU/RAM contention — GPU-resident decode is insulated).

This is a **living checkpoint** — updated after every phase/measurement (operator asked for continuous checkpointing; periodic `/wrap-up` dispatched to an opus medium subagent).

## Session summary (outcomes) — 2026-07-03
Single-stream best for Qwen3.6-27B-MTP-Q8_0 rose **29 → 40.4 t/s (+37%)**: embedded-NEXTN MTP (no `-md`, n_max=3, GPU-pinned draft) reaches 33.6, then the **MMVQ→MMQ small-batch verify-dispatch fix** adds **+17.4%** to 40.4 (validated in `llama.cpp-experimental` commit `de447119f`; ~1-line diff, coherent output, numerically-valid-not-bit-exact; **operator-gated for prod promotion**). Scoping results established this session:
- **MMVQ fix is dense-Q8-specific** — it does NOT transfer to MoE experts (separate `get_mmvq_mmid_max_batch` dispatch); frontdoor qwen35moe stays kernel-flat (+0.7%). Confirmed on a **second dense model** (gemma-31B dense-Q8: **+31.7%**, same sign, larger magnitude).
- **MTP is net-negative for MoE on GPU** (head-quant-independent — measured control: gemma-26B plain 94.3 vs Q8-head MTP ~89.6 vs f16-head MTP ~81.5, both lose to plain → it's the MoE-verify + GPU-resident overhead, not the head quant); GPU-resident MoE should run plain (gemma bf16 plain 96.6 > MTP 84.5).
- **bf16 > Q8 crossover at high batch** (dequant-amortization: bf16 744 vs Q8 561 @ B=32; 10.19× vs 5.81× scaling).
- **GDN recurrence is the aggregate/batch-scaling bottleneck and is qwen35-specific** (2%→19.5% of decode across B1→B32); the fused-verify hypothesis was **FALSIFIED** (verify is already fused). The **GDN-MFMA kernel was then KILLED for decode** (rocprofv2 @B=32: memory/occupancy-latency-bound — MemUnitBusy 65% vs VALUBusy 16%, MfmaUtil **0%**, ~42% occupancy — no compute bottleneck an MFMA kernel could relieve; the real GDN lever is occupancy + recurrent-state traffic/layout). Frontdoor still sustains **~430 t/s aggregate @128-way at 80k context**.
- **Production CPU fix briefed** (commit `5879129b`): drop the `-md <same GGUF>` double-load for embedded-NEXTN roles (frontdoor/architect) — it costs 2× DRAM on BW-bound CPU decode.

**These final probes have since COMPLETED** (see "Final probes" line below / findings-05b §9): KV-quant **no-help** (VRAM not the binding constraint on the weight-dominated MoE), GDN-MFMA **KILLED** (rocprofv2), context-flatness **FALSIFIED** (SWA confound — hybrid −22% vs gemma-SWA −8%), gemma-31B dense-Q8 MMVQ **CONFIRMED +31.7%**.

**Still PENDING (kernel subagent running now, in `llama.cpp-experimental`, uncommitted; results fold in next):** n-gram/prompt-lookup GPU spec-dec test, Q8 dequant-GEMV roofline profiling, and MFMA compute-bound-path (prefill/high-batch) measurement.

## Fixed facts
- **Model arch**: `qwen35` = hybrid SSM (delta-net: state_size 128, group_count 16, conv_kernel 4, inner_size 6144) + attention. **DENSE (no experts)** → batches cleanly, the MoE-weaker-batching caveat does NOT apply. 65 blocks, embd 5120, FFN 17408, 24 heads / 4 KV heads, ctx 262144, M-RoPE (dim_sections [11,11,10,0], freq_base 1e7). **Embedded 1-layer NEXTN MTP head** (`nextn_predict_layers=1`). Q8_0, 29.0 GB file.
- **Substrate**: MI210 gfx90a CDNA2, 64 GB HBM2e (~65.4 GB free), ~1.64 TB/s peak, ROCm 6.2. HIP build = `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip` (version 9777 / `0ebf1b4d7`, the fp8-fix leg). Must prepend `LD_LIBRARY_PATH=$HIP/bin:/opt/rocm/lib`.
- **Prior roofline (2026-07-02 obs, non-MTP Q8)**: 28.69 t/s = 47% roofline (766 GB/s) single-stream; fp16 62%; batched fp16 (8B) scaled ~15×. All numbers OBSERVATIONS per MEASUREMENT.md.
- **Guardrails**: GPU-only (`-ngl 99`), no CPU offload/sidecar; pair every speed number with a correctness/garbage check; label observation vs gating.

## Phases
- [x] **P0 — harness + baseline** (DONE): arch ✅ + op-coverage smoke; single-stream (llama-bench pp512/tg128, -fa 0/1) + MTP (llama-server draft-mtp: α + speedup) + aggregate (llama-batched-bench + llama-server -np sweep).
- [x] **P1 — runtime-knob sweep** (DONE): -np dequant-amortization sweep; -fa/ubatch/MMQ-vs-rocBLAS/KV-quant/HIP-env/HIP-graph; MTP×batching crossover → latency-vs-throughput Pareto. **Settled config below; no runtime knob moves the ceiling.**
- [x] **P2 — vLLM reference + gap-closing** (DONE): current-vLLM qwen35 support on gfx90a? → **NOT viable on gfx90a** (4 blockers below); gap-closing = porting GDN algorithm into our HIP/ggml, not running vLLM.
- [x] **P3 — kernel authoring (llama.cpp-experimental)** (DONE — MMVQ fix measured +17.4%; both in-flight audits landed): fork change-site audit + rocprof done → the reframed GDN fused-verify hypothesis is **FALSIFIED** (verify is already fused). The real single-stream lever is the **MMVQ→MMQ small-batch verify-dispatch fix** (~1 line, ~2× projected), **in build+measure in `llama.cpp-experimental` now**; GDN recurrence is the *aggregate* bottleneck (a separate, larger kernel). See "P3 findings" section below.
- [x] **P4 — synthesize** 2 winning configs + record in GPU handoffs (DONE — see "P3/P4 RESULTS" below + findings-05b §1/§2/§7).

## Measurement log (append-only; every number is an OBSERVATION unless tagged P-GPU-1)
| date | phase | config | single t/s | aggregate t/s @ conc | roofline% | correctness | notes |
|------|-------|--------|-----------:|---------------------:|----------:|-------------|-------|
| 07-03 | P0 | plain Q8, -fa 0, `llama-bench` tg128 | **29.51** (±0.01) | — | ~52% (856 GB/s) | pending eyeball | -fa 1 = 29.16 (FA hurts decode); pp512 840/849 t/s |
| 07-03 | P0 | plain Q8 aggregate `-npl 1..64` | — | _in flight_ | — | — | batched-bench npp128/ntg128 |

**P0 single-stream read (2026-07-03):** plain Q8 decode **29.51 t/s / ~52% roofline** via **`llama-bench`** (`-fa 0` beats `-fa 1` for decode — FA is prefill-only on gfx90a, re-confirmed). This is the MTP-OFF floor.

> **Baseline labeling (reconciled):** two plain single-stream numbers exist and are NOT interchangeable — **29.51 t/s via `llama-bench`** and **29.06 t/s via `llama-server`**. The MTP result (33.61) is measured under `llama-server`, so the **`+15.6%` uplift is `33.61 / 29.06` (apples-to-apples, both `llama-server`)**. Do not compute the uplift against the `llama-bench` 29.51.

**P0 aggregate curve (batched-bench, npp128/ntg128, S_TG = aggregate decode t/s):** B=1 **29.4** · 2 46.9 · 4 48.8 · 8 68.9 · 16 138.1 · 32 **165.8** · 64 171.5. Full GPU residency, no op fallback. **Sweet spot B=32 (~5.6× single); B=64 adds only +3.4%.** Scaling caps at ~5.8× — well below a pure-attention model's ~15× — because the hybrid-SSM recurrent state is per-sequence (batching the SSM scan doesn't amortize weight reads the way attention does). Weight-BW util falls 856→~150 GB/s across the batch (findings-05 batch-1-artifact confirmed).

**P0 MTP single-stream — NO speedup, ROOT-CAUSED (2026-07-03):** `--spec-type draft-mtp -md <same 27GB file>` → decode **29.75 t/s ≈ plain 29.51 (+0.8%)** despite draft acceptance **53.6%** (156/291, mean-accept 2.59 of n_max=3, per-pos 0.755/0.490/0.347) and correct output. Server log: *"estimated memory usage of draft model is 26894 MiB; loading draft model Qwen3.6-27B-MTP-Q8_0.gguf"* — i.e. `-md <same file>` **loads the full 27 GB model as the draft**, so each draft token costs a full-model forward pass, cancelling the acceptance savings (drafting dur only 806 ms, but target eval unchanged at ~8.6 s / 256 tok). This is the findings-02 §2 prediction ("embedded-MTP needs the no-`-md` path; small fork change if ever needed"). **The embedded NEXTN head must draft cheaply from the target's hidden state, not run as a full second model** — this is the #1 single-stream lever and likely needs a fork change in `llama.cpp-experimental`. Investigating the invocation first (no-`-md` embedded path) before concluding code work.

**P1 MTP path fix + n_max sweep (2026-07-03) — the #1 single-stream win:**
- **The `-md <same file>` MTP invocation is WRONG for embedded-NEXTN Qwen models** — it loads a full 27 GB second model as the draft (double HBM, full forward per draft token) → **~0% speedup** (29.75 vs 29.51). The **embedded path is `--spec-type draft-mtp` with NO `-md`** — the NEXTN head drafts from the target trunk.
- **Draft must be GPU-pinned** (`--spec-draft-ngl 99 --spec-draft-device ROCm0`): unpinned 32.15 → pinned 33.61 (+4.5%).
- **n_max sweep (embedded, GPU-pinned)**: **n_max=3 → 33.61 t/s** (accept 66.3%, mean-accept 2.99); n_max=5 → 29.89 (accept 43.6%); n_max=7 → 16.8 (collapses). **n_max=3 optimal.**
- **BEST SINGLE-STREAM: 33.61 t/s = +15.6% over plain (29.06, `llama-server` — apples-to-apples; the `llama-bench` plain floor is 29.51).** Modest vs mean-accept-2.99 because hybrid-SSM verification is sequential over draft positions (not a batched attention verify) — the deeper lever (P3, needs experimental-tree work). Correctness: coherent `<think>`+answer output. **Action item: the production/gemma `-md` recipe should be corrected to the embedded no-`-md` path for all Qwen NEXTN roles** (this likely means the CPU frontdoor/architect self-MTP is ALSO double-loading — worth a check by the CPU session).

## P1 runtime knobs — COMPLETE (settled config)
- **Optimal config for BOTH single and aggregate: `-fa 0` + default MMQ + `-ub 512`.** Every alternative regresses:
  - `-fa 1`: 28.8 / 135.5 / 162.2 t/s (B=1/16/32) vs `-fa 0`'s 29.4 / 138 / 166 — **FA is prefill-only on gfx90a**, so it only costs decode.
  - Forced rocBLAS (`GGML_CUDA_FORCE_CUBLAS=1`): 157.98 @ B=32 (vs 166 default MMQ).
  - `-ub 256`: 158.4 @ B=32; `-ub 1024`: 157.05 @ B=32 — both below `-ub 512`.
- **No runtime knob moves the ceiling** — the ~5.6× aggregate cap and the +15.6% MTP uplift are a **kernel/arch limit**, not a tuning miss.
- **Production-bug flag (for the CPU session, fixed later on 2026-07-03):** at the time of this MI210 run, production Qwen NEXTN roles still appeared to launch with `-md <same GGUF>`, which (as measured here) loads a full second copy of the model as the draft and yields **~0% MTP speedup**. The CPU lane fixed this live later the same day; current same-realpath NEXTN roles use **`--spec-type draft-mtp` with NO `-md`**.

## P2 vLLM — verdict: NOT viable for this model on gfx90a
Four independent blockers (opus survey, cited):
1. The `qwen3_5` arch needs a **post-0.16 vLLM nightly**; our on-hand gfx90a image is **vLLM 0.10.1**, which predates it.
2. The **gated-delta-net Triton kernel does not compile on gfx90a** (vLLM issue #44973; the unmerged fix needs ROCm-7.2-era Triton — we run 6.2/6.4).
3. **No native-fp8 / efficient-quant path on CDNA2.**
4. **MTP-on-AMD is "under development."**

→ **llama.cpp-HIP is the only substrate for Qwen3.6-27B on the MI210.** "Closing the vLLM gap" therefore means **porting the GDN algorithm into our own HIP/ggml**, not running vLLM.

## P3 direction — idea-mining result (reframes the hypothesis)
The bottleneck (MTP verify ≈ 2.6 plain-decode-steps → only +15.6% despite mean-accept 2.99) is the **gated-delta-net recurrent state being paid per-token during verify**. Neither vLLM nor SGLang uses a chunk/parallel-scan to verify (the chunk kernel is prefill-only, chunk_size 64 — too heavy for N≈3); both use a **fused recurrent** verify that walks the N draft tokens sequentially with the state resident in registers/SMEM (no per-token HBM round-trip).

**Portable techniques, ranked:**
1. **[HIGHEST]** Fuse the N-token GDN verify into ONE state-resident recurrent kernel (no per-token HBM round-trip). Source: FLA `fused_sigmoid_gating.py` / vLLM `qwen_gdn_linear_attn.py:1455-1475`.
2. **[HIGH]** Size the SSM-state cache with **+num_spec slots**, store one intermediate state per draft token, select the accepted prefix by index (O(1) accept/rollback). Source: vLLM `qwen3_next.py:769-790`, SGLang `gdn_backend.py`.
3. **[HIGH, correctness]** conv1d (kernel-4) state advance/rollback by exactly the accepted count.
4. **[MED]** EAGLE-style tree draft to lift mean-accept above 2.99.
5. **[MED]** Adaptive draft length; the NEXTN head is **1 full-attention layer** (drafting never touches GDN — only verify hits the 3×GDN layers).

**Portable math** (port the algorithm, not the Triton): FLA `fla/ops/gated_delta_rule/naive.py` (`naive_recurrent_gated_delta_rule` for verify/decode, `naive_chunk_gated_delta_rule` for prefill); papers **arXiv 2406.06484** (delta-rule chunkwise/WY) + **arXiv 2412.06464** (Gated Delta Networks). Kernel work target tree: **llama.cpp-experimental** (per operator).

**DECISION PENDING on two in-flight audits:** (a) does our fork's qwen35 verify already fuse the scan, or run T separate `ggml_ssm_scan`s (change-site check); (b) rocprof — does the GDN/SSM bucket dominate decode. **Build the fused-verify only after those land.**

## P3 findings (audit + profile + verify-amortization + DFlash) — 2026-07-03
Both in-flight audits landed → P3 substantially advanced (rank-1 kernel now in build+measure). **Full architecture writeup:** [`handoffs/active/fable5-window2-findings-05b-mi210-inference-architecture.md`](../../handoffs/active/fable5-window2-findings-05b-mi210-inference-architecture.md).

- **Fused-verify hypothesis FALSIFIED.** The qwen35 GDN verify is ALREADY fused — one `ggml_gated_delta_net` op over the whole draft block, state resident in registers, snapshot-indexed O(1) rollback (`delta-net-base.cpp:527,564-567`; `gated_delta_net.cu:53-61`). There is **no fused-verify to build**; the idea-mine rank-1 was a non-task.
- **rocprof (the linchpin).** Single-stream decode is BW-bound **Q8 weight-GEMV**: `mul_mat_vec_q` **77.8%**, whole GEMM/dequant bucket **84%**; GDN only **2.0%**, attention **0.2%**. At B=32 the GEMM bucket amortizes (84%→65%) while GDN balloons **2%→19.5%** (absolute ×39) → **the GDN recurrence is the aggregate/batch-scaling bottleneck**, not the single-stream one. VRAM: model 26.4 GB, RS-state 149.6 MB (fixed, does not grow per-token), ~38 GB free.
- **THE #1 LEVER — MMVQ non-amortization (confirmed).** MTP's 4-token verify batch (`ne11=4`) dispatches to `mul_mat_vec_q`, NOT the batched `mul_mat_q`, because CDNA2 Q8_0 hits `default: ne11 <= MMVQ_MAX_BATCH_SIZE(=8)` (`ggml-cuda/mmvq.cu:320-322`) → it pays **2.32 weight-reads/block** instead of ~1. Smoking gun: B=8 MMVQ **14.8 ms/tok** vs B=12 MMQ **8.5 ms/tok** (more tokens, less time). **Fix** = route small Q8 verify batches to MMQ — ~1 line, numerically safe (same result). Projected single-stream ceiling **~55–80 t/s** (from 33.6). **Being built + measured in `llama.cpp-experimental` now.** Transfers to every Q8 spec-dec on gfx90a (frontdoor + architect MTP verify included).
- **Q2 — the head.** MTP wins (post-MMVQ-fix ~2×) and is the deployment head. **EAGLE-3 machinery already ships in v6** (`common/speculative.cpp:419-850`) → the cheapest capability upgrade *if a trained qwen35 EAGLE-3 head GGUF exists* (open question — check HF). **DFlash HELD**: v2-era worktree, CPU-only, block-mode never worked (τ≈0), taps never wired into `qwen35.cpp`; its go/no-go gates on a cheap offline block-τ that is CPU-heavy → deferred under the GPU-only directive + live parallel CPU session. Token-metadata landmine on the DFlash GGUF: missing pad/unk (set pad=248044), eos discrepancy (GGUF 248046 vs HF 248044) — the silent-block class to verify, not assume.
- **CPU cross-check (audit):** CPU MTP verify already amortizes (iqk tiled GEMM, no MMVQ-analog) → GPU MMVQ fix is CDNA2-specific, no CPU transfer. The audit found a production bug: `-md <same file>` double-loads the model (server-context.cpp:1172,1199,1220) → 2× DRAM on BW-bound CPU decode. The CPU session fixed this later on 2026-07-03 by dropping `-md` for same-realpath NEXTN roles.

## P3/P4 RESULTS (measured) — 2026-07-03

**P3 done, P4 done.** Best single-stream = **MTP + MMVQ-fix 40.4 t/s** (**+37% vs plain 29.4**). The **MMVQ→MMQ verify-dispatch fix measures +17.4%** (34.4→40.4 t/s) — a **measured win, not the ~2× projected** (`mul_mat_vec_q` already amortizes tile loads across the 4 verify columns in-register, so MMQ removes only ~15% redundant HBM traffic) — validated in `llama.cpp-experimental` commit **de447119f** (one-line diff, 31 s build, coherent output, acceptance 0.673→0.728, numerically-valid-not-bit-exact; **operator-gated for prod promotion**). **EAGLE-3 measured 25.0 t/s → no-go, MTP wins** (acceptance mean 2.34 < MTP 2.99; the `Ex0bit/PRISM-EAGLE3` head loads/runs on our v6/HIP build and survives 900 tokens, so upstream #24541 Part-2 does NOT reproduce on our fork — a capability finding, but a slower head). **Aggregate 166 t/s @ B=32** unchanged — the **GDN-MFMA kernel is the next lever** (aggregate/concurrent regime). Two **GPU re-opens of CPU-era verdicts** are recorded in findings-05b §7: hybrid **tree-drafting** (Phase-8 Approach B, deferred ~40% viability, state-clone cost flips on GPU: 149 MB @ ~1.6 TB/s ≈ 0.1 ms) and **GPU-draft / CPU-target** (`-devd`/`-ngld`/`-otd`; CPU verify amortizes the weight read so no findings-02 amortization penalty). The CPU-session production flag was closed later on 2026-07-03: same-realpath Qwen NEXTN roles now omit the `-md <same GGUF>` double-load. See findings-05b §1 (MMVQ measured), §2 (EAGLE-3 no-go), §7 (GPU re-opens).

## Current bests (living)
| Metric | Config | Value |
|---|---|---|
| Single-stream | embedded MTP, n_max=3, draft GPU-pinned, -fa 0 | **33.61 t/s** (+15.6% vs plain **29.06 `llama-server`**; `llama-bench` floor 29.51) |
| Aggregate | plain Q8 batched-bench, B=32 | **165.8 t/s** (~5.6×); B=64 171.5 (+3.4%) |

## Artifacts
- Scripts + logs: `/mnt/raid0/llm/tmp/mi210-build/campaign/`
- Bench harness: `p0_single_baseline.sh` (→ `p0_single_baseline.json`)

## Next action
P0/P1/P2 done; **P3 substantially advanced** — both audits landed (fused-verify FALSIFIED; rocprof attributes single-stream to BW-bound Q8 GEMV, aggregate to GDN recurrence; see "P3 findings" + findings-05b). The **MMVQ→MMQ small-batch verify-dispatch fix** (P3 rank-1, ~1 line, ~2× projected) is in **build+measure in `llama.cpp-experimental`**. On landing: record MTP t/s + MMQ@4 ms/tok + correctness, confirm ~55–80 t/s, then close out with P4 (synthesize 2 winning configs).

**Multi-model sweep:** MMVQ fix is DENSE-Q8-specific (MoE experts use separate get_mmvq_mmid_max_batch dispatch, untested); frontdoor qwen35moe kernel-flat (+0.7%); GDN bottleneck confirmed qwen35-specific (frontdoor batch-scales 3.4× vs gemma 5.9×/8.6×); MMQ non-bit-exact perturbs acceptance (dominates MoE deltas).

**f16 test (gemma-26B-A4B bf16):** bf16>Q8 crossover at high batch (744 vs 561 @B32, 10.19× vs 5.81× scaling — dequant-amortization confirmed); MTP net-NEGATIVE for MoE on GPU (plain 96.6 > MTP 84.5) — MTP is a CPU/BW-bound win, GPU-resident MoE should run plain. gemma-31B dense-Q8 transfer test pending (download ~1h).

**Final probes:** KV-quant no help (VRAM not the constraint, ~430 t/s @128-way @80k), GDN-MFMA KILLED (latency/occupancy-bound not compute — rocprofv2), context-flatness FALSIFIED (hybrid −22% vs gemma-SWA −8%; gemma is SWA-capped, qwen35 attn is full-global), gemma-31B dense-Q8 MMVQ CONFIRMED +31.7%. GPU kernel campaign exhausted.

**Follow-on 2026-07-04:** dead-ends qualified (EAGLE-3/tree/KV-quant dead only for dense-Q8/MoE-on-GPU regime, open for dense targets); two kernel handoffs opened (Q8 dequant-GEMV roofline + MFMA compute-bound paths); opus subagent started (ngram-spec test → dequant profiling → MFMA measurement); ingest_long_context = qwen3next hybrid full-global-attn (long-ctx degradation is the right recall tradeoff).

## a8afd338 kernel-thread RESULTS (2026-07-04) — all OBSERVATION, serial single-GPU (transcript-verified)
Kernel subagent (Q8-dequant + MFMA handoffs) landed; ran serially on the sole GPU (52 inference calls all foreground except one llama-server that was pkilled before the next bench; No-KFD-PID checks between phases).
- **nwarps 2→4 for batch-1 Q8_0 (CDNA2) = +4.6%** (28.99→30.32 t/s, `llama-bench` tg128 `-fa 1 -r 3`). `test-backend-ops MUL_MAT` 1103/1103. Committed **`5dc116130`** (fork `upstream-mtp-verify`). Down-payment on async-prefetch (Little's law: more warps → more in-flight loads).
- **REFRAME: Q8_0 GEMV is already int8-native** (`vec_dot_q8_0_q8_1` = `dp4a` + one fp scale/32-block) → **no dequant to hide** → the 47→62% gap is **BW/occupancy, not dequant-compute**. The dequant-GEMV handoff's Tier-1 premise is superseded (banner-corrected there).
- **`quantize_q8_1` = 3.37%** of decode (was 5.68% on the mi210-hip build); graph-level fix only (activation caching / RMSNorm-fuse), ceiling ~1.5–3% on the 82%-hot-path → deferred.
- **n-gram / prompt-lookup GPU spec = NEGATIVE** (plain 28.4 > every variant; best ngram-simple 27.7; ~15% acceptance << break-even). Trained drafter (MTP/EAGLE3) remains the spec path; raises the bar for corpus-static (CPL-4b).
- **MFMA both paths DEFERRED (measured gate failed):** prefill VALUBusy 3.55% / MemUnitBusy 78.5% (already MFMA + memory-bound); high-batch VALUBusy 16.8% (not compute-bound), 43% of B=128 time is non-GEMM norm/elementwise. Orthogonal levers noted (prefill skip Q8→f16 convert ~15%; fuse high-batch norm tail).
- **Async weight-prefetch LANDED (+3.3%):** `raw.buffer.load.lds` LDS double-buffer on the nwarps=4 base = 30.20→31.20 t/s (alternated-A/B tg128 -fa 1), output **byte-identical**, `test-backend-ops` 1103/1103, rocprofv2 **MemUnitStalled −62%** (mechanism confirmed), commit **`7c28056b7`** (runtime-gated `GGML_CUDA_Q8_PREFETCH`, default-off). Stacked with nwarps=4 ≈ +8% over the 28.99 base. **Cap:** covers ~half the Q8 GEMV dispatches (fused-SwiGLU FFN up/gate excluded) → **fused-path extension FALSIFIED** — coverage doubled to 100% of dispatches but throughput −1.8%@full-occupancy / −13%@naive (the large FFN GEMVs are already wave-pipelined; per-iter barrier > stall-benefit; patch saved not committed). **+3.3% = the CDNA2 ceiling for LDS-prefetch.** SoA-repack not warranted (coalescing healthy). Single-stream dense-Q8 now: plain 29 → +MTP 33.6 → +MMVQ 40.4 (MTP-verify path); non-MTP kernel path 28.99 → nwarps4 30.3 → +prefetch 31.2.
- **Megakernel RULED OUT + single-stream CLOSED (Pass-2 diagnostic, 2026-07-04):** HIP graphs (kill all host-launch) buy only +5.9%; decode memory-latency-bound at ~50% roofline. The 62→100% gap is the batch-1 MLP floor, not a launch/grid-drain bubble the megakernel could remove (rocprofv2's 64% "gap" = profiler artifact, ~10µs × ~1860 hybrid kernels/token; profiled 19.1 vs real 30.3 t/s). Single-stream dense-Q8 lever set is exhausted. **PIVOT to aggregate/MoE regime** (L1-MoE mmid dispatch / L16 bf16-aggregate / L20 GDN-aggregate).
- rocprof note: v1 aborts at init on this build (PDL/graph); use **rocprofv2** + add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH`.
