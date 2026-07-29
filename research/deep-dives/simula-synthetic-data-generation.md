# Deep Dive: Simula -- Reasoning-Driven Synthetic Data Generation and Evaluation

**Intake ID**: intake-410
**Paper**: "Reasoning-Driven Synthetic Data Generation and Evaluation" (arxiv:2603.29791)
**Authors**: Tim R. Davidson (EPFL), Benoit Seguin (Google), Enrico Bacis (Google), Cesar Ilharco (Google DeepMind), Hamza Harkous (Google)
**Published**: March 2026, Transactions on Machine Learning Research (TMLR) with J2C Certification
**Blog**: [Google Research blog post](https://research.google/blog/designing-synthetic-datasets-for-the-real-world-mechanism-design-and-reasoning-from-first-principles/) (April 16, 2026)

## Summary

Simula is a reasoning-first, seedless framework for generating and evaluating synthetic datasets at scale. Unlike prior methods that rely on manual prompts, evolutionary algorithms, or seed data from the target distribution, Simula constructs datasets from first principles using an agentic, multi-stage pipeline. The core insight is that synthetic data generation should be treated as **mechanism design** -- independently controlling coverage, complexity, and quality rather than optimizing a single proxy.

The framework was used internally at Google as a data engine for ShieldGemma, FunctionGemma, MedGemma, on-device Gemini safety classifiers, and Android scam detection. The paper evaluates on five diverse domains (CTI cybersecurity, legal reasoning, math, multilingual knowledge) using Gemini 2.5 Flash as teacher and Gemma 3 4B as student, generating up to 512K data points per domain.

Key finding: there is no single "optimal" way to generate synthetic data. The relationship between data properties and downstream performance is deeply idiosyncratic -- high complexity yields +10% accuracy on GSM8k but hurts performance on LEXam where the teacher model is weak. The full Simula system (all axes combined) is almost always the dominant strategy, confirming that mechanism design is non-negotiable.

**Verdict**: Not directly actionable for model training (EPYC has no training GPUs), but contains three highly transferable patterns: (1) double-critic rejection sampling for quality verification, (2) calibrated complexity scoring via Elo for eval difficulty estimation, and (3) taxonomy-based coverage analysis for benchmark construction.

---

## 1. Simula Framework Architecture

Simula decomposes synthetic data generation into four independently controllable axes, implemented as a five-stage pipeline:

### Pipeline Stages

```
Stage 1: Factor Identification
    User provides description y and/or sample data S
    → M3 proposes factors of variation f_i (e.g., "cat type", "story format")
    → Factors accepted/rejected by M3 or human

Stage 2: Taxonomy Generation (Global Diversification)
    For each factor f_i, expand breadth-first into taxonomy T_i of depth d_i
    → Best-of-N proposal: sample N candidate children per node
    → Generator-critic gap: separate M3 refines proposals (add/remove/merge/edit)
    → Optional level planning: M3 generates consistent expansion plan per level
    → Output: hierarchical tree mapping concept space

Stage 3: Taxonomic Sampling + Meta-Prompting (Local Diversification)
    M3 formulates sampling strategies (which taxonomies, what weights)
    → Sample node-sets from taxonomies
    → Convert node-sets to "meta prompts" (scenario descriptions)
    → Generate multiple instantiations per node-set to prevent mode collapse

Stage 4: Complexification
    Configurable fraction c (default 0.5) of meta prompts undergo complexity increase
    → M3 refines prompts to be more elaborate/difficult
    → Orthogonal to coverage -- shifts difficulty distribution without changing semantics

Stage 5: Quality Checks (Double-Critic + Critiquing)
    Point-wise semantic/syntactic requirement checks
    → Double-critic rejection sampling (see Section 2)
    → Failed samples: reject or auto-modify + re-critique
```

### System Versions (Ablation Configurations)

| Configuration | Taxonomy Depth | Meta Prompting | Critic Steps |
|---|---|---|---|
| Baseline | 1 (top-level only) | No | No |
| Local | 1 | Yes | No |
| Global | >1 (full depth) | No | No |
| Local + Global | >1 | Yes | No |
| Full System (L+G+C) | >1 | Yes | Yes |

The Baseline requires up to 5x fewer inference calls per data point than the Full System. Despite the cost difference, the Full System produces higher-performing data at every tested scale, making the cheaper baseline more expensive over the full data lifecycle (training costs dominate generation costs).

### Key Design Properties

- **Seedless**: No seed data from the target distribution required. Generation starts from a text description.
- **Agentic**: Each stage uses reasoning models (M3) with structured prompting, not fixed templates.
- **Future-proof**: Generation quality scales naturally with the reasoning capabilities of the underlying M3.
- **Auditable**: Every data point traces back to taxonomy nodes, meta-prompts, and critic decisions -- full provenance chain.

---

## 2. Double-Critic Rejection Sampling

The double-critic is the most technically novel quality control mechanism in Simula. It addresses a fundamental problem: LLMs exhibit **sycophancy bias** when asked to verify their own outputs, tending to agree with plausible-sounding answers.

### Mechanism

Instead of asking a single question ("Is this answer correct?"), the double-critic independently queries two assessments:

```
Critic 1: "Is this answer CORRECT?"     → p(correct | x, y)
Critic 2: "Is this answer INCORRECT?"   → p(incorrect | x, y)

Accept if: Critic 1 says YES and Critic 2 says NO
Reject otherwise (disagreement triggers rejection or auto-repair)
```

The independence is critical: a sycophantic model might say "yes" to both "is this correct?" and "is this incorrect?" -- the disagreement itself becomes the rejection signal.

### Mathematical Framework

Let:
- `mu_gen` = model's generative baseline accuracy
- `p(y)` = probability of critic accepting a correct answer
- `p(y_corrupt)` = probability of critic accepting an incorrect answer

The accepted proportion after critic filtering:

```
|D_accept| = mu_gen * p(y) + (1 - mu_gen) * p(y_corrupt)
```

The expected accuracy of the accepted subset:

```
E[mu_critic] = mu_gen * p(y) / |D_accept|
```

A positive "lift" exists whenever `E[mu_critic] > mu_gen`, which requires `p(y) > p(y_corrupt)` -- the critic must be better at accepting correct answers than incorrect ones.

### Empirical Results (MATH Dataset)

The paper evaluates in two settings:

**Controlled Setting** (causal intervention -- correct vs. deliberately corrupted answers):
- Consistent theoretical lift across all complexity levels
- Rejection cost increases with task complexity (harder problems require more rejections)
- The critic reliably distinguishes correct from subtly corrupted answers

**Empirical Setting** (critic filtering the model's own generated outputs):
- Lift transfers but with reduced effectiveness vs. controlled setting
- Higher complexity necessitates higher empirical rejection rates to sustain accuracy gains
- Rejected samples have systematically higher model-perceived complexity (Elo scores)

### Rejection Rates by Dataset

| Dataset | Critic Rejection Rate | Teacher Accuracy | Notes |
|---|---|---|---|
| CTI-MCQ | 2% | High | Minimal filtering needed |
| Global MMLU | 3% | High | Small rejection, significant downstream improvement |
| CTI-RCM | 9% | 70% | Moderate filtering |
| GSM8k | 9% | 88% | Moderate filtering |
| LEXam | **61%** | 57% | Massive rejection -- weak teacher produces mostly wrong answers |

The LEXam result is a critical cautionary finding: when the teacher model is weak on a domain (57% accuracy), the double-critic rejects the majority of generated data. This is actually **correct behavior** -- the critic is catching the teacher's errors -- but it means the pipeline becomes extremely inefficient for domains where the teacher lacks competence.

---

## 3. Calibrated Complexity Scoring

Simula introduces a reasoning-based complexity metric that assigns chess-style Elo ratings to individual data points, enabling cross-dataset complexity comparisons.

### Algorithm

```
1. Sample batches of data points, each point appearing K times across batches
2. Within each batch: M3 assigns complexity scores using pairwise comparisons
3. Break batch-level scores into pairwise comparisons
4. Compute Elo ratings across all pairwise outcomes
5. Result: per-sample Elo complexity score, calibrated across datasets
```

### Why Batch-Wise?

Per-sample scoring suffers from overconfidence -- the model assigns absolute scores without calibration context. By providing a batch of items to score together, the model calibrates relative to the batch members, producing more consistent rankings. The Elo aggregation across multiple batch appearances further reduces noise.

### Validation

- Model-assigned Elo scores **align with human-annotated complexity labels** on MATH (5-level difficulty) and Global MMLU (education levels: elementary, high school, college)
- Stratified by human complexity level, rejected samples have higher Elo scores than accepted ones -- the critic systematically filters samples the model perceives as harder
- Different datasets exhibit distinctly different complexity profiles: GSM8k/CTI span wide ranges; LEXam is concentrated (correlating with teacher weakness)

---

## 4. Ablation Analysis: Component Contributions

### Taxonomy Quality (Table 2)

| Method | Grounded: Completeness | Grounded: Soundness | Conceptual: Completeness | Conceptual: Soundness | Novelty | Coverage |
|---|---|---|---|---|---|---|
| Simula | 0.74 | 0.75 | 0.78 | 0.97 | 0.94 | **1.72** |
| 0-Shot | 0.52 | 0.70 | 0.50 | 0.97 | 0.32 | 0.83 |

Key insight: the generator-critic refinement loop nearly doubles coverage (1.72 vs 0.83) while maintaining soundness. The "novelty" score of 0.94 means the M3-generated taxonomies contain almost as many relevant nodes NOT in the expert taxonomy as the expert taxonomy has nodes itself -- the M3 discovers edge cases humans missed.

### Intrinsic Diversity (Figure 4)

- **Global diversification** (deep taxonomy sampling) is the primary driver of dataset-wide embedding diversity
- **Local diversification** (meta-prompting) primarily increases nearest-neighbor diversity (within-cluster variation)
- The two are **additive** -- combining them yields both global coverage and local variation
- Real data can match or exceed synthetic data on embedding-based diversity but **almost always has lower taxonomic coverage** at deeper levels
- Critiquing does not significantly affect diversity metrics

### Intrinsic Complexity (Figure 5)

- The full Simula system covers the **entire complexity range** of real data, often generating more complex items
- Local and Global components provide **different types of complexity** (additive)
- Diversity and critiquing can reduce complexity on some datasets (GSM8k) -- removing incorrect complex items shifts the distribution

### Downstream Performance (Figure 6)

Each component's contribution depends on dataset and scale:

| Finding | Evidence |
|---|---|
| Full System never hurts | Dominant strategy across all 5 datasets and all data sizes |
| Baseline scales worst | Data-scaling law is a function of data properties, not size alone |
| Student-teacher gap matters | CTI-RCM saturates at 128k bridging ~83% of gap; GSM8k keeps growing |
| Global alone insufficient | No better than Baseline on LEXam; slightly worse scaling on GSM8k |
| Local alone insufficient | Plateaus before Global variants on CTI-MCQ; weak in small-data regime for CTI-RCM |
| Combined L+G critical | Improved performance on all datasets and all sizes |
| Critic impact varies | Significant on Global MMLU despite only 3% rejection; no significant change on other datasets |

### Complexity-Performance Relationship (Figure 7)

| Dataset | High Complexity Effect | Low Complexity Effect | Explanation |
|---|---|---|---|
| GSM8k | **+10% accuracy** at 64k | Poor scaling | Strong teacher (88%) produces reliable complex data |
| CTI-MCQ | Better scaling | Negligible scaling | Complex examples drive learning |
| LEXam | **Hurts performance** | Only split that improves | Weak teacher (57%) produces wrong complex answers |
| CTI-RCM | Mixed | Mixed | Moderate teacher gap |

This is the paper's most important negative result: **complexity is not universally beneficial**. When the teacher model is weak on a domain, complex synthetic data is counterproductive because the teacher gets the complex answers wrong, teaching the student incorrect reasoning.

---

## 5. Limitations and Failure Modes

### LEXam Weak Teacher Problem

The clearest failure mode: Gemini 2.5 Flash achieves only 57% accuracy on LEXam (Swiss/EU legal reasoning). Consequences cascade through the pipeline:
- Double-critic rejection rate: 61% (majority of generated data rejected)
- High-complexity data hurts downstream performance
- Only low-complexity split shows improvement with scale
- Student model cannot exceed teacher's knowledge ceiling

**Implication**: Simula is a knowledge distillation framework at its core. It cannot create knowledge that the teacher does not have.

### Complexity-Performance Inversions

As documented in Figure 7, high complexity data degrades performance when:
- Teacher accuracy on the domain is low
- The domain requires specialized knowledge the teacher lacks
- Complex examples amplify teacher errors (wrong reasoning chains on hard problems)

### Student-Teacher Saturation

Performance saturates when the student approaches the teacher's accuracy ceiling. CTI-RCM saturates at ~65% student accuracy vs 70% teacher (bridging 83% of the gap at 128k samples). Beyond this point, more data yields diminishing returns regardless of quality.

### Single Teacher Family Limitation

All experiments use Gemini 2.5 Flash as teacher. The paper acknowledges but does not test:
- Multi-teacher ensembles for broader knowledge coverage
- Cross-family distillation effects
- Whether findings transfer across different model architectures

### Intrinsic Metric Limitations

Embedding-based cosine distance provides "coarse" signals with "limited actionable insights." The paper's own taxonomic coverage and Elo complexity metrics are improvements but still proxy measures. The fundamental disconnect between intrinsic data quality and downstream utility remains unresolved.

### Cost-Quality Tradeoffs

The full Simula system requires up to 5x more inference calls per data point than the Baseline. The paper argues this is justified by lifecycle costs (training is more expensive than generation), but this creates a significant barrier for:
- Low-budget deployments
- Domains requiring very large datasets (the 512K ceiling was already expensive)
- Iterative experimentation where fast turnaround matters

---

## 6. Related Work Positioning

### vs. Self-Instruct (Wang et al., 2022)

Self-Instruct generates instructions from a seed set using an LLM, then generates instances. Simula differs fundamentally:
- **Seedless**: No seed data required (Self-Instruct requires 175 seed tasks)
- **Coverage-aware**: Taxonomies ensure systematic domain coverage; Self-Instruct relies on random sampling and diversity heuristics
- **Multi-axis control**: Simula separates diversity, complexity, and quality; Self-Instruct conflates them

### vs. Evol-Instruct / WizardLM (Xu et al., 2023)

Evol-Instruct applies evolutionary mutations (deepening, broadening, concretization) to instructions. Simula critique:
- Evolutionary steps are "opaque" -- no audit trail explaining why a mutation was applied
- Lacks global coverage planning -- evolved instructions cluster around seed distribution modes
- No principled complexity control -- difficulty is a side-effect of evolution, not an independent axis
- Simula's complexification is explicit and configurable (fraction c = 0.5)

### vs. GLAN (Li et al., 2024)

GLAN (Generalized Instruction Tuning via Taxonomy) is closest to Simula's taxonomy approach. Key differences:
- Simula uses reasoning-driven taxonomy generation with generator-critic refinement; GLAN uses a simpler taxonomy but with human-curated fields
- Simula adds double-critic quality filtering; GLAN does not include rejection sampling
- Simula provides calibrated complexity metrics; GLAN does not address complexity evaluation
- Both are seedless and taxonomy-based -- GLAN is a plausible precursor

### vs. GEPA (intake-327 / intake-240)

GEPA is a prompt optimization algorithm (Genetic-Pareto evolution), not a data generation framework. The relationship is orthogonal:
- GEPA optimizes prompts for a fixed task given eval data
- Simula generates the eval/training data itself
- Simula's taxonomy generation could theoretically use GEPA for optimizing the M3 prompts at each stage
- Both share the "no seed data" philosophy but operate at different levels (meta-prompts vs task prompts)

### vs. Arena Learning / Self-Play Approaches

Arena Learning and self-play methods generate data through model competition. Simula differs:
- No competitive dynamic -- single teacher generates all data
- Explicit coverage control via taxonomies rather than emergent diversity from competition
- More controllable but potentially less creative than adversarial generation

---

## 7. Key Findings for Mechanism Design

The paper distills several principles from its extensive experiments:

1. **No silver bullet**: Optimal data properties are idiosyncratic to domain, model, task, and scale. Systems must be flexible.

2. **Mechanism design is non-negotiable**: Across all domains, the full system (controlling all axes) outperformed simpler baselines. Cutting corners on generation mechanism costs more in downstream performance than it saves in generation cost.

3. **Quality > Quantity**: Better data scales better. Simula achieves higher downstream performance with fewer samples than baseline approaches. The data-scaling law is a function of data properties, not size alone.

4. **Complexity requires calibration**: High complexity helps when the teacher is competent (+10% on GSM8k) but hurts when the teacher is weak (LEXam). The right complexity level is teacher-dependent.

5. **Evaluation is multi-faceted**: Embedding cosine distance is too coarse. Taxonomic coverage and Elo-calibrated complexity provide more actionable signals, but the fundamental challenge of disconnecting intrinsic quality from downstream utility remains open.

6. **Audit trails matter**: Transparent generation enables post-hoc analysis of what worked and why, supporting iterative improvement.

---

## 8. EPYC Applicability

Although EPYC does not train models (no training GPUs), several Simula components map directly to EPYC's inference-time evaluation, quality scoring, and benchmark construction infrastructure.

### 8.1 Double-Critic Pattern for Q-Scorer

**Simula component**: Double-critic rejection sampling (independent correctness/incorrectness assessment)
**EPYC target**: `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`

The Q-Scorer currently uses Claude-as-Judge with a single assessment pass for graded rewards. The double-critic pattern could strengthen this:

```
Current Q-Scorer:
    "Rate this response quality" → single score

Double-Critic Q-Scorer:
    Critic 1: "Did this response correctly address the task?" → p(correct)
    Critic 2: "Is there an error in this response?"          → p(incorrect)
    Accept quality score only when critics agree
    Flag for review when critics disagree (sycophancy detection)
```

This is deployable today: it requires only prompt changes to the judge model, no architecture changes. The cost is 2x judge inference per scored item, but the Q-Scorer already runs asynchronously off the critical path.

**Concrete implementation**: Modify `StagedQScorer` to run dual assessment prompts, computing agreement rate as a confidence signal alongside the quality score. Disagreement rate per model would also serve as a calibration metric for model reliability.

### 8.2 Calibrated Complexity Scoring for Benchmark Construction

**Simula component**: Batch-wise pairwise Elo complexity scoring
**EPYC target**: `epyc-inference-research/docs/chapters/06-benchmarking-framework.md`, benchmark question generation

EPYC's ch07 benchmark philosophy emphasizes difficulty-stratified evaluation. Simula's Elo complexity scoring provides a principled method:

1. **Eval question difficulty estimation**: For any benchmark suite, batch-score questions using an LLM, compute pairwise Elo ratings, and stratify by difficulty band. This replaces ad-hoc difficulty labels with calibrated, model-relative scores.

2. **Cross-benchmark comparison**: Elo scores are calibrated across datasets -- a difficulty-500 question on GSM8k is comparable to a difficulty-500 question on CTI-MCQ. This enables cross-domain difficulty normalization for the autopilot eval tower.

3. **Adaptive evaluation**: Use Elo difficulty bands to implement adaptive testing -- start with medium difficulty, escalate/de-escalate based on model performance, reducing total eval tokens needed.

**Implementation path**: Create a `complexity_scorer.py` utility in `epyc-inference-research/scripts/benchmark/` that:
- Takes a benchmark question set as input
- Runs batch-wise pairwise scoring through a local LLM
- Outputs per-question Elo complexity ratings
- Generates difficulty-stratified subsets for targeted evaluation

### 8.3 Taxonomy-Based Coverage for Synthetic Eval Generation

**Simula component**: Taxonomy generation + taxonomic coverage metrics (Level Ratio Coverage)
**EPYC target**: Benchmark construction, eval question generation for specialized domains

EPYC currently constructs eval sets manually or semi-manually. Simula's taxonomy approach offers systematic coverage:

1. **Domain taxonomy generation**: For any eval domain (coding, math, reasoning, tool use), generate a deep taxonomy of the concept space using a local model.

2. **Coverage gap analysis**: Map existing eval questions to taxonomy nodes. Compute Level Ratio Coverage to identify which sub-domains are over/under-represented.

3. **Targeted question generation**: Generate eval questions specifically for under-covered taxonomy nodes, ensuring comprehensive domain coverage.

4. **Seeder integration**: The taxonomy structure could inform the specialist routing seeder (`seed_specialist_routing.py`) by providing structured domain maps for generating routing evaluation data.

### 8.4 Complexity-Aware Routing Decisions

**Simula component**: Complexity-performance relationship (Figure 7 findings)
**EPYC target**: Routing classifier, model selection

Simula's finding that complexity interacts with teacher competence translates to routing: a model's optimal complexity band is bounded by its competence. For the routing classifier:

- Route high-complexity queries to the strongest available model (architect)
- Route low-complexity queries to the cheapest model (worker/draft)
- Use Elo complexity scores as features for the MLP routing classifier (intake-driven, Phase 1 done with 92% val accuracy)

### 8.5 Mechanism Design Philosophy for Autopilot Eval Tower

**Simula component**: "No silver bullet" principle, context-dependent optimization
**EPYC target**: Autopilot evaluation pipeline (`epyc-orchestrator/scripts/autopilot/`)

Simula's core finding -- that optimal data properties are domain/model/scale-dependent -- directly applies to eval tower design:

- Different models need different eval distributions (complexity, diversity, coverage)
- Eval results on one difficulty band may not predict performance on another
- The eval tower should separately control and report on diversity, complexity, and quality metrics rather than a single aggregate score

### Summary: Transferable Components

| Simula Component | EPYC Target | Effort | Impact |
|---|---|---|---|
| Double-critic rejection sampling | Q-Scorer quality verification | Low (prompt changes) | Medium -- reduces sycophancy in judge |
| Calibrated Elo complexity scoring | Benchmark difficulty estimation | Medium (new utility) | High -- principled difficulty stratification |
| Taxonomy-based coverage | Eval question generation | Medium (new workflow) | High -- systematic coverage gaps |
| Complexity-performance insight | Routing classifier features | Low (insight, no code) | Medium -- informs routing thresholds |
| Mechanism design principles | Autopilot eval tower design | Low (design insight) | Medium -- multi-axis evaluation |

### What Is NOT Transferable

- **Downstream fine-tuning pipeline**: EPYC has no training GPUs. The SFT/LoRA distillation workflow is not applicable.
- **Data generation at scale**: Generating 512K synthetic samples requires significant inference budget. Useful only for targeted eval set construction (hundreds to low thousands), not bulk data generation.
- **Student-teacher distillation loop**: EPYC runs inference, not training. The teacher->student knowledge transfer is irrelevant.
- **Multi-modal extension**: Paper is text-only but mentions multimodal potential. EPYC is text-only inference.
