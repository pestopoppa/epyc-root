# Cross-Model LoRA Transfer & Hypernetwork-Adapter Cluster — Decision Reference

**Date:** 2026-07-02 · **Source:** research intake intake-764..771 (+ existing intake-098/707/618) · **Status:** synthesis / decision-shaping (no code changes proposed)

## TL;DR

Eight indexed works now form one coherent research line — *adapt a frozen LLM cheaply, and carry that adaptation across a rotating model roster without full re-training per base.* This is a direct match for our operational pain (rotating open-weight roster: Qwen3.6, gemma4-26B-A4B, GLM). **But the entire cluster shares one blocker: adapter/hypernetwork/converter training is gradient-based and GPU-gated — the same Phase-B gate that keeps our `doc-to-lora` line on backburner.** Two things cut through:

1. **The only CPU-plausible member is Cross-LoRA (intake-765)** — a pure SVD + least-squares weight-space port, no training. Low fidelity (~14% task-lift recovery per PorTAL), but runs on the EPYC host today.
2. **The only OPEN-code + OPEN-weights member is Text-to-LoRA (intake-771, Sakana)** — enabling a genuinely **zero-cost CPU validation** (pull a released hypernetwork, generate a LoRA from a text description, GGUF-convert, hot-swap in llama.cpp).

Everything else is decision-shaping reference for a *future* Phase-B reopen (training-capable GPU + a demonstrated need REPL retrieval can't cover).

## Why this matters to us

Per `handoffs/completed/08-doc-to-lora-prototype.md`: llama.cpp LoRA hot-swap is DONE (Finding 1); the real gaps are (a) no training-capable GPU on the EPYC host — the MI210 is inference-only — and (b) an unresolved orchestrator `--lora` wiring gap (Finding 7). Our roster turns over (the general LLM-release cadence is ~monthly), so "adapt once, port cheaply" is exactly the value proposition we would want *if* we had a task-specialization need that in-context/REPL retrieval doesn't already cover.

## Two axes of the cluster

**Axis A — how the adapter is GENERATED (conditioning signal):**

| Conditioning | Work | intake |
|---|---|---|
| Natural-language **task description** | Text-to-LoRA (Sakana, ICML'25) | 771 |
| **Document** | DocToLoRA | 098 |
| **Code repo / diff** | Code2LoRA | 707 |
| **In-context / memory tokens** | SHINE (single pass, M2P hypernet) | 768 |
| **User profile** | Profile-to-PEFT | 769 |
| directly trained (baseline) | classic LoRA | — |

**Axis B — how the adapter is PORTED to a new base:**

| Port mechanism | Training-free? | Cross-family? | Fidelity | Work | intake |
|---|---|---|---|---|---|
| **Weight-space SVD projection** | ✅ transfer only | ⚠ same-family favored | low (~14% lift recovery) | Cross-LoRA | 765 |
| **SVD-subspace-constrained + project** | ✅ transfer only | ❌ same-family only | low cross-family | LoRA-X (ICLR'25) | 766 |
| **Activation-manifold projection heads** | ❌ per-pair C4 training | claimed cross-family | ~85-95% (weak evidence) | CAST | 767 |
| **Base-agnostic latent + per-base converter refit** | ❌ converter refit | ✅ (Gemma-3-4B ~94%) | high (~98%) | PorTAL | 764 |

## The shared blocker & the one exception

Every high-fidelity option (PorTAL, CAST, and all Axis-A hypernetworks) needs a gradient step on a GPU — either to train the hypernetwork or to refit the per-base converter/projection heads. That is the standing Phase-B gate. **Cross-LoRA (765) is the sole exception**: its LoRA-Align/LoRA-Shift is pure `torch.linalg.lstsq` over weight matrices, CPU-runnable — but PorTAL measures its no-refit fidelity at only ~14% of the per-task lift, and its own headline "≈trained-LoRA" is on general-commonsense QA where the base already scores high, masking that gap.

**Fidelity ↔ cost tradeoff:** Cross-LoRA (cheap, CPU, ~14%) — LoRA-X (cheap, same-family) — CAST (per-pair GPU, weak evidence) — PorTAL (converter refit, ~98%). They occupy genuinely different points; none dominates.

## Theoretical grounding — and its caveat

The Platonic Representation Hypothesis (intake-770, MIT/Isola, ICML'24, cred 5) is the cited basis for *why* any of this works: models converge to a shared representation of reality, so a task behavior learned on one base is partly portable to another. **Critical caveat for us:** the Capacity Hypothesis says convergence is *strongest for large/capable models and weakest for small/heterogeneous ones* — exactly the regime our small drafters (Qwen3-0.6B/1.7B) and mixed roster occupy. Our own cross-tokenizer spec-dec deep-dive (2026-05-27) already found acceptance is capped by capability gap + vocab overlap. **Implication: do not assume portability — the actionable residue is the mutual-kNN alignment metric as a cheap per-pair pre-screen** (itself GPU/representation-extraction-gated).

## The one action that is CPU-runnable NOW

**Text-to-LoRA zero-cost validation (intake-771).** It is the only cluster member shipping open code + open pretrained hypernetwork weights (Mistral-7B, Llama-3.1-8B, **Gemma-2-2b-it**). A no-GPU spike:
1. Pull the released Gemma-2-2b-it T2L hypernetwork.
2. Generate a LoRA from a natural-language task description (single forward pass, ~5-55M-param hypernet).
3. Convert the adapter to GGUF; hot-swap into llama.cpp on Gemma-2-2b-it (hot-swap path is DONE per 08-doc-to-lora Finding 1).
4. Observe whether text-conditioned adapters do anything useful on a base we can actually load.

This tests the *inference-side* mechanism end-to-end without touching the training GPU-gate, and its finding gates whether the doc-to-LoRA line is worth reopening at all. **Blocker to close first:** orchestrator `--lora` wiring (08-doc-to-lora Finding 7).

## Recommendation

- **Reopen-gate for `doc-to-lora`:** (training-capable GPU) **AND** (a demonstrated specialization need REPL/in-context retrieval cannot cover). Neither holds today.
- **If reopened, method selection:**
  - Generate-from-text, single base → **Text-to-LoRA** (open, forward-pass, our default entry point).
  - Port an existing adapter across a *rotating* roster, high fidelity, GPU available → **PorTAL** (per-base converter refit).
  - Zero-training CPU baseline to port an adapter → **Cross-LoRA** (accept the low fidelity; re-measure per-task lift on OUR bases, not the paper's <1% commonsense deltas).
  - Personalization slot (orchestrator B1 user-modeling) → **Profile-to-PEFT** as the weight-baking alternative to our current prompt-injection — but our single-user host nullifies its multi-user amortization value prop.
- **Do now (CPU, no gate):** the Text-to-LoRA validation spike, once orchestrator `--lora` wiring lands.
- **Do not** invest in CAST until its "activation-space > weight-space" claim is re-validated head-to-head (current evidence is estimated baselines / illustrative ranges / single author).

## Cross-references

- Handoff: `handoffs/completed/08-doc-to-lora-prototype.md` (the line this cluster feeds; reopen-gated), `handoffs/active/swarm-dataset-distillation.md`, `handoffs/active/orchestrator-conversation-management.md` (B1 user modeling ↔ Profile-to-PEFT).
- Intake: 764 (PorTAL), 765 (Cross-LoRA), 766 (LoRA-X), 767 (CAST), 768 (SHINE), 769 (Profile-to-PEFT), 770 (Platonic), 771 (Text-to-LoRA); existing 098 (DocToLoRA), 707 (Code2LoRA), 618 (ZeTT).
- Related deep-dive: `research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md` (empirical counterweight on cross-model portability).

## Measurement note

All fidelity/accuracy figures in this cluster are self-reported preprint observations (only LoRA-X and Text-to-LoRA are peer-reviewed; PorTAL is a fintech-labs writeup with product-lab bias and no independent corroboration). Per MEASUREMENT.md they are hypothesis-shaping, never decision-gating — any adoption gates on local re-measurement on our own bases/tasks.
