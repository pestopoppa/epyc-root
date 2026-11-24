# Dive — rhind — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://github.com/EleutherAI/rh-indicators", retrieved: "2026-11-24", sha256: "de7f03282193"}

Stage 2b wave 1, light dive. Expanded from intake-2877 (loopholes). Question: what predictor, status, license, usable as-is?

## 1. Stage-1 fields
- **Title**: EleutherAI/rh-indicators (Leading Indicators of Reward Hacking).
- **Authors**: EleutherAI (individual authors NOT-FOUND-IN-SOURCE).
- **State**: public repo, 26 commits; shallow clone read at SHA `1e8783d74f34e8e80c9d9daeb38e71dc7b506bc0`, latest commit 2026-04-14 ("latest script changes"). 2 stars, 0 forks (page text).
- **Categories**: training_distillation, benchmark_methodology.
- **Novelty**: medium. Predicts which exploit types emerge from early checkpoints or from prefill sensitivity; contrasts with the exposure predictor of intake-2877 (pre-training, no checkpoints).
- **Relevance: low.** Both predictors presuppose a training run (checkpoints of an SFT/GRPO model) on the djinn exploitable-coding testbed. We have no such run planned.
- **Credibility: 0/6.** peer-reviewed +0 (paper is a LaTeX draft, "Target: ICML 2026 submission (Jan 28 deadline)"); <=12 months +1 (last commit April 2026); known contributor +1 (EleutherAI); independent corroboration 0; commercial bias 0. Total 2 (WIP repo, results gitignored; the rubric has no penalty line for that).
- **Verdict: worth_investigating.** Not usable as-is today (needs a training run and the djinn testbed, neither planned); keep as the checkpoint-based alternative named in A4's wording so it is picked up if a local GRPO/RLVR run is planned.

## 2. Key claims
1. **CONFIRMED.** It implements prefill elicitation plus importance sampling to detect latent reward-hacking propensity on the djinn testbed. Anchors 0, 1.
2. **CONFIRMED (repo docs).** The concrete predictor in the shipped docs is "binary emergence prediction": from checkpoints up to a cutoff, features (KL divergence slope, logprob lower bound, Laplace-smoothed exploit rate) classify exploit-trained versus control runs; AUC by leave-one-out over 16 type-by-condition samples. Repo docs (`docs/binary_emergence_results.md` @ 1e8783d) report KL slope AUC 0.97 at cutoff 1 for GPT-OSS-20B exploit vs misalignment control (8 exploit types vs 8). For Qwen3-8B the table shows AUC 0.16-0.60 for KL level and 0.36-0.64 for KL slope (cutoffs 3, 5, 8, 11) and notes a Laplace-smoothing artefact for an AUC of 1.0. These are repo results, not anchored to page.txt; page.txt only has the README. Anchor: none for numbers.
3. **CONFIRMED.** Status is work in progress: README target is an ICML 2026 deadline, results/ is gitignored (README structure), no releases. No LICENSE file in the clone root; `pyproject.toml` carries the classifier "License :: OSI Approved :: MIT License". Anchor 2.
4. **PARTIAL.** It competes with exposure (p-hat x FPR) only loosely: it predicts emergence from within-training signals for an already fine-tuned model, while exposure predicts from the judge and the starting policy before training. The two are not compared in either source. Anchor 3.
5. **NOT-FOUND-IN-SOURCE.** Any evidence that its predictors transfer to LLM-judge hacking; the testbed is exploitable coding problems.

## 3. Reported results
README reports none. Repo docs report the numbers in claim 2 (GPT-OSS-20B 9 checkpoints per condition, ~611 problems per eval; Qwen3-8B 12-16 checkpoints, ~220 problems per eval). Draft paper abstract: proposes "low-probability elicitation" using importance sampling to track rare behaviours over training; it compares three estimators of decreasing cost and fidelity (fine-tuned proposal importance sampling, prompted prefills, direct logprob tracking).

## 4. Performance-principles table (mechanism)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Prefill sensitivity: P(exploit | exploit-like prefill) - P(exploit | neutral) | PARTIAL: forward passes only; usable on a 27B served model, but meaningful only across checkpoints of a trained policy. | PARTIAL: CPU forward passes slow for 20B+ checkpoints. |
| KL-slope across log-spaced checkpoints | NO: needs checkpoint series from a training run; none exists. | NO. |
| Importance-sampling probability bound for rare behaviour | YES as a method for rare patterns (could sharpen A2's zero-count bound); needs a proposal model. | PARTIAL. |

## 5. In-house state
No predictor of this kind in the lane. The only RL hook is a monitor line (`context-and-token-economy.md:1397` @ f74b175). The dependency `djinn` (EleutherAI exploitable-coding testbed) is not installed or referenced in the lane (not grepped across the whole repo; index grep only).

## 6. Derived-actionables ledger
| # | Task line | Owner | Type | Stop/decision rule |
|---|---|---|---|---|
| H1 | refines loopholes A4: record rh-indicators as the checkpoint-based alternative to exposure in the pre-RL audit wording; if a local GRPO run is planned, add KL-slope tracking over log-spaced checkpoints (its `select_checkpoints.py`) as a secondary signal. | `context-and-token-economy.md:1397` monitor | doc-only | Decision wording only; revisit when the trigger fires. |
| H2 | Decline: run the repo as-is. Reason: it needs a trained exploit model and the djinn testbed, and answers a different question (when will a training model start hacking) than our audit (is a judge/verifier exploitable); no gate consumes it. |  |  |  |

## 7. Dive-surfaced sources
- djinn (github.com/EleutherAI/djinn): would change no ledger row; decline.
- arXiv 2410.13211 (ARC, importance sampling for AI control; cited in README): would change A2's bound only if p-hat estimation is needed below the zero-count bound; decline until A2 reports hits.

## 8. Contradiction / adversarial pass
Repo is WIP with a gitignored results directory; reported AUCs are the authors' own, small-sample (16 samples, leave-one-out). Qwen3-8B results are much weaker than GPT-OSS-20B in the same doc, and the doc itself notes a smoothing artefact. No LICENSE file despite the MIT classifier; license is therefore not clear for reuse. No independent replication; 2 stars.

## 9. read_depth
PARTIAL: README page, `docs/binary_emergence_results.md` (first 60 lines), paper abstract (`paper/main.tex` lines 31-42), `paper_skeleton.md` header, file listing and `pyproject.toml` license line; scripts and run_utils code not read. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
