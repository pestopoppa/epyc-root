# Ouroboros Multi-Model Validation

## Closure note (2026-06-12, Fable 5 portfolio pass)

**Final outcome**: Never executed — no acceptance criterion was ever checked. Archived to `handoffs/archived/` (not `completed/`) because it **references a deprecated model stack**: the named worker models (Qwen2.5-7B as worker, Nanbeige-3B, MiroThinker-8B) predate the worker swaps to 30B-A3B (2026-03-21) and then gemma4-26B-A4B MTP (2026-05-08), and both dependency handoffs (`02-nanbeige-3b-worker-eval.md`, `04-mirothinker-worker-eval.md`) are themselves in `archived/`. Per fable5-findings-04, this is a stale blocked stub, not live work.

**Why archived**: stale premise + never started; the historical-documentation warning applies — verify everything against the current stack before reusing any detail below.

**Where residuals now live**: the adoptable *pattern* (cross-model validation of worker outputs before acceptance) is not lost — verification-before-accept concerns are owned today by the eval-tower / accept-path redesign (`eval-tower-verification.md`, fable5-findings-01 sequential verdicts) and the multi-file edit-transaction work's optional functional-verifier-in-the-loop. None of those inherit this file's implementation steps.

**Reopen triggers**: if a cross-model output-validation lever is wanted on the current stack, write a fresh handoff against today's roles and the per-question eval ledger — do not resume this plan.

---

**Status**: ACTIVE
**Created**: 2026-03-03
**Priority**: P2 — depends on worker model availability
**Effort**: Medium
**Depends On**: `02-nanbeige-3b-worker-eval.md`, `04-mirothinker-worker-eval.md` (need multiple validated models)
**Source**: [Ouroboros (github.com/joi-lab/ouroboros)](https://github.com/joi-lab/ouroboros)

## Research Review

### Ouroboros: Self-Modifying AI Agent
**Source:** github.com/joi-lab/ouroboros

Autonomous self-modifying agent that evolves its own code through git commits. Features supervisor layer (process lifecycle, budget accounting), background consciousness loops, auto-discovering tool registry, multi-model code review (Claude + o3 + Gemini), task decomposition with parent-child tracking. Evolved through 30+ autonomous cycles (v4.1→v4.25) in 24 hours.

**Orchestrator Relevance: MEDIUM.** Not directly adoptable (our orchestrator shouldn't self-modify), but useful architectural patterns:
- **Multi-model code review**: Using 3 models to validate before committing — could apply to our REPL output validation
- **Budget accounting**: Their per-task spending limits with real-time tracking
- **Task decomposition with parent-child tracking**: More structured than our current escalation context passing
- **Auto-discovering tool registry**: Pattern for dynamically registering/discovering available tools

**Caution:** Self-modification is explicitly out of scope for production orchestrator.

### Applicable Pattern: Multi-Model Validation
The core adoptable idea: before accepting a worker's output as final, validate it with a second (cheaper/different) model. This catches:
- Hallucinated code that looks correct but fails at runtime
- Logic errors that the primary model is systematically blind to
- Format/protocol violations

## References

- [Ouroboros repo](https://github.com/joi-lab/ouroboros)
- Worker models: Qwen2.5-7B (current), Nanbeige-3B (candidate), MiroThinker-8B (candidate)
- REPL output validation: `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py`
- Solution file persistence: `_persist_solution_file()` in helpers.py

## Implementation Steps

### 1. Design cross-model validation protocol
- Define which outputs warrant multi-model validation (not all — too expensive)
- Candidates: final REPL output before returning to user, escalation decisions, code that will be persisted
- Define validation prompt: "Review this code/output for correctness, logic errors, and hallucinations"

### 2. Implement lightweight validation step
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py`
- After worker produces final output, route to a different model for review
- Use cheapest available model (e.g., if worker is 7B, validate with 3B)
- Validation is pass/fail + optional feedback

### 3. Handle validation failures
- On failure: feed validation feedback back to original worker for one retry
- On second failure: escalate with both outputs + validation feedback
- Track validation failure rate per worker model for routing decisions

### 4. Add parent-child task tracking
- Extend state dict with parent_task_id / child_task_ids
- Track task decomposition tree for debugging and analysis
- Log decomposition depth alongside escalation depth (from #01)

### 5. Budget-aware validation
- Skip validation when task budget is nearly exhausted (from #01 budget controls)
- Track validation overhead as percentage of total task cost
- Target: validation adds < 15% overhead

## Acceptance Criteria

- [ ] Cross-model validation protocol defined (which outputs, which validators)
- [ ] Validation step implemented with pass/fail + feedback
- [ ] Validation failure → retry → escalation flow working
- [ ] Parent-child task tracking in state dict
- [ ] Validation overhead measured and within budget (< 15%)
- [ ] Validation failure rate tracked per model for routing feedback
