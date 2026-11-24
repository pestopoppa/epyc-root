# Dive — noisyrew — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2604.07666v2", retrieved: "2026-11-24", sha256: "d3720b7af1a2"}

Stage 2b wave 1, light dive. Expanded from intake-2877 (loopholes). Question: does it set A1's futility threshold?

## 1. Stage-1 fields
- **Title**: An Imperfect Verifier is Good Enough: Learning with Noisy Rewards.
- **Authors**: NOT-FOUND-IN-SOURCE (author block not in the stripped page text read).
- **Version**: arXiv 2604.07666 v2 (arxiv_meta.json).
- **Categories**: training_distillation, benchmark_methodology.
- **Novelty**: medium. Controlled bit-flip noise on unit-test rewards plus two model-based verifiers.
- **Relevance: low-medium.** It does NOT supply a usable FPR threshold for exploit-prone judges (see claim 1), so it cannot set A1's futility threshold. Useful only as a boundary: random, resampled noise is tolerated; persistent, policy-reachable error is outside what it tests.
- **Credibility: 1/6.** peer-reviewed +0; <=12 months +1; major lab 0; bias 0; independent corroboration 0. Total 1. The v2 abstract is unusually hedged, which raises trust in its narrow claims.
- **Verdict: adopt_patterns** (cite as the random-noise bound and for the "report reward contrasts within a group, not just FPR/FNR" lesson; do not cite as a threshold).

## 2. Key claims
1. **OVERTURNED as a threshold.** The title suggests tolerance; the authors say they do not establish a verifier-accuracy threshold or robustness to persistent biases. Corrected fact: they show only that resampled random noise did not hurt much in their setup. Anchor 0.
2. **CONFIRMED (narrow).** Qwen3 8B on MBPP (3-6 seeds per setting, 4 baseline seeds): mean of evaluation steps 239 and 259 within 1 percentage point of the clean 0.890 baseline at noise 0.05 to 0.20, losses 1.4 points at 0.25 and 2.0 at 0.30; drops substantially at 0.40 and above. Intervals are wider than 1 point (95% for the difference at 0.20: -2.9 to +1.8). Anchors 1, 2.
3. **CONFIRMED (and critical for us).** The noise is bit-flips independent of whether the original is pass or fail, resampled each encounter; FPR and FNR both equal p. The paper says explicitly that its controlled experiments do not model persistent verifier blind spots. An exploitable string (a master key) is exactly a persistent, learnable false positive. Anchors 3, 4, 5.
4. **PARTIAL.** Noise structure matters more than rate: group-level noise gives higher best and final reward than sample-level noise, but with 1-2 seeds per cell. Model-based verifiers: Qwen3 30B-A3B verifier peak 0.871 versus 0.900 clean; Qwen3 4B verifier peak 0.704 (single seed each; cause not isolated). Anchors 6, 7.
5. **CONFIRMED (limits).** Single model family for most runs, 90 MBPP validation problems, peak selection optimistic; GPQA check uses one seed per setting. Anchor 8.

## 3. Reported results
Training: GRPO, about 64 H100-hours per run (page text). Noise injection p in 0.05-0.50; clean Qwen3 8B baseline 0.884 final, 0.900 best. GLM4 9B group-rollout noise p=0.10 final 0.895 vs 0.884 clean. Llama 3.1 8B baseline 0.658 best (0.505 final). GPQA Diamond (Qwen3 8B, GSPO, one seed): base 0.540, clean 0.600, noise 0.05 0.604, noise 0.30 0.603.

## 4. Performance-principles table (cost model)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Random reward noise up to ~20% is tolerated by GRPO | NO transfer to our audit: no GRPO planned; and the noise is random, not exploit-reachable. | NO, same. |
| Group-level (whole-group) corruption preserves advantage information; per-sample corruption hurts more | PARTIAL: informs how to read a judge FPR (what matters is within-group reward contrast), applicable if a GRPO run is ever planned. | n/a |
| Judge size changes the verifier's training outcome (30B vs 4B) | PARTIAL: single seed; consistent with using the 27B judge, not a rule. | PARTIAL, same. |

## 5. In-house state
No lane component uses a noisy-reward tolerance number. AP-27 RLVR export is deterministic (`autopilot-program.md:195` @ f74b175); the GRPO monitor line is `context-and-token-economy.md:1397`. A1's futility rule in the loopholes dive (all strings < 1% FPR, citing Qwen3.8-27B-FP8 at most 1.5% in the paper) stays a self-chosen number; this paper does not move it.

## 6. Derived-actionables ledger
| # | Task line | Owner | Type | Stop/decision rule |
|---|---|---|---|---|
| N1 | refines loopholes A1: keep the FPR futility threshold as a pre-registered local choice; do NOT cite this paper as the source of a 10-20% tolerance. State in the A1 write-up that random-noise tolerance does not bound exploit-reachable FPR. | `eval-tower-program.md` | doc-only | Decision wording only. |
| N2 | refines loopholes A4: if a GRPO run is planned, log within-group reward contrast of the judge (not only aggregate FPR/FNR) as the paper recommends. | `context-and-token-economy.md:1397` monitor | doc-only | Decision wording only. |
| N3 | Decline: run a noisy-reward tolerance sweep. Reason: needs GRPO (about 64 H100-hours per run in the paper) with no consuming gate; the result would still not cover persistent blind spots. |  |  |  |

## 7. Dive-surfaced sources
None that change a ledger row. Decline: Shao et al. 2025 and Zhu and Kang 2026 (cited for noisy rewards in math, not in the page text beyond the name) would change no row.

## 8. Contradiction / adversarial pass
Authors disclaim a threshold, persistent biases, and a precision-recall preference; peak scores include unequal checkpoint-selection opportunities; unadjusted t-test p-values at 25% and 30% noise are 0.028 and 0.023 so degradation is detectable there; MBPP has 90 validation problems; pass@1 falls to 0.756 at 40% noise even though pass@16 matches baseline (metric-dependent tolerance). Model-based verifier comparison is single-seed and confounded.

## 9. read_depth
PARTIAL: read abstract, intro, Sections 3-6 and limitations; appendices (derivations, hyperparameters, per-seed tables) not read. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
