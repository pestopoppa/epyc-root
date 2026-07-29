# Deep Dive: SFT Generalization & Reasoning Pattern Quality

**Covers**: intake-373, intake-374, intake-378
**Date**: 2026-04-15
**Cluster theme**: How reasoning pattern structure determines SFT generalization quality

## The Core Finding

Two papers published days apart (April 2026) converge on a critical insight: **the structure of reasoning patterns in training data matters more than quantity, loss, or even data diversity for SFT generalization**.

| Paper | Key Claim | Evidence |
|-------|-----------|----------|
| intake-374 (Ren et al.) | SFT CAN generalize — failures reflect under-training, not inability | Dip-and-recovery in cross-domain performance |
| intake-378 (Li et al.) | But generalization DEPENDS on reasoning pattern structure | DeepSeek-R1 vs gpt-oss-120b: 21pp gap on Llama3.1-8B despite lower R1 training loss |

Together they say: **SFT generalizes when trained on convergent, deductive reasoning traces. It memorizes when trained on divergent, branch-heavy traces.**

## Quantitative Pattern Taxonomy

From intake-378's analysis using DeepSeek-V3.2 for automated reasoning step annotation:

| Metric | DeepSeek-R1 (bad) | gpt-oss-120b (good) | Delta |
|--------|-------------------|---------------------|-------|
| Propose steps (branching) | 33.3% | 22.5% | +10.8pp |
| Deduce steps (linear forward) | 62.0% | 74.6% | -12.6pp |
| Propose→Propose transition | 0.53 | 0.34 | +0.19 |
| Avg SFT loss (post-training) | 0.2-0.3 | ~0.6 | Paradoxically lower |
| Key token loss (post-training) | 1.533 | 1.784 | Comparable |

**The "dilution effect"**: DeepSeek-R1's lower overall SFT loss comes from a higher proportion of trivial "routine" tokens (e.g., "3 + 2 = 5") that are easily learned. The hard reasoning transitions have comparable difficulty. Low loss is a MISLEADING quality signal.

## Performance Impact (Full Table)

Average across MATH500, AIME24, AIME25, BeyondAIME, HMMT25:

| Student Model | R1 Data (avg) | gpt-oss Data (avg) | Gap |
|---------------|---------------|---------------------|-----|
| Qwen2.5-7B | 49.5% | 54.6% | **+5.1pp** |
| Qwen2.5-32B | 71.5% | 76.3% | **+4.8pp** |
| Llama3.1-8B | 29.5% | 50.5% | **+21.0pp** |
| Qwen3-8B | 57.4% | 62.7% | **+5.3pp** |

The Llama3.1-8B result is extreme — a 21pp gap from the same problem set, same training budget, different reasoning traces.

## Trajectory Filtering: A Zero-Cost Fix

Removing branch-heavy trajectories from DeepSeek-R1 data improves generalization. Two proxy metrics tested:

**Proxy 1**: Difference ratio of reasoning step count (R1 vs gpt-oss for same problem)
**Proxy 2**: Proportion of steps containing branching keywords ("Perhaps", "Another", "Alternatively")

Best results (Qwen2.5-7B, 96k context, Proxy 2 bottom 90%):
- AIME24: 61.7% → 64.9% (+3.2pp)
- BeyondAIME: 27.5% → 33.0% (+5.5pp)
- Average: 54.9% → 58.5% (+3.6pp)

**Critical**: Filtering by branching density ≠ filtering by length. "Trajectories filtered out with our proposed two proxy metrics have a very limited overlap with trajectories filtered out with the length metric."

## Random Step Deletion Validates Redundancy

Deleting 10% of reasoning steps randomly from training data:
- **gpt-oss-120b data**: significant performance drops (each step matters)
- **DeepSeek-R1 data**: minimal/no degradation, sometimes IMPROVEMENTS

This directly validates our Tier 1 reasoning compression approaches (TrimR, short-m@k) — inference-time pruning works because the branching IS redundant.

## Repeated Exposure > Coverage

From intake-374 and independently confirmed by arxiv:2602.11149 (Kopiczko et al.):
- Ren et al.: Repeating 2.5k samples 8x outperforms one-pass 20k under fixed 640-step budget
- Kopiczko et al.: 128 epochs on 400 samples beats 1 epoch on 51,200 samples by **12-26pp** on AIME'24/25

This is counter-intuitive but robust across two independent studies. Token accuracy serves as the saturation indicator.

## Safety Degradation

From intake-374: "Generalization is asymmetric — reasoning improves while safety degrades with long-CoT SFT."

This is mentioned but not quantified with specific benchmark numbers in the available content. It's a red flag for any future fine-tuning work (Doc-to-LoRA, OPSDC self-distillation).

## Relevance to EPYC

### Direct actions

1. **Reasoning compression (handoff)**: The branching-density metrics give us a quantitative tool for evaluating which reasoning traces to compress vs keep. Convergent traces should be preserved; divergent branches are safe to prune.

2. **Trajectory selection for future training**: If we ever use OpenR1-Math-220k data (intake-376), we MUST filter by branching density first. The raw DeepSeek-R1 traces produce worse generalization. Use Proxy 2 (branching keyword proportion) as a filter — it's the simplest effective method.

3. **Routing intelligence**: The branching density of a model's output could serve as a runtime quality signal. High branching = the model is exploring unproductively → escalate or truncate.

4. **Model selection**: The 21pp gap for Llama3.1-8B suggests that model architecture interacts strongly with training data quality. Some architectures are more susceptible to learning surface patterns from branch-heavy data.

### Indirect insights

5. **Doc-to-LoRA**: Safety degradation with reasoning SFT is a concern. Any future adapter training needs safety evaluation alongside capability evaluation.

6. **Eval tower**: The dip-and-recovery pattern means early-training checkpoints look deceptively bad. Evaluation protocols should account for this if we ever evaluate fine-tuned models.

## Referenced Papers Worth Tracking

| arxiv_id | Title | Why |
|----------|-------|-----|
| 2602.11149 | Data Repetition Beats Data Scaling in Long-CoT SFT | Independent confirmation of repeated exposure > coverage |
| 2602.13517 | Think Deep, Not Just Long | Measuring reasoning effort — complements branching density |
| 2601.06002 | Molecular Structure of Thought | Topology of reasoning chains |
| 2512.22255 | Shape of Thought | Distribution of reasoning patterns |
| 2603.07078 | CoTJudger | Graph-driven CoT efficiency evaluation |
