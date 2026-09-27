# Decision-Aware Routing — superseded history through 2026-09-27

> **Historical ledger only; current work lives in [../active/decision-aware-routing.md](../active/decision-aware-routing.md).**
> **Nothing here is dispatchable.** Moved verbatim at the 2026-09-27 wrap-up (workspace-8d): the April dependency
> graph, research-intake updates whose actionables were carried into the active file or superseded, and the
> replaced Status line and Start here block.

## Superseded Status line (as of 2026-09-26)

**Status**: REFRESHED 2026-07-03 (Fable 5 follow-up) — current-traffic DAR-1 replay completed 2026-07-03 and kept the routing-expansion gate CLOSED (22,992 routing decisions, 98.6% regret-identifiable, 0.00% gate regret; report in `epyc-orchestrator/orchestration/reports/dar1_regret_replay_2026-07-03.md`). Current dispositions: **DAR-2 contrastive is live-ON in production**; **DAR-3 (SPO+/epsilon-greedy) and DAR-6 are FROZEN per fable5-findings-02** until a future replay proves >=5% regret; **DAR-4 bilinear is retained** as the candidate descriptor-conditioned predictor (findings-02 §3). The April-era body below is historical record.

## Superseded Start here (2026-09-26)

### Start here (2026-09-26)

**2026-09-27: DAR-LAT is FROZEN (operator, narrowed plan) apart from the UFH-13 thesis experiment.** DAR-LAT-3h is ✅:
G1 chose T96 and nothing was applied (live `:8074` `-t 96` is the measured-better shape; see DAR-LAT-3h below). The
paragraph that follows is the pre-freeze plan; each DAR-LAT box carries its own unfreeze trigger.

The live work is the **latency-term track** at the end of this file, in § *Research Intake Update — 2026-09-26*.
Next is **DAR-LAT-1** (the `SlotCapacity` + `expected_wait_s` snapshot on the admission ledger), then DAR-LAT-2 at
weight 0. DAR-LAT-3 is the decision-grade A/B under P-SERVE-SEL-1 (ratified and landed `3573028b`). Its gate 3g is
blocked on the `:8074` thread/recipe reconciliation (DAR-LAT-3h). The sections between here and there are the
April-July DAR-1..6 record. DAR-3/4/5 were rescoped on 2026-07-21 (§ *RESCOPE*) and stay gated.

## Dependency Graph

```
DAR-1 (offline regret analysis)    ──independent──
DAR-2 (contrastive Q-score)        ──depends on DAR-1 confirming regret > threshold──
DAR-3 (SPO+ with exploration)      ──depends on DAR-2 producing ranked Q-values──
DAR-4 (model-feature-conditioned)  ──independently developable in parallel with DAR-2/3──
```

## Research Intake Update — 2026-04-18

### Episodic Memory Benchmark: Routing Intelligence Signal (intake-408/409 deep-dive)

The Tulving Episodic Memory Benchmark (arXiv 2501.13121, ICLR 2025) tested 21 models on 100K-token narratives requiring entity tracking and temporal ordering. Two metrics: Simple Recall (F1) and Chronological Awareness (Kendall τ). Key routing-relevant findings:

**Reasoning models catastrophically fail at long-context episodic memory:**

| Model | Recall (10K→100K) | Chronological (10K→100K) | Architecture |
|-------|-------------------|--------------------------|--------------|
| DeepSeek-R1 | 0.988→0.572 (-42%) | 0.964→0.147 (-85%) | MoE, reasoning |
| o1 | 0.978→0.384 (-61%) | 0.948→0.052 (-95%) | reasoning |
| GPT-4o | 0.908→0.670 (-26%) | 0.182→0.204 (+12%) | base |
| Gemini-2.5-Pro | 0.982→0.968 (-1%) | 0.948→0.796 (-16%) | base |

**Routing implications:**
- Chronological awareness varies **10x** across models (0.033 to 0.817) — a stronger differentiator than recall for routing decisions
- Reasoning models excel at short-context episodic tasks but collapse at 100K — their effective context utilization windows are much shorter than advertised context lengths
- For long-document temporal reasoning tasks, routing to reasoning-focused models is **actively harmful** (o1 scores worse than GPT-4o-mini)
- MoE vs dense architecture shows no clear signal — model size and training approach dominate
- **RAG chunk granularity matters**: chapter-level RAG matches in-context (0.82 vs 0.81 F1), paragraph-level RAG degrades to 0.60. Event-boundary-aligned chunking is critical.

**Actionable for DAR-4**: The `is_moe` binary feature in the bilinear scorer model features is less informative than a `reasoning_model` binary flag. Consider adding `is_reasoning_model` to `ModelFeatures` — it strongly predicts long-context episodic performance.

**Provenance pin (2026-09-07, `intake-408#06`, dive-verified).** Corrected "24 models" to **21** above.
The per-model 10K→100K deltas in the table are correct and are now pinned to
`epbench/experiments/additional_o1_o3_gemini_deepseek_ranking.ipynb` @ `892b22af097d4389d4f1b9cd47b5c51fdacd9bef`.
The routing signal stands and is now citable rather than asserted: **chronological awareness spans
0.033–0.817 across 21 models (10×) against recall's 0.300–0.968 (3×)**, and reasoning models invert
between scales (deepseek-reasoner 0.988 short → 0.572 long; o1 0.978 → 0.384). Record this as the
justification for the `is_reasoning_model` feature, with the notebook provenance attached.

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-474] "TRINITY: An Evolved LLM Coordinator"** (arxiv:2512.04695, ICLR 2026, openreview:5HaRjXai12)
  - Authors: Jinglue Xu, Qi Sun, Peter Schwendeman, Stefan Nielsen, Edoardo Cetin, Yujin Tang
  - Relevance: Fourth peer in this handoff's Research Context table alongside xRouter / RouteLLM / Router-R1 — same problem (lightweight policy that selects among LLMs), qualitatively different optimizer.
  - Key technique: ≈0.6B base LM + ≈10K-parameter head, trained with **separable CMA-ES** (an evolutionary strategy) instead of RL/SFT. Penultimate-token hidden state is mapped to agent-role logits for multi-turn role-typed delegation (Thinker / Worker / Verifier).
  - Reported results: 86.2% on LiveCodeBench (claimed coordinator-system record at submission); consistent gains over individual constituent models on coding/math/reasoning/domain-knowledge benchmarks; OOD generalization without SFT or RL.
  - Delta from current approach (DAR): DAR is reshaping the *learning objective* of the existing TD-trained Q-scorer (predict-then-optimize → decision-aware). Trinity drops the TD/RL frame entirely and trains the routing head with a black-box ES against an end-task fitness signal — directly side-stepping the credit-assignment / Q-magnitude problem that DAR-1 diagnosed. If DAR-2/3/4 underdeliver on the zero-predictive-spread pathology, sep-CMA-ES on the existing routing head is the natural escalation path that does NOT require multi-GPU RL infra (xRouter / Router-R1's blocker) and is CPU-feasible at our scale (10K params, no gradient). Caveat: author-acknowledged limitation is the abstract-vs-grounded-execution gap, which Trinity does NOT solve — that part stays inside our orchestrator.
  - Recommended follow-up: spike sep-CMA-ES as an alternative trainer for the existing `routing_classifier.py` MLP head when distillation labels are sparse. Add Trinity to the handoff's Research Context table.
  - **Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) — read before extending DAR-2/3/4. Specifically section 2.2 ("ES side-steps the credit-assignment problem DAR is trying to solve") and action #4 ("Re-examine DAR-2/3/4 for hidden REINFORCE-class pathology" — analytical check on whether SPO+/bilinear gradients share REINFORCE's off-block-noise weakness on block-ε-separable losses).

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-493] "Learning to Orchestrate Agents in Natural Language with the Conductor"** (arxiv:2512.04388, ICLR 2026, Sakana AI)
  - **Framing**: competitive intelligence on the optimizer-choice axis. NOTE: Trinity uses **sep-CMA-ES** (evolutionary strategy), not RL — earlier framing of "RL counterpart" was imprecise.
  - Relevance: Conductor (7B + GRPO) and Trinity (0.6B + sep-CMA-ES + 10K head) are two distinct points in the published optimizer-design space, both adjacent to DAR's question of "what objective trains the routing head". They are not the two *extremes*, just two published data points; many other formulations exist (BaRP intake-495 — bandit-feedback REINFORCE; LLM Bandit intake-496 — PPO+IRT). DAR remains a TD-trained-Q-scorer-loss-reshape problem.
  - Key technique: end-to-end GRPO with terminal task reward (no labelled trajectories), 2× H100 80GB, randomized agent-pool training, recursive self-as-worker for test-time scaling.
  - Reported results (concrete): LCB V6 +1.03 pp vs GPT-5 (within noise); GPQA-D +2.7 pp; open-source-only inference +~10 pp vs Claude Sonnet 4 (strongest ablation).
  - Delta from DAR scope: Conductor demonstrates that with sufficient base-model capacity (7B), terminal-reward RL can recover joint coordination decisions without explicit Q-objective shaping — this is competitive intelligence, not a target for DAR. **Implication for DAR-2/3/4**: if predict-then-optimize loss reshaping continues to underdeliver, the realistic CPU-feasible escalation is *Trinity-style sep-CMA-ES on the existing routing head* (10K params, no gradient), NOT a 7B GPU-class RL coordinator. Document this branching as one option among several in the DAR phase plan.
  - Caveats (Tier 2b): code/weights promised in supplementary, not yet public; six-author overlap with Trinity means not independent corroboration; LCB +1.03 pp is within noise; terminal-reward RL does not directly address inter-agent verification failures (MAST, arxiv:2503.13657, 36.9% of multi-agent breakdowns).

- **[intake-495] "Learning to Route LLMs from Bandit Feedback (BaRP)"** (arxiv:2510.07429 — earlier internal references at `2510.08429` are TYPOS pointing to ClauseLens)
  - Relevance: directly named in this handoff at L177 as the next escalation path if DAR-2/3 underperform. BaRP solves the exact train/test mismatch DAR cares about: production logs only record the chosen specialist's outcome, not counterfactuals — BaRP trains under bandit feedback rather than full-information offline labels.
  - Key pattern to lift: **bandit-feedback training** (don't require labels for un-chosen specialists) + **2-D performance-cost preference vector** dialed at inference time without retraining. Both are concrete additions to the existing learned router; do NOT replace the Phase-1 MLP wholesale.
  - Reported results: aggregate +16.84% score and -50% monetary cost vs GraphRouter on RouterBench-derived ID; +25.99% on OOD vs offline routers.
  - Caveat (Tier 2b): RouterBench is MMLU-skewed; OOD evaluated on public benchmarks the candidates likely saw; REINFORCE is high-variance on small pools — LinUCB / Thompson sampling may match without policy-gradient instability and the paper does not ablate this.
- **[intake-496] "LLM Bandit"** (arxiv:2502.02743, Yang Li, Feb 2025)
  - Relevance: companion bandit-routing paper. Direct hit on the "every model swap requires a full benchmark sweep" pain — IRT-based 20-50-prompt cold-start would compress that to hours.
  - Key pattern to lift: **IRT score predictor** + **model identity vectors** + **stratified-by-discrimination cold-start prompt selection**. Do not adopt the full PPO+GAE apparatus; that's heavyweight for our small pool.
  - Caveat (Tier 2b): single-author, no major-lab signal, slightly outside freshness window. Cost reductions only measured vs RouteLLM (not GraphRouter / RouterDC / BaRP). Short-output benchmarks may not transfer to autopilot multi-turn workload.

## Research Intake Update — 2026-05-27

### New Related Research

- **[intake-614] Fortytwo Network — chunk-ranking pipeline for agentic workloads (unpublished founder claim)**
  - Relevance: chunk-ranking, if disclosed, is a candidate mid-stream quality gate — rank partial completions from multiple models against milestones during a single tool-calling turn, rather than retrying full completions post-hoc. Maps onto DAR's escalation question: instead of "should we escalate this whole prompt to a stronger model based on uncertainty?", a chunk-rank gate could ask "should we keep, swap, or branch the model mid-generation based on a peer's ranking of the chunk so far?"
  - Status: claim has no paper, no blog, no code as of 2026-05-27 — the published Fortytwo paper (intake-615) is post-hoc pairwise on full completions only. Track for disclosure; do not design against it yet.
  - Founder-claimed result: 16-way parallel inference on vision tasks at "negligible" per-stream throughput hit. Unverified.
- **[intake-615] "Fortytwo: Swarm Inference with Peer-Ranked Consensus"** (arxiv:2510.24801)
  - Relevance: the post-hoc full-completion version of the above — could inform a DAR escalation mode where high-uncertainty prompts are dispatched to N≥2 models concurrently and the Bradley-Terry winner returned, in lieu of (or alongside) the current single-model escalate-to-stronger flow.
  - Reported result: +17.21pp on GPQA-Diamond over majority voting; 0.12% vs 6.20% prompt-injection degradation.
  - Open question: latency cost — at our stack a 2-way concurrent serve already halves per-stream throughput; need explicit roofline before considering.
