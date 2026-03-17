# Context-Folding: Scaling Long-Horizon LLM Agents (Deep Dive)

**Paper**: arXiv 2510.11967 | **Authors**: Sun, Lu, Ling, Liu, Yao, Yang, Chen (ByteDance Seed)
**Code**: https://github.com/sunnweiwei/FoldAgent
**Intake**: intake-154

## Core Architecture

Treats agent trajectory as a call stack. Four operations:
1. **Branch** — spawn sub-trajectory for subtask (own context scope)
2. **Execute** — work within branch
3. **Fold** — collapse all branch intermediate steps into concise summary
4. **Return** — rejoin main trajectory with only summary appended

Policy: `p_CF(tau|q) = prod pi_theta(a_i | q, F(tau_{<i}))` — model conditions on **folded** history.

### Fold Triggers
- Agent-initiated `return` action at branch end (learned via RL)
- Hard constraint: forced fold when main thread context exceeds 50% of budget

### Context Budget
- Active window: 32K tokens
- Max branches: 10 (training), 32.6 avg (hard inference — generalizes)
- Theoretical max: 327K tokens across branches
- Main trajectory after folding: ~8K tokens

## FoldGRPO Training

Base model: **Seed-OSS-36B-Instruct** (ByteDance)

Extends GRPO with folded context during rollouts + token-level process rewards:

| Penalty | Value | Trigger |
|---------|-------|---------|
| Unfolded Token | -1.0 | Main thread >50% context capacity |
| Out-of-Scope | -0.2 | Branch deviates from subtask (GPT-5-nano judge) |
| Failure | -1.0 | Failed tool call |
| Success baseline | +0.2 | Successful tool call |

Training: 32K response, 200 max turns, 10 max branches, verl framework, vLLM inference.

## Key Results

| Configuration | BrowseComp+ (150) | SWE-Bench (500) |
|---|---|---|
| Seed-OSS-36B baseline | 28.6% | 43.6% |
| ReAct + GRPO (327K context) | 54.0% | 57.4% |
| Summary Agent + GRPO (32K) | 52.7% | 55.0% |
| **Folding + FoldGRPO (32K)** | **62.0%** | **58.0%** |

**Headline**: Folding at 32K **beats** ReAct at 327K by +8pp.

Completion rate: 73.8% (untrained) → 93.5% (FoldGRPO trained).
Tool calls increase with training (12.9→19.2 BrowseComp, 72.8→96.5 SWE) — more exploration in less context.

## Ablations

- FoldGRPO vs standard GRPO: +5.3pp BrowseComp, +1.6pp SWE (process rewards matter)
- Folding vs Summarization architecture: +4.0pp BrowseComp, +1.4pp SWE
- BrowseComp-Plus Hard subset: only 4.0% — folding doesn't solve fundamentally hard reasoning

## Failure Modes

1. Information loss during folding (summaries are lossy)
2. Premature folding (50% penalty is a blunt instrument)
3. Out-of-scope judge quality (GPT-5-nano imperfect)
4. Self-conditioning on own summaries (addressed by follow-up FoldAct, 2512.22733)
5. Training-inference distribution mismatch

## EPYC Applicability

### Session Compaction Upgrade
Replace fixed 2-turn compaction with **branch-scoped fold**: when worker escalation completes, fold entire worker trace into structured summary. Requires no RL — fold triggers are structural (escalation boundaries).

### Process Reward Analogs
- Unfolded Token Penalty → `_repl_turn_token_cap()` truncation → could become soft penalty signal
- Out-of-Scope → routing classifier `factual_risk.py` in shadow mode for task deviation detection
- Failure Penalty → `TurnRecord` error tracking + anti-loop hash detection

### FoldGRPO for MemRL
Process rewards for decomposition quality could improve routing decisions — rewarding effective task splitting rather than just final outcome. Currently no RL loop in production, but could compute as telemetry.

### CPU Inference Impact
- 10x context reduction → 10x less KV cache → proportionally faster prefill
- Fold overhead (one summary per branch) amortized across many turns
- Main trajectory at ~8K instead of growing unbounded = constant prefill cost

## Key References
- FoldAct (follow-up): 2512.22733 — fixes gradient dilution, self-conditioning, 5.19x training speedup
- ReSum: 2509.13313 — periodic summarization (complementary approach)
- SWE-bench: 2310.06770
- DeepSeek-R1/GRPO: 2501.12948
