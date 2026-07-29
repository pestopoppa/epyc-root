# Architect Model Selection — Evidence + Decision Tree (2026-07-20)

**Question:** which model should hold the **architect** role — deep multi-step planning /
decomposition / reasoning over broad context (*not* the frontdoor/router, *not* a knowledge-QA
role)? "The worst thing we can have is a mediocre architect." Candidates, at their deploy quant/device:

| Candidate | Active / Total | Deploy | ~Decode t/s | Notes |
|---|---|---|---|---|
| **Qwen3.5-122B-A10B** UD-IQ2_M | 10B / 122B | MI210 (GPU-resident) | 43.7 single / 148.7 agg@B32 | fits 64 GB only at IQ2; IQ2 PPL 5.02; **reasoning not yet gated** (see §3) |
| **Qwen3.5-122B-A10B** UD-Q4_K_M | 10B / 122B | CPU (current production architect) | ~18–21 single | 73 GiB → CPU-only; near-lossless quant; **the incumbent** |
| **Qwen3.6-27B dense** | 27B / 27B | MI210 (GPU) | ~40 (MTP) | max active width; Q8 near-lossless; CPU-poor (~4.4 t/s) |
| **Qwen3.6-35B-A3B** Q8 | 3B / 35B | CPU or MI210 | 34.5 CPU / ~120 GPU | the frontdoor model; **shallowest reasoning** (3B active) — baseline only |

This note is the rationale behind [`../../handoffs/active/architect-model-selection-bench.md`](../../handoffs/active/architect-model-selection-bench.md),
which converts the principled ranking below into a **decision-grade** local result. Sources were
deep-dived read-only on 2026-07-20 (see that handoff's intake list).

## 1. Reasoning depth ∝ ACTIVE params; knowledge breadth ∝ TOTAL params  *(SOLID)*
- **Qwen3 Technical Report (arxiv 2505.09388):** at ~equal size, dense **Qwen3-32B vs MoE Qwen3-30B-A3B**
  (thinking mode) — AIME'24 **81.4 vs 80.4**, AIME'25 **72.9 vs 70.9**, LiveCodeBench-v5 **62.7 vs 62.6**,
  GPQA slightly *ahead* for the MoE. I.e. dense edges the MoE by **~1–2pp on hard reasoning (near-parity)**
  while the MoE uses **~1/10 the active compute** (3B vs 32B). MoE reaches dense-level quality at a
  fraction of the active FLOPs → the core reason **MoE wins on a bandwidth-bound CPU**.
- **Optimal Sparsity of MoE for Reasoning (arxiv 2508.18672, ICLR'26 oral):** *active FLOPs* drive
  reasoning; *total params* drive memorization. Reasoning is **non-monotonic in sparsity** — at low
  active compute sparser wins, but **once active-param counts grow, denser overtakes**; raising total
  experts at fixed top-k **degrades** reasoning, raising top-k (active) **mitigates** it. Neither
  test-time compute nor GRPO rescues an over-sparse reasoning deficit — it is **architectural**.
- **Ranking implication (reasoning axis):** **27B-dense (27B active) ≳ 122B-A10B (10B active) ≫ 35B-A3B (3B active)**.
  **Knowledge axis:** 122B (122B total) > 35B (35B) > 27B (27B). The architect wants **both** →
  a **large-total / moderate-active MoE (122B-A10B)** is the literature-default profile: enough active
  width for reasoning *plus* large total for knowledge, at a CPU-affordable active-param decode cost.
  Dense-27B maximizes reasoning-per-token but has **zero knowledge headroom** and is **CPU-costly** (only
  viable GPU-resident). 35B-A3B is the low-active corner → **weakest reasoning bet**.

## 2. Q4 is safe for reasoning on large MoE; sub-4-bit is fragile on REASONING and knowledge evals hide it  *(SOLID)*
- **DeepSeek quant analysis (arxiv 2505.02390) — our EXACT toolchain (llama.cpp GGUF K-quants + Unsloth,
  DeepSeek-class MoE):** Q4_K_M ≈ FP8. At 2-bit, **MMLU holds ~99%** (90.99→89.72) while **uniform Q2_K
  halves reasoning** (DeepSeek-V3 **AIME 38.34 → 15.41**). Crucially, **dynamic per-layer quant holds**:
  **DQ3_K_M ≈ Q4** (V3 75.73 vs Q4 75.79). ⇒ IQ2 is admissible **only** as dynamic/imatrix (UD-IQ2_M),
  **never uniform Q2**, and a **dynamic 3-bit mid-precision fallback exists** if IQ2 proves too weak.
- **Quantization Hurts Reasoning? (arxiv 2504.04823):** W4A16 / Q4_K ≈ lossless on ≥14B models; the
  danger zones are **activation/KV quant and sub-4-bit**; **harder tasks (AIME) degrade up to ~4× more**
  than easy ones (GSM8K).
- **Quantization Meets Reasoning (arxiv 2505.11574):** low-bit PTQ **disproportionately raises
  method/execution (procedural) errors** — exactly the architect's multi-step-planning capability.
  Mitigation: a **~332-example curated recovery-SFT (minutes on 1 GPU)** restores most of the loss.
- **Caveat (keeps us honest):** 2504.04823 / 2505.11574 measure **GPU-style W-A/KV quant on SMALL models
  (0.5–7B)** — the most fragile regime; our case (large MoE, weights-only GGUF) should degrade **less**.
  So the IQ2-122B reasoning penalty is **genuinely uncertain in direction magnitude** — which is *why*
  it must be measured, not assumed.

## 3. The load-bearing gap in OUR data — the Δ0.0pp parity is powerless on reasoning
AXA-1 (`../../handoffs/active/mi210-big-model-and-acceleration-roadmap.md`) records the GPU-resident
IQ2 candidate as quality-gated: a **212-question deterministic paired eval**, IQ2 163/212 = Q4 163/212,
**Δ0.0pp, McNemar p=1.000** (2026-07-05, commit `679a6f61`). But the pool composition (from the scratch
harness `iq2_parity_results.jsonl`) is **knowledge/instruction-following dominated**:

| slice | n | kind |
|---|---|---|
| instruction_precision | 84 | instruction-following (programmatic) |
| simpleqa / hotpotqa / general | 24 / 24 / 24 | factual + multi-hop **knowledge** |
| thinking | 24 | reasoning-formatting |
| **gpqa / math / usaco / livecodebench / debugbench / coder / mode_advantage / long_context** | **4 each (~24 total)** | **hard reasoning** |

So the reasoning slice is **n ≈ 4 per suite (~11% of the pool)** — **statistically powerless** to detect
the exact degradation §2 predicts (which lands hardest on AIME/GPQA). The Δ0.0pp is a valid
**knowledge / instruction-following** parity; it is **not** a reasoning certification. The **LLM-rubric
(reasoning-quality) gate was explicitly deferred**, and the whole result is **observation-grade under
`P-GPU-1`** (measured on experimental v7). ⇒ The bench runs **full-power AIME'25 + GPQA-Diamond** where
this parity had n≈4.

## 4. Tool-availability adjustment (operator, 2026-07-20)
The orchestration has web-search / RAG / sub-agent tools, so the architect can **delegate retrieval** →
legitimately **down-weights knowledge breadth** for this role and up-weights reasoning depth →
strengthens the **dense-27B** case. Honest caveats: the model still needs enough internalized knowledge
to *know what to retrieve* and to *integrate* results, and some reasoning-relevant knowledge (identities,
algorithms) isn't retrievable mid-thought. ⇒ the bench includes a **tool-using multi-step planning task**,
not only closed-book AIME/GPQA.

## 5. Decision tree (resolved by the bench)
- **IQ2 ≈ Q4 on AIME/GPQA** → **122B-A10B stays architect, GPU-resident at IQ2** — AXA-1's 2.2×/~8–9×
  residency win becomes reasoning-certified; the literature default holds.
- **IQ2 ≪ Q4 (reasoning tanks), Q4 strong** → IQ2 is out. Probe **dynamic 3-bit (DQ3/Q3_K)**: if it ≈ Q4
  and fits the GPU, GPU architect = 122B-DQ3 (2505.02390); else the architect stays **Q4-122B on CPU**
  (~20 t/s) and the GPU slot goes to Qwable / vision / drafter. (The quant-asymmetric self-spec — IQ2 GPU
  *drafter* + Q4 CPU *verifier* — is the graceful fallback for a too-weak-to-serve-but-fine-to-draft IQ2.)
- **27B-dense-Q8 meaningfully out-reasons the 122B arms on hard tasks + fits GPU cheaply** → reconsider
  **27B-dense as GPU architect** (weigh its lost knowledge headroom, offset by tool access).
- **35B-A3B trails both** (expected, 3B active) → confirms it is not an architect; the frontdoor is unchanged.

## 6. Ranking (principled — the bench makes it decision-grade)
Best-supported prior: **122B-A10B is the architect**, at **Q4 by default** (safe), **IQ2 only if the
reasoning re-gate passes** (plausible for a large *dynamic*-quant MoE, but unproven), with **dynamic-3-bit
as the mid-precision fallback**. 27B-dense is the live challenger *if* its max active width buys real
hard-reasoning margin. 35B-A3B is the reasoning floor / control.

## 7. Frontdoor stays fast/shallow (settled 2026-07-20)
First-contact should NOT be a "smarter" model: routing is classification/dispatch (a 3B-active model
suffices) and routing intelligence is **externalized** (learned router controller / difficulty bands /
reviewer-control-plane). Depth is applied on **escalation** to the architect, not speculatively on the
hot path. Weak routing → fix the **router controller**, not the frontdoor model.

## 8. Evidence grade
- **SOLID:** reasoning∝active (2505.09388 + 2508.18672); IQ2 hurts reasoning ≫ knowledge, our exact
  toolchain (2505.02390) + corroborating (2504.04823 / 2505.11574); dynamic-IQ2 ≫ uniform-IQ2; Q4 ≈ FP8.
- **THIN:** every *direct* benchmark of the exact Qwen3.5/3.6 models — community aggregators, high
  variance, no official 3.5/3.6 report (e.g. 27B-dense GPQA reported as both 73.4 and 87.8; a
  deployment-eval preprint scores Qwen3-30B-A3B dead-last 0.226, a harness/prompt artifact contradicting
  its own 80% AIME elsewhere). ⇒ the ranking is **principled, not benchmark-certified** → the local bench
  converts it to decision-grade.
