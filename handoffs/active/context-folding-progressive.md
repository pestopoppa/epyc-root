# Context-Folding: Progressive Session Compaction Upgrade

**Status**: Phase 0 complete (2026-03-29), Phase 1 next
**Created**: 2026-03-17
**Categories**: context_management, session_compaction, rl_training_data
**Priority**: HIGH
**Depends on**: Current `session_compaction` feature (production ON, 60% trigger, worker_explore index + 20% recent context)

---

## Objective

Upgrade the orchestrator's session compaction pipeline from single-level rule-based summarization to a multi-tier condensation system with process reward telemetry. Each phase is independently valuable and builds toward full Context-Folding (branch/fold call stack with RL).

Current state: `session_compaction` is ON in production (60% trigger, `worker_explore` index + 20% recent context). Session log regenerates summary every 2 turns via `worker_fast` (1.5B).

---

## Research Context

| Phase | Source Paper | Intake ID | Key Technique Adopted |
|-------|-------------|-----------|----------------------|
| 0 | AgentFold (arxiv:2510.24699) | intake-155 | Delay compaction to preserve context longer |
| 1 | AgentFold (arxiv:2510.24699) | intake-155 | Two-level condensation (granular + deep) |
| 1 | MemAgent (arxiv:2504.02861) | intake-156 | Segment-based reading with overwrite |
| 2 | Context-Folding (arxiv:2510.11967) | intake-154 | Summarizer quality evaluation methodology |
| 2 | AgentFold (arxiv:2510.24699) | intake-155 | SFT data collection from consolidation I/O |
| 3 | Context-Folding (arxiv:2510.11967) | intake-154 | FoldGRPO process rewards |
| 3 | ReSum (arxiv:2509.13313) | intake-157 | Position-weighted advantage broadcasting |

Additional context: intake-153 (Recursive Language Models, arxiv:2512.24601) — foundational RLM paper, EPYC implements 80% of RLM architecture.

---

## Dependency Graph

```
Phase 0 → Phase 1 → Phase 2 (parallel with Phase 3)
                  → Phase 3 (parallel with Phase 2)
```

---

## Phase 0 — Raise Compaction Trigger Threshold

**Objective**: Reduce quality-degrading early compaction by raising the trigger from 60% to 75% of context window, with a configurable parameter.

**Rationale**: AgentFold and MemAgent both show that delaying compaction preserves critical context. The current 60% trigger fires too early on many tasks, discarding recent turns that are still actively referenced. A configurable threshold lets us tune without code changes.

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/config/models.py` | Add `session_compaction_trigger_ratio: float = 0.75` to config model |
| `epyc-orchestrator/src/config/__init__.py` | Wire env override `ORCHESTRATOR_SESSION_COMPACTION_TRIGGER_RATIO` |
| `epyc-orchestrator/src/graph/helpers.py` (~line 877) | Replace hardcoded `0.6` with `get_config().session_compaction_trigger_ratio` |

**Feature flag**: None (config param, not a feature toggle)
**Risk**: Zero — only changes when compaction fires, not what it does
**Acceptance criteria**:
- Config param respected with env override
- Default changed from 0.6 to 0.75
- Existing tests pass (compaction logic unchanged)

---

## Phase 1 — Two-Level Condensation

**Objective**: Replace the every-2-turns `worker_fast` re-summarization with a two-tier system: fast granular blocks that accumulate without re-processing, and periodic deep consolidation at natural boundaries.

**Rationale**: Current approach re-summarizes ALL turn history every 2 turns via `worker_fast` (1.5B). This is wasteful (redundant work on already-summarized turns) and lossy (1.5B model quality). AgentFold's two-level approach eliminates redundant re-summarization while MemAgent's segment-based design provides a clean data structure.

**Tier 1 (granular)**: After each turn, `TurnRecord.to_log_line()` produces a stable 1-2 sentence block. Blocks accumulate in a list without re-summarization. No LLM call needed — deterministic formatting from structured turn data.

**Tier 2 (deep)**: At escalation boundaries, sub-task completion, or compaction trigger, consolidate accumulated Tier 1 blocks into a dense paragraph via `worker_explore` (7B). This is a single LLM call over a bounded window of granular blocks, not the entire history.

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/features.py` | Add `two_level_condensation` flag (default off, env `ORCHESTRATOR_TWO_LEVEL_CONDENSATION`) |
| `epyc-orchestrator/src/graph/state.py` | Add `consolidated_segments: list` to `TaskState` |
| `epyc-orchestrator/src/graph/session_log.py` | Add `ConsolidatedSegment` dataclass, `build_granular_summary()`, `_maybe_consolidate_segment()` |
| `epyc-orchestrator/src/graph/helpers.py` | Modify `_maybe_refresh_session_summary()` — when flag on, accumulate granular blocks instead of calling `worker_fast` every 2 turns; trigger Tier 2 consolidation at boundaries |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for granular accumulation and consolidation triggers |

**Feature flag**: `two_level_condensation` (default off, env `ORCHESTRATOR_TWO_LEVEL_CONDENSATION`)

**Consolidation triggers** (any of):
- Escalation boundary (role change in routing)
- Sub-task completion (FINAL() accepted)
- Compaction trigger threshold reached (Phase 0 param)
- Accumulated granular blocks exceed 15 entries without consolidation

**New dataclass**:
```python
@dataclass
class ConsolidatedSegment:
    turn_range: tuple[int, int]  # (start_turn, end_turn) inclusive
    granular_blocks: list[str]   # raw Tier 1 lines preserved for audit
    consolidated: str            # Tier 2 dense paragraph
    trigger: str                 # what triggered consolidation
    timestamp: float
```

**Acceptance criteria**:
- Feature flag off: zero behavior change, existing tests pass
- Feature flag on: granular blocks accumulate, Tier 2 fires at boundaries
- No `worker_fast` calls when flag is on (Tier 1 is deterministic)
- Tier 2 consolidation produces shorter output than concatenated Tier 1 blocks
- `consolidated_segments` survives checkpoint serialization

**Depends on**: Phase 0 (configurable trigger threshold used by consolidation trigger)

---

## Phase 2 — Summarizer Quality Assessment

**Objective**: Evaluate Tier 2 consolidation quality across model tiers and build SFT data collection infrastructure for future fine-tuning.

**Rationale**: Context-Folding's FoldGRPO achieves its results partly through RL-trained summarizers. Before we can train, we need (a) evidence of which model tier produces adequate consolidation, and (b) a pipeline to collect consolidation I/O pairs. AgentFold used SFT on consolidation data — we build the collection infra here.

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-inference-research/scripts/benchmark/eval_summarizer.py` | **CREATE** — evaluation script: run Tier 2 consolidation across model tiers (1.5B, 7B, 32B) on 20 real session logs, Claude-as-Judge scoring on faithfulness + compression ratio + information retention |
| `epyc-orchestrator/src/features.py` | Add `compaction_training_data` flag (default off, env `ORCHESTRATOR_COMPACTION_TRAINING_DATA`) |
| `epyc-orchestrator/src/graph/session_log.py` | When `compaction_training_data` flag on, log consolidation I/O pairs to `/mnt/raid0/llm/tmp/compaction_sft_{task_id}.jsonl` |

**Feature flag**: `compaction_training_data` (default off, env `ORCHESTRATOR_COMPACTION_TRAINING_DATA`)

**Eval methodology** (mirrors `eval_trimr.py` pattern from reasoning-compression handoff):
- Input: 20 real session logs from `/mnt/raid0/llm/tmp/session_*.md`
- For each log, extract Tier 1 granular blocks as consolidation input
- Run Tier 2 consolidation via each model tier
- Score with Claude-as-Judge on 3 axes: faithfulness (0-3), compression ratio, information retention (0-3)
- Output: CSV with per-model-tier scores

**Acceptance criteria**:
- Eval script runs end-to-end on at least 5 session logs
- Claude-as-Judge scores differentiate between model tiers
- SFT JSONL format: `{"input": [granular_blocks], "output": consolidated_text, "task_id": str, "turn_range": [start, end]}`
- SFT collection gated behind feature flag, zero overhead when off

**Depends on**: Phase 1 (needs Tier 2 consolidation to exist)
**Cross-reference**: Shares eval methodology with `reasoning-compression.md` (TrimR evaluation uses same `eval_trimr.py` pattern and Claude-as-Judge scoring)

---

## Phase 3 — Process Reward Telemetry

**Objective**: Log FoldGRPO-analog process reward signals per turn, and compute position-weighted segment advantages at consolidation boundaries. This is pure telemetry — no routing changes.

**Rationale**: Context-Folding's FoldGRPO uses three process reward signals to train fold/expand decisions. ReSum's advantage broadcasting solves credit assignment across summary boundaries. By logging these signals now, we build the training data needed for future RL-based compaction decisions, and provide a `segment_advantage` signal usable by MemRL Q-value enrichment (see routing-intelligence.md Phase 5).

**Reward signals per turn**:

| Signal | Definition | Source |
|--------|-----------|--------|
| `token_budget_ratio` | `tokens_used / band_budget` | `TurnRecord.tokens_generated` / `_repl_turn_token_cap()` |
| `on_scope` | Heuristic: did the turn make progress toward the task? | 1.0 if code executed successfully or FINAL() accepted; 0.5 if code executed with non-fatal error; 0.0 if no code extracted or repeated code hash |
| `tool_success_ratio` | Fraction of tool calls that succeeded | `TurnRecord.tool_calls` success/total |

**Segment advantage** (computed at Tier 2 consolidation boundaries):
```python
def segment_advantage(turns: list[TurnRecord]) -> float:
    """Position-weighted advantage à la ReSum-GRPO."""
    rewards = [t.reward_signals.composite() for t in turns]
    baseline = mean(rewards)
    # Later turns weighted more (position-weighted broadcasting)
    weights = [i / len(turns) for i in range(1, len(turns) + 1)]
    return sum(w * (r - baseline) for w, r in zip(weights, rewards)) / sum(weights)
```

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/features.py` | Add `process_reward_telemetry` flag (default off, env `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY`) |
| `epyc-orchestrator/src/graph/session_log.py` | Extend `TurnRecord` with `token_budget_ratio`, `on_scope`, `tool_success_ratio` fields; add `compute_segment_advantage()` |
| `epyc-orchestrator/src/graph/helpers.py` | Populate reward fields in `TurnRecord` construction; call `log_process_reward()` at consolidation boundaries |
| `epyc-orchestrator/orchestration/repl_memory/progress_logger.py` | Add `log_process_reward()` (same pattern as `log_delegation()`) |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for reward computation and segment advantage |

**Feature flag**: `process_reward_telemetry` (default off, env `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY`)

**Acceptance criteria**:
- Feature flag off: zero behavior change, no reward computation
- Feature flag on: all three signals logged per turn via `log_process_reward()`
- `segment_advantage` computed and logged at every Tier 2 consolidation boundary
- Telemetry visible in `logs/agent_audit.log` and inference tap
- No latency impact (all computation is O(1) per turn, no LLM calls)

**Depends on**: Phase 1 (needs consolidation boundaries for segment advantage)
**Parallel with**: Phase 2 (independent work streams)
**Cross-reference**: `segment_advantage` signal feeds into MemRL Q-value enrichment tracked in `routing-intelligence.md` Phase 5. ReSum-GRPO's position-weighted advantage broadcasting is applicable to delegation episode training.

---

## Cross-References

| Handoff | Relationship |
|---------|-------------|
| `reasoning-compression.md` | Phase 2 shares eval methodology (Claude-as-Judge scoring, `eval_trimr.py` pattern); SFT data collection mirrors TrimR pattern |
| `routing-intelligence.md` | Phase 3 `segment_advantage` feeds Phase 5 MemRL Q-value enrichment; advantage broadcasting applicable to delegation episodes |
| ~~`rlm-orchestrator-roadmap.md`~~ | ARCHIVED 2026-03-29 — D1 Context Compaction superseded by this handoff |
| `routing-and-optimization-index.md` | Phase 0-1 should precede autoresearch baseline (P5-AR-1); Phase 3 process rewards tracked as upstream dependency (concern #7) |

---

## Verification

```bash
# Phase 0: config change
python3 -c "from src.config import get_config; assert get_config().session_compaction_trigger_ratio == 0.75"

# Phase 1: two-level condensation tests
python3 -m pytest tests/unit/test_session_log.py -v -k "condensation or granular or consolidat"

# Phase 2: eval script dry-run
python3 scripts/benchmark/eval_summarizer.py --dry-run

# Phase 3: reward telemetry tests
python3 -m pytest tests/unit/test_session_log.py -v -k "reward or advantage"

# Full gate
python3 -m pytest tests/unit/ -x -q
```
