# SAE Utility Falsification — AxBench (Wu et al. ICML 2025) + Wang et al. ICLR 2026

**Date**: 2026-05-04
**Origin**: Discovered during deep-dive of intake-521 (Qwen-Scope, `research/deep-dives/qwen-scope-sae-suite.md`). Both papers are cited *in passing* by Qwen-Scope but not benchmarked against; they are load-bearing falsification work for Qwen-Scope steering / SASFT / SAE-DAPO claims.
**Sources**: arxiv:2501.17148 (AxBench, ICML 2025 PMLR 267), arxiv:2510.03659 (Wang et al., ICLR 2026, OpenReview Q4ooLNOFeR). Joined deep-dive because the two papers form a complementary pair: AxBench shows the AVERAGE performance gap; Wang 2026 explains the underlying MECHANISM (interpretability-utility correlation is too weak to use interpretability as a quality proxy).
**Intake entries**: intake-522 (AxBench), intake-523 (Wang 2026)
**Status**: Both `adopt_patterns`. Two concrete methodological gates extracted; integration deferred until any EPYC SAE pilot starts.

## TL;DR

Standard SAE feature selection — including the contrastive-difference selection used in Qwen-Scope Sections 3 and 7 and the auto-interpretability pipeline used by GemmaScope — does not reliably produce features that are *useful* for downstream steering or behavior-modification tasks, even when the features are interpretable. Two independent quantitative findings on Gemma-2 and Qwen-2.5 anchor this:

- **AxBench (Wu et al. ICML 2025)**: across eight tasks on GemmaScope-equipped Gemma-2-2B-it / -9B-it, prompting beats every method, finetuning is second, ReFT-r1 is the best representation-based method, and difference-in-means dominates SAEs at concept detection. Authors\' own framing: *"even at SAE scale, representation steering is still far behind simple prompting and finetuning baselines."* Acknowledged confound: the SAE-feature labels come from Neuronpedia\'s auto-interp pipeline (token-level skewed); higher-quality labels improve SAE numbers but do NOT close the gap.
- **Wang et al. ICLR 2026**: across 90 SAEs (5 architectures × 6 sparsities) on Gemma-2-2B / Qwen-2.5-3B / Gemma-2-9B at fixed 16K width, Kendall tau-b between SAEBench auto-interp score and AxBench steering harmonic mean is **0.298** overall (per-model: Gemma-2-2B 0.218, **Qwen-2.5-3B 0.458**, Gemma-2-9B 0.306). After Delta Token Confidence-based feature selection, the correlation falls to **-0.069** — vanishes or flips. DTC selection itself yields +52.52% steering improvement over the prior best output-score baseline (Arad et al. 2025).

Both papers were known to the Qwen-Scope team — Wang 2026 is in the Qwen-Scope reference list (cited as Wang et al. 2026 with OpenReview ID Q4ooLNOFeR), AxBench is not cited but predates Qwen-Scope and is well-known in the SAE community. Neither paper\'s baselines (difference-in-means, prompting, ReFT-r1, DTC selection) are benchmarked against in Qwen-Scope. This is the single most important methodological gap in Qwen-Scope.

## What each paper actually shows

### AxBench (Wu, Arora, Geiger, Wang, Huang, Jurafsky, Manning, Potts — Stanford NLP, ICML 2025)

**What\'s measured**: two utility axes — concept detection C ∈ {0, 1, 2} and model steering S ∈ {0, 1, 2} — across many concepts. Steering is evaluated by an LLM judge on long-form generations. Concept detection uses labelled synthetic data as ground truth.

**Pipeline**: AxBench takes natural-language concept descriptions, samples positive / negative training and evaluation data via an LLM, then evaluates each method on detection (AUROC) and steering (LLM-judged harmonic mean of Concept / Instruction-following / Fluency). The authors explicitly position this against prior steering benchmarks "that only evaluate a few methods at merely toy scales."

**Methods evaluated** (per the paper\'s methodology section):
- Self-supervised: SAEs, SAE-A (alternative variant)
- Supervised dictionary learning (SDLs): DiffMean, PCA, LAT, Probe, SSV, ReFT-r1
- Behavioral baselines: Prompt, LoRA, LoReFT, SFT (SFT only on 2B due to compute)

**Headline result**: per Figure 1 — steering ranks in approximate order: Prompt > SFT > LoRA > LoReFT > ReFT-r1 > DiffMean > LAT > PCA > Probe > SAE > SSV > SAE-A. Concept detection ranks differently but SAE is similarly low. Quote from §6: "we can see that even at SAE scale, representation steering is still far behind simple prompting and finetuning baselines."

**Author-acknowledged confounds** (§6 + Appendix E.4):
1. Concept lists adapted from Neuronpedia\'s auto-interpretability pipeline. "Often skewed towards token-level concepts and misses high-level abstractions." Higher-quality labels improve SAE performance "but do not narrow its gap to SDLs such as ReFT-r1."
2. Two layers tested per backbone (specific layers not surfaced in our extract).
3. Tested on Gemma-2-it variants only.
4. Synthetic data generation depends on LLM judge quality.

**ReFT-r1 framing**: rank-1 representation finetuning that jointly learns concept detection (`ReLU(h · w)`) and steering (`h + (1/k) · TopK(detection-latents) · w`) from labelled data. The SDL framing makes it an interpretable supervised counterpart to SAEs. Released alongside the benchmark as SAE-scale dictionaries on `huggingface.co/pyvene`.

### Wang et al. (Wang, Hu, Wang, Zou — CityU + HKBU + HKU, ICLR 2026)

**What\'s measured**: per-SAE Kendall tau-b between SAEBench Automated Interpretability Score (Concept100 — average precision of an LLM judge\'s prediction across 100 sampled features) and AxBench steering harmonic mean (HM(C, I, F) = 3 / (1/C + 1/I + 1/F)).

**Sweep**: 90 SAEs trained from scratch:
- 3 base LLMs: Gemma-2-2B (layer 12), Qwen-2.5-3B (layer 17), Gemma-2-9B (layer 20)
- 5 architectures: BatchTopK, Gated, JumpReLU, ReLU, TopK
- 6 sparsity levels: target L0 ≈ {50, 80, 160, 320, 520, 820}
- Fixed dictionary width: 16K
- Training corpus: The Common Pile v0.1, ~5×10⁸ tokens per SAE
- Compute: 2× NVIDIA A800

**Headline result** (overall, axis-controlled):
- Kendall tau-b ≈ 0.298 [95% CI: 0.159, 0.419]
- Per-model Psi_C: Gemma-2-2B 0.2184, Qwen-2.5-3B 0.4575, Gemma-2-9B 0.3057
- After DTC-based selection: tau-b ≈ -0.069 [95% CI: -0.202, 0.067]

**Mechanism** (per the paper\'s framing): not all interpretable features steer effectively. The steering-effective features are *orthogonal or inversely related* to the interpretability axis. Hence "interpretability is at best irrelevant and potentially detrimental for top steering features."

**Delta Token Confidence (DTC)**: amplify feature `f` at layer `l` by α = 10, measure the change in negative-log-probability of the top-1 next token on a neutral prefix ("From my experience,"). Features with high DTC magnitude are the steering-causal features. DTC-selected features improve average steering harmonic mean by 52.52% over the prior best output-score-based selection (Arad et al. 2025).

**Author-stated caveats**:
- Weak overall signal (tau-b ≈ 0.3) indicates substantial interpretability-utility gap.
- Feature selection protocol is post-hoc rather than integrated into training.
- Future work likely needs "advanced post-training feature selection protocols or fundamentally new, utility-oriented SAE training paradigms."
- Tested on three models, residual-stream layer interventions only.

## Joint interpretation

The two papers are complementary:
- AxBench measures the average gap between SAE methods and simpler baselines — descriptively, on average SAEs lose. This is the externally-visible result.
- Wang 2026 measures *why* this happens — for any given SAE, only a small subset of interpretable features are steering-effective, and the standard contrastive / activation-frequency / output-score selection criteria don\'t isolate them. This is the underlying mechanism.

The combined story for any SAE-application proposal:
1. Vary architecture and sparsity, measure per-SAE interpretability and utility, plot the joint distribution. If your SAE is in the upper-right corner of that distribution (high interpretability AND high utility), you may have a defensible claim.
2. Or: explicitly use a utility-aware selector (DTC or successor) instead of the standard contrastive / output-score / auto-interp pipelines.
3. Either way, baseline against difference-in-means / linear probe / prompting before claiming SAE-specific value.

## How this binds Qwen-Scope (intake-521)

| Qwen-Scope section | What it claims | How AxBench / Wang 2026 bind it |
|--------------------|---------------|-------------------------------|
| §3 Steering case studies | Two anecdotal Qwen3 case studies showing feature suppression / activation works | Directly bound by AxBench: prompting and finetuning beat SAE steering on Gemma-2-it. Wang 2026 confirms the underlying interpretability-utility correlation is weak on Qwen-2.5-3B (tau 0.458 — better than Gemma but still <0.5). Anecdotes are not evidence. |
| §4 Benchmark redundancy via feature footprints | Spearman 0.85 with performance redundancy across 17 benchmarks | NOT directly bound — redundancy uses feature COVERAGE not feature interpretability. Wang 2026\'s findings on auto-interp ↔ steering correlation do not apply. AxBench does not test this regime. Section 4 stands. |
| §5 Rule-based OR-classifier on top1-diff features | F1 0.92 / 0.96 on toxicity, no extra trained head | Partially bound. AxBench reports difference-in-means dominates SAEs at concept detection on Gemma-2. Qwen-Scope does NOT run this comparison. Without the comparison, Section 5\'s framing as a primary classifier is unsupported. The audit-primitive framing (interpretability layer atop a learned classifier) survives. |
| §7 SASFT auxiliary loss on language-specific features | 50-100% code-switching reduction with documented HellaSwag -2.88 / MMLU -2.06 regressions on Qwen3-8B | Wang 2026 directly applies — SASFT identifies language-specific features via the same mean-activation-difference contrast that AxBench-evaluated methods use. Wang\'s Qwen-2.5-3B tau 0.458 says these features are not reliably the steering-causal ones. The Section 7 Table 5 regressions are consistent with selecting interpretable-but-not-useful features. |
| §8 Repetition feature + SAE-DAPO rare negatives | Repeat ratio drops, +5.84pp MGSM on Qwen3-30B-A3B | Less directly bound. AxBench tests output-space steering; SAE-DAPO uses rare-negative augmentation where the model learns to *avoid* steered outputs. This sidesteps the steering-degradation finding. Wang 2026\'s utility-falsification still applies in the sense that the repetition feature may not be the most-steerable feature — but the rare-negative setup is more robust to wrong-feature-selection than direct steering. |

## Two methodological gates extracted

These are the actionable deliverables. Already integrated into the deep-dive-revised handoff `qwen-scope-sae-toolkit.md`; documented here as the canonical citation.

### Gate 1 — Mandatory baselines (from AxBench)

Before piloting any SAE-feature classifier or SAE-steering intervention on EPYC, run these baselines on the same residual stream:
1. Difference-in-means: `wDiffMean = mean(H+) - mean(H-)`, normalized; detection via dot product, steering via `h + α · w`.
2. Linear probe: BCE on `Sigmoid(h · w)`.
3. Prompting (where applicable): a strong instruction-following prompt that targets the same concept.

If the baselines match within 5pp on the relevant utility metric, the SAE buys interpretability only. Useful for audit; not a deployment-grade alternative to the learned classifier or to prompting.

### Gate 2 — Utility-aware feature selection (from Wang 2026)

For any SAE feature used in a downstream intervention (steering, classifier rule, SASFT loss, SAE-DAPO):
1. Compute Delta Token Confidence for each candidate feature: amplify by α=10 on a neutral prefix and measure log-probability change on top-1 next token.
2. Select features in the top decile of DTC magnitude rather than top-K of contrastive activation-difference.
3. If the chosen features\' DTC ranks are not in the top decile, the intervention is selecting interpretable-but-not-useful features. Either re-select or re-justify.

This adds modest compute to the SAE-application pipeline — one extra forward pass per candidate feature per layer — but is cheap relative to the full inference workload.

## Why AxBench was not in the original intake-521 contradicting evidence

First-pass intake searched WebSearch for `"sparse autoencoder" feature steering LLM limitations criticism failure 2025 2026` and the AxBench paper was returned as a hit. The deep-dive of intake-521 then engaged with AxBench more substantively. The original intake captured the headline finding accurately ("On Gemma-2, prompting and finetuning OUTPERFORM SAE steering") but did not flag it as an EPYC-actionable methodological gate. The deep-dive elevated AxBench to the priority-1 baseline-ablation requirement, and this standalone intake completes the formalization.

## Why Wang 2026 was already cited but is now upgraded

Wang 2026 was cited in intake-521\'s deep-dive contradicting evidence with the OpenReview ID and headline tau ~0.298, but as a passing reference rather than a separate intake entry. Upgrading to intake-523 because:
1. The per-model Psi_C values are useful — Qwen-2.5-3B specifically scores 0.4575 (highest of three). This nuances the EPYC story: the interpretability-utility correlation on Qwen-family SAEs is not as weak as the Gemma-2 numbers suggest, but still well below 1.0.
2. The Delta Token Confidence selector is a concrete, adoptable artifact — Gate 2 above. This deserves its own intake-entry traceability rather than being buried in 521\'s contradicting evidence.
3. The "fundamentally new utility-oriented SAE training paradigms" call-to-action is a watch signal we should track separately — when somebody publishes such an SAE on Qwen, we want to find it.

## Watch signals

- **AxBench / SAEBench / Wang-2026-style evaluation run on Qwen-Scope SAEs specifically** — this is the most decisive single experiment to clarify how strongly Wang 2026 binds Qwen-Scope adoption. Likely candidates to do this run: anyone in the Stanford NLP / GemmaScope / SAEBench community responding to Qwen-Scope.
- **Utility-aware SAE training** — Wang 2026 calls for "fundamentally new, utility-oriented SAE training paradigms." If such an SAE for Qwen3 / Qwen3.5 emerges, it would supplant Qwen-Scope artifacts.
- **ReFT-r1 dictionaries for Qwen3** — `huggingface.co/pyvene` currently hosts Gemma-2 dictionaries. If Qwen3 dictionaries appear, the comparison shape becomes ReFT-r1 (Qwen3) vs Qwen-Scope (Qwen3) at matched scale.
- **Anything from Anthropic or DeepMind publicly pushing back on the AxBench finding** — an authoritative SAE-favorable counter-result would re-open the question.

## Files updated as a result of this deep dive

- `research/intake_index.yaml` — appended intake-522 (AxBench) and intake-523 (Wang 2026); both `adopt_patterns` with `expanded_from: intake-521` and `discovered_via: expansion`.
- This deep-dive document.
- (Not modified) — `qwen-scope-sae-toolkit.md` and `routing-intelligence.md` already encode the deep-dive-revised priority order from intake-521\'s deep-dive; the intake-522 / intake-523 IDs strengthen the citation but don\'t change the actionables.
