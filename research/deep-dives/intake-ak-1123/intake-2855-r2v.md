# Dive — r2v — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/html/2605.16604v1", retrieved: "2026-11-23", sha256: "ae4894d6ce58"}
> SOURCE-QUARANTINE: {url: "https://github.com/RaghuHemadri/r2v-agent", retrieved: "2026-11-23", sha256: "c041476ce49d"} (repo front page `r2v/repo.txt`; `gh api` metadata read: 3 commits, last push 2026-05-10, size 3 KB, MIT)

Bearing entry: intake-2835 (ADAPT; dive `research/deep-dives/intake-ak-1123/intake-2835-adapt.md`, ledger A1-A5). That dive listed R2V as the closest prior and asked: how much of ADAPT's gain over untrained asking did R2V already show, and does its protocol change A2/A3.

## 1. Stage-1 fields

- **Title**: R2V Agent: Teaching SLMs When to Ask for Help.
- **Authors**: Raghu Vamshi Hemadri, Humaira Firdowse Mohammed (equal contribution), Rishabh Maheshwary, Srivatsava Daruru, Sagar Davasam, Vikas Yadav, Srinivas Sunkara, Sai Rajeswar (NYU Tandon, UC San Diego, ServiceNow Research, Stanford, Mila, Université de Montréal).
- **Version/date**: arXiv:2605.16604v1 [cs.LG], 15 May 2026, CC BY 4.0. Preprint.
- **Categories**: cost_aware_routing, routing_intelligence, agent_architecture.
- **Novelty**: medium. Step-level SLM-to-LLM escalation with a calibrated residual-risk router (Brier + CVaR-constrained objective) over a fixed BC-then-DPO distilled SLM. The distillation scaffold is explicitly "standard", not claimed as new.
- **Relevance**: medium. It is the router-shaped answer to the same question ADAPT answers policy-shaped, and its router is a ~10,000-parameter CPU model fitted on logged-rollout labels, which removes the GPU gate that intake-2835 attached to "a learned ask policy".
- **Credibility**: 1 = peer-reviewed 0 (preprint) + within 12 months +1 + major lab / known contributor 0 + independent corroboration 0 + commercial bias 0. Internal inconsistency in the headline number (claim 1) and no public code (claim 4) keep it at 1.
- **Verdict**: adopt_patterns. Adopt the episode-outcome labelling of residual risk, the Bayes-threshold form tau = (c_LLM - c_SLM)/kappa and the entropy-router/oracle-router baselines as readouts; do not adopt the headline numbers.

## 2. Key claims

**Claim 0 — escalation is decided by a separate router over a fixed trained SLM, labelled by SLM-only episode outcome. CONFIRMED.** The SLM is first distilled (BC on teacher trajectories, then verifier-guided DPO with a JSD consistency term); "only after the distilled SLM policy is fixed" is the router trained. Router labels: y_t = 1 on every context of a logged SLM rollout that fails the episode, "not from counterfactual teacher success". The router is a 15-feature MLP (128/64 hidden, batch norm, dropout 0.2, post-hoc temperature scaling, about 10,000 parameters, "runs entirely on CPU", 20 epochs, 25 s per Table 10). Inference (Algorithm 2): the SLM samples K=5 candidates per step, a CPU verifier scores them, the router fires above tau, and the teacher then chooses the step's action itself (hand-off of one step, not advice). Anchors: abstract/section 1 and section 4.1 quotes below.

**Claim 1 — headline "94.3% HumanEval+ at 0.6% escalation, 98.2% TextWorld at 41.7%, 93.3% TerminalBench at 33.9%". PARTIAL (HumanEval+ SR is contradicted by the paper's own tables).** Table 2 and the abstract give 94.3 for HumanEval+. The paper's per-backbone Table 5 gives 91.9 / 95.8 / 93.1 / 92.4, whose mean is 93.3, and Table 9 "Full" repeats 93.3 (LLM% 0.65 in both, matching 0.6). TextWorld (98.0/98.4/98.1/98.3, mean 98.2; escalation 38.3/48.8/38.4/41.2, mean 41.7) and TerminalBench (92.8/95.5/89.2/95.7, mean 93.3; escalation 38.9/67.2/13.2/16.3, mean 33.9) reproduce exactly. So the HumanEval+ gain over SLM-only (91.9) is +1.4, not +2.4, by the paper's own per-model rows. All three benchmarks are replay-based (clean teacher trajectories replayed under 5 perturbation seeds), with HumanEval+ test about 25 tasks and TerminalBench about 14 tasks ("approximately 62 / 13 / 14").

**Claim 2 — "token entropy alone misses the failures; the learned router with verifier features is what helps". CONFIRMED, and it is the only untrained-signal evidence in the paper.** Entropy Router row: 92.9 / 0.8% (HumanEval+), 64.6 / 0.0% (TextWorld, i.e. it never escalates and equals SLM-only), 87.4 / 4.1% (TerminalBench). Feature ablations (Qwen2.5-7B, applied at inference without retraining): entropy-only on TextWorld 64.6 / 2.4%; removing the verifier on TextWorld drops to 62.6. This is relevant to us because the orchestrator's `generation_monitor` (entropy, repetition, perplexity triggers) is the same family as R2V's Entropy Router.

**Claim 3 — R2V already showed that training the ask behaviour adds value over untrained asking. NOT-FOUND-IN-SOURCE (this is the steering question, answered negatively).** Every R2V baseline shares "the same distilled SLM and verifier and differ only in the routing decision", so the SLM-only row is itself BC+DPO-distilled; there is no untrained-SLM-asks-via-a-tool arm and no comparison of a trained versus untrained ask policy. R2V therefore shows router gain over a distilled SLM and over a training-free entropy rule, not ADAPT's gain over an untrained agent that holds an `ask_advisor` tool. What ADAPT borrowed from R2V is smaller: ADAPT's text takes "post-hoc perturbations ... as suggested in R2V-Agent" for its SFT warm start and follows R2V's LiveCodeBench-stdin harness (intake-2835 page, cross-source). For scale, ADAPT's own Table 2 (as recorded in intake-2835) puts its generic SFT stage (RFT) at 58.7 / 48.25 / 36.8 against Neutral 24.5 / 21.8 / 17.5 and final 77.32 / 56.01 / 49.25, i.e. RFT alone carries (58.7-24.5)/(77.32-24.5)=65%, (48.25-21.8)/(56.01-21.8)=77% and (36.8-17.5)/(49.25-17.5)=61% of the Neutral-to-ADAPT gain on TextWorld / LCB / GAIA (derived arithmetic on intake-2835 numbers, not an R2V figure). R2V adds no evidence on the remainder.

**Claim 4 — code is public. OVERTURNED in substance (consistent with ADAPT's statement).** The paper's footnote gives `github.com/RaghuHemadri/r2v-agent`. The repository has 3 commits (initial commit, README notice, MIT licence; last push 2026-05-10), 3 KB, and a README that says the reproduction code "will be added here soon". There is no code to run six months after the paper.

**Claim 5 — evaluation soundness. PARTIAL / protocol gap.** The paper never says how a mixed SLM/teacher trajectory is scored. Table 10 gives "Offline evaluation" as CPU under 1 minute and "Ablation sweeps" as CPU under 5 minutes, which cannot include live environment rollouts with a model; my inference (not stated) is that routed success rates are estimated from cached trajectories. The TerminalBench verifier "operates without Docker or subprocess execution" and parses logged terminal output; its episode-level AUROC is 0.508 ("near-chance separation"), yet R2V reaches 93.3 there. The oracle router is hindsight over SLM failure labels, "not an attainable policy". Counts conflict: TextWorld is "250 tasks" but "800/200/250 train/validation/test episodes", not a 70/15/15 task split.

## 3. Reported results (as the source states them)

- Setup: four SLM backbones (Gemma-9B, LLaMA-3.1-8B, Qwen2.5-7B, Qwen2.5-14B); teacher Gemini 3 Flash Preview for HumanEval+ and TextWorld; TerminalBench teachers Claude Opus 4.6, GPT-5.5, Gemini 3.1 Pro; verifier CPU-only; K=5 candidates via vLLM; alpha 0.20, epsilon 0.10, c_LLM/c_SLM = 50; success rate (SR) and LLM% = fraction of steps escalated, noisy evaluation (perturbed), 95% bootstrap CIs per backbone.
- Table 2 (SR / LLM%, averaged over four backbones): SLM-only 91.9/0.0, 64.6/0.0, 81.1/0.0; Entropy 92.9/0.8, 64.6/0.0, 87.4/4.1; Heuristic 97.4/26.6, 98.4/99.9, 95.0/66.0; R2V 94.3/0.6, 98.2/41.7, 93.3/33.9; Oracle 98.6/8.1, 98.6/35.4, 97.8/18.4; LLM-only 98.8/100, 98.7/100, 98.1/100 (HumanEval+ / TextWorld / TerminalBench).
- CVaR sweep (combined suite, Table 7): (0.20, 0.10) 97.76 SR at 27.47% escalation; (0.05, 0.02) 98.05 at 56.63%; (0.20, 0.15) 95.29 at 21.11%.
- Closed-source adaptation: no-entropy and verifier-score pseudo-entropy variants; TextWorld pseudo-entropy 98.1 SR / ECE 0.054; TerminalBench no-entropy drops to 90.9.
- Compute: single server with four H100 80 GB; 25-40 GPU-hours per benchmark-backbone configuration, about 360-576 H100 GPU-hours in total; API spend "on the order of $200-$500"; the router trains in about 25 s on CPU.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Separate calibrated router (10k-parameter MLP) deciding per-step escalation | YES. Trivial model; features come from the served model's logprobs and a verifier. | YES. Trains on CPU in seconds (paper: 25 s); no accelerator needed. |
| Per-step K=5 candidate sampling plus verifier to build features | PARTIAL. K candidates are one small batch (fits our small-ubatch regime), but costs K-fold decode per step and, on the speculative-decode served path, interacts with draft/accept; features such as candidate consistency need K full samples, while token-entropy/logprob features come free from one sample. | PARTIAL. K-fold bandwidth-bound decode; use only the one-sample logprob features first. |
| Episode-outcome labels from logged SLM-only rollouts (no counterfactual) | YES. Needs logs, not inference. | YES. |
| Bayes threshold tau = (c_LLM - c_SLM)/kappa and CVaR operating-point knob | YES (arithmetic). | YES (arithmetic). |
| BC + DPO distillation scaffold on 7-14B models | PARTIAL. The paper's own cost (4 x H100, 12-16 h DPO per configuration) is a build cost; LoRA on one MI210 is plausible but unverified (intake-2834 CR1 provisioning applies). Not needed for the router part. | NO at this scale; not needed for the router part. |

## 5. In-house state (orchestrator `1a10541b` read-only; lane `d785b6d`)

- Failure-driven rule policy, no learned risk: `EscalationPolicy.decide` (src/orchestration/escalation.py:L227-L350 @ 1a10541b, per intake-2835).
- R2V's Entropy Router has an in-house analogue: `src/generation_monitor.py` (training-free entropy, repetition and perplexity triggers; entropy_threshold, entropy_sustained_count; module docstring cites Gnosis, ZIP-RC, KnowLoop) feeding `chat_pipeline.stages._quality_escalate` and the opt-in `/v1` escalation (src/api/routes/v1_escalation.py:L1-L30 @ 1a10541b; flag `v1_escalation` default off). R2V's TextWorld result (entropy router escalates 0.0%) is evidence that this family can be blind where failures are observation-induced.
- Per-token probabilities are reachable from the llama.cpp backend (`completion_probabilities` in src/backends/llama_server.py:L634-L635 @ 1a10541b), so R2V's logprob/entropy feature group is available without new server work; candidate-consistency and semantic-entropy features would need extra samples.
- Reward side: fixed escalation penalty 0.15 per escalation (`escalation_penalty = len(escalations) * 0.15`, orchestration/repl_memory/q_reward.py:L173 @ 1a10541b; verified in this dive).
- Gating: DAR-LAT frozen with an unfreeze trigger, DAR-3/DAR-6 frozen (routing-program.md:L7, L64 @ d785b6d); filing a design note does not unfreeze them. `routing-program.md:L79` records zero difficulty spread (62.2 / 60.7 / 62.2% escalation across bands).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| R1 | Fit a residual-risk probe on logged episodes that were NOT escalated (label = episode failed; features = per-step logprob/entropy statistics, step index, context length) and report AUROC, ECE and Brier against the entropy-only rule already in `generation_monitor`. Refines intake-2835 A2 (it removes A2's matched-ask/no-ask confound by using SLM-only outcomes as labels). | `routing-program.md` (RTG-09 reward axis; DAR-3/6 and DAR-LAT frozen sections excluded) | code + replay, zero inference | Question: does a calibrated multi-feature probe beat entropy-only at predicting episode failure on our logs (R2V's TextWorld says entropy-only can score at SLM-only)? Stop on answer after one fit; stop on futility if non-escalated failed episodes with per-step logprobs are too few to hold out 30% (record the count and stop). |
| R2 | Add R2V's three non-learned readouts to the A3 ask-calibration set: entropy-only router, heuristic router, and the failure-mask oracle (escalate exactly the steps of failed rollouts), each reported as success versus escalation-% with ECE/Brier for the probe. Refines intake-2835 A3 (the failure-mask oracle needs no counterfactual replay and precedes ADAPT's K-rollout oracle). | `eval-tower-program.md` J17 consult harness (L1629/L1766) and `routing-program.md` consult track | code/doc now; inference rows later | Question: what share of failed-episode steps would a router need to catch to reach the failure-mask oracle? Stop on answer when the three baselines are tabulated on existing J17 artifacts; no new inference. |
| R3 | Write the A4 design note as a two-architecture choice (in-policy ask tool trained by DPO/GRPO versus a separate CPU router over the served policy), stating that the router path needs no GPU training and that per-step K-sampling is optional. Refines intake-2835 A4. | `routing-program.md` (learned-routing-controller track; frozen with unfreeze trigger, filing a note is allowed) | doc-only | Decision: which architecture to try first; done when the note states the cost of each in advisor-seconds and training hours. |
| R4 | DECLINE: reproduce R2V's headline numbers. Reason specific to this entry: the repository is a placeholder with no code, and the paper does not say how routed success is computed (replay versus live rollouts), so a reproduction would be a guess at the protocol; R1 and R2 test the transferable parts on our own logs. | n/a | n/a | n/a |
| R5 | DECLINE: adopt the CVaR-constrained objective now. Reason specific to this entry: Table 7 shows (alpha, epsilon) only slides the operating point along the same success-versus-escalation curve (97.76/27.47 versus 98.05/56.63 versus 95.29/21.11), the same effect a threshold sweep on a calibrated probe gives; our logs carry no perturbation seeds, which the CVaR term is defined over. Revisit if R1 shows seed-level tail behaviour. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `github.com/RaghuHemadri/r2v-agent` (0 hits for URL and author): placeholder, no code. Decline: it settles nothing until code lands; re-check only if R1 is opened.
- arXiv:2406.00430 KnowLoop, 2512.20578 Gnosis, 2512.01457 ZIP-RC (cited by `generation_monitor.py`): not checked against the index here; they concern the in-house monitor, not any ledger row of this run. Decline.
- arXiv:2601.11868 Terminal-Bench and the `yoonholee/terminalbench-trajectories` dataset: R2V's TerminalBench inputs; would not change R1-R3. Decline.

## 8. Contradiction / adversarial pass

- Headline HumanEval+ 94.3 vs per-model mean 93.3 (Tables 5, 9): own tables disagree by 1.0.
- Small replayed test sets (about 25 HumanEval+ tasks, about 14 TerminalBench tasks); bootstrap CIs in Table 5 are over perturbation episodes of those tasks.
- Verifier AUROC 0.508 on TerminalBench, yet the router recovers 93.3: the gain there comes from the other 14 features, and the paper concedes "some shell-task failures are identifiable in hindsight but not yet fully captured".
- Heuristic router reaches 98.4 on TextWorld at 99.9% escalation (effectively LLM-only), so R2V's advantage over heuristics is cost, not accuracy; against the oracle's 35.4% escalation R2V uses 41.7%.
- Ablations single-backbone (Qwen2.5-7B); consistency regularisation lowers HumanEval+ SR (94.0 to 92.4) at the canonical setting.
- No public code; no independent replication; the authors' own future-work note: dependence on verifier and feature quality.

## 9. Read depth

read_depth: FULL for the paper (main text, appendices A-F, all tables); repo front page and `gh api` metadata read; no repo code exists. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | Abstract | "using Brier-calibrated probability estimation and a Conditional Value-at-Risk (CVaR)-constrained objective"
- claim 0 | page | Section 4.1 | "The routing label is derived from the downstream SLM episode outcome, not from counterfactual teacher success."
- claim 0 | page | Appendix C.3 | "and runs entirely on CPU"
- claim 1 | page | Table 2 | "R2V (ours) 94.3 0.6% 98.2 41.7% 93.3 33.9%"
- claim 1 | page | Table 5 (HumanEval+ rows) | "Gemma-9B 91.9 [89.6, 93.8] 0.50% LLaMA-3.1-8B 95.8 [94.3, 97.3] 1.46% Qwen2.5-14B 93.1 [91.1, 94.9] 0.25% Qwen2.5-7B 92.4 [90.1, 94.2] 0.36%"
- claim 1 | page | Table 9 | "HumanEval+ Full 93.3 0.65% 0.067 0.114"
- claim 2 | page | Table 2 | "Entropy Router 92.9 0.8% 64.6 0.0% 87.4 4.1%"
- claim 2 | page | Appendix D.2 feature groups | "entropy-only routing reaches only"
- claim 3 | page | Section 5.1 Baselines | "All deployable methods share the same distilled SLM and verifier and differ only in the routing decision"
- claim 4 | page | Section 6 footnote | "github.com/RaghuHemadri/r2v-agent"
- claim 5 | page | Table 10 | "8 Offline evaluation CPU < < 1 min 9 Ablation sweeps CPU < < 5 min"
- claim 5 | page | Appendix C.2 TerminalBench verifier | "reflecting near-chance separation when local step scores are mean-aggregated"
- claim 5 | page | Section 5.1 Baselines | "The oracle is a diagnostic upper bound: it has hindsight access to the SLM-only episode outcome"

Anchors verified: 13 of 13 (python count >= 1 in `r2v/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/r2v.json` written; all anchor quotes verified in `r2v/page.txt`).
