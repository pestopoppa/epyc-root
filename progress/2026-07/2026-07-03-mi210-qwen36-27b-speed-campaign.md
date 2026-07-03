# 2026-07-03 — MI210 GPU-only speed campaign: Qwen3.6-27B-MTP-Q8_0 (LIVING CHECKPOINT)

**Goal (operator):** make `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` run as fast as possible on the MI210, GPU-only. Track **both single-stream and aggregate-concurrent** throughput. Kernel work → `llama.cpp-experimental` (never production-consolidated-v6). Explore vLLM / close llama.cpp↔vLLM gaps. Runs in parallel with a separate CPU-only session (no CPU/RAM contention — GPU-resident decode is insulated).

This is a **living checkpoint** — updated after every phase/measurement (operator asked for continuous checkpointing; periodic `/wrap-up` dispatched to an opus medium subagent).

## Fixed facts
- **Model arch**: `qwen35` = hybrid SSM (delta-net: state_size 128, group_count 16, conv_kernel 4, inner_size 6144) + attention. **DENSE (no experts)** → batches cleanly, the MoE-weaker-batching caveat does NOT apply. 65 blocks, embd 5120, FFN 17408, 24 heads / 4 KV heads, ctx 262144, M-RoPE (dim_sections [11,11,10,0], freq_base 1e7). **Embedded 1-layer NEXTN MTP head** (`nextn_predict_layers=1`). Q8_0, 29.0 GB file.
- **Substrate**: MI210 gfx90a CDNA2, 64 GB HBM2e (~65.4 GB free), ~1.64 TB/s peak, ROCm 6.2. HIP build = `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip` (version 9777 / `0ebf1b4d7`, the fp8-fix leg). Must prepend `LD_LIBRARY_PATH=$HIP/bin:/opt/rocm/lib`.
- **Prior roofline (2026-07-02 obs, non-MTP Q8)**: 28.69 t/s = 47% roofline (766 GB/s) single-stream; fp16 62%; batched fp16 (8B) scaled ~15×. All numbers OBSERVATIONS per MEASUREMENT.md.
- **Guardrails**: GPU-only (`-ngl 99`), no CPU offload/sidecar; pair every speed number with a correctness/garbage check; label observation vs gating.

## Phases
- [ ] **P0 — harness + baseline** (in progress): arch ✅ + op-coverage smoke; single-stream (llama-bench pp512/tg128, -fa 0/1) + MTP (llama-server draft-mtp: α + speedup) + aggregate (llama-batched-bench + llama-server -np sweep).
- [ ] **P1 — runtime-knob sweep**: -np dequant-amortization sweep; -fa/ubatch/MMQ-vs-rocBLAS/KV-quant/HIP-env/HIP-graph; MTP×batching crossover → latency-vs-throughput Pareto.
- [ ] **P2 — vLLM reference + gap-closing**: current-vLLM qwen35 support on gfx90a? else shared-arch bar + technique port.
- [ ] **P3 — kernel authoring (llama.cpp-experimental)**: rocprof → GEAK/agentic-rocm Q8 dequant-GEMV + MFMA util; correctness first.
- [ ] **P4 — synthesize** 2 winning configs + record in GPU handoffs.

## Measurement log (append-only; every number is an OBSERVATION unless tagged P-GPU-1)
| date | phase | config | single t/s | aggregate t/s @ conc | roofline% | correctness | notes |
|------|-------|--------|-----------:|---------------------:|----------:|-------------|-------|
| 07-03 | P0 | plain Q8, -fa 0, `llama-bench` tg128 | **29.51** (±0.01) | — | ~52% (856 GB/s) | pending eyeball | -fa 1 = 29.16 (FA hurts decode); pp512 840/849 t/s |
| 07-03 | P0 | plain Q8 aggregate `-npl 1..64` | — | _in flight_ | — | — | batched-bench npp128/ntg128 |

**P0 single-stream read (2026-07-03):** plain Q8 decode **29.51 t/s / ~52% roofline** (`-fa 0` beats `-fa 1` for decode — FA is prefill-only on gfx90a, re-confirmed). This is the MTP-OFF floor.

**P0 aggregate curve (batched-bench, npp128/ntg128, S_TG = aggregate decode t/s):** B=1 **29.4** · 2 46.9 · 4 48.8 · 8 68.9 · 16 138.1 · 32 **165.8** · 64 171.5. Full GPU residency, no op fallback. **Sweet spot B=32 (~5.6× single); B=64 adds only +3.4%.** Scaling caps at ~5.8× — well below a pure-attention model's ~15× — because the hybrid-SSM recurrent state is per-sequence (batching the SSM scan doesn't amortize weight reads the way attention does). Weight-BW util falls 856→~150 GB/s across the batch (findings-05 batch-1-artifact confirmed).

**P0 MTP single-stream — NO speedup, ROOT-CAUSED (2026-07-03):** `--spec-type draft-mtp -md <same 27GB file>` → decode **29.75 t/s ≈ plain 29.51 (+0.8%)** despite draft acceptance **53.6%** (156/291, mean-accept 2.59 of n_max=3, per-pos 0.755/0.490/0.347) and correct output. Server log: *"estimated memory usage of draft model is 26894 MiB; loading draft model Qwen3.6-27B-MTP-Q8_0.gguf"* — i.e. `-md <same file>` **loads the full 27 GB model as the draft**, so each draft token costs a full-model forward pass, cancelling the acceptance savings (drafting dur only 806 ms, but target eval unchanged at ~8.6 s / 256 tok). This is the findings-02 §2 prediction ("embedded-MTP needs the no-`-md` path; small fork change if ever needed"). **The embedded NEXTN head must draft cheaply from the target's hidden state, not run as a full second model** — this is the #1 single-stream lever and likely needs a fork change in `llama.cpp-experimental`. Investigating the invocation first (no-`-md` embedded path) before concluding code work.

**P1 MTP path fix + n_max sweep (2026-07-03) — the #1 single-stream win:**
- **The `-md <same file>` MTP invocation is WRONG for embedded-NEXTN Qwen models** — it loads a full 27 GB second model as the draft (double HBM, full forward per draft token) → **~0% speedup** (29.75 vs 29.51). The **embedded path is `--spec-type draft-mtp` with NO `-md`** — the NEXTN head drafts from the target trunk.
- **Draft must be GPU-pinned** (`--spec-draft-ngl 99 --spec-draft-device ROCm0`): unpinned 32.15 → pinned 33.61 (+4.5%).
- **n_max sweep (embedded, GPU-pinned)**: **n_max=3 → 33.61 t/s** (accept 66.3%, mean-accept 2.99); n_max=5 → 29.89 (accept 43.6%); n_max=7 → 16.8 (collapses). **n_max=3 optimal.**
- **BEST SINGLE-STREAM: 33.61 t/s = +15.6% over plain (29.06).** Modest vs mean-accept-2.99 because hybrid-SSM verification is sequential over draft positions (not a batched attention verify) — the deeper lever (P3, needs experimental-tree work). Correctness: coherent `<think>`+answer output. **Action item: the production/gemma `-md` recipe should be corrected to the embedded no-`-md` path for all Qwen NEXTN roles** (this likely means the CPU frontdoor/architect self-MTP is ALSO double-loading — worth a check by the CPU session).

## Current bests (living)
| Metric | Config | Value |
|---|---|---|
| Single-stream | embedded MTP, n_max=3, draft GPU-pinned, -fa 0 | **33.61 t/s** (+15.6% vs plain 29.06) |
| Aggregate | plain Q8 batched-bench, B=32 | **165.8 t/s** (~5.6×); B=64 171.5 (+3.4%) |

## Artifacts
- Scripts + logs: `/mnt/raid0/llm/tmp/mi210-build/campaign/`
- Bench harness: `p0_single_baseline.sh` (→ `p0_single_baseline.json`)

## Next action
Read P0 single-stream baseline result; then MTP single-stream + aggregate -np sweep.
