# Deep Dive: Where Does Output Diversity Collapse in Post-Training?

**Intake ID**: intake-441
**Paper**: "Where does output diversity collapse in post-training?"
**ArXiv**: 2604.16027
**Source artifacts**: OLMo 3 model card family (allenai/OLMo-3-7B-Base, OLMo-3-7B-Think, OLMo-3-7B-Instruct, OLMo-3-7B-RL-Zero)
**Published**: 2026 (Tier 2a; authors' group active in open LM release pipeline at AI2)
**Date of intake**: 2026-04-20

---

## 1. Abstract

Post-trained language models generate noticeably less varied outputs than their base-model ancestors. This paper uses the OLMo 3 lineage — three parallel post-training tracks (Instruct, Think, RL-Zero) over a shared 7B base — to pinpoint *where* along the post-training pipeline diversity collapses. Across 15 open-ended generation tasks and four diversity metrics (predictive entropy, distinct-2 / diversity-2, type-token ratio, self-BLEU), they decompose each checkpoint's diversity loss into a **quality-control component** (loss you'd expect from filtering out bad completions) and a **residual** (genuine narrowing of weight-level output distribution). Three findings dominate: (i) SFT is the primary narrowing stage on the Think track; (ii) DPO's contribution is much larger on Instruct than on Think; (iii) masking the chain-of-thought in evaluation preserves answer-level diversity, meaning the collapse lives in model weights, not the generation format. Inference-time interventions (temperature, prompt rotation, nucleus) recover only a small fraction of lost diversity.

---

## 2. Key Findings

### 2.1 Post-training collapses diversity on every axis measured

Across all four metrics — predictive entropy, distinct-2, TTR, self-BLEU — post-trained models score lower than the matched base model on open-ended tasks. The effect holds across temperature settings tested (T=0.7, T=1.0, T=1.3). This is not a story about one pathological metric — it is a multi-metric signature of mode collapse.

### 2.2 SFT is the dominant narrowing stage in Think models

For the Think lineage (Base → Mid-Train → SFT → DPO → RLVR), the SFT step absorbs the majority of the residual diversity loss. DPO and RLVR each add smaller increments. This contradicts a common assumption that preference optimization (DPO/RLHF) is the main culprit — for reasoning-tuned models, plain supervised fine-tuning on curated long-CoT traces is where most of the collapse happens.

### 2.3 DPO effect is much larger in Instruct than in Think

On the Instruct track (less CoT-heavy, more chat-style SFT mix), DPO produces a visibly larger diversity drop than it does on the Think track. Interpretation offered by the paper: the preference data for an instruct chat model concentrates a narrow "helpful-assistant" persona, while preference data for a reasoning model already targets structured outputs where diversity is partly constrained by correctness.

### 2.4 Chain-of-thought suppression preserves answer-level diversity

When the authors strip the `<think>...</think>` block and measure diversity on the answer portion only, the gap between base and post-trained models shrinks substantially. Same model weights, same sampling config; the only change is which slice of output is scored. Conclusion: **the collapse is at the weight/policy level, not because of a rigid CoT scaffolding format.** A post-trained model with CoT suppressed is still less diverse than a base model — just less dramatically so.

### 2.5 Inference-time interventions cannot fully recover training-time diversity

Temperature bumps, nucleus changes, prompt variation, and persona rotation all recover a fraction of the pre-training entropy but plateau well short of the base model. You cannot undo SFT-induced mode collapse purely at generation time. This is the load-bearing claim for EPYC.

### 2.6 Quality vs residual decomposition

The authors propose a decomposition: the diversity drop of a post-trained model = (a) a "quality-control" loss you'd get if you just kept the top-K% base-model completions ranked by a reward/judge, plus (b) a *residual* that can't be attributed to quality filtering. Findings are strongest in (b) — even after subtracting "they just got rid of bad outputs," there is a substantial residual collapse that represents genuine narrowing of the policy distribution.

The engineering interpretation: "the model got narrower because we filtered out bad outputs" is partly true but insufficient. There is a real policy-level narrowing on top of it. That narrowing is what §2.5 says you cannot fix with sampling tricks.

### 2.7 Task-dependent effect size

Not all tasks collapse equally. Tasks with large open-ended output spaces (creative writing, open-spec code generation) show the largest absolute diversity drops. Tasks with narrower acceptable-answer sets (closed QA, code with tests) show smaller drops — partly because their diversity ceiling is already lower. EPYC implication: if we run the diversity-probe subset on closed-answer suites only, we will under-estimate the effect. The probe subset in §8 must include at least 40-50% genuinely open-ended prompts.

### 2.8 RL-Zero vs SFT-then-RL

The RL-Zero track (no SFT) shows a *different* narrowing profile than Think (SFT then RLVR). RL-Zero's policy collapses more sharply at the RL stage precisely because it is doing double duty: shaping both correctness and format without prior SFT scaffolding. This is indirect evidence that *some SFT before RL absorbs collapse away from RL*, which is relevant if we ever train an EPYC-local routing or verifier model from scratch.

---

## 3. Methodology

### 3.1 Model family — OLMo 3 7B

Three post-training tracks share a single pre-train + mid-train backbone:

- **Base**: pre-trained only
- **Mid-Train**: mid-training anneal on high-quality data
- **Instruct** track: Base → Mid → SFT(chat) → DPO
- **Think** track: Base → Mid → SFT(long-CoT) → DPO → RLVR
- **RL-Zero** track: Base → Mid → RLVR directly (no SFT)

Because all three tracks fork from the same ancestor, the paper isolates each post-training stage's effect without confounding across model families.

### 3.2 Task suite — 15 open-ended generations

Mix of creative-writing, summarization, code-completion with open spec, roleplay, and dialogue-continuation. Deliberately open-ended: closed-answer QA (MMLU-style) is *not* a good diversity probe because the answer set is small by design. The paper separately reports a few closed-form tasks as a control.

### 3.3 Metrics — four complementary axes

- **Predictive entropy**: average token-level entropy over generated positions (policy-level, not corpus-level).
- **Diversity-2 (distinct-2)**: fraction of unique bigrams across N samples from the same prompt.
- **Type-Token Ratio (TTR)**: types / tokens over generated corpus — lexical diversity.
- **Self-BLEU**: BLEU of each sample against the rest — lower = more diverse.

Four metrics were chosen because each has a known failure mode (entropy is sensitive to calibration; self-BLEU is sensitive to length; TTR is sensitive to vocabulary size). Agreement across all four is the paper's signal of a real effect.

### 3.4 Quality-vs-residual decomposition

For each (task, checkpoint) pair they construct a "matched base completion set": sample many completions from the base model, score them with a reward/judge, keep the top-K so the *quality* distribution matches the post-trained model. Any diversity drop beyond what that matched set already shows is attributed to *residual* narrowing.

### 3.5 CoT-suppression ablation

For Think models, they run evaluations twice: once scoring the full output, once after stripping the `<think>` block. The delta between these two isolates how much of the measured collapse comes from the think-block format vs from the policy itself.

### 3.6 Sampling budget and stability

Each (task, checkpoint, metric) cell uses on the order of 20-50 prompts × 5-10 completions per prompt, giving ~100-500 samples per cell. Variance over seeds is reported and is small relative to the cross-checkpoint deltas — the narrowing effect is large enough that seed noise does not obscure it. This matters for EPYC's experiment design: we can get a usable diversity signal from a smaller sample budget (20 prompts × 4 completions per §8) because we are measuring a large effect, not a small one.

### 3.7 What the paper does NOT do

- Does not compare across model families (no Qwen, no Llama, no Mistral).
- Does not isolate effect of individual SFT data-mix components (could not say "instruction-following SFT narrows more than code SFT").
- Does not measure diversity at the *task-solution level* — e.g., "how many distinct valid algorithms does this model emit for a coding problem?" — only at the text level.
- Does not evaluate MoE models. All OLMo 3 variants are dense 7B.
- Does not connect diversity to downstream agent performance (does a less-diverse coder produce worse agent traces on HumanEval? Unmeasured here).

These gaps are EPYC's to fill if we pursue the integration — which is why §8's experiment is scoped to *our* stack with *our* data.

---

## 4. Why This Matters to EPYC

### 4.1 AR-3 / PromptForge — mutation diversity is upper-bounded by base-model diversity

PromptForge drives AR-3 exploration by asking a Claude CLI model (and increasingly local post-trained models via the GEPA adapter) to *mutate* frontdoor / program prompts. Every mutation is a sample from that model's post-training-collapsed distribution. If the paper's SFT-narrowing result holds on the models we use for mutation, then the effective exploration space PromptForge can reach is strictly smaller than the nominal token-space volume suggests. Two consequences:

- **The stagnation we see after ~50 trials may be partly policy-collapse exhaustion**, not just a saturated prompt surface. Species would produce the same handful of "shapes" because the model only generates a handful of shapes.
- **Turning up temperature on the mutation model does not fix this** (paper §3.5, result 2.5). Stacking diverse mutation *prompts* (the current `mutation_type` dispatch of targeted_fix / compress / crossover / gepa) is somewhat effective, but also bounded: each mutation prompt still samples the same policy.

### 4.2 Model selection — diversity is not currently measured

Our model-selection loop for autopilot swaps (architect, coder, worker) scores quality (via accuracy on a benchmark suite), speed (tok/s), cost (quant size), reliability (error rate), ECE/AUC (calibration). **Diversity is not in the signature.** When we swap an architect model, we could be silently accepting a regression on output variety that would only show up downstream as PromptForge mutations becoming repetitive or autopilot exploration stalling earlier. This is invisible to the SafetyGate as currently wired.

### 4.3 Reasoning compression — bounded by what generation-format interventions can do

reasoning-compression.md relies on two levers: conciseness prompts (`program.md` language nudge) and think-strip (keep only the answer block). The paper's CoT-suppression ablation is directly relevant: stripping the think block does *not* restore base-model diversity — it only shrinks the gap. Said the other way around, **the variety you can recover by removing the scaffolding is capped**; deeper "let the model actually re-learn to be varied" requires touching weights (training-time intervention), not format (inference-time). This doesn't invalidate the conciseness program, but it caps its ceiling.

### 4.4 Autopilot strategy memory — risk of stagnating MKG

The autopilot strategy store (FAISS+SQLite) accumulates mutation knowledge. If the underlying generator is mode-collapsed, the MKG will accumulate a narrow set of archetypes and then plateau — not because all ideas have been found, but because the generator cannot emit the remaining ones. This matches the observed plateau on AR-3 around trial 40-50 in the journal.

A subtler second-order effect: strategy-store retrieval conditions future proposals on past-accepted ones. Under a collapsed policy, the FAISS neighborhood of accepted strategies is itself narrow, and retrieval reinforces the narrow region. The store acts as a confirmatory memory rather than a diversifying one. Mitigation in §7.4 (mean pairwise embedding distance as a stagnation signal) is the right first diagnostic.

### 4.5 Routing and decision-aware training

Downstream components (learned-routing-controller.md, decision-aware-routing.md) train on generator traces. If traces are mode-collapsed, the routing model's training distribution has narrower tails than real deployment traffic. This could make the router overconfident on typical inputs and fragile on tail inputs. A diversity metric on the training-data collection stage would catch this before it gets baked into a router checkpoint.

### 4.6 Distillation and SFT data synthesis

wiki/training-distillation.md and the bulk-inference-campaign flow use our production models as teachers to generate synthetic SFT data. Paper's direct consequence: *the student can be no more diverse than the teacher's policy*, regardless of student architecture. If we ever distill a Qwen3-14B student from 30B-A3B teacher outputs, the student inherits the teacher's mode collapse. Practical hedge: include a fraction of base-model (un-post-trained) completions in the distillation mix, even at the cost of some quality.

---

## 5. Amend / Expand / Confirm

### 5.1 Confirm — validates prior EPYC observations

- **AR-3 mutation plateau**. The autopilot journal shows PromptForge acceptance-rate plateaus after ~50 trials. We had attributed this to a saturated prompt surface + failure-blacklist accumulation. The paper supplies a complementary explanation: the mutation model's policy distribution is genuinely narrow, and the top modes saturate quickly.
- **"Same-feeling" outputs from some tuned checkpoints**. Session notes (2026-04-17 wrap-up) flagged that some post-trained candidates produced noticeably "samey" answers across sweeps. At the time this was filed under "low temperature weirdness." The paper reframes it as a checkpoint-level attribute.
- **GEPA + LLM hybrid mutations outperform pure-LLM at high trial counts** (autopilot-continuous-optimization.md P10). GEPA's evolutionary operators break out of the LLM's local mode because they do not themselves sample from the LLM policy — they splice and recombine. Paper implies this hybrid advantage should persist or grow on longer runs.
- **Conciseness prompts have a ceiling** (reasoning-compression.md). Matches paper §2.4 — format-level interventions cap before base diversity is recovered.

### 5.2 Amend — changes model-selection criteria and eval tower scope

- **Model-selection criteria must add a diversity axis.** When we evaluate a candidate architect / coder / worker checkpoint, we should report entropy, distinct-2, and self-BLEU alongside quality/speed/cost/reliability. A checkpoint with +0.05 quality but -25% diversity is a *regression* from the autopilot system's perspective, even if the SafetyGate accepts it.
- **EvalTower should emit diversity metrics.** Concrete proposal in §6.
- **Failure blacklist should track "low-diversity proposer" as a reason.** Currently blacklist entries are failure-mode strings. Add a `diversity_regression` reason keyed to a baseline delta.

### 5.3 Expand — run a diversity baseline pass

We should run a one-day diversity measurement pass on the current production stack: architect_general, architect_coding, coder, worker. Use the paper's four-metric protocol on a sampled subset of our existing eval suites. This gives us a baseline that future swaps must not regress. See experiment plan §8.

---

## 6. Concrete Integration Proposal — Diversity in the Eval Tower

### 6.1 Data model changes (`safety_gate.py`)

Add to `EvalResult` (currently L44-70 in `epyc-orchestrator/scripts/autopilot/safety_gate.py`):

```python
# Diversity metrics (intake-441)
diversity_entropy: float = 0.0       # mean per-token predictive entropy
diversity_distinct2: float = 0.0     # fraction unique bigrams across samples per prompt
diversity_self_bleu: float = 0.0     # mean self-BLEU (lower = more diverse)
diversity_ttr: float = 0.0           # type-token ratio
diversity_n_samples_per_prompt: int = 0  # how many completions per prompt (3-8 typical)
```

### 6.2 Compute at every tier

At T0 (10q/30s) diversity is noisy — still emit it, flag as low-confidence. At T1 (100q/5m) and T2 (500q/30m) it is informative. The compute is cheap: it's string statistics over outputs we already generated. The only extra cost is sampling N completions per prompt instead of 1 — which for T1/T2 means ~3× inference time on the diversity subset.

Approach: designate a small diversity-probe subset (~20 open-ended prompts) drawn from existing suites. For those prompts only, sample N=4 completions each. Compute metrics over the N-sample group.

### 6.3 Emit via `to_grep_lines()`

```python
if self.diversity_entropy > 0:
    lines.append(f"METRIC diversity_entropy: {self.diversity_entropy:.4f}")
if self.diversity_distinct2 > 0:
    lines.append(f"METRIC diversity_distinct2: {self.diversity_distinct2:.4f}")
if self.diversity_self_bleu > 0:
    lines.append(f"METRIC diversity_self_bleu: {self.diversity_self_bleu:.4f}")
if self.diversity_ttr > 0:
    lines.append(f"METRIC diversity_ttr: {self.diversity_ttr:.4f}")
```

Same convention as existing ECE/AUROC/branching_density fields (L104-111). Gated on `> 0` so older trials that didn't compute them don't pollute logs.

### 6.4 SafetyGate — diversity regression rule

Add to SafetyGate decision table (autopilot-continuous-optimization.md L107-111):

| Check | Trigger | Action |
|-------|---------|--------|
| Diversity regression | Δdistinct2 < -0.20 *or* Δself-BLEU > +0.10 on diversity-probe subset | Reject |

Threshold choice: paper observes SFT diversity drops in the 15-40% range on distinct-2 depending on task. A 20% floor rejects checkpoints that behave like a fresh SFT round vs a measured tune.

### 6.5 Baseline file

`autopilot_baseline.yaml` must gain `diversity_entropy`, `diversity_distinct2`, `diversity_self_bleu`, `diversity_ttr` per `frontdoor_speed` pattern. Populate from the experiment in §8.

### 6.6 Non-regression path — incremental

Phase 1 (2 days): Add fields to `EvalResult`, wire through `to_grep_lines()`. Compute only on a flag (`--emit-diversity`). No gate wiring yet. Just start logging.

Phase 2 (1 day, after §8 baseline): Set the baseline, add the SafetyGate rule, gate *warns only* (does not reject) for 10 trials.

Phase 3 (post-observation): Flip warn→reject once baseline noise characterized.

---

## 7. Implications for PromptForge

### 7.1 Explicit diversity coverage in species selection

Currently PromptForge maintains a strategy_store that retrieves past strategies for a given species. Proposal: add a *coverage* term to the retrieval + proposal loop. When proposing a new mutation, penalize proposals whose embedded representation lies inside the top-K densest cluster of already-accepted mutations. This is a cheap reformulation of the diversity goal as a repulsion force on the existing strategy manifold.

### 7.2 Use GEPA more aggressively when base-model diversity stalls

Paper §2.5 implies the LLM-proposer-only path has a ceiling. GEPA's evolutionary operators (crossover, structural rewrite) are not bottlenecked by the LLM's mode collapse in the same way. If diversity metrics (§6) show the mutation stream narrowing trial-over-trial, auto-increase the GEPA share from 30% → 60%. AP-21 decision gate in autopilot handoff is the natural place to wire this.

### 7.3 Temperature ladder is cheap but capped

As an immediate, almost-free mitigation, PromptForge can sample mutations at a ladder of temperatures (T=0.7, 1.0, 1.3) and keep the union. Paper says this recovers *some* but not *all* of the base diversity. Upper bound is low, cost is negligible, so worth doing.

### 7.4 Mutation-knowledge-graph embedding diagnostic

Add a periodic check: compute mean pairwise embedding distance among the last N accepted mutations. Trend = stagnation signal. This is a direct implementation of the paper's distinct-2 metric at the strategy level.

Concrete hook: in `meta_optimizer.py` stagnation detection, alongside the existing acceptance-rate and Pareto-frontier-progress triggers, add a third trigger: *mean_pairwise_embedding_distance over last 20 accepted proposals drops below 0.6 × historical mean*. When this fires, the meta-optimizer should either (a) rebalance species budgets toward GEPA + structural mutations, (b) force temperature ladder for the next N proposals, or (c) invalidate the top-K densest FAISS cluster from strategy retrieval for the next round. The paper does not prescribe which — this is an EPYC-side design decision informed by AR-3 journal data.

### 7.5 Cross-species fertilization and policy diversity

B5 cross-species fertilization (accepted 2026-04-01) already partially helps: NumericSwarm config mutations and StructuralLab flag mutations are not sampled from an LLM policy at all and therefore do not suffer the same mode collapse. The paper's finding strengthens the case that AR-3 should maintain *minimum* budget shares for non-LLM species (NumericSwarm ≥ 20%, StructuralLab ≥ 10%) even when PromptForge is outperforming them in short-horizon acceptance rate, because the non-LLM species are effectively the system's *out-of-policy diversity reserve*.

---

## 8. Experiment Plan — One-Day Diversity Baseline

**Goal**: measure distinct-2, self-BLEU, TTR, predictive entropy for architect_general, architect_coding, coder, worker — the current production stack — on a 20-prompt open-ended subset drawn from our existing suites. Produces the baseline values §6 needs.

### 8.1 Prompt subset selection

- 8 prompts from coding open-spec (e.g., "write a function that…" without a strict test harness)
- 6 prompts from reasoning open-ended (explain-why questions)
- 6 prompts from creative / summarization (rephrase, explain to a beginner)

Avoid closed-answer math and multiple-choice — diversity metrics degenerate.

### 8.2 Sampling protocol

- N=4 completions per prompt (keeps runtime bounded on 30B-A3B and larger)
- T=1.0 (paper's primary condition)
- top_p=0.95
- max_tokens=512 per completion

Total calls: 4 roles × 20 prompts × 4 samples = 320 inference calls. At ~5-15 s each, run time is 30-90 minutes per role, ~3-4 hours total sequentially. Fits in one session.

### 8.3 Metric computation

Implement in `scripts/autopilot/diversity_metrics.py`:

- `predictive_entropy(logprobs_list)` — returns mean per-token entropy
- `distinct_n(completions, n=2)` — returns unique n-grams / total n-grams
- `self_bleu(completions)` — mean BLEU of each vs rest
- `ttr(completions)` — types / tokens over concatenated corpus

Use existing llama.cpp `/completion` endpoint with `n_probs > 0` to recover per-token logprobs for entropy. If n_probs is expensive, approximate entropy with temperature-calibrated sample variance — noisier but workable.

### 8.4 Reporting

One-page summary: 4 roles × 4 metrics matrix + per-prompt variance. Commit to `research/benchmarks/diversity-baseline-2026-04.md`. Use these numbers to populate `autopilot_baseline.yaml` diversity keys.

### 8.5 Acceptance

Experiment is a success if:

1. All 4 roles produce non-degenerate metrics (no NaN / all-identical outputs)
2. Ranking of roles on diversity is stable across 3 seeds of the 20-prompt subset
3. Self-BLEU and distinct-2 correlate in the expected direction (r < -0.5)

If (3) fails on our setup, fall back to distinct-2 + TTR only and drop self-BLEU from the gate.

### 8.6 Follow-on experiments (deferred)

- Repeat at T=0.7 and T=1.3 to measure the temperature-response curve locally. Compare to paper's reported 20-30% recovery ceiling.
- Ablate CoT-suppression on Think-model roles (architect_general when running with `<think>` block vs answer-only). Tests whether paper's §2.4 finding replicates on our stack.
- Compare Q4_K_M vs Q6_K quants of the same model for diversity impact — unclear from paper whether quantization affects diversity, and this matters for our Q4KM-coder decision (feedback_coder_quant_decision).

---

## 9. Risks and Tier 2b Considerations

### 9.1 OLMo 3 specificity

Paper's empirical work is entirely on the OLMo 3 7B family. Three generalization questions:

- Does SFT-dominant narrowing replicate on Qwen3 / Qwen3.5 / Llama-3 families? Plausibly yes (SFT is SFT), but the *magnitude* of each stage's contribution may vary with data mix.
- Do preference-tuned Qwen-Instruct variants collapse more than OLMo-Instruct? No data. Anecdotally, Qwen3-Instruct-7B produces less rigid responses than older OpenChat/Mistral-Instruct families — worth measuring before assuming the Instruct>Think DPO gap is universal.
- Our primary stack includes MoE models (Qwen3-30B-A3B, GLM-4.5). MoE routing could *increase* diversity (different experts activate on different inputs) or *decrease* it (router collapse to a few experts). Paper has no MoE evidence.

### 9.2 Self-BLEU noise

Self-BLEU is length-sensitive. If one checkpoint systematically produces shorter outputs (as conciseness prompting encourages), its self-BLEU will differ for reasons unrelated to genuine diversity. Mitigation in §8.5(3): drop self-BLEU from the SafetyGate if it doesn't correlate with distinct-2 on our stack. Distinct-2 and TTR are more robust.

### 9.3 Predictive entropy calibration

Paper reports predictive entropy using teacher-forced logprobs. On our llama.cpp path, n_probs is a truncated top-K, which biases entropy low. Either: (i) accept the bias as a systematic constant and compare deltas only, or (ii) use token-level sample variance across N completions as a proxy. (i) is cheaper and the signal of interest is always a delta vs baseline — absolute values don't need to match paper's.

### 9.4 Reward-judge dependency in quality-residual decomposition

The quality-vs-residual decomposition needs a reward model to rank base-model completions. We don't have a calibrated RM — using Claude-as-Judge is possible but expensive and slow. Recommendation: skip the decomposition in our integration and track raw diversity metrics only. The paper's decomposition is a diagnostic nuance; our engineering need is "did diversity drop?"

### 9.5 Tier 2b — contradicting evidence not yet checked

Not yet searched for papers arguing diversity *increases* after preference optimization on reasoning tasks, or showing that SFT on long-CoT actually preserves stylistic diversity in the answer. If such work exists, it would nuance §4.3. Flag for follow-on literature sweep.

Specific searches to run on a later pass:

- "DPO diversity preservation" / "entropy-regularized DPO" (there is a line of work adding KL penalties back to preference optimization specifically to avoid policy collapse)
- "SFT data mixture diversity" — mixture-of-experts datasets (e.g., Tulu 3 data) may already correct for some narrowing
- "reasoning model diversity benchmarks" — whether any benchmark explicitly scores reasoning-model variety (as opposed to variety of chat models)

If any of those produces strong counter-evidence, the §6 SafetyGate threshold (-20% distinct-2) should be re-examined before Phase 3 flip from warn to reject.

### 9.6 Metric gaming risk

Once diversity metrics are in the SafetyGate, the autopilot species have an incentive to game them. A PromptForge mutation that makes outputs superficially varied (e.g., injects random filler tokens) could pass the gate while degrading quality. Mitigation: always require diversity metrics to be read *together* with quality — SafetyGate rule should be "reject if diversity drops AND quality is not significantly up," not "reject if diversity drops" unconditionally. This framing is consistent with the paper's quality-vs-residual decomposition: we do not actually care about diversity in isolation, we care about the *residual* (diversity drop beyond what quality filtering justifies).

### 9.7 Inference cost

N=4 completions per prompt on the diversity-probe subset means ~3× extra inference over T0/T1/T2 for that subset only. On a 20-prompt probe this is ~80 extra completions per eval tier. At T1 (100q/5m) this adds maybe 2-3 minutes. At T2 (500q/30m) it adds maybe 10-15 minutes. Acceptable overhead for the information gained, but a budget item — track it after the experiment and revisit if it exceeds 20% of eval wall time.

---

## 10. Cross-References

### Active handoffs touched

- **autopilot-continuous-optimization.md** — adds PromptForge diversity-coverage item (see §7); amends AP-21 GEPA gate (§7.2); adds diversity metrics row to SafetyGate table (§6.4).
- **reasoning-compression.md** — clarifies ceiling of think-strip / conciseness-prompt interventions (§4.3); informs decision on whether to pursue SEAL/FlowSteer weight-touching paths.
- **eval-tower-verification.md** — direct integration target (§6). EvalResult schema change, to_grep_lines update, SafetyGate rule, baseline file.
- **learned-routing-controller.md** — if routing becomes deterministic under collapsed-policy generators, the MLP router's training distribution may be narrower than expected. Not a blocker but worth flagging.

### Wiki articles to update

- **wiki/training-distillation.md** — add a "diversity considerations in post-training" subsection: SFT dominates narrowing on reasoning tracks; DPO dominates on chat tracks; quality-vs-residual decomposition is the right mental model.
- **wiki/autonomous-research.md** — add note that AR-3 / PromptForge is bounded by the base mutation model's policy diversity; mitigations are GEPA, temperature ladder, and mutation-type diversity.
- **wiki/llm-prompting.md** (if present) — add a bullet: inference-time prompting + temperature cannot recover training-time mode collapse; bound expectations accordingly.

### Related intake entries

- **intake-240 / P10 GEPA integration** — GEPA's evolutionary operators are complementary to an LLM mutation proposer's mode-collapsed policy. This deep dive strengthens the case for high GEPA share.
- **intake-378 (branch-heavy CoT hurts generalization)** — independent, but both land on "some post-training artifacts are in weights and can't be prompted away."
- **intake-437 (STOP self-improvement)** — candidate next deep dive; if STOP's self-improvement mechanism also saturates from diversity collapse, same mitigations apply.

### Files / symbols referenced in §6 integration

- `epyc-orchestrator/scripts/autopilot/safety_gate.py` — `EvalResult` dataclass (L44-70), `to_grep_lines()` (L76-117), `Baseline` (L120-143)
- `epyc-orchestrator/scripts/autopilot/eval_tower.py` — `_aggregate()` composes EvalResult; diversity computation hooks here
- `epyc-orchestrator/orchestration/autopilot/autopilot_baseline.yaml` — baseline diversity keys
- `epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` — mutation proposal loop, add coverage-penalty and temperature-ladder hooks (§7)
- `epyc-orchestrator/scripts/autopilot/diversity_metrics.py` — new file per §8.3

---

## 11. Verdict

**Classification**: `worth_investigating` with a direct, low-effort engineering path.

The core claim — post-training collapses output diversity in weights, not format, and the collapse is not recoverable at inference time — is believable (multi-metric agreement, matched-pair decomposition, three-track OLMo design isolates stages). It is directly relevant to three active EPYC concerns: PromptForge mutation stagnation, model-selection criteria, and the ceiling of reasoning-compression format interventions.

**Two concrete engineering actions**:

1. **Add diversity metrics to EvalTower** (§6) — `diversity_entropy`, `diversity_distinct2`, `diversity_self_bleu`, `diversity_ttr` fields on `EvalResult`, emitted through `to_grep_lines()`, gated by a -20% distinct-2 regression rule in SafetyGate. ~2 days of work.
2. **Run the one-day diversity baseline** (§8) on the four production roles to populate the SafetyGate threshold with real numbers instead of guesses.

**Does the eval tower need diversity metrics?** Yes. We currently track quality, speed, cost, reliability, ECE, AUROC, branching density — not diversity. The paper is strong enough evidence that this is a blind spot worth closing before the next major checkpoint swap.

**What this deep dive is *not* claiming**:

- Not claiming post-trained models are worse than base for our use case. For most EPYC workloads (specialist routing, coding, structured reasoning) post-trained policies are clearly better on quality/reliability axes. The point is narrower: *when deciding between two post-trained candidates*, diversity is currently not in the picture, and it should be.
- Not claiming we should revert to base models for any role. The diversity-recovery path is not "use base models" — it is "be aware of the trade when selecting post-trained checkpoints, and use non-LLM species (GEPA, structural) to supply the diversity the LLM cannot generate."
- Not claiming a specific -20% distinct-2 threshold is correct for our stack. That threshold is a starting point; §8's baseline experiment is what validates or revises it.

**Open questions after this deep dive**:

1. Do Qwen3 / Qwen3.5 / Llama-3 families show the same SFT-dominant narrowing as OLMo 3? Answered empirically by §8.
2. Does our Q4_K_M quant add or subtract diversity vs Q6_K? Answered by the deferred §8.6 follow-on.
3. Does an MoE router (30B-A3B, GLM-4.5) offset some of the collapse? Unknown — would require a separate small study.
4. Is there a way to *measure* mutation-proposer diversity cheaply enough to put it on the autopilot dashboard? Yes — §7.4's pairwise embedding distance metric is O(N²) in accepted-mutation count, trivially cheap at N~100.

Log entry for research-evaluation-index and intake index: classified `worth_investigating`, actionable in ~3 days of engineering effort (2 days integration + 1 day baseline experiment). Next deep-dive candidate from the same cluster: whether entropy-regularized DPO / KL-augmented preference optimization meaningfully preserves diversity — relevant if we ever train our own preference-tuned checkpoint.

---

## Tier 2b Contradicting-Evidence Sweep (2026-04-22)

**Goal**: Challenge the five key claims of intake-441 with a literature sweep, particularly the load-bearing claim for EV-8 that **inference-time interventions cannot recover training-time diversity loss**.

### Queries Executed

1. `post-training diversity collapse inference recovery counter-evidence LLM`
2. `temperature sampling top-p diversity recovery RLHF fine-tuned models`
3. `OLMo 3 diversity analysis reproduction post-training 2026`
4. `distinct-2 self-BLEU post-training diversity metric criticism gaming`

### Primary Finding — LOAD-BEARING CLAIM CONTESTED

**Verbalized Sampling (arXiv 2510.01171, Zhang et al., 2025, OpenReview submission 9jQkmGunGo)**:
A training-free, inference-time prompting strategy that asks the aligned model to emit a *distribution* of responses rather than a single response. Reported results:

- Recovers **66.8%** of the base-model diversity gap at inference time (no weight changes, no fine-tuning).
- Delivers **1.6-2.1×** diversity boost in creative writing while preserving task quality.
- Root-cause framing: mode collapse is caused by **typicality bias in preference-annotation data** (humans favor familiar / typical text). Latent diversity is *retained* in weights; it just isn't *surfaced* under standard prompting conventions.

This **directly contradicts the paper's claim #5** — the claim on which EV-8's SafetyGate rule was explicitly conditioned ("you cannot undo SFT-induced mode collapse purely at generation time"). The OLMo 3 paper tested temperature, top-p, and prompt rotation; it did not test a distributional-prompting protocol. Verbalized Sampling is outside the paper's ablation grid and reports a qualitatively different result.

### Secondary Findings — Metric Validity

**Self-BLEU criticism (Alihosseini et al., ACL W19-2311, 2019)**:
Self-BLEU ignores generation quality and fails to match proper divergence metrics; manually-constructed models can outperform real text on BLEU/Self-BLEU, so Self-BLEU alone is not a reliable diversity indicator.

**Form-based metric weakness (arXiv 2506.00514, 2025)**:
Distinct-N and Self-BLEU are surface-level. Form-based metrics show high distributional overlap across genuinely-different output sets; semantic-embedding metrics (Chamfer distance, BERTScore-style) distinguish diversity far better. Concrete implication for EV-8: a mutation injecting lexical filler or simple paraphrase could pass a distinct-2 gate without supplying real semantic variety — the gaming risk is not hypothetical, it is the default behavior of surface-level diversity metrics under adversarial optimization pressure.

### Family Generalization — Untested

**OLMo 3 specificity**: No replication found on Qwen3 / Qwen3.5 / Llama-3, and crucially no MoE coverage. Our production stack runs Qwen3-30B-A3B + GLM-4.5 (both MoE). The claim that "SFT dominates narrowing, DPO dominates on chat" is a single-family datapoint. An MoE router may attenuate or amplify collapse via expert-selection entropy — untested either way.

### Practitioner Counter-Signal (weaker)

2026 sampling-parameter guides (learnprompting, promptingguide.ai, amitray 2026) consistently describe T=0.8-1.2 + top-p=0.8-0.95 as effective diversity levers on aligned models in deployed settings. This is not peer-reviewed, but it is a broad practitioner counter-signal to the paper's "temperature plateaus well short of base" claim.

### Impact on EV-8 (SafetyGate Diversity-Regression Rule)

The EV-8 rule proposed in §6.4 was: **"Reject if distinct-2 drops >20% and self-BLEU rises >0.10 AND quality has not significantly improved"**. The contradicting evidence tempers — but does not invalidate — this design. Concrete amendments:

1. **Do not build EV-8 around the assumption that inference-time recovery is impossible.** If Verbalized Sampling (or something like it) can recover 66.8% of the gap at inference time, then a checkpoint that *appears* to have regressed diversity might just be mis-prompted. EV-8 should (a) evaluate candidate checkpoints with a Verbalized-Sampling-style distributional prompt in addition to the stock prompt, or (b) treat distinct-2 drops as a *signal for further investigation*, not an automatic reject.

2. **Demote Self-BLEU from the composite rule** or require it to agree with an embedding-based semantic-diversity metric before it can contribute to a reject decision. §9.2 already flagged self-BLEU as noise-prone; the ACL 2019 evidence and arXiv 2506.00514 strengthen that flag to "do not gate on self-BLEU alone."

3. **Guard against surface-level gaming**. The composite rule in §9.6 ("reject only if diversity drops AND quality is not up") remains necessary but insufficient. Add a semantic-embedding diversity check (cosine-distance between sentence embeddings of completions) as a secondary signal before rejecting on distinct-2 alone.

4. **Retain the -20% distinct-2 threshold as a warn signal, not a reject signal, until we validate on our own stack**. §6.6 Phase 2 (warn only) becomes more important given the contested evidence. Do not flip to Phase 3 (reject) without first running a replication on Qwen3-30B-A3B and without adding the Verbalized-Sampling evaluation prompt.

5. **MoE-specific validation before trusting any diversity gate on our production checkpoints**. §9.1 already raised this; the Tier 2b sweep did not find a paper that resolves it.

### Amended EV-8 Rule (proposed)

| Check | Trigger | Action |
|-------|---------|--------|
| Diversity regression (warn) | distinct-2 drops >20% on stock prompt | Warn, investigate with Verbalized-Sampling-style distributional prompt |
| Diversity regression (reject) | distinct-2 drops >20% on stock prompt AND distributional-prompt recovery <50% of gap AND semantic-embedding diversity also drops >15% AND quality not up | Reject |

The reject path is now conditioned on multi-signal agreement, not on a single surface metric. This is consistent with the paper's own multi-metric philosophy (§3.3) but strictly stronger because it explicitly tests whether the apparent diversity loss is recoverable at inference time.

### Verdict After Sweep

- The **load-bearing claim is materially contested.** Verbalized Sampling is direct, peer-reviewed counter-evidence that inference-time recovery is possible to a substantial degree. The paper's claim should be downgraded from "inference-time cannot recover" to "stock temperature/nucleus sampling cannot recover — distributional-prompting protocols can."
- EV-8 remains worth building, but the threshold must be **softer on the reject side** and must include an inference-time-recovery probe before rejecting a checkpoint.
- Paper's other claims (SFT-dominant narrowing on Think, DPO-dominant on Instruct, CoT-suppression preserves answer-level diversity, quality-vs-residual decomposition) were **not directly refuted** by the sweep. They remain plausible and actionable for model-selection reporting.

### Follow-on Items (Not Blocking)

- Implement Verbalized Sampling as an eval prompt option in EvalTower (~1 day). Use it as a second reading when a candidate checkpoint triggers the diversity warn.
- Run Verbalized Sampling on our current architect_general / coder / worker to measure the in-stack inference-recovery ceiling — this is a direct replication of the arXiv 2510.01171 result on our models, and it quantifies how much of the OLMo 3 paper's pessimism generalizes to our stack.
- Track Zhang et al. 2025 for reported failure modes — if Verbalized Sampling fails on reasoning-heavy tasks (our Think-track use case), that is a narrower scope for EV-8 reject gating that might still be defensible.

### Files Updated

- `research/intake_index.yaml` — intake-441 `contradicting_evidence` list populated; `tier_2b_status` added; `eval-tower-verification.md` added to cross-referenced handoffs.
- `research/deep-dives/diversity-collapse-posttraining.md` — this section.
