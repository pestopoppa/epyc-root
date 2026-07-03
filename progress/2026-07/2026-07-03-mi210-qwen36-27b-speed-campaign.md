# 2026-07-03 — MI210 GPU-only speed campaign: Qwen3.6-27B-MTP-Q8_0 (LIVING CHECKPOINT)

**Goal (operator):** make `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` run as fast as possible on the MI210, GPU-only. Track **both single-stream and aggregate-concurrent** throughput. Kernel work → `llama.cpp-experimental` (never production-consolidated-v6). Explore vLLM / close llama.cpp↔vLLM gaps. Runs in parallel with a separate CPU-only session (no CPU/RAM contention — GPU-resident decode is insulated).

This is a **living checkpoint** — updated after every phase/measurement (operator asked for continuous checkpointing; periodic `/wrap-up` dispatched to an opus medium subagent).

## Fixed facts
- **Model arch**: `qwen35` = hybrid SSM (delta-net: state_size 128, group_count 16, conv_kernel 4, inner_size 6144) + attention. **DENSE (no experts)** → batches cleanly, the MoE-weaker-batching caveat does NOT apply. 65 blocks, embd 5120, FFN 17408, 24 heads / 4 KV heads, ctx 262144, M-RoPE (dim_sections [11,11,10,0], freq_base 1e7). **Embedded 1-layer NEXTN MTP head** (`nextn_predict_layers=1`). Q8_0, 29.0 GB file.
- **Substrate**: MI210 gfx90a CDNA2, 64 GB HBM2e (~65.4 GB free), ~1.64 TB/s peak, ROCm 6.2. HIP build = `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip` (version 9777 / `0ebf1b4d7`, the fp8-fix leg). Must prepend `LD_LIBRARY_PATH=$HIP/bin:/opt/rocm/lib`.
- **Prior roofline (2026-07-02 obs, non-MTP Q8)**: 28.69 t/s = 47% roofline (766 GB/s) single-stream; fp16 62%; batched fp16 (8B) scaled ~15×. All numbers OBSERVATIONS per MEASUREMENT.md.
- **Guardrails**: GPU-only (`-ngl 99`), no CPU offload/sidecar; pair every speed number with a correctness/garbage check; label observation vs gating.

## Phases
- [x] **P0 — harness + baseline** (DONE): arch ✅ + op-coverage smoke; single-stream (llama-bench pp512/tg128, -fa 0/1) + MTP (llama-server draft-mtp: α + speedup) + aggregate (llama-batched-bench + llama-server -np sweep).
- [x] **P1 — runtime-knob sweep** (DONE): -np dequant-amortization sweep; -fa/ubatch/MMQ-vs-rocBLAS/KV-quant/HIP-env/HIP-graph; MTP×batching crossover → latency-vs-throughput Pareto. **Settled config below; no runtime knob moves the ceiling.**
- [x] **P2 — vLLM reference + gap-closing** (DONE): current-vLLM qwen35 support on gfx90a? → **NOT viable on gfx90a** (4 blockers below); gap-closing = porting GDN algorithm into our HIP/ggml, not running vLLM.
- [ ] **P3 — kernel authoring (llama.cpp-experimental)** (PENDING fork-audit + rocprof): rocprof → GEAK/agentic-rocm Q8 dequant-GEMV + MFMA util; correctness first. **Direction reframed to GDN fused-verify (below); build only after the two in-flight audits land.**
- [ ] **P4 — synthesize** 2 winning configs + record in GPU handoffs.

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
- **Production-bug flag (for the CPU session):** the production Qwen NEXTN roles launch with `-md <same GGUF>`, which (as measured here) loads a full second copy of the model as the draft and yields **~0% MTP speedup**. The correct embedded-NEXTN invocation is **`--spec-type draft-mtp` with NO `-md`**.

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

## Current bests (living)
| Metric | Config | Value |
|---|---|---|
| Single-stream | embedded MTP, n_max=3, draft GPU-pinned, -fa 0 | **33.61 t/s** (+15.6% vs plain **29.06 `llama-server`**; `llama-bench` floor 29.51) |
| Aggregate | plain Q8 batched-bench, B=32 | **165.8 t/s** (~5.6×); B=64 171.5 (+3.4%) |

## Artifacts
- Scripts + logs: `/mnt/raid0/llm/tmp/mi210-build/campaign/`
- Bench harness: `p0_single_baseline.sh` (→ `p0_single_baseline.json`)

## Next action
P0/P1/P2 done. **P3 gated on two in-flight audits:** (a) fork qwen35-verify change-site check (fused scan vs T separate `ggml_ssm_scan`s), (b) rocprof GDN/SSM decode-bucket attribution. Build the GDN fused-verify kernel (P3 rank-1) only after both land.
