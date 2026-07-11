# Gemma-Challenge Kernel Techniques → v7-Experimental Candidates

**Status**: stub / exploration (created 2026-07-11 via research intake, operator-directed)
**Categories**: speculative_decoding, hardware_optimization, quantization, local_inference
**Source**: intake-798 — "The Gemma Challenge and the Case for Agent Collabs" (HF + Google DeepMind)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (onegraph deep-dive lives here), [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) (GPU-graph home), [`v6-iqk-promotion.md`](v6-iqk-promotion.md) / [`kernel-reconciliation-audit.md`](kernel-reconciliation-audit.md) (the v7 workflow), [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md)

## Objective

The Gemma Challenge (100+ agents, 6 days) drove `google/gemma-4-E4B-it` inference 5× — the **same MTP-drafter family and model family as our production `worker_general`** (gemma-4-26B-A4B, Google official assistant head). **v7 was never promoted to production**, so the `llama.cpp-experimental` line is a clean slot to fold the *validated, quality-preserving* subset of these techniques into a v7 candidate — via the mandated four-step experimental workflow (fresh-pull production → build → validate-no-regression → promote), never touching frozen production kernels.

## Governance rails (non-negotiable, per CLAUDE.md)

- **Production kernels are FROZEN.** All work on `llama.cpp-experimental` (fresh-pulled from current production tip first, so the iqk AVX-512 GEMM + CPU forward-ports are already present — do not repeat the 2026-06-22 GPU-opts fork that silently lacked the entire iqk subsystem).
- **Quality gate is the gate, not TPS.** The challenge's own lesson: a **PPL-only** gate was gamed (top lossy submission held PPL but lost **15 GPQA-Diamond / 40 MMLU-Pro** points). Any v7 candidate must pass downstream evals (MMLU-Pro + GPQA-Diamond), production sampling (seed 42), per [`MEASUREMENT.md`](../../MEASUREMENT.md) + eval-tower — **not** PPL alone. This is a hard prerequisite, especially for the lossy techniques below.
- **Inference is operator-gated** (`feedback_no_concurrent_inference`); bench only via codified recipes with approval.

## Technique candidates (from intake-798 submissions)

| Technique | Lossy? | Our-regime fit | v7 workflow slot | Open question |
|---|---|---|---|---|
| **`onegraph`** — drafter is Q-only, KV-shared, no cross-position deps ⇒ multi-position warm-up is redundant; fold warm-up into the 7-step drafting loop, record as ONE GPU graph, single-launch replay | **Lossless** (no output change) — fastest lossless: 315 TPS | GPU-drafter path (MI210/HIP graphs) directly; **structural insight may port to CPU** MTP drafter loop | GPU-graph capture → `gpu-drafter-mi200-investigation.md`; CPU-warm-up-redundancy → `speculative-decoding-mtp-refresh.md` | Do the Q-only/KV-shared/no-cross-position preconditions hold for OUR gemma-4-26B-A4B assistant head (verify GGUF drafter structure)? Does HIP graph capture on gfx90a support the folded routine? |
| **Task-targeted fine-tuned drafter** — drafter fine-tuned on the eval's math/science prompt distribution to raise acceptance rate α | Lossy **as executed** (overfit to eval set); the *method* (raise α on our real workload) can be lossless | CPU + GPU spec-dec; raises α for both | Drafter-training track (new); gate via rescue-rate on real task corpus | Can we lift α on our real frontdoor/worker workload without overfitting? (`feedback_measure_alpha_before_specdec_investment` — measure α first; `frontier-f1-real-task-corpus.md` for the distribution) |
| **CUDA-graph capture throughout decode** — capture the decode routine as a replayable graph to cut per-step launch/bookkeeping overhead | Lossless (kernel-level) | GPU only (HIP graph equivalent on MI210) | `gpu-drafter-mi200-investigation.md` / `gpu-acceleration-path.md` | Does ROCm/HIP graph capture cover our decode + MTP path on gfx90a? Overlaps `onegraph`. |
| **Vocabulary pruning** — drop rarely-used vocab rows to shrink the output projection / embedding | **Lossy** (contributed to the 15/40-pt degradation) | Applies to any regime, but degrades downstream | Explore-only, hard-gated on MMLU-Pro/GPQA | Is there a *lossless* vocab-prune band (truly-dead tokens only) that survives the downstream gate? High risk. |
| **Layer removal / depth pruning** | **Lossy** (part of the 491.8-TPS lossy stack) | Any regime, degrades quality | Explore-only, hard-gated; likely reject | Almost certainly fails our quality gate; document as a cautionary boundary, low priority. |

## Prioritization (proposed, operator to confirm)

1. **`onegraph` structural check** (lossless, highest value): verify preconditions on our gemma4 assistant-head drafter, then prototype warm-up folding — GPU-graph on MI210 first, and separately test whether the redundant-warm-up removal helps CPU. Coordinate with `speculative-decoding-mtp-refresh.md` (already carries the onegraph note).
2. **Drafter-α uplift** (potentially lossless): measure current α on the real task corpus before any fine-tuning investment; only pursue if α headroom is real and generalizes beyond the eval set.
3. **Lossy techniques** (vocab prune / layer removal): explore-only, hard-gated; primarily useful as documented quality boundaries unless a lossless sub-band exists.

## Tasks

- [ ] **K1 — `onegraph` precondition check**: verify the Q-only / KV-shared / no-cross-position preconditions hold for our gemma-4-26B-A4B assistant-head drafter (GGUF structure inspection; no inference needed)
- [ ] **K2 — `onegraph` GPU prototype**: on `llama.cpp-experimental` (fresh-pulled), prototype warm-up folding + HIP graph capture on the MI210 drafter path; coordinate with [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md)
- [ ] **K3 — CPU warm-up-redundancy test**: separately test whether removing the redundant drafter warm-up helps the CPU MTP worker (structural insight may port even without GPU graphs)
- [ ] **K4 — drafter-α baseline**: measure current acceptance α on the real task corpus ([`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md)) BEFORE any fine-tuned-drafter investment (`feedback_measure_alpha_before_specdec_investment`)
- [ ] **K5 — quality-gate wiring**: confirm any v7 candidate is gated on MMLU-Pro + GPQA-Diamond (production sampling, seed 42), NOT PPL alone — the challenge's PPL-only gate was gamed for 15/40-pt loss
- [ ] **K6 (explore-only, low priority)**: characterize whether a *lossless* vocab-prune sub-band (truly-dead tokens) survives the downstream gate; document layer-removal as a cautionary quality boundary

## Notes

- The challenge ran on A10G/GPU with E4B (small Gemma); our production worker is **CPU MTP on a 26B-A4B** with the MI210 as the GPU path — so GPU-graph techniques land on the MI210 drafter track, while the drafter-α and warm-up-redundancy *insights* are the CPU-transferable ones.
- All intake-798 numbers (315 / 491.8 TPS, ±15/40 eval deltas, PPL ≤ 2.42) are OBSERVATION-grade (challenge-internal, single-config, self-reported) — hypotheses only, re-measure on our stack before any keep/promote per MEASUREMENT.md.
- Submission-level detail (per-result `method` fields, taskforce notes) is available on the challenge leaderboard/bucket for a deeper follow-up if a technique graduates past the structural check.
