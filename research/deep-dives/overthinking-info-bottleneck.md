# Deep Dive: Overthinking Analysis + Information Bottleneck Theory

**Papers analyzed:**
- intake-130: "Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs" (arxiv:2412.21187)
- intake-133: "Reasoning as Compression: Unifying Budget Forcing via the Conditional Information Bottleneck" (arxiv:2603.08462)

**Date**: 2026-03-15

---

## 1. Paper 1: Overthinking in o1-Like LLMs (Chen et al., 2024)

### 1.1 Problem Statement

Reasoning LLMs (o1, DeepSeek-R1, QwQ) allocate computational resources
inversely to problem difficulty. On trivially easy problems like "2+3=?",
QwQ-32B generates 901 tokens and 13 redundant solution attempts, consuming
1,953% more tokens than a conventional model. This is not just wasteful --
later solution rounds introduce minimal reasoning diversity and occasionally
flip correct answers to wrong ones.

### 1.2 Efficiency Metrics

Two formal metrics are introduced. These are the first standardized measures
for evaluating reasoning compute allocation.

**Outcome Efficiency** (xi_O):

```
xi_O = (1/N) * sum_{i=1}^{N} sigma_i * (T_hat_i / T_i)
```

Where:
- N = number of test instances
- sigma_i = 1 if instance i is answered correctly, 0 otherwise
- T_hat_i = tokens up to (and including) the first correct answer
- T_i = total tokens generated for instance i

Interpretation: What fraction of generated tokens actually contributed to
reaching the correct answer? For "2+3=?", xi_O = 39/901 = 4.3%. This means
95.7% of compute was pure waste.

**Process Efficiency** (xi_P):

```
xi_P = (1/N) * sum_{i=1}^{N} (D_i / T_i)
```

Where:
- D_i = sum of tokens in distinct (non-redundant) solutions
- Distinctness is measured via GPT-4o clustering of solution strategies

Interpretation: What fraction of tokens explored genuinely novel reasoning
paths? Even for wrong answers, diverse exploration has value; repeated
identical strategies do not.

### 1.3 Key Empirical Results

**Solution distribution across difficulty levels (QwQ-32B-Preview):**

| Dataset   | Difficulty | Avg Solutions | Avg Tokens | xi_O   | xi_P   |
|-----------|-----------|---------------|------------|--------|--------|
| ASDIV     | Trivial    | 3.5           | 741.8      | 41.9%  | 59.8%  |
| GSM8K     | Easy       | 3.1           | 580.2      | 55.7%  | 67.3%  |
| MATH500   | Medium     | 3.2           | 2,407.9    | 52.3%  | 71.2%  |
| GPQA      | Hard       | 2.3           | 2,508.4    | 44.1%  | 63.5%  |
| AIME24    | Very Hard  | 2.1           | 6,023.7    | 32.8%  | 58.4%  |

Critical finding: **92% of correct answers appear in the first solution
round**, which comprises less than 60% of total tokens. Solution round 4+
has 11.5% lower distinctness ratio than round 3 -- later rounds are mostly
restating what was already tried.

**Inverse effort allocation within MATH500:**
- Levels 1-2 (easy): 3.7 solution rounds on average
- Levels 4-5 (hard): 3.0 solution rounds on average

Easier problems trigger MORE reasoning iterations, not fewer. This is the
core pathology.

### 1.4 Mitigation Strategies

**Self-training pipeline:**
1. Generate 10 samples per problem at temperature 1.0 using PRM12K dataset
2. Construct preference pairs: shortest correct response (positive) vs
   longest correct response (negative)
3. Train with SimPO (chosen over SFT, DPO, RPO as most effective)

**Response simplification strategies:**
- **First-Correct Solution (FCS):** Keep only the earliest correct solution.
  Achieves 99.5% outcome efficiency but hurts accuracy on hard problems
  (AIME drops from 46.7% to 36.7%).
- **FCS+Reflection:** Keep first correct + one additional diverse correct
  solution. Best balance: 80% outcome efficiency, 89.5% process efficiency,
  only -0.2% accuracy on MATH500.
- **Greedily Diverse Solutions:** Preserve solutions that introduce novel
  reasoning strategies (measured by distinctness ratio > threshold).

**Results after SimPO with FCS+Reflection on QwQ-32B:**

| Testset | Vanilla Acc | Trained Acc | Vanilla Tokens | Trained Tokens | Reduction |
|---------|------------|-------------|----------------|----------------|-----------|
| MATH500 | 93.0%      | 92.8%       | 2,407.9        | 1,330.7        | -44.7%    |
| GSM8K   | 95.8%      | 96.0%       | 575.5          | 416.6          | -27.6%    |
| GPQA    | 56.6%      | 59.1%       | 3,318.7        | 2,085.7        | -37.1%    |
| AIME24  | 46.7%      | 43.3%       | 9,456.8        | 5,154.5        | -45.5%    |
| ASDIV   | 96.4%      | 96.8%       | 731.5          | 381.6          | -47.8%    |

The AIME24 result is notable: 3.4pp accuracy drop at frontier difficulty.
This confirms OPSDC's finding that compression harms the hardest problems.

### 1.5 Distinctness Ratio Decay

Measured via GPT-4o semantic clustering of solution strategies:

- Solution #1: 100% distinct (by definition)
- Solution #2: ~75% distinct
- Solution #3: ~62% distinct
- Solution #4+: ~51% distinct (11.5% drop from #3)

After ~3 solutions, additional reasoning rounds are overwhelmingly
redundant. This is the empirical ceiling for useful "thinking time."


---

## 2. Paper 2: Reasoning as Compression (Massoli, Kuzmin, Behboodi, 2026)

### 2.1 Theoretical Framework

This paper provides the information-theoretic foundation that explains WHY
the overthinking phenomenon exists and HOW to address it principally.

**Core insight:** Chain-of-thought reasoning is a lossy compression problem.
The reasoning trace Z should contain only the information about the response
Y that is not directly accessible from the prompt X. Any information in Z
that duplicates what the prompt already provides is waste.

**The Attention Paradox:** Standard Information Bottleneck (IB) theory
assumes a Markov chain Y <-> X <-> Z, but transformer decoders violate this
because attention operates over both the prompt and the reasoning trace
simultaneously. The prompt X is not "forgotten" when generating Z -- it
remains in context.

**Resolution via Conditional Information Bottleneck (CIB):**

The optimization objective becomes:

```
max I(Z; Y | X)  -  beta * I(X; Z)
```

Where:
- I(Z; Y | X) = sufficiency: how much the reasoning trace helps predict the
  answer BEYOND what the prompt already tells us
- I(X; Z) = minimality: how much redundant information from the prompt leaks
  into the reasoning trace
- beta = tradeoff parameter controlling compression aggressiveness

**Key theoretical contributions:**

**Proposition 4.1:** Linear length penalties (e.g., penalize by total token
count) correspond to CIB with a uniform vocabulary prior -- implicitly
assuming all tokens carry equal information. This is demonstrably suboptimal
because filler tokens ("Let me think about this...") and essential reasoning
tokens ("Therefore x = 3 by substitution") have vastly different
information content.

**Proposition 4.2:** Target-length penalties (e.g., LCPO's "generate within
N tokens") correspond to CIB with an implicit Laplace distribution over
sequence lengths. Better than linear, but still ignores per-token semantics.

These propositions formally unify all prior budget-forcing methods under one
framework, showing they are special cases of CIB with increasingly crude
approximations to the ideal prior.

### 2.2 Semantic Token Cost

Instead of counting tokens uniformly, the paper assigns semantic cost via
surprisal under a frozen language model prior Q_phi:

```
cost(z_t) = -log Q_phi(z_t | z_{<t})
```

Low surprisal = predictable filler (e.g., "Let me reconsider", "So we
have"). High surprisal = novel information (e.g., a new equation, a key
insight). The compression objective naturally targets the low-surprisal
tokens for elimination while preserving high-information content.

### 2.3 Training Method

**Reward function for GRPO (Group Relative Policy Optimization):**

```
R(X, Y, Z) = r_acc(X, Y, Z) + beta * r_min(X, Z)
```

Where:
- r_acc = 1 if answer correct, 0 otherwise (binary accuracy reward)
- r_min = sum_t log Q_phi(z_t | z_{<t}) (cumulative surprisal cost -- note
  this is NEGATIVE, penalizing verbose outputs)
- beta controls the accuracy-compression tradeoff

Training uses:
- GRPO with group size 16
- Frozen Qwen2.5-Base (1.5B or 7B) as the prior Q_phi
- DeepScaleR (DLER) checkpoints as initialization
- Prior is used ONLY during training; zero inference overhead

### 2.4 Key Numerical Results

**DLER-1.5B experiments:**

| Method          | MATH500 | AIME24 | Avg Acc | Token Reduction |
|-----------------|---------|--------|---------|-----------------|
| DLER-1.5B base  | 84.4%   | 26.7%  | 43.7%   | 0%              |
| CIB (1.5B, B-)  | 85.6%   | 28.3%  | 45.1%   | -6%             |
| CIB (1.5B, B+)  | 84.8%   | 27.2%  | 44.5%   | -7%             |
| CIB (7B, B+)    | 82.2%   | 25.0%  | 42.5%   | -38%            |

**DLER-7B experiments:**

| Method          | MATH500 | AIME24 | Avg Acc | Token Reduction |
|-----------------|---------|--------|---------|-----------------|
| DLER-7B base    | 94.8%   | 53.3%  | 54.2%   | 0%              |
| CIB (7B, B-)    | 94.0%   | 49.4%  | 53.5%   | -8%             |
| CIB (7B, B+)    | 92.2%   | 48.3%  | 52.9%   | -32%            |

**Comparison with baselines (DLER-7B):**

| Method     | Avg Acc | Token Reduction | Pareto Optimal? |
|------------|---------|-----------------|-----------------|
| L1-Exact   | 51.5%   | -29%            | No              |
| L3L1       | 39.7%   | -65%            | No (5% acc drop)|
| CIB (B-)   | 53.5%   | -8%             | Yes             |
| CIB (B+)   | 52.9%   | -32%            | Yes             |

CIB dominates the Pareto frontier: it achieves better accuracy than L1-Exact
at greater compression, and vastly better accuracy than L3L1 at moderate
compression.

### 2.5 Information Density Analysis

The paper measures token-wise surprisal -log p(z_t | z_{<t}, x) across
reasoning traces:

- **Baseline models:** Information density valleys at ~0.1 nats (predictable
  filler tokens -- "Let me verify", "OK so", "Hmm let me reconsider")
- **CIB-trained models:** Information floor raised to >=0.2 nats

This confirms the compression mechanism: CIB eliminates low-information
tokens while preserving high-information reasoning steps. The 0.2 nat floor
means every retained token carries at least 0.2 nats of information about
the answer.

### 2.6 Three Compression Mechanisms

Analysis of what CIB actually removes reveals three distinct patterns:

1. **Algorithmic generalization:** Model discovers mathematically superior
   solution paths (e.g., using trigonometric identities instead of
   brute-force coordinate computation). The compressed trace is not just
   shorter but more elegant.

2. **Elimination of exploration bloat:** Removes trial-and-error loops,
   self-verification tautologies ("Let me check: yes, that's right"), and
   redundant re-derivations. This directly targets the "Solution #4+"
   waste identified in Paper 1.

3. **Syntactic noise filtering:** Strips conversational scaffolding ("OK,
   so the next step would be to...") while preserving computational logic.
   These are precisely the low-surprisal tokens the semantic prior
   identifies.


---

## 3. Synthesis: How the Papers Connect

### 3.1 Paper 1 diagnoses; Paper 2 prescribes

Paper 1 establishes the empirical facts:
- Reasoning models waste 50-70% of tokens on redundant computation
- 92% of correct answers appear in the first solution round
- Easy problems suffer MORE from overthinking than hard ones
- Distinctness ratio decays rapidly after solution #3

Paper 2 provides the theoretical explanation:
- Wasted tokens have low surprisal under a language model prior
- The Information Bottleneck framework defines the optimal compression
- Linear token penalties (like our current flat cap) are provably suboptimal
- A semantic prior yields Pareto-dominant compression

### 3.2 The difficulty-adaptation connection

Both papers converge on the same finding from different angles:

**Paper 1 (empirical):** Easy problems get 47.8% token reduction vs only
45.5% for AIME (hard), but hard-problem accuracy drops 3.4pp while easy
accuracy is unchanged or improves.

**Paper 2 (theoretical):** The CIB objective naturally compresses more on
easy problems because:
- Easy problems have lower I(Z; Y | X) -- the answer is more accessible
  from the prompt alone
- The accuracy reward r_acc fires frequently (easy problems are usually
  correct), so compression penalty dominates
- Hard problems have higher I(Z; Y | X) -- the reasoning trace carries
  genuine information the prompt doesn't provide

This validates the difficulty-adaptive approach: reasoning budgets SHOULD
scale with difficulty. A flat token cap is a uniform prior -- Proposition 4.1
tells us this is the least efficient choice.

### 3.3 What "optimal" looks like

Combining both papers, the optimal reasoning budget allocation would:

1. **Measure per-token information content** (surprisal against a reference
   model) -- this identifies waste in real time
2. **Scale the reasoning budget with problem difficulty** -- easy problems
   get tight budgets, hard problems get loose ones
3. **Stop after the first correct solution** for easy problems, but allow
   2-3 diverse attempts for hard problems
4. **Never exceed 3 solution rounds** -- distinctness ratio data shows
   diminishing returns plateau at round 3


---

## 4. EPYC Integration Path

### 4.1 Current State

Our REPL token budget system:

| Component | Current Value | Source |
|-----------|--------------|--------|
| `_repl_turn_token_cap()` | 5000 tokens | `ORCHESTRATOR_REPL_TURN_N_TOKENS` env var |
| `_frontdoor_repl_non_tool_token_cap()` | 5000 tokens | `ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS` |
| Difficulty classifier | shadow mode | `difficulty_signal.py` (3 bands: easy/medium/hard) |
| Band thresholds | easy < 0.3, hard >= 0.6 | `classifier_config.yaml` |

The current 5000-token flat cap is exactly the "uniform prior" that
Proposition 4.1 proves is suboptimal.

### 4.2 Proposed: Difficulty-Adaptive Token Budgets

Using Paper 1's efficiency data to derive per-band budgets:

**Derivation from outcome efficiency data:**
- Easy problems (ASDIV/GSM8K): xi_O ~50%, meaning ~50% of tokens are waste.
  First-correct-solution tokens average ~280 for ASDIV, ~330 for GSM8K.
  Safe budget: 1500 tokens (4-5x first-correct, covers diverse exploration).
- Medium problems (MATH500): xi_O ~52%, first-correct averages ~1,200 tokens.
  Safe budget: 3500 tokens (~3x first-correct).
- Hard problems (GPQA/AIME): xi_O ~35-40%, first-correct averages ~2,000+.
  Safe budget: 7000 tokens (3.5x first-correct, allows 2-3 diverse attempts).

**Proposed configuration:**

```yaml
difficulty_signal:
  mode: enforce
  token_budgets:
    easy: 1500    # ~3x reduction from current 5000
    medium: 3500  # ~1.4x reduction
    hard: 7000    # 1.4x increase -- hard problems were UNDER-budgeted
  threshold_easy: 0.3
  threshold_hard: 0.6
```

**Implementation path** (in `src/graph/helpers.py`):

```python
def _repl_turn_token_cap(difficulty_band: str = "medium") -> int:
    """Difficulty-adaptive REPL token cap.

    Budget derived from overthinking efficiency metrics (arxiv:2412.21187)
    and information bottleneck theory (arxiv:2603.08462).
    """
    budgets = {
        "easy": _env_int("ORCHESTRATOR_REPL_EASY_TOKENS", 1500),
        "medium": _env_int("ORCHESTRATOR_REPL_MEDIUM_TOKENS", 3500),
        "hard": _env_int("ORCHESTRATOR_REPL_HARD_TOKENS", 7000),
    }
    cap = budgets.get(difficulty_band, budgets["medium"])
    return max(64, cap)
```

### 4.3 Outcome Efficiency as a Telemetry Metric

We can compute xi_O on our own Qwen3 outputs without any model changes:

1. **Instrument REPL turns:** For each task, record:
   - Total tokens generated per turn (T_i)
   - Whether the turn produced a correct result (sigma_i)
   - Tokens up to first correct code execution (T_hat_i)

2. **Compute xi_O per difficulty band:** This validates whether our
   difficulty classifier bands actually correlate with reasoning efficiency.
   If easy-band problems have xi_O < 30%, we are severely over-budgeting.
   If hard-band problems have xi_O > 70%, we are under-budgeting.

3. **Calibration loop:** Adjust band thresholds until xi_O is roughly
   uniform across bands (target: 60-70% for all bands). This means each
   band's budget is well-matched to its actual computational needs.

**Implementation:** Add to `session_log.py`:

```python
@dataclass
class EfficiencyMetrics:
    outcome_efficiency: float  # xi_O: T_hat / T for correct, 0 for wrong
    total_tokens: int
    first_correct_tokens: int  # tokens to first passing code execution
    num_solution_rounds: int   # count of distinct code submissions
    difficulty_band: str
```

### 4.4 Information Density Monitoring (from Paper 2)

Paper 2's key insight -- that wasted tokens have low surprisal -- gives us
a real-time overthinking detector:

**Approach:** Use the worker model itself as the reference prior. During
generation, track token-level log-probabilities (already available from
llama-server via `--log-disable false`). If the rolling average surprisal
drops below 0.2 nats for more than 50 consecutive tokens, the model is
generating filler.

**Integration with existing infrastructure:**
- llama-server already returns `completion_probabilities` when requested
- `inference.py` can accumulate a rolling surprisal window
- When surprisal drops below threshold, inject an early-stop signal

This is more principled than a fixed token cap because it adapts to the
CONTENT of the reasoning, not just its length. A 3000-token trace of dense
mathematical reasoning (high surprisal throughout) should not be cut, while
a 1500-token trace that devolved into self-verification loops (low surprisal
after token 800) should be stopped early.

**Caveat:** This requires streaming log-probabilities, which adds latency.
Start with post-hoc analysis of collected traces before implementing
real-time stopping.

### 4.5 Validating Difficulty Bands with Overthinking Metrics

Our `difficulty_signal.py` uses regex features (prompt length, multi-step
indicators, constraints, code presence, math presence, nesting, ambiguity).
Papers 1 and 2 give us ground-truth calibration targets:

**Validation protocol:**

1. Run seeding benchmarks across all difficulty bands with full token logging
2. For each band, compute:
   - Mean outcome efficiency (xi_O)
   - Mean process efficiency (xi_P)
   - Mean information density (nats per token)
   - First-correct-solution token count

3. Expected pattern if bands are well-calibrated:

| Band   | xi_O Target | Info Density | First-Correct Tokens |
|--------|-------------|--------------|---------------------|
| easy   | 65-80%      | > 0.3 nats   | < 500               |
| medium | 50-65%      | 0.2-0.3 nats | 500-2000             |
| hard   | 30-50%      | 0.15-0.2 nats| 2000+                |

4. If xi_O for "easy" band is < 50%, either:
   - The band threshold is too high (classifying medium problems as easy)
   - The model needs conciseness prompting for easy problems
   - The token budget needs further reduction to force efficiency

5. If xi_O for "hard" band is > 60%, either:
   - The band threshold is too low (classifying medium problems as hard)
   - The token budget can be reduced without accuracy loss

### 4.6 Connection to Existing Handoff Work

The reasoning-compression handoff (`handoffs/active/reasoning-compression.md`)
already tracks related work. These two papers fill specific gaps:

| Gap in Handoff | Paper 1 Fills | Paper 2 Fills |
|----------------|--------------|---------------|
| "How much compression is safe?" | xi_O/xi_P metrics quantify waste | CIB Pareto frontier defines optimal tradeoff |
| "Should budget vary by difficulty?" | Yes: 47.8% reduction safe for easy, 45.5% with 3.4pp cost for hard | Yes: I(Z;Y\|X) is higher for hard problems |
| "How to validate difficulty bands?" | Compare xi_O across bands | Compare info density across bands |
| "What is the right REPL cap?" | First-correct token data → band-specific caps | Semantic prior → content-adaptive stopping |
| "Is flat cap suboptimal?" | Empirically yes (inverse allocation) | Theoretically yes (Proposition 4.1) |

### 4.7 Phased Implementation Plan

**Phase 0 — Telemetry (no behavioral changes, 1-2 days)**
- Add `EfficiencyMetrics` to session log
- Track xi_O per difficulty band in shadow mode
- Collect baseline data: what is our current per-band efficiency?

**Phase 1 — Band-Adaptive Budgets (behavioral change, gated, 1 day)**
- Modify `_repl_turn_token_cap()` to accept difficulty_band
- Wire difficulty_band from routing result through to REPL cap
- Gate behind `difficulty_adaptive_budget` feature flag
- Default budgets: easy=1500, medium=3500, hard=7000
- A/B test against flat 5000

**Phase 2 — Surprisal Monitoring (observability, 2-3 days)**
- Collect token-level log-probs from REPL generations
- Compute rolling surprisal in post-hoc analysis
- Identify the "filler threshold" for our specific models (Qwen3.5)
- Determine if real-time stopping is worth the complexity

**Phase 3 — Content-Adaptive Stopping (optional, research-grade)**
- If Phase 2 shows clear filler detection signal:
  - Implement rolling surprisal window in inference.py
  - When surprisal < threshold for N consecutive tokens, inject stop
  - This replaces the token cap entirely with a content-aware signal
- If Phase 2 shows weak signal: stick with Phase 1 band-adaptive budgets


---

## 5. Key Takeaways

### For inference serving

1. **Our 5000-token flat cap is simultaneously too high for easy problems
   and too low for hard problems.** Paper 1 shows easy problems need ~1500
   tokens max; hard problems need 7000+.

2. **92% of correct answers appear in the first solution round.** Our REPL
   should detect when the model starts a second solution attempt for a
   problem already solved correctly and consider early termination.

3. **Token count is a poor proxy for reasoning quality.** Paper 2 proves
   that semantic content (surprisal) matters more than length. Two traces
   of identical length can have radically different information density.

4. **Difficulty-adaptive budgets are theoretically optimal** (CIB framework)
   and empirically validated (overthinking metrics). Our difficulty_signal.py
   classifier already produces the bands needed to implement this.

### For difficulty classification

5. **Our regex-based difficulty signal can be validated** by measuring xi_O
   per band on benchmark data. If the bands don't correlate with efficiency,
   the feature weights need recalibration.

6. **The OPSDC length-ratio trick** (output length with vs without
   conciseness prompt) is a complementary difficulty signal that could
   augment our regex features with an output-side measurement.

### For model training/fine-tuning

7. **SimPO with FCS+Reflection** achieves 37-48% token reduction with
   minimal accuracy loss across all difficulty levels. If we fine-tune
   Qwen3 models, this is the recipe.

8. **CIB with a 7B prior** achieves 32% compression with <1.5% accuracy
   drop on average. This is the principled alternative if we want
   theoretically grounded compression.

9. **Never compress frontier-difficulty problems aggressively.** Both papers
   show 3-5pp accuracy drops on AIME-class problems. Hard-band routing
   should explicitly protect against over-compression.


---

## 6. References

- Chen, X. et al. (2024). "Do NOT Think That Much for 2+3=? On the
  Overthinking of o1-Like LLMs." arXiv:2412.21187v2.
- Massoli, F.V., Kuzmin, A., Behboodi, A. (2026). "Reasoning as
  Compression: Unifying Budget Forcing via the Conditional Information
  Bottleneck." arXiv:2603.08462v1.

## 7. Related EPYC Artifacts

- Difficulty classifier: `/mnt/raid0/llm/epyc-orchestrator/src/classifiers/difficulty_signal.py`
- REPL token cap: `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py` (line 53)
- Reasoning compression handoff: `/mnt/raid0/llm/epyc-root/handoffs/active/reasoning-compression.md`
- Session log: `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py`
- Feature flags: `/mnt/raid0/llm/epyc-orchestrator/src/features.py`
