# ReSum: Long-Horizon Search via Context Summarization (Deep Dive)

**Paper**: arXiv 2509.13313v2 | **Authors**: Wu et al. (Tongyi Lab, Alibaba)
**Intake**: intake-157 | **No code released**

## Core Architecture

### The ReSum Loop

1. Agent generates reasoning + tool call, environment returns observation
2. History accumulates: `H_t = H_{t-1} . (tau_t, a_t, o_t)`
3. **Trigger check**: If approaching context token limit → summarize
4. External summarizer `pi_sum` generates summary `s ~ pi_sum(.|H_t)`
5. **History RESET**: `H_t <- (original_query, summary)` — full context replaced
6. Agent continues from compressed state

### Summarization Trigger

Rule-based: approaching context token limit (hard threshold). Paper acknowledges this as a limitation — "intelligently triggering summary calls at appropriate moments" is future work.

### Summary Structure

Structured output in `<summary>` tags:
- **Essential Information**: Verified evidence organized by certainty
- **Information Gaps**: What's still unknown
- **Next-Step Directions**: Actionable search strategies

### External Summarizer (Critical)

**ReSumTool-30B**: Qwen3-30B-A3B-Thinking, SFT-tuned on `<Conversation, Summary>` pairs.

Summary quality is THE critical variable:

| Summarizer | Params (active) | BC-zh P@1 (driving WS-3B) |
|-----------|-----------------|---------------------------|
| Qwen3-30B (untrained) | 3B | 6.9% (**worse** than ReAct 8.2%) |
| Qwen3-235B | 22B | 11.1% |
| DeepSeek-R1-671B | 37B | 13.0% |
| ReSumTool-30B (SFT) | 3B | 13.7% |
| GPT-OSS-120B | ~120B | 15.2% |

Key: SFT-specialized 3B-active model matches/exceeds 235B and 671B general models.

## ReSum-GRPO Training

### Trajectory Segmentation

K summarization events → K+1 segments. Each segment starts from compressed state `(query, summary)`.

### Advantage Broadcasting

Trajectory-level binary reward (LLM-as-Judge) broadcast uniformly to ALL segments:
```
A_hat_g^(i) = A_hat_g  for all segments i in rollout g
```

Intuition: early evidence-gathering is as responsible for outcome as late reasoning.

### Objective

Standard clipped surrogate (GRPO-style) with per-segment policy ratios. No KL term.

| Parameter | Value |
|-----------|-------|
| Batch size | 64 |
| Group size | 8 |
| Learning rate | 2e-6 |
| Epochs | 4 |
| Training data | 1K samples from SailorFog-QA |
| Max tool calls | 60 |
| Temperature | 0.6, top_p 0.95 |

Training overhead: 1.33x-1.69x vs standard GRPO (summarization calls during rollouts).

## Key Results

### WebSailor-30B (Best Configuration)

| Setting | GAIA P@1 | BC-zh P@1 | BC-en P@1 |
|---------|----------|-----------|-----------|
| ReAct baseline | 45.0 | 23.9 | 12.8 |
| ReSum (no RL) | 48.5 | 29.3 | 15.0 |
| GRPO (no ReSum) | 48.2 | 23.3 | 14.3 |
| **ReSum-GRPO** | **48.5** | **33.3** | **18.3** |

- ReSum without RL: +5.4/+4.5 avg over ReAct
- ReSum-GRPO: +9.4 BC-zh, +5.5 BC-en over ReAct
- GRPO alone can HURT BrowseComp (-0.6 BC-zh) — ReSum paradigm is the enabler

### Diminishing Returns at Large Context

| Context | ReSum Δ BC-zh P@1 | ReSum Δ BC-en P@1 |
|---------|-------------------|-------------------|
| 64K | +5.0 | +4.0 |
| 128K | +0.9 | +2.3 |

At 128K, raw history is mostly usable — summarization adds marginal value.

### MEM1 Comparison (Critical)

| Method | GAIA P@1 | BC-zh P@1 | BC-en P@1 |
|--------|----------|-----------|-----------|
| MEM1 (training-free) | 33.3 (-11.7!) | 25.0 | 12.7 |
| MEM1-GRPO | 35.7 | 29.1 | 19.5 |
| ReSum-GRPO | 48.5 | 33.3 | 18.3 |

MEM1's constant-window consolidation **destroys GAIA** (-11.7 P@1). Too aggressive for structured reasoning. MEM1-GRPO edges ReSum on BC-en (+1.2) but at ~3x token cost.

## Ablations

1. **Summary quality**: Bad summarizer = worse than no summarization. SFT specialization essential.
2. **With/without RL**: +4.0 BC-zh from ReSum-GRPO over untrained ReSum
3. **Context window**: Diminishing returns at 128K
4. **MEM1 vs ReSum**: ReSum preserves structured reasoning (GAIA), MEM1 destroys it
5. **Tool call distribution**: solved cases ~10 calls, failed cases >20 (motivates summarization)

## Failure Modes

1. **Summary quality dependency**: Poor summarizer is worse than none
2. **Rule-based triggering**: Suboptimal — needs learned triggers
3. **External tool dependency**: Requires separate summarization model
4. **Crude advantage broadcasting**: Uniform across segments ignores per-segment quality
5. **~2x token overhead**: Summarization calls + re-searching previously known info
6. **Diminishing returns at large context**: Marginal at 128K
7. **Binary reward**: No partial credit, noisy training signal

## EPYC Applicability

### Advantage Broadcasting for MemRL

ReSum's uniform broadcasting works for homogeneous search trajectories. For our heterogeneous routing decisions, use **position-weighted** broadcasting:
```
A_hat_g^(i) = gamma^(n_g - i) * A_hat_g  where gamma in [0.8, 1.0]
```

### Session Compaction Timing

**Key finding: do not compact too early.** ReSum confirms that at 64K, summarization helps (+5 P@1). At 128K, marginal (+0.9). Our compaction should trigger at 70-80% of context window, not on fixed turn count.

### Summarizer Quality Threshold

Our `worker_fast` (Qwen2.5-7B) acts as session summarizer. ReSum shows untrained 30B fails — a 7B model may be below quality threshold for complex sessions. Options:
1. SFT-specialize a small MoE for summarization (even few hundred pairs helps)
2. Be conservative about compaction trigger timing

### Web Research Tool Alignment

ReSum's pipeline (search → visit → extract) mirrors ours (search → parallel fetch → worker synthesis). Summarization should happen AFTER tool results are processed. Our architecture is correct.

### Token Budget

Expect ~2x token consumption with summarization enabled. Budget in `ORCHESTRATOR_REPL_TURN_N_TOKENS`.

## Comparison with Peers

| Paper | Approach | Trigger | Training | Context Management |
|-------|----------|---------|----------|-------------------|
| Context-Folding | Branch/fold call stack | Learned (RL) | FoldGRPO | Sub-task scoped |
| AgentFold | Granular + deep condensation | Learned (SFT) | SFT | Multi-scale summaries |
| MemAgent | Segment reading + overwrite | Fixed segments | Multi-conv DAPO | 1K memory buffer |
| **ReSum** | **Periodic full-context reset** | **Rule-based (token limit)** | **ReSum-GRPO** | **Summary replaces history** |

ReSum is simplest but most fragile (summary quality dependent). Context-Folding is most sophisticated. AgentFold is best compromise (SFT-only, two-level). MemAgent is most extreme (437x extrapolation).

## Key References
- MEM1: 2506.15841
- MemAgent: 2507.02259
- GRPO/DeepSeekMath: 2402.03300
- DeepSeek-R1: 2501.12948
- DAPO: 2503.14476
- Context-Folding: 2510.11967 (via FoldAct 2512.22733)
- BrowseComp: 2504.12516
- GAIA: 2403.18910
- Qwen3: 2505.09388
