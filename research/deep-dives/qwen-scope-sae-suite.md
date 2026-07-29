# Qwen-Scope SAE Suite — Deep Dive

**Date**: 2026-05-04
**Source**: intake-521 (`research/intake_index.yaml`); paper `Qwen_Scope.pdf` (35pp); HF collection `Qwen/qwen-scope`; HF Space `Qwen/QwenScope` (paused); HF model card spot-checks (`SAE-Res-Qwen3-1.7B-Base-W32K-L0_50`, `SAE-Res-Qwen3.5-27B-W80K-L0_50`)
**Status**: Deep-dive complete. Original intake-521 stands as `new_opportunity` but with materially narrower practical pathways than the first-pass verdict suggested.

## TL;DR

The first-pass intake correctly identified that Qwen-Scope releases SAEs for the EPYC production stack (Qwen3-1.7B drafter, Qwen3.5-27B frontdoor candidate, Qwen3-30B-A3B production worker, Qwen3.5-35B-A3B predecessor). Six material corrections surfaced on second read:

1. **License is NOT Apache 2.0.** Per HF model card metadata, the SAE checkpoints carry the custom `qwen` license. Section 9.3 of the paper adds an explicit prohibition on using SAEs to "interfere with model capabilities" or for content "violating socialist core values" with author-reserved final interpretation. Steering / SASFT / SAE-DAPO are exactly "interfere with model capabilities" — there is operational legal ambiguity around the very applications the paper itself demonstrates.
2. **Storage cost is enormous.** SAE-Res-Qwen3.5-27B-W80K-L0_50 alone is ~213 GB FP32 across all 64 layers; the L0_100 sibling adds another ~213 GB. SAE-Res-Qwen3-30B-A3B carries both W32K (~30 GB) and W128K (~96 GB) variants, ~126 GB total per L0 setting. Full production-stack SAE inventory (Qwen3-1.7B + Qwen3.5-27B + Qwen3-30B-A3B + Qwen3.5-35B-A3B, both L0 settings) is in the order of **~900 GB FP32**, ~450 GB FP16. Not free, fits, but not casual.
3. **Independent SAE-utility falsification literature is cited *by* the Qwen-Scope paper but not benchmarked against.** Wang et al. 2026 (`Q4ooLNOFeR`, ICLR 2026) — same authors' own reference list — show on Qwen-2.5-3B + Gemma-2 that interpretability and steering utility have only Kendall ~0.298 correlation, can become **negative** under common feature selection. AxBench (Wu et al. ICML 2025) — not cited — shows on Gemma-2 that *prompting* and *finetuning* outperform SAE steering, and that *difference-in-means* dominates SAEs at concept detection (the exact regime of Section 5's toxicity classifier).
4. **Section 5 toxicity-classifier baselines are missing.** F1 0.92 / 0.96 are reported with no comparison against (a) linear probe on the same residual stream, (b) difference-in-means (the AxBench-recommended baseline), (c) a trained classification head, or (d) BERT/RoBERTa-class toxicity models. The "interpretability + sparsity + no extra trained head" framing is structural, but the *performance* claim is uncontextualized.
5. **Section 8 repetition-feature methodology has a structural confound.** Features are identified by comparing first-vs-last occurrence of the *same token* within an already-repetitive sample, which mechanically selects for "fires more later in repetitive contexts" features. The paper notes — and confirms via Figure 21 — that the same features fire on benign repetition (instruction-echo, multiple-choice answer-choice repetition). Bidirectional steering provides causal validation, but the rare-negative-augmentation result on Qwen3-30B-A3B (+5.84pp MGSM) cannot be cleanly attributed to "repetition suppression learning" because the training also injects out-of-distribution token sequences that may have other regularizing effects.
6. **SAE training data is undisclosed** ("in-house pretraining data"). Reproducing on Qwen3.6 is not possible from the paper alone. Section 4's "evaluation-free benchmark redundancy" claim is in-distribution (26 in-house Qwen pre-training checkpoints, all from the same data regime as the SAE training data); cross-family or strong-OOD validation is absent.

Verdict revision: keep at `new_opportunity`. Practical adoption pathway is narrower than the first-pass verdict. The strongest single application for EPYC remains **Section 4 benchmark-redundancy analysis on the in-house eval suite using the Qwen3.5-27B SAE**; everything else needs head-to-head ablation against simple baselines (linear probe, difference-in-means, prompting) before commitment.

## What the original intake got right

- SAE coverage of production stack is real and accurate (Qwen3-1.7B / Qwen3.5-27B / Qwen3-30B-A3B / Qwen3.5-35B-A3B all directly covered; Qwen3.6 family NOT covered).
- The four-application taxonomy (steering / eval / classification / post-training) reflects the paper's actual structure.
- Section 7 SASFT is a separately-published ICLR 2026 paper (Deng et al. 2026, OpenReview `BQOFU9qO5j`) — this elevates Section 7 credibility above the rest of the technical-report. The first-pass entry did not surface this distinction.
- The repetition-feature mechanism in Section 8 is the closest published analogue to the Ring-mini stuck-in-think methodology — that mapping survives the deep dive.
- Tier 2b contradicting evidence pointers (ICML 2025 SAE refusal paper, frequency-bias work, CorrSteer / SAE-RSV) hold up against verification: arxiv:2411.11296 confirmed, broad-task degradation finding confirmed.

## Six corrections / additions

### 1. License: `qwen` custom, not Apache

HF model cards for both `SAE-Res-Qwen3-1.7B-Base-W32K-L0_50` and `SAE-Res-Qwen3.5-27B-W80K-L0_50` list `license: qwen`. This is the same custom license used for Qwen3 model weights, with two operational concerns specific to this SAE release:

- Section 9.3 of the paper: *"It is strictly prohibited to use interpretability tools for non-scientific research purposes to interfere with model capabilities"* — every Section 3 / 7 / 8 application is precisely "interfere with model capabilities" via the authors' own framing.
- *"Right of final interpretation of this statement belongs to the project owner"* — author-reserved interpretation creates ambiguity for any production deployment.

Per memory `feedback_license_not_a_blocker` we don't worry about commercial licensing as a category. But this is a different concern: it's an **operational ambiguity** about whether the demonstrated applications are licensed even for non-commercial research use. For pure post-hoc analysis (Section 4 benchmark redundancy, Section 5 classifier without behavior modification) this is unambiguously fine. For SASFT and SAE-DAPO that train against the SAE-derived signal, the "interfere with model capabilities" prohibition is at least debatable.

Action: route any Section 7 / 8 adoption through a review of the qwen license clauses. Section 4 / 5 use is unaffected.

### 2. Storage cost ≈ 1 TB FP32 for the full production-stack SAE inventory

| Backbone | SAE width | Layers | Per-layer FP32 | Per-variant total | Both L0 settings |
|----------|-----------|--------|----------------|-------------------|------------------|
| Qwen3-1.7B | 32K (16x) | 28 | ~536 MB | ~15 GB | ~30 GB |
| Qwen3-8B | 64K (16x) | 36 | ~2.0 GB | ~73 GB | ~146 GB |
| Qwen3.5-2B | 32K (16x) | 24 | ~536 MB | ~13 GB | ~26 GB |
| Qwen3.5-9B | 64K (16x) | 32 | ~2.0 GB | ~65 GB | ~130 GB |
| Qwen3.5-27B | 80K (16x) | 64 | ~3.34 GB | ~213 GB | ~426 GB |
| Qwen3-30B-A3B | 32K + 128K | 48 | ~530 MB / ~2.1 GB | ~25 / ~101 GB | ~126 GB |
| Qwen3.5-35B-A3B | 32K + 128K | 40 | ~530 MB / ~2.1 GB | ~21 / ~84 GB | ~105 GB |

Production-stack-only inventory (Qwen3-1.7B + Qwen3.5-27B + Qwen3-30B-A3B + Qwen3.5-35B-A3B, both L0 settings each): **~687 GB FP32** / ~344 GB FP16. The /mnt/raid0 3.7 TB array has room, but this is not a casual download and shouldn't go on the 120 GB root SSD per memory `user_hardware`.

Practical implication: don't pull the whole suite. Per-application pulls suffice:
- Section 4 redundancy on eval suite: one model's L0_50, one or two layers in the middle band → ~10 GB
- Section 5 toxicity classifier: similar — middle-layer slice of one model
- Section 7 / 8 post-training: full coverage of the target backbone needed

### 3. Independent falsification literature — including the paper's own self-citation

**Wang et al. 2026** (`Does Higher Interpretability Imply Better Utility? A Pairwise Analysis on Sparse Autoencoders`, ICLR 2026, OpenReview `Q4ooLNOFeR`, **cited in Qwen-Scope's own reference list as Wang et al. 2026**):
- Trained 90 SAEs across Gemma-2-2B, **Qwen-2.5-3B**, and Gemma-2-9B at six sparsity levels.
- Used SAEBench for interpretability and AxBench for steering utility.
- Result: Kendall's tau correlation between interpretability and steering utility is ~0.298 ("only a relatively weak positive association"). After their proposed Delta Token Confidence feature filter, "the correlation between interpretability and utility vanishes and can even become negative."
- They report a 52.52% steering improvement using Delta Token Confidence over standard feature-selection methods.

This is a critical finding. Qwen-Scope cites this paper but does not run any of its applications against the Wang et al. baseline or the Delta Token Confidence selector. Qwen-Scope's Section 3 / 7 use *contrastive feature identification* (basically activation difference between positive and negative sets) — exactly the regime Wang et al. show has weak interpretability-utility correlation.

**Wu et al. 2025 — AxBench** (`Steering LLMs? Even Simple Baselines Outperform Sparse Autoencoders`, ICML 2025 poster, OpenReview `K2CckZjNy0`, NOT cited by Qwen-Scope):
- Authors: Wu, Arora, Geiger, Wang, Huang, Jurafsky, Manning, Potts (Stanford).
- Tested on Gemma-2-2B and Gemma-2-9B (NOT Qwen, but methodologically equivalent SAEs).
- Results: "Prompting outperforms all existing methods, followed by finetuning. SAEs are not competitive." For concept detection, "representation-based methods such as difference-in-means perform the best."
- They propose ReFT-r1 (rank-1 representation finetuning) as a competitive interpretable alternative.

Direct implication for Qwen-Scope's Section 5 (toxicity classifier): the paper's rule-based OR-classifier over class-biased SAE features is competing in the AxBench "concept detection" regime where difference-in-means (no SAE) is reported as the strongest method. Qwen-Scope does not run this comparison.

**Ma et al. 2026** (`Falsifying sparse autoencoder reasoning features in language models`, arxiv:2601.05679, **cited in Qwen-Scope's own reference list**) — directly tackles whether SAE-discovered "reasoning features" hold up under causal interventions. Not pulled in detail here, but its presence in Qwen-Scope's own references — without Section-9.2 acknowledgement of how Section 8's repetition features sit relative to Ma's falsification framework — is a notable omission.

### 4. Section 5 baseline gap

The paper reports F1 0.92 (Qwen3-1.7B) / 0.96 (Qwen3-8B) for English toxicity classification using a rule-based OR over top-K class-biased SAE features. It does NOT compare against:

- Linear probe on the same residual stream (cheap baseline; would isolate the SAE's value-add)
- Difference-in-means (AxBench-recommended baseline; per Wu et al. 2025 dominates SAEs at concept detection)
- Trained classification head (standard supervised baseline)
- BERT/RoBERTa-class toxicity models (production-grade external comparator)

The structural value of the SAE classifier is clear (sparse, interpretable per-prediction, no extra trained head, 10% data-efficient). The *performance* claim — that this matches what a learned head would do — is not established by the paper alone. Plausible interpretations:
- (a) The SAE features genuinely concentrate the toxicity signal into a few interpretable directions, and a linear probe on raw activations would also score 0.90+. In that case the SAE is buying interpretability and sparsity at no performance cost.
- (b) The SAE features are not actually better than raw-activation difference-in-means, and the F1 numbers are headline-favorable because the residual stream itself is doing the work. In that case the value-add is interpretability only.

Either way, the EPYC adoption story for Section 5 is "audit primitive on top of a learned classifier" rather than "primary classifier." The first-pass intake already gestured at this; the deep dive sharpens it: do not invest in the SAE classifier path unless the parallel difference-in-means baseline is also evaluated and reports comparable F1, in which case the SAE features remain attractive for *transparency* but do not justify storage / compute by themselves.

### 5. Section 8 methodological tightening

The repetition-feature identification procedure (Section 8.1):
1. Collect samples where the model spontaneously enters endless repetition.
2. Within each sample, for each repeated token, compute the SAE-feature activation difference between the *first* occurrence of that token and the *last* repeated occurrence in the same context.
3. Rank features by activation increase.

This identifies features whose activation rises monotonically across token positions in a repetitive context — by construction, "monotone-rising under repetition" is the selection criterion. It does not establish that these features *cause* repetition rather than simply *track* it. The paper provides bidirectional steering (Figure 20) as causal validation: amplifying the feature on non-repetitive samples induces repetition; suppressing on repetition-prone samples reduces repetition. This addresses the causal direction adequately, but the steering coefficients used in those experiments are not surfaced in the extracted text and the figures are layer-aggregated.

Section 8.1 also surfaces a more important caveat: the same features fire on benign repetition (Figure 21: instruction-echo, multiple-choice answer-choice). The paper uses this as the *justification* for choosing rare-negative-rollout augmentation over SASFT-style suppression — which is correct — but it also implies that the features are **not specific to pathological repetition**. The +5.84pp MGSM gain on Qwen3-30B-A3B (RL+SAE vs Before-RL) is therefore *not necessarily* a clean "stop endless repetition" effect; it could include collateral effects from injecting OOD steered samples into the rollout distribution. The vanilla-RL +1.08pp baseline does control for "is RL helping at all" but not for "is the gain specifically from repetition suppression."

For EPYC purposes this means: the rare-negative-augmentation idea is genuinely interesting and is the most defensible Section 7/8 application against the steering-degradation literature, **but** any port to Qwen-family stuck-in-think failures must include an ablation distinguishing "repetition-feature-targeted" from "any-feature-amplification-induced-OOD" rollouts.

### 6. SAE training data undisclosed

Section 2.2 says only "in-house pretraining data." This has three concrete consequences:

- Cannot retrain SAEs ourselves on Qwen3.6 from scratch — the recipe, hyperparameters, token budget, and training distribution are not surfaced. A community / lab-internal re-implementation would have to reconstruct the recipe from Gao et al. 2024 + the auxiliary-loss weight `1/32` mentioned in Section 2.2 + the L2-norm outlier filter — but the data side remains opaque.
- Section 4 "evaluation-free" benchmark redundancy validity: the SAEs were trained on Qwen pretraining data. The 17 evaluated benchmarks (MMLU, GSM8K, MATH, etc.) are likely well-represented in that pretraining distribution, which means the feature-coverage curve is computed using SAEs that have effectively *seen* the benchmarks during training. The Spearman 0.85 correlation with performance redundancy is therefore in-distribution. Cross-family validity (e.g., would a Llama-trained SAE see the same redundancy ranking?) is not tested.
- Reproducibility / falsifiability: the entire empirical claim chain depends on the SAE quality. A Qwen-3.6 SAE trained on different data could produce different feature footprints and thus different redundancy / similarity numbers. Without the recipe this is hard to investigate.

For EPYC: Section 4 adoption should be framed as "uses Qwen-Scope's released Qwen-3.5-27B SAE to estimate redundancy on our specific eval suite, with the explicit caveat that the proxy is in-distribution to Qwen pretraining." That's still operationally useful — we use Qwen models, our eval prompts likely overlap Qwen pretraining anyway — but the "evaluation-free" framing must not be over-extended.

## Implications by application pathway

### Section 3 — inference-time steering — DEPRIORITIZE

- AxBench: prompting and finetuning beat SAE steering on Gemma-2.
- ICML 2025 SAE refusal paper: broad-task degradation even on safe inputs.
- Wang et al. 2026 (Qwen-Scope's own citation): interpretability-utility correlation ~0.298 on Qwen-2.5-3B + Gemma-2.
- Qwen-Scope Section 3 evidence: two anecdotal Qwen3 case studies, no broad-benchmark validation.

Verdict: not on EPYC's path. Use prompting where possible; if behavioral modification is needed, use SFT / RL via the rare-negative-augmentation pathway or external alignment work. Steering-as-deployed-mechanism is not warranted by current evidence.

### Section 4 — benchmark-redundancy / inter-benchmark similarity — STRONGEST APPLICATION

- Genuinely evaluation-free given the in-distribution caveat.
- Spearman 0.85 with performance redundancy is the most reliable empirical claim in the report (largest evaluator panel, multiple benchmarks).
- 4-step adoption: (a) pull SAE-Res-Qwen3.5-27B-W80K-L0_50 for one or two middle-band layers (~3-7 GB), (b) compute feature footprints on the EPYC eval suite (`mathsmith-hc-formalizer-eval.md`, `eval-tower-verification.md`, internal benchmark JSONLs), (c) compute feature-redundancy R-hat per benchmark and asymmetric overlap matrix between benchmarks, (d) propose a smaller eval suite for iterative-development use without losing model-ranking power.
- Cost: bounded by the storage hit and a few hours of inference compute on the eval prompts.
- Risk: the in-distribution caveat. Mitigation: cross-validate the redundancy ranking against actual model-ranking-preservation on a held-out 5-checkpoint panel (cheap, since EPYC has many Qwen quants on disk).

This is the single recommended Section-by-Section action.

### Section 5 — rule-based feature classifier — EXPLORATORY ONLY

- Cannot be adopted as a primary classifier without head-to-head against difference-in-means (the AxBench-recommended baseline). If difference-in-means matches or beats the SAE rule-classifier, the SAE buys only interpretability — value still exists but the storage / inference cost / integration effort is harder to justify.
- The transparency value (per-prediction trace to feature ID + layer + token position) is real and complements the routing-intelligence factual-risk classifier work, but should be framed as an *audit primitive* not a *classifier*.
- Action: when investing time, run difference-in-means and a linear probe on the same residual stream as concurrent baselines. Do not deploy without that comparison.

### Section 7 — SASFT — DEFER

- Section 7 has higher credibility than the rest of the technical report (separately published ICLR 2026 paper by Deng et al., OpenReview `BQOFU9qO5j`).
- But Table 5 itself shows non-trivial regressions (Qwen3-8B HellaSwag -2.88, MMLU -2.06; Qwen3-1.7B MGSM -2.06).
- Wang et al. 2026 (Qwen-Scope's own citation) on Qwen-2.5-3B suggests SASFT-style supervision via SAE features may not generalize — interpretability-utility correlation on the same family is weak.
- EPYC has no immediate code-switching pain in production (per memory `project_orchestrator_stack_freeze.md` the stack is frozen at v5; per memory the production worker is Qwen3 30B-A3B; no documented English-output→non-English-token leakage at the autopilot or routing layer).
- Adoption blocked on (a) DGX Spark not yet acquired (memory `project_dgx_spark_target`), (b) intake-441 diversity-collapse evaluation hooks (eval-tower EV-8) — Wang et al. 2026's negative correlation finding plausibly downstream of the same diversity-collapse mechanism.

Action: monitor the SASFT ICLR 2026 paper's reception and any independent re-implementations; do not invest until either a code-switching production failure mode appears or training infra is online.

### Section 8 — SAE-DAPO rare-negative augmentation — STRONG-MODEL CANDIDATE, INFRA-BLOCKED

- Most defensible against the steering-degradation literature: the model learns to *avoid* SAE-steered outputs rather than imitate them.
- +5.84pp MGSM on Qwen3-30B-A3B is the single most quantitatively interesting result in the paper, but per Section 5 of this deep dive it is not cleanly attributable to repetition suppression.
- Identical infra blocker as Section 7: no on-prem RL training capability.
- Cross-link to per-request-reasoning-budget.md: if/when budget enforcement lands and we observe Qwen-family stuck-in-think failures during real EPYC workloads, the methodology (contrastive identification of stuck-state features → rare-negative-rollout augmentation in DAPO) is portable. Ring-mini is non-Qwen and out-of-scope for direct SAE transfer.

Action: keep on watch list. Re-evaluate when (a) RL training infra is online, (b) at least one Qwen-family stuck-in-think failure mode is documented in our own benchmark logs, (c) the Falsifying-SAE-Reasoning-Features result (Ma et al. 2026, arxiv:2601.05679) has been reviewed for whether it implicates Section 8's repetition features specifically.

## Cross-references — implied additions to the EPYC research backlog

The paper's Section 9.2 "Exploring Directions" cites several follow-up papers worth tracking, **none of which were captured in intake-521 cross_references**. Adding them as flagged items rather than full intake entries (per `feedback_audit_parallel_agent_first.md` and the 10-entry expansion cap respected during the original intake):

- **Macar et al. 2026 — Thought Branches** (arxiv:2510.27484): "Interpreting LLM reasoning requires resampling." Directly relevant to per-request-reasoning-budget.md and reasoning-compression.md. Argues that single-forward-pass interpretability is insufficient for chain-of-thought models — multi-sample branch analysis is needed. Worth a separate intake entry on next pass.
- **Bogdan et al. 2025 — Thought Anchors** (arxiv:2506.19143): Which LLM reasoning steps matter? Same authorship cluster as Thought Branches; relevant to reasoning-compression.md Action 9 reasoning-length-alarm.
- **Goldowsky-Dill et al. 2025 — Linear deception probes** (arxiv:2502.03407): adjacent to factual-risk-routing in routing-intelligence.md. Linear probes on internal activations as a deception detector.
- **Minder et al. 2026 — Narrow finetuning leaves clearly readable traces in activation differences** (ICLR 2026, OpenReview `qyVzZsrsnS`): post-training analysis via activation diffs. Could feed into the Qwen3.5→Qwen3.6 upgrade evaluation in qwen36-production-upgrade.md.
- **Casademunt et al. 2025 — Concept ablation fine-tuning** (arxiv:2507.16795): generalization-improving ablation during SFT. Adjacent to SASFT.
- **Coalson et al. 2025 — IF-Guide influence-function-guided detoxification** (arxiv:2506.01790): training-data-attribution alternative to feature-driven synthesis (Section 6). Adjacent to the bulk-inference-campaign / training-data work on EPYC if/when training infra lands.
- **Wu et al. 2025 — AxBench** (ICML 2025, OpenReview `K2CckZjNy0`): NOT cited by Qwen-Scope. Should be a standalone intake entry as the canonical methodological skepticism against SAE steering. Strongly relevant to any steering-adjacent decision.
- **Wang et al. 2026 — Higher interpretability ≠ better utility** (ICLR 2026, OpenReview `Q4ooLNOFeR`): cited by Qwen-Scope but not benchmarked against. Should be a standalone intake entry as the direct utility-falsification result on Qwen-2.5-3B + Gemma-2.

Action: queue (Wu 2025 AxBench, Wang 2026 utility analysis) for next research-intake batch. The Macar/Bogdan/Goldowsky-Dill cluster is also worth a single batched intake.

## Revised verdict

`new_opportunity` stands. The application priority order, post-deep-dive:

1. **Section 4 redundancy on EPYC eval suite** (single layer, ~5 GB pull, in-distribution caveat documented). Real value, low cost, no behavior modification.
2. **Section 5 classifier as audit primitive** (NOT primary classifier; head-to-head difference-in-means baseline mandatory).
3. **Section 8 rare-negative-augmentation** — gated on (a) RL infra online, (b) documented Qwen-family stuck-in-think failure, (c) ablation distinguishing feature-targeted from generic-OOD rollouts.
4. **Section 7 SASFT** — defer until diversity-collapse evaluation hooks land and a real code-switching production failure appears.
5. **Section 3 inference-time steering** — do not adopt. AxBench + ICML 2025 refusal-steering + Wang 2026 utility-correlation collectively make the case against. Steering remains an analysis tool only.

Storage: pull on demand per-application; do not mirror the full ~700 GB inventory.

License: post-hoc analysis (Section 4, Section 5 audit) is unambiguously fine; behavior-modification (Section 7, 8) requires a license-clause review before adoption.

## Watch signals

- Independent re-implementation of the SAE training recipe surfaces (would unblock Qwen3.6 SAE training).
- AxBench / Wang 2026-style utility-falsification benchmarks run specifically on Qwen-Scope's released checkpoints (would test whether Qwen-Scope evades or confirms the SAE-utility-gap finding).
- Falsifying-SAE-Reasoning-Features (Ma et al. 2026, arxiv:2601.05679) review pass — does it implicate Section 8's repetition features?
- Hugging Face Space `Qwen/QwenScope` un-paused and exposes interactive feature exploration → much faster iteration on candidate features for routing-intelligence audit.
- Qwen-Scope github repo materializes from QwenLM org with proper inference + training code (currently absent — only third-party ComfyUI integration exists).
- Qwen3.6 SAEs released by anyone (would unblock qwen36-production-upgrade.md interpretability-assisted regression analysis).

## Files revised as a result of this deep dive

- `research/intake_index.yaml` intake-521 `contradicting_evidence` and `verdict_justification` updated to reflect deep-dive findings.
- `handoffs/active/qwen-scope-sae-toolkit.md` Open Questions and Application Pathways revised.
- `handoffs/active/routing-intelligence.md` 2026-05-04 intake update augmented with AxBench / Wang 2026 baseline-gap caveat.

No revisions to per-request-reasoning-budget.md or qwen36-production-upgrade.md updates — they were already appropriately gated in the original intake update.
