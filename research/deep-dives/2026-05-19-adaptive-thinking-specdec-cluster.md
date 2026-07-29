# Adaptive Thinking + Spec-Dec Concurrency Cluster — 2026-05-19

**Cluster #7 of 8 — deep-dive synthesizing three intakes around a single practitioner signal**

| Intake | Source | Status post-deep-dive |
|--------|--------|----------------------|
| intake-542 | @jun_song X-post (Super-Tune); @ZenMagnets reply | Direction-setting (anecdotal); validated by intakes 566/567 |
| intake-566 | CGR / Certainty-Guided Reasoning (arXiv:2509.07820) | **Actionable** — concrete sampling-loop patch viable on EPYC |
| intake-567 | ECHO / Elastic Speculative Decoding (arXiv:2604.09603) | **Corroborative-not-actionable** — high-concurrency regime, SGLang-bound |

## Executive Summary

CGR is concretely actionable on EPYC: a model-agnostic, **train-free**, ~150-LoC sampling-loop patch in `epyc-llama` that probes answer-token certainty every 1,000 tokens and stops thinking when min-max probability ≥ 0.97 — projected ~5% token reduction at iso-accuracy on AIME2025-style benches with single-knob tunability. ECHO is **corroborative-not-actionable** for our single-user (bs≈1) regime: its super-tree scheduler targets bs=8–256 SGLang serving on H100 clusters, and the paper's own data (Qwen3-235B 2.02× at bs=1, +19% over EAGLE-3) is interesting but contradicts our shelved-dispatcher decision only for **non-greedy verifiers + large drafters** — the exact reopen criteria documented in `project_slot_promotion_shelved`. The jun_song practitioner signal sharpens priorities: adaptive-thinking-first (CGR), spec-dec-second (still shelved unless reopen criteria activate). Net: one concrete spike (CGR prototype), one negative-result reference (ECHO confirms our shelved decision was right for our workload), one piece of practitioner intuition validated by two academic papers in the same week.

## CGR Mechanism in Detail

### Certainty probe (verified from arXiv:2509.07820)
- **What it measures**: `p_min-max = min(max_i p(t_i))` — the **minimum probability among answer tokens only** (not all tokens, not top-k entropy). Each answer token is the model's most likely output at that step; we take the min across the answer span.
- **Cadence**: every **1,000 tokens** of the thinking trace, the model's current output is examined for a candidate answer. If a candidate answer is present, its certainty is computed; if `p_min-max ≥ θ`, thinking is terminated and the answer emitted.
- **Threshold**: **fixed θ = 0.97** in headline results (not adaptive). Authors tested 0.90–0.99; 0.97 is the operating point where "certainty values above 0.97 reliably correlate with correct predictions."
- **Single knob**: `θ ∈ [0.90, 0.99]` is the only tunable hyperparameter. Higher θ → less aggressive early-stopping → fewer tokens saved, lower accuracy hit.
- **Grade metric**: `Grade = Total Correct − c × Total Incorrect`. Tested with c ∈ {0, 0.25, 1.0}. Permits **abstention = 0 points** (vs. wrong = −c). This is critical: CGR encourages "stop thinking AND emit answer" only when certain; otherwise the model can continue or abstain.
- **AIME2025 (DeepSeek-R1-Distill-Qwen-14B)**:
  - Baseline: 13/30 (43%)
  - CGR (θ=0.97): 12/30 (40%) — **1 question lost**, ~3pp accuracy hit
  - Tokens saved: 3,081,690 total / ~48,151 per seed / ~1,605 per question (~5% relative)
- **Models tested (3, supports model-agnostic claim)**: DeepSeek-R1-Distill-Qwen-14B, Phi-4-reasoning-plus, Qwen3-14B.
- **Code**: **NOT released**. No GitHub URL, no license. We'd implement from the paper description — fortunately, the algorithm is trivial.

### Why this fits EPYC

1. **Train-free** — no fine-tune cost on our hardware (no GPU).
2. **Inference-only** — patches the sampling loop, not the model weights.
3. **Model-agnostic** — works across DeepSeek, Phi, Qwen architectures already on our shelf.
4. **Single knob** — easy A/B against existing hard-cap budget in `per-request-reasoning-budget` handoff.
5. **Cheap probe** — 1 in 1,000 tokens means probe overhead is negligible (<0.1% of decode).

## CGR EPYC Integration

### Patch design (concrete)

**Target**: `epyc-llama` fork's `common/sampling.cpp` or equivalent main decode loop in `llama-cli` / `llama-server`.

**Algorithm**:
```
on every token decoded:
    if (token_count % PROBE_CADENCE == 0):
        candidate = extract_answer_span(decoded_buffer)
        if (candidate is not None):
            p_min_max = min(max_token_probs_in_span(candidate))
            if (p_min_max >= THRESHOLD):
                inject_stop_thinking_token()  // or directly terminate <think>
                break
```

**Surface**:
- New server flag: `--certainty-threshold 0.97` (default off; off = 0.0 = disabled)
- New server flag: `--certainty-cadence 1000` (default 1000)
- New server flag: `--answer-extractor regex|sentinel` (regex match for `\\boxed{...}` or sentinel `<answer>...</answer>`)
- Metric exposure via `/metrics`: `cgr_probes_total`, `cgr_early_stops_total`, `cgr_tokens_saved_total`.

**Estimated cost**: ~150 LoC in sampling loop + ~50 LoC for answer-extraction utility + ~30 LoC for server flag plumbing + ~50 LoC tests. **Total ~280 LoC, 1 PR.**

**A/B vs. existing levers**:
- Baseline: no thinking budget
- Lever A: hard-cap budget (`per-request-reasoning-budget` handoff — already landed)
- Lever B: CGR (this spike)
- Lever C: hard-cap ∧ CGR (compose — CGR fires whichever comes first)

**Test bench**:
- **Coder bench**: a long-CoT subset of `epyc-inference-research/benchmarks/coder/` — measure tokens + pass@1
- **Architect bench**: `architect_bench` (long planning traces) — measure tokens + grade
- **Optional sanity**: AIME-2024 (frozen subset to reproduce paper) — 30 problems, ~10 min on 30B-A3B Q4_K_M

**Success criteria**:
- **Primary**: ≥10% aggregate token reduction at ≤2pp pass@1 drop on coder bench
- **Secondary**: tunability — show monotone θ → tokens/accuracy curve with at least 3 operating points
- **Tertiary**: composability — CGR ∧ hard-cap doesn't double-penalize (no compounding regressions)

## CGR Failure Modes

The paper acknowledges almost no failure modes (`Question 2, 3, 13, 21` are "particularly challenging," and "the model never stopped thinking" on some questions). The literature is harsher:

### From related literature (cross-checked against handoffs already in scope)

1. **Bimodal brittleness (arXiv:2505.15400)** — adaptive thinking is **under-thinking on hard problems** AND **over-thinking on easy ones**. CGR's fixed 0.97 threshold cannot distinguish "I am certain because the problem is easy" from "I am certain because I have not yet uncovered my error." On hard problems where the correct answer hasn't crystallized, the model can be locally confident in a wrong intermediate answer.
2. **ASRR class of methods** — adaptive stopping in general achieves ~32.5% budget reduction at ~1.2% pass@1 loss. The accuracy hit is **non-zero by construction** — there's a frontier, not a free lunch.
3. **Probability-over-answer-tokens is noisy on hard problems** — sharp distributions don't imply correctness; they imply low calibrated entropy at that step. RLHF/reasoning-trained models are known to be **overconfident in wrong answers** mid-chain (well-documented in `reasoning-recall-cot-controllability.md` and `flowsteer-concise-reasoning.md` deep-dives).
4. **Cadence interaction** — probing every 1,000 tokens means CGR can miss early correct answers (model arrives at answer at token 200 but probes at 1,000) — silently wasting 800 tokens. Lower cadence costs more probes but catches more savings.

### Mitigations to bake into the spike

- **Measure tokens AND pass@1 jointly** — never report token reduction without paired accuracy.
- **Abstention rate as a 3rd metric** — if c (incorrect penalty) is enabled and abstention is encouraged, track abstention separately so we can tell "saved tokens because confident" from "saved tokens because gave up."
- **Per-bench analysis** — easy/hard split (e.g., GSM8K-easy vs. AIME-hard) to detect bimodality.
- **Sweep cadence** in 1 spike — {200, 500, 1000, 2000} — to characterize the cadence/savings tradeoff.

## ECHO Analysis (Why Not Actionable)

### What ECHO actually does (verified from arXiv:2604.09603)

- **Regime**: bs ∈ [8, 256] on **8× H100 80GB** with SGLang serving.
- **Mechanism**: reformulates token-tree construction as a **budget scheduling problem** under a strict verification cap. Two-priority scheduler:
  - P1: global depth extension for high-confidence requests
  - P2: opportunistic width expansion when no request can extend depth
- **Sparse confidence gating**: offline-calibrated "sweet spot" depths (AUC > δ) where binary extend/truncate decisions are made via learned thresholds τ_d. Not dense per-layer like prior work.
- **Super-tree**: batch becomes one unified super-tree sharing one global verification budget `K_max`. Individual request trees `{G_i}` are unified via `⋃_i G_i` and verified in one parallel forward pass.
- **Integration**: **SGLang** (explicitly), with specialized irregular-batch operators.
- **Numbers**:
  - Qwen3-235B at **bs=1**: 2.02× speedup (vs. EAGLE-3 1.69× — **+19% relative over EAGLE-3**)
  - LLaMA3.3-70B at bs=1: 5.35× (vs. EAGLE-3 4.98×)
  - Qwen3-235B at bs=256: 14.4% throughput gain (2,803 → 3,207 tok/s)
  - LLaMA-3.1-8B at bs=256: +8%
- **Code**: not yet released. "Source code of this project will be made available at a later time."

### Why not actionable for EPYC

1. **bs=1 is our regime, but the bs=1 gain is "+19% over EAGLE-3"** — EAGLE-3 itself is not running on llama.cpp; getting EAGLE-3 first is the dominant cost. ECHO is an incremental improvement on top of an infrastructure layer we don't have.
2. **SGLang-coupled**: super-tree verification + irregular batch operators are SGLang-kernel work. Porting to llama.cpp CPU is a multi-month research effort with no guarantee of CPU translatability (the verification-bound regime is GPU-specific).
3. **Single-user bs=1 with greedy verifier**: this is the **exact regime where `project_slot_promotion_shelved` proved dispatcher v1 net-negative**. ECHO operates further up the stack — even if the underlying drafter were perfect, our shelve decision wasn't about tree topology, it was about verifier-greedy + small-drafter + single-stream KV-cache contention.
4. **ECHO's "bs=1 advantage" doesn't necessarily translate to CPU**: their bs=1 number is on H100 with hardware-accelerated tree verification (CUDA kernels for sparse attention masks). EPYC CPU does verification with a different cost model.

### Value of ECHO to EPYC (what it IS good for)

- **Evidence supporting `project_slot_promotion_shelved`**: confirms vanilla EAGLE-3 falls below baseline at bs=128 (paper's Table). Our shelve decision is consistent with the broader literature.
- **Reopen-criteria reference**: if/when we adopt SGLang serving OR move to a multi-user regime, ECHO is the first thing to reach for. File under "deferred research" with reopen condition.
- **Drafter-target disagreement framing**: ECHO's confidence-gating math (which depths to probe) is the same math we'd want for a smarter dispatcher under our shelved criteria (larger drafter, non-greedy verifier).

## jun_song Practitioner Signal — What it Says + Doesn't

### What's signal

- **100k+ context regime** (a regime we don't routinely test but care about for architect/agentic workloads).
- **SFT duplicate-suppression + Adaptive Thinking are the levers that survived** — this is a 2-of-N elimination result, not just "thing worked." When a practitioner reports "everything else collapsed quality," that's stronger than "X improved quality."
- **Validated by two same-week papers**: CGR (adaptive thinking, train-free) and ECHO (spec-dec at concurrency) — convergent academic evidence in the same week as the X-post.

### What's noise

- N=1 practitioner, no eval suite cited, no public reproducer.
- "Quality" is undefined — could be hallucination, repetition, instruction-following, reasoning, all of the above.
- Korean-language source — translation/contextual nuance may be lost.

### @ZenMagnets reply (spec-dec hurts high-concurrency)

- **Partially right**: ECHO's paper itself documents vanilla EAGLE-3 degrading at bs=128. ZenMagnets is correct about the **vanilla** failure mode.
- **Wrong about the ceiling**: ECHO + DDD + super-tree scheduling **recover and exceed** baseline. The problem is solvable; it's just not solved by stock implementations.
- **Net**: ZenMagnets' assertion is true for the deployment context most practitioners are in (vanilla vLLM/SGLang spec-dec), but is not a fundamental ceiling.

### duplicate-suppression SFT

- **Necessary-not-sufficient**: open-r1 issue #492 documents that even with duplicate-suppression SFT, repetition can recur post-SFT on long-form generation. This is consistent with our `ring-mini-stuck-in-think-failure-mode.md` deep-dive — adaptive stopping at the **decode side** is a complementary mitigation.
- **EPYC implication**: we don't fine-tune, so duplicate-suppression SFT is out of scope. CGR + hard-cap budget are the inference-side mitigations that achieve a related outcome (stop the loop before it explodes).

## Concrete Spike Proposal

Three steps, ordered by cost and unblocking value:

### Spike 1 (CHEAPEST, ACTIONABLE NOW): CGR prototype in epyc-llama

- **Dev cost**: ~280 LoC, ~1 day to land (sampling-loop patch + flags + tests). One PR, one reviewer.
- **Compute cost**: A/B sweep at 3 θ values × 2 benches × 3 seeds ≈ 18 runs. **Requires `feedback_no_concurrent_inference` approval** before launch. Estimated wall clock: 4-6 hours on EPYC (coder bench + architect bench at typical 30B-A3B Q4_K_M throughput).
- **Success criteria**:
  - Primary: ≥10% token reduction at ≤2pp pass@1 drop on coder bench
  - Secondary: monotone θ → tokens/accuracy curve (3 points)
  - Tertiary: composability with `per-request-reasoning-budget` hard-cap (no double-penalty)
- **Risk**: low — paper shows 5% savings at 3pp loss on a hard bench (AIME), our coder bench should be easier with more headroom.
- **Unblocks**: closes intake-566; informs `reasoning-compression.md` handoff with a concrete adaptive-stop primitive.

### Spike 2 (MEDIUM): Adaptive Thinking failure-mode evaluation

- **Dev cost**: ~50 LoC bench-runner extension to split easy/hard subsets and report per-subset metrics. ~0.5 day.
- **Compute cost**: GSM8K-easy + AIME-hard split, each at 3 θ values, 3 seeds = 18 runs. Wall clock ~3-4 hours.
- **Goal**: directly test the bimodal-brittleness hypothesis (arXiv:2505.15400) on **our** models in **our** quants. Measure under-thinking on hard problems vs. over-thinking on easy ones.
- **Success criteria**: explicit characterization of where CGR fails — produces a "use/don't use" routing rule (e.g., "enable CGR for coder bench, disable for architect bench" or "enable only for token_budget > 4k requests").
- **Depends on**: Spike 1 landed and merged.

### Spike 3 (DEFERRED): ECHO

- **Not actionable until**: we adopt SGLang OR move to multi-user serving OR satisfy `project_slot_promotion_shelved` reopen criteria (larger drafter, non-greedy verifier, long-context workload, high drafter-target disagreement).
- **Watch criteria**: monitor ECHO code release; when it lands, re-evaluate.
- **Recorded as**: deferred-research note in `moe-spec-cpu-spec-dec-integration.md` handoff with explicit reopen condition.

## Open Questions for User

1. **CGR θ default if we ship a flag**: do we want CGR off-by-default (safer; explicit opt-in) or on-by-default at conservative θ=0.99 (maximizes deployed coverage)?
2. **Answer-extractor surface**: should the spike support pluggable extractors (regex + sentinel + model-specific like `\\boxed{}`), or land with one and add others later?
3. **Bench selection for Spike 1 A/B**: do you have a preferred coder bench in `epyc-inference-research/benchmarks/` with long-CoT traces, or should we use a standard one (HumanEval+ with extended reasoning prompts)?
4. **Compute approval**: do we want to bundle Spike 1's 18-run A/B sweep into the next autopilot batch, or run it as a dedicated session under explicit per-run approval per `feedback_no_concurrent_inference`?
5. **Reopen-spec-dec watch**: should `project_slot_promotion_shelved` be re-checked when a larger drafter lands (e.g., the gemma4-26B-A4B drafter for some target — currently used as worker), per the existing reopen criteria, OR should that wait for a multi-user workload?

## References

- **CGR paper**: arXiv:2509.07820 — *Certainty-Guided Reasoning* — Pranav et al. — three-model evaluation on AIME2025 with grade-based metric.
- **ECHO paper**: arXiv:2604.09603 — *ECHO: Elastic Speculative Decoding* — super-tree + sparse confidence gating on SGLang/H100.
- **jun_song X-post (intake-542)**: practitioner signal, Super-Tune post on 100k+ ctx survivors.
- **@ZenMagnets reply (intake-542)**: spec-dec-at-concurrency concern; partially validated by ECHO Table.
- **Adaptive-thinking brittleness**: arXiv:2505.15400 — bimodal under/over-thinking failure mode.
- **ASRR**: ~32.5% budget reduction at ~1.2% pass@1 loss — adaptive-stop reference frontier.
- **open-r1 issue #492**: duplicate-suppression SFT necessary-not-sufficient — post-SFT repetition persists.

### EPYC handoffs touched by this cluster

- `handoffs/active/per-request-reasoning-budget.md` — updated 2026-05-19 with CGR composability note
- `handoffs/active/reasoning-compression.md` — updated 2026-05-19 with CGR adaptive-stop primitive
- `handoffs/active/memento-block-reasoning-compression.md` — referenced for SFT-side compression
- `handoffs/active/context-folding-progressive.md` — referenced for long-context regime (jun_song signal)
- `handoffs/active/moe-spec-cpu-spec-dec-integration.md` — ECHO recorded as deferred-research reference, reopen-criteria documented

### Related EPYC deep-dives

- `research/deep-dives/reasoning-compression-s3cot-adaptive.md` — adjacent adaptive-stop survey
- `research/deep-dives/flowsteer-concise-reasoning.md` — overconfidence-in-wrong-answers reference
- `research/deep-dives/ring-mini-stuck-in-think-failure-mode.md` — stuck-thinking failure mode
- `research/deep-dives/reasoning-recall-cot-controllability.md` — CoT controllability framing
- `research/deep-dives/overthinking-info-bottleneck.md` — overthinking as info bottleneck
- `research/deep-dives/qwen36-27b-dense-spec-dec-cpu-feasibility.md` — spec-dec feasibility on CPU
- `research/deep-dives/dflash-dart-diffusion-speculation.md` — alternative speculation primitive

### EPYC memory anchors

- `project_slot_promotion_shelved` — dispatcher v1 net-negative; reopen criteria documented
- `feedback_think_mode_benchmarks` — benchmarks run without think mode for stability
- `feedback_no_concurrent_inference` — per-run approval required before any benchmark launch
- `feedback_always_sweep` — never skip param sweeps; verify with measurement
- `feedback_sanity_check_before_compute` — verify new infra produces different output before long compute
