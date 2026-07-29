# AgentFold: Proactive Context Management for Long-Horizon Agents (Deep Dive)

**Paper**: arXiv 2510.24699 | **Authors**: Ye et al. (Tongyi Lab, Alibaba)
**Intake**: intake-155 | **No code released**

## Core Architecture

Context at each step: `C_t = (Q, T, S_{t-2}, I_{t-1})`
- **Q**: User question (invariant)
- **T**: Tool schemas
- **S_{t-2}**: Multi-scale state summaries — ordered sequence of summary blocks `(s_{x1,y1}, ..., s_{xm,ym})`
- **I_{t-1}**: Latest interaction (verbatim: explanation + action + observation)

Response: `R_t = (thinking, folding_directive, explanation, action)`

### Two Folding Operations

**Granular Condensation** (k = t-1): Fold ONLY latest interaction into fine-grained summary block. Preserves maximum resolution. Default operation.

**Deep Consolidation** (k < t-1): Fuse latest interaction + chain of prior summary blocks (steps k through t-1) into single coarse summary. Abstracts entire sub-tasks. Prevents linear context growth.

**Trigger**: Entirely learned via SFT — no rules. Model discovers when to apply each level through training.

### Context Efficiency

| Metric | Value |
|--------|-------|
| Context at turn 100 | ~7,000 tokens |
| ReAct context at turn 100 | ~91,000 tokens |
| Reduction vs ReAct | 92% smaller |
| Model context window | 128K tokens |
| Context growth | Sub-linear, sometimes decreasing (dead-end pruning) |

## Training: SFT Only

**Base model**: Qwen3-30B-A3B-Instruct-2507

**Fold-Generator Pipeline**:
1. Use powerful LLMs to generate trajectories
2. Rejection sampling: discard format violations and excessive errors
3. Output: `{(C_t, R_t*)}` training pairs

No RL. Authors acknowledge RL as "clear next step." SFT distills generate-and-filter strategy into weights.

### Information Survival Analysis
Assuming 1% loss per full-history re-summarization:
- Step 1 survival to step 100: 36.6%
- Step 1 survival to step 500: 0.66%
- AgentFold's granular blocks are exempt from re-processing → avoids exponential decay

## Key Results

| Agent | BrowseComp | BrowseComp-ZH | WideSearch | GAIA |
|---|---|---|---|---|
| **AgentFold-30B-A3B** | **36.2%** | **47.3%** | **62.1%** | **67.0%** |
| OpenAI-o3 | 49.7% | 58.1% | 60.0% | 70.5% |
| DeepSeek-V3.1-671B | 30.0% | 49.2% | — | 63.1% |
| GLM-4.5-355B | 26.4% | 37.5% | — | 66.0% |

- **WideSearch 62.1%** is highest score overall, surpassing all proprietary models
- Beats DeepSeek-V3.1-671B (22x larger) on BrowseComp by +6.2pp
- Scaling: Performance improves through 256+ turns while GLM-4.5-355B saturates at 64 turns

## Ablations

**None provided.** Major gap. Missing: granular-only vs deep-only, folding frequency, rule-based vs learned triggers.

## Failure Modes

1. ~20% of tasks hit 100-turn limit (forced termination)
2. Over-folding: deep consolidation may irreversibly lose corrective details
3. SFT cannot discover novel strategies outside training distribution
4. No recovery mechanism for prematurely folded information
5. Training data pipeline opacity (scale, source LLMs undisclosed)

## EPYC Applicability

### Two-Level Condensation for session_compaction

Replace single-level compaction with:
1. **Granular**: After each turn, compress output into compact stable block (not re-summarized)
2. **Deep**: At sub-task boundaries (escalation return, approach change, dead end), merge blocks into abstract summary

Maps to existing architecture:
- Granular → compress `TurnRecord` to one-line summary, store as stable block
- Deep → merge N consecutive TurnRecords into "sub-task summary" at escalation boundaries
- Session log format: extend `## Turn N` with `## Consolidated Turns N-M`

### Qwen3.5-35B-A3B Transferability

Paper uses Qwen3-30B-A3B (predecessor). Results should transfer or improve with our Qwen3.5-35B-A3B.
Caveat: Fine-tuning required for reliable structured output. Prompt-only approach may be feasible for simpler orchestrator use case.

### Latency Impact

- Folding directive is ~50-100 extra output tokens per turn (~5-10s at our speeds)
- But context stays at ~7K instead of 91K → **13x faster prefill per step**
- Net win over long trajectories

### Multi-Tier Delegation Mapping

- Root LM: Deep consolidation when delegating to new specialist
- Worker REPL: Granular per turn, deep at sub-task completion
- Escalation: `EscalationContext` carries deep-consolidated summary instead of full log

## Key References
- MEM1: 2506.15841
- MemAgent: 2507.02259
- Context-Folding: 2510.11967
- BrowseComp: 2504.12516
- GAIA: 2403.18910
- Qwen3: 2505.09388
