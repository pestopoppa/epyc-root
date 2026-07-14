# Fable 5 window-2 — mid-session focus injection: MI210 inference improvement (rev 2)

> **Archived 2026-07-14** (backlog ROI audit, [backlog-roi-audit-2026-07-14.md](../active/backlog-roi-audit-2026-07-14.md)): brief authored and consumed by findings-05b; MI210 work lives in the findings-05x set.

*Paste the block below into the running Fable 5 session. It re-aims remaining depth at the MI210
architecture layer; it assumes the window-2 brief + your findings-00..04 are already in context.*
**rev 2 (2026-07-03):** the 27B DFlash head is now converted to GGUF and in-hand; the DFlash→v6/HIP
inference **port is explicitly handed to you** (operator decision); a converter token-metadata gap is
flagged as a named correctness risk.

---

**Focus injection — go deep on MI210 inference improvement (the architecture, not the benchmarks).**

You've mapped the fleet-placement picture (findings-02: everything but the 122B fits 64 GB HBM; the
fork ships the flags; the orchestrator is the gap). Now spend your remaining depth one level down, on
the **architecture of making inference on this single MI210 as fast as it can be** — the layer the
empirical work below cannot reach by itself.

**What is already being ground in parallel — do NOT redo it.** A separate GPU-only speed campaign is
live (`progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md`): P0 baseline, P1 runtime-knob
sweep (-np / ubatch / MMQ-vs-rocBLAS / KV-quant / HIP-env / HIP-graph), P2 vLLM reference, P3 kernel
authoring in `llama.cpp-experimental`, P4 synthesis. That machinery will *measure*. Your job is the
**architecture that directs it** — which kernel to author first and why, which spec-dec head wins, what
the ROCm↔CUDA gap actually is — not another bench.

**Substrate deltas since your findings-02 (confirm at preflight; raw-read the fork — it is not in the
gitnexus registry):**
- gfx90a CDNA2, 64 GB HBM2e (~1.64 TB/s peak), ROCm 6.2; HIP build =
  `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip` (fp8-fix leg).
- Roofline (2026-07-02/03 **observations**, no P-GPU-1): Q8 dense-27B **47% / 766 GB/s**, Q4_K **33% /
  537 GB/s**, **fp16 62%** → the ceiling is a **quantized-MMQ dequant artifact on CDNA2**, not general
  kernel immaturity. FA is prefill-only on gfx90a (hurts decode). MTP self-spec measured **1.44×**.
- vLLM (rocm6.4.1/0.10.1, the only gfx90a-computing image): fp16 **+11%** single-stream, **+24%** at
  32-way — **but cannot load our `qwen35`/`gemma4` archs**; the fork is the only substrate for them.
- Spec-dec heads for the 27B, both now in-hand: **MTP** (`Qwen3.6-27B-MTP-Q8_0.gguf`, fused NEXTN, runs
  today, 1.44×) and **DFlash** — `z-lab/Qwen3.6-27B-DFlash` (1.73B, block_size 16, target taps
  [1,16,31,46,61]) **now converted to GGUF**:
  `/mnt/raid0/llm/models/dflash/Qwen3.6-27B-DFlash/Qwen3.6-27B-DFlash-f16.gguf` (8.56 GB, f16,
  `general.architecture=dflash`, 60 tensors, `dflash.block_size=16`, `dflash.mask_token_id=248070`,
  `dflash.target_layer_ids=[1,16,31,46,61]`, bos 248044 / eos 248046). **Known gap:** the stale
  converter did **not** emit `tokenizer.ggml.padding_token_id` (nor `unknown_token_id`) — per your
  findings-02 aligned-specials triple the pad should be **248044** (bos 248044 / eos 248046 / pad
  248044); this is the exact silent-block class you warned about, so treat token metadata as a
  correctness landmine to verify, not assume. The DFlash **inference path** exists only in a stale
  **v2-era** worktree (`/mnt/raid0/llm/llama.cpp-dflash`, `feature/dflash-speculation`, 21 commits, C++
  forward pass verified <0.01 vs HF); its reference impls are CUDA-only.

**The questions we cannot answer ourselves (reframe any that are wrong):**
1. **The kernel gap.** Is the Q4/Q8 dequant-bound CDNA2 ceiling architecturally addressable, and if so
   what is the *single highest-leverage kernel to author first* (MMQ-MFMA dequant-GEMV? a Q8-native
   path? something else), what roofline % would it unlock, and how do we know before writing it? Is Q8
   simply the correct deployment quant here and the Q4 path a dead end on gfx90a?
2. **The GPU drafter — and the DFlash port is yours to design.** The operator has decided the
   **DFlash→v6+HIP inference port is your deliverable to architect** (the head GGUF above is ready; only
   the runtime path is missing). Design that port: how to graft the `feature/dflash-speculation` block-
   diffusion path (target hidden-state taps at layers [1,16,31,46,61], 16-token denoise block, shared
   lm_head) onto the v6 server + gfx90a/HIP build; how to close the missing pad/unk token metadata
   safely; and — decisively — **is it worth it** vs the in-hand MTP head (1.44×) and EAGLE-3, given the
   CUDA-only reference and the CPU recurrence-verify history that killed DFlash before? Name the single
   cheapest measurement (τ accepted-tokens/round on-GPU, or per-block α) that ranks MTP vs DFlash vs
   EAGLE-3 *before* we sink the port cost, and the go/no-go threshold.
3. **The serving fabric.** Does the fork stay the sole substrate, or is there a real architecture where
   vLLM's batched-serving edge matters despite it not loading our archs (e.g. subagent fan-out on stock
   models)? Is closing the fork's batched-serving gap (fork is +0% single but −24% at 32-way) worth it,
   or is single-user latency the only regime that counts here?
4. **The reframe.** Is "make MI210 inference faster" even the right frame, or is it "which roles migrate
   and what is the CPU↔GPU serving architecture" (your findings-02 instrumented-placement) — and what is
   the **smallest kernel + head + placement bet that compounds** across the next card and next model?

**How to work / deliverables:** gitnexus-first for the orchestrator/research repos, raw reads for the
fork's HIP/kernel internals and the `llama.cpp-dflash` worktree; ground every claim `file:line`.
Guardrail: every kernel/head/serving claim ships with the single cheapest decisive experiment that
validates it before we build, and you flag any recommendation resting on an unverified "cheap"
assumption. Measurement discipline: **P-GPU-1 is not yet ratified — every throughput number is an
observation and gates nothing.** Persist to
`handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md` as a supplement (or a new
`findings-05-mi210-inference.md`), leave a progress note, and close with a self-critique of the weakest
link. If the highest-value thing you can say is that this whole framing is wrong, say that first.

## Progress checklist

- [x] Focus-injection brief authored (consumed by findings-05b) ✅
