# Qwen-Scope SAE Toolkit — Production-Stack Interpretability

**Status**: stub (deep-dive complete 2026-05-04)
**Created**: 2026-05-04 (via research intake)
**Updated**: 2026-05-04 (post deep-dive — application priority order revised)
**Categories**: training_distillation, benchmark_methodology, routing_intelligence, agent_architecture
**Priority**: MEDIUM — diagnostic / exploratory; not on the inference critical path
**Deep dive**: `research/deep-dives/qwen-scope-sae-suite.md`
**Parent index**: none yet (would slot under a future `interpretability-index.md`)
**Related**:
- [`routing-intelligence.md`](routing-intelligence.md) — SAE-feature classifier as transparency primitive
- [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md) — repetition-feature pre-activation as stuck-state precursor
- [`reasoning-compression.md`](reasoning-compression.md) — same family of stuck/repeat failure modes
- [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md) — Qwen3.5-35B-A3B SAE coverage; Qwen3.6 not yet covered
- [`learned-routing-controller.md`](learned-routing-controller.md) — SAE feature footprints as auxiliary classifier inputs
- [`eval-tower-verification.md`](eval-tower-verification.md) — feature-coverage redundancy for benchmark suite pruning
- [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) — same eval-suite pruning angle

## Objective

Stand up a local capability for downloading, running, and querying the Qwen-Scope SAE suite (intake-521) on the production-stack Qwen3 / Qwen3.5 backbones, then surface SAE feature activations as a reusable representation-level signal for routing classifiers, benchmark suite pruning, and stuck-state diagnostics. Not a replacement for any current inference path — a diagnostic and post-training tool layered on top of unchanged production decode.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-521 | Qwen-Scope: Turning Sparse Features into Development Tools for LLMs | high | new_opportunity |

## SAE Suite Coverage vs EPYC Stack

| Backbone | EPYC role | Qwen-Scope SAE | Notes |
|----------|-----------|----------------|-------|
| Qwen3-1.7B base | drafter candidate | W32K, L0_{50,100}, all 28 layers | Direct overlap |
| Qwen3-8B base | n/a (not in stack) | W64K, L0_{50,100}, all 36 layers | Useful as Section 5 / Section 8 baseline (paper experiments mostly on Qwen3-8B) |
| Qwen3.5-2B base | n/a | W32K, all 24 layers | — |
| Qwen3.5-9B base | n/a | W64K, all 32 layers | — |
| Qwen3.5-27B Instruct | frontdoor candidate | W80K, L0_{50,100}, all 64 layers (only **instruct** backbone in the release) | Direct overlap |
| Qwen3-30B-A3B base | production worker | W32K (L0_50) + W128K (L0_100), all 48 layers | Direct overlap |
| Qwen3.5-35B-A3B base | predecessor of Qwen3.6-35B-A3B upgrade target | W32K (L0_50) + W128K (L0_100), all 40 layers | Predecessor-only — Qwen3.6 NOT covered |
| Qwen3.6 family | active upgrade target | NOT released | Architecture-family-close to Qwen3.5; transferability uncharacterized |

## Application Pathways — Deep-Dive-Revised Priority Order

**Post deep-dive (2026-05-04, see `research/deep-dives/qwen-scope-sae-suite.md`)** the priority order is materially narrower than the first-pass intake suggested. AxBench (Wu et al. ICML 2025, OpenReview K2CckZjNy0) shows prompting + finetuning beat SAE steering on Gemma-2 and difference-in-means dominates SAEs at concept detection; Wang et al. 2026 (ICLR 2026, OpenReview Q4ooLNOFeR — cited BY Qwen-Scope but not benchmarked against) shows on Qwen-2.5-3B + Gemma-2 that SAE interpretability and steering utility correlate at Kendall ~0.298 (negative under common feature selection). Combined with the Section 7/8 regressions visible in Qwen-Scope's own tables, the application matrix collapses to:

1. **Section 4 evaluation analysis — STRONGEST APPLICATION.** Feature-coverage AUC + asymmetric / min-normalized inter-benchmark overlap as evaluation-free redundancy / similarity proxies. Spearman 0.85 vs performance redundancy across 17 benchmarks; partial Pearson 75.5% after partialling MMLU. **Direct candidate for `eval-tower-verification.md` and `mathsmith-hc-formalizer-eval.md`** — prune the in-house eval suite without running additional model sweeps. **Caveat (deep dive)**: in-distribution to Qwen pretraining; cross-validate redundancy ranking against actual model-ranking-preservation on a held-out 5-checkpoint panel before committing to suite changes.
2. **Section 5 classifier as AUDIT primitive — pilot only with baselines.** Rule-based OR-classifier over class-biased SAE features. F1 > 0.90 on English toxicity. **Deep-dive caveat**: AxBench reports difference-in-means is the dominant baseline for concept detection; Qwen-Scope does not run this comparison. Do NOT deploy as primary classifier without head-to-head against (a) difference-in-means on the same residual stream, (b) linear probe, (c) trained classification head. Frame as **transparency / audit primitive** for routing-intelligence factual-risk decisions, not as a learned-classifier replacement.
3. **Section 8 SAE-DAPO rare-negative augmentation — INFRA-BLOCKED.** One SAE-steered repetitive rollout per group of G in DAPO. Drops repeat ratio sharply across Qwen3-1.7B / Qwen3-8B / Qwen3-30B-A3B; Qwen3-30B-A3B also gets +5.84pp MGSM. Sidesteps the steering-degradation issue (model learns to avoid steered outputs, not imitate them). **Triple-blocked**: (a) RL training infra (DGX Spark not yet acquired, `project_dgx_spark_target`), (b) need a documented Qwen-family stuck-in-think failure mode in EPYC's own logs, (c) ablation distinguishing feature-targeted from generic-OOD rare-negative rollouts is mandatory before crediting +5.84pp MGSM to the targeted intervention.
4. **Section 7 SASFT — DEFER FURTHER.** Auxiliary `ReLU(f_s(x) - alpha_j)` suppression loss on language-specific SAE features added to cross-entropy. Documented 50-100% code-switching reduction across Qwen3-1.7B / Qwen3-8B for zh / ru / ko. **Deep-dive caveats stack**: Section 7 Table 5 itself shows Qwen3-8B HellaSwag -2.88 / MMLU -2.06 regressions; Wang et al. 2026 reports negative interpretability-utility correlation under common feature selection on Qwen-2.5-3B; SASFT auxiliary loss is exactly the regime under which Wang et al.'s critique applies. EPYC has no documented code-switching production failure to motivate the work. Monitor SASFT ICLR 2026 paper reception (Deng et al., OpenReview BQOFU9qO5j) and any independent re-implementations; do not invest until either a production failure appears or training infra is online.
5. **Section 3 inference-time steering — DO NOT ADOPT.** Stacked evidence against: AxBench (prompting + finetuning beat SAEs on Gemma-2), ICML 2025 SAE-refusal-steering broad-task degradation paper (arxiv:2411.11296), Wang et al. 2026 utility-falsification on Qwen-2.5-3B, and Qwen-Scope's own Section 3 evidence is two anecdotal Qwen3 case studies with no broad-benchmark validation. Steering remains an analysis tool only.

## Storage Cost Map (FP32, deep-dive-confirmed)

| Backbone | SAE width | Layers | Per-variant | Both L0 |
|----------|-----------|--------|-------------|---------|
| Qwen3-1.7B | 32K | 28 | ~15 GB | ~30 GB |
| Qwen3.5-27B | 80K | 64 | ~213 GB | ~426 GB |
| Qwen3-30B-A3B | 32K + 128K | 48 | ~25 / ~101 GB | ~126 GB |
| Qwen3.5-35B-A3B | 32K + 128K | 40 | ~21 / ~84 GB | ~105 GB |
| Production-stack subset total | | | | **~687 GB FP32 / ~344 GB FP16** |

**Practical guidance**: pull per-application, not en bloc. Section 4 redundancy on a single middle-band layer of Qwen3.5-27B-W80K-L0_50 is ~3.34 GB; that's the recommended starting point. Do NOT mirror full suite on the 120 GB root SSD (`feedback_no_core_dumps`-adjacent — root SSD is the wrong target). Use `/mnt/raid0/llm/...`.

## License Map

License tag on HF: `qwen` (custom). NOT Apache 2.0. Section 9.3 of the paper prohibits using SAEs to "interfere with model capabilities" with author-reserved final interpretation; per the paper's own framing every Section 3/7/8 application qualifies as "interfere with model capabilities." `feedback_license_not_a_blocker` applies to commercial use; the operational ambiguity here is around behavior-modification *authorization* even for non-commercial research.

| Application | License posture |
|-------------|-----------------|
| Section 4 redundancy analysis | unambiguously permitted (post-hoc analysis only) |
| Section 5 classifier as audit primitive | unambiguously permitted (read-only) |
| Section 7 SASFT (training-time feature suppression) | requires license-clause review before adoption |
| Section 8 SAE-DAPO (rare-negative augmentation) | requires license-clause review before adoption |
| Section 3 inference-time steering | irrelevant (do not adopt anyway) |

## Open Questions

- Are the Qwen3.5-35B-A3B SAEs portable to Qwen3.6-35B-A3B post-training? Paper does not characterize predecessor→successor SAE transfer for MoE+hybrid-SSM architectures; only Qwen3 vs Qwen3.5 longitudinal comparisons exist. Cited follow-up direction: Minder et al. 2026 "Narrow finetuning leaves clearly readable traces in activation differences" (ICLR 2026, OpenReview qyVzZsrsnS) is the methodological analogue.
- What is the actual EPYC CPU cost of running an SAE pass on the residual stream at one chosen layer per token? TopK over a 32K-128K dictionary is small relative to the 30B-A3B forward pass, but BW-bound reality on EPYC 9655 needs measurement before any classifier or eval-time use becomes routine. Per the deep dive, loading is custom PyTorch (no transformers / sae_lens integration); residual-stream extraction in llama.cpp is not exposed as an API and would need custom integration.
- **(Deep dive 2026-05-04)** Does the Section 5 SAE classifier beat difference-in-means on the same residual stream? AxBench (Wu et al. ICML 2025) reports difference-in-means dominates SAEs at concept detection on Gemma-2. Mandatory ablation before committing to the SAE classifier path. Same applies to linear probe baselines.
- **(Deep dive 2026-05-04)** Does the Wang et al. 2026 utility-falsification finding (Kendall ~0.298 SAE-interp-vs-utility on Qwen-2.5-3B + Gemma-2, negative under common feature selection) hold on Qwen-Scope's specific Qwen3 / Qwen3.5 SAEs? The paper cites Wang et al. but does not benchmark against their Delta Token Confidence selector. Direct re-run on Qwen-Scope checkpoints would be the most decisive validation.
- **(Deep dive 2026-05-04)** Does the Section 8 +5.84pp MGSM gain on Qwen3-30B-A3B survive an ablation that injects generic OOD rollouts (not feature-targeted)? Without that control, the gain is not cleanly attributable to "stop endless repetition"; it could be a generic regularization effect of OOD rollout injection.
- How sensitive is the Section 5 toxicity-classifier methodology to **frequency-bias** in feature interpretation (OpenReview tbiCWZgGD3, vc1i3a4O99)? The paper's `top1-diff` proxy is purely activation-frequency-difference based — exactly the regime that frequency-bias critiques target. Validation pass needed before relying on selected features as semantic detectors.
- Does Qwen-Scope's Qwen3-30B-A3B repetition feature transfer to non-Qwen hybrid models like Ring-mini-linear-2.0? Probably not directly (different tokenizer, different layer geometry), but the *methodology* (contrastive identification of stuck-state features → causal validation via bidirectional steering → rare-negative-rollout RL) is the closest published analogue to the Ring-mini stuck-in-think failure mode (`research/deep-dives/ring-mini-stuck-in-think-failure-mode.md`, 2026-05-04). Worth attempting on a Qwen-family stuck-in-think workload once the SAE infra exists.
- **(Deep dive 2026-05-04)** Does the Falsifying-SAE-Reasoning-Features paper (Ma et al. 2026, arxiv:2601.05679, cited in Qwen-Scope's own references but not engaged in Section 9.2) implicate Section 8's repetition features specifically? Section 9.2 passes over this without comment. Worth reading Ma et al. for whether repetition-class features survive their falsification framework.

## Notes

Released 2026-04-30 by the Qwen Team. Hosted on Hugging Face Collections, ModelScope, and Alibaba OSS (PDF: `https://qianwen-res.oss-accelerate.aliyuncs.com/qwen-scope/Qwen_Scope.pdf`). Interactive QwenScope HF Space exists but is in "Paused" state at intake date. No first-party github repo from QwenLM org for Qwen-Scope inference; only third-party `embeddr-net/ComfyUI-QwenScope` (image-generation-focused, not directly applicable).

Section 7 (SASFT) is a separately-published ICLR 2026 paper (Deng et al., OpenReview BQOFU9qO5j) — peer-reviewed status higher than the rest of the technical report. Sections 3, 4, 5, 6, 8 are technical-report-only at deep-dive date.

Tier 2b contradicting evidence (recorded under intake-521):
- ICML 2025 "Steering Language Model Refusal with Sparse Autoencoders" — broad-task degradation under steering even on safe inputs; relevant if Section 3 steering is adopted, NOT relevant for Section 5 classifier mode or Section 8 rare-negative-rollout mode.
- Frequency bias in feature interpretation (multiple 2025 OpenReview papers) — applies to Section 5 selection criterion.
- SAE-RSV (arxiv:2509.23799) and CorrSteer (arxiv:2508.12535) — explicit fixes to noisy-steering-vector limitations the paper does not adopt.
- Section 7 / Section 8 paper tables themselves document task-dependent regressions; "preserves general utility" claim is directional, not categorical.
