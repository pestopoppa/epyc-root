# OpenMythos Looped Transformer Pointers — Deep Dive

- **Source**: https://github.com/kyegomez/OpenMythos
- **Date**: 2026-04-20
- **Intake ID**: intake-420
- **Author**: Kye Gomez
- **Verdict (initial)**: worth_investigating

---

## 1. What OpenMythos Claims to Be

A speculative, reverse-engineered implementation of "Claude Mythos" as a Recurrent-Depth Transformer (RDT). The core hypothesis: Claude uses **looped transformer layers** (recycle L layers K times → KL effective depth with L parameters) with continuous latent reasoning across loop iterations instead of discrete chain-of-thought tokens.

**Finding: This is 100% speculation.** No verified information about Claude's actual architecture is used. The repo is a PyTorch implementation of a theoretical architecture combining:
- Looped/recycled transformer blocks
- Mixture of Experts routing
- Adaptive Computation Time (ACT) halting
- LTI-constrained training stability (Parcae technique)

## 2. The Repo Itself — Not Valuable

| Property | Assessment |
|----------|------------|
| Pretrained weights | None |
| Benchmarks | None |
| Novel code | Boilerplate PyTorch + config classes |
| Documentation | Marketing-heavy README |
| Community | Recent, no forks with substance |

The implementation is a standard PyTorch model definition with configurable components. There's nothing here you couldn't write in an afternoon. No novel engineering.

## 3. What IS Valuable — The Reference Papers

OpenMythos surfaces **two April 2026 arXiv papers** not yet in our intake index:

### 3a. arXiv:2604.07822 — "Loop, Think & Generalize"

Based on the reference context: This paper likely demonstrates that looped transformers exhibit systematic generalization on compositional tasks — something standard deep transformers fail at. The "phase transition" claim (sudden capability emergence with loop count) is the interesting bit.

**Relevance to us**: If models gain compositional reasoning via looping rather than depth, this has implications for:
- Whether our Qwen3.5-27B (hybrid SSM-Dense) could benefit from architectural modifications
- Whether future model choices should favor looped architectures
- Whether the "reasoning budget" concept (per-request-reasoning-budget.md) maps to loop iterations

**Assessment**: Worth a standalone intake entry. The paper likely has empirical results (unlike OpenMythos).

### 3b. arXiv:2604.12946 — "Parcae" (Scaling Laws for Stable Looped LMs)

This paper addresses a known failure mode of looped transformers: training instability when loop count is high. The technique constrains injection parameters so the spectral radius of the recurrence stays below 1, guaranteeing stability by construction.

**Relevance to us**: Limited — we don't train models. But if looped architectures become viable (Ouro-1.4B/2.6B from ByteDance, intake-332), understanding their stability guarantees helps evaluate which models to deploy.

**Assessment**: Low priority intake. Theoretical training-side contribution.

## 4. Relationship to Existing Work

| Existing Entry | Relationship to OpenMythos |
|---------------|---------------------------|
| intake-332 (Ouro) | **Supersedes** — Ouro has actual pretrained looped models (1.4B, 2.6B) with empirical results (AIME24 64.7%, MATH-500 90.85%) |
| log-linear-gated-deltanet-readiness.md | Tangential — GDN is about linear attention (O(n) inference), looped transformers are about depth reuse |
| reasoning-compression.md | Conceptual overlap — "latent reasoning without tokens" relates to reasoning compression goals |
| per-request-reasoning-budget.md | Conceptual overlap — ACT (adaptive halting) maps to "variable compute per request" |

## 5. Looped Transformers for CPU Inference — Would They Help Us?

**Theoretical advantage**: A looped transformer with 8 unique layers × 4 loops = 32 effective layers. The model parameters are 4x smaller (only 8 layers of weights to load). On CPU where memory bandwidth is the bottleneck, this could mean:
- 4x less memory bandwidth needed for weights
- Same effective depth
- Much smaller GGUF file

**Practical problem**: No production-quality looped models exist in our size/quality range. Ouro tops out at 2.6B parameters. Nobody has trained a 27B-class looped model. Until that happens, this is theoretical.

**When this becomes actionable**: If a major lab releases a 20B+ looped model with competitive quality AND someone produces GGUF quantizations. Then we'd get a massive CPU inference win (same quality, fraction of the memory bandwidth). Watch for this.

## 6. Other Referenced Papers (Quick Assessment)

| arXiv ID | Likely Topic | Priority |
|----------|-------------|----------|
| 2604.07822 | Loop, Think & Generalize (compositional generalization via looping) | Medium — intake candidate |
| 2604.12946 | Parcae (stable looped LM training) | Low — training-side |
| 2502.17416 | Unknown — Feb 2025 | Low |
| 2412.06769 | Unknown — Dec 2024 | Low |
| 2410.20672 | Unknown — Oct 2024 | Low |
| 2603.15619 | Unknown — Mar 2026 | Low |
| 1807.03819 | Universal Transformers (2018, foundational) | Already known |
| 2401.06066 | Unknown — Jan 2024 | Low |

## 7. Verdict Delta

| Aspect | Initial Assessment | Post Deep-Dive |
|--------|-------------------|----------------|
| Repo value | worth_investigating | **not_applicable** — no code, no weights, no benchmarks, pure speculation |
| Pointer value | Surfaces new arxiv IDs | **arXiv:2604.07822 worth intake** — empirical results on looped generalization |
| Relevance | low | **low** — no looped models available in our size range |
| Action | "track Parcae paper" | **Intake 2604.07822 only**; skip Parcae unless we plan to train models |
| Future trigger | "when looped architectures become relevant" | **When a 20B+ looped model gets GGUF quantization** — then revisit for massive CPU bandwidth win |

**Updated verdict: `not_applicable` for the repo; `worth_investigating` for arXiv:2604.07822 as a separate intake.**
