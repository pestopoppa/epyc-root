# Context-Folding: Progressive Session Compaction Upgrade

**Status**: Phase 0 complete (2026-03-29), Phase 1 complete (2026-04-04), Phase 1+/2/3 next (scope expanded 2026-04-05 with intake-261/262 findings)
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
| 1+ | AgentOCR (arxiv:2601.04786) | intake-262 | Hash-based segment dedup, adaptive compression rates |
| 2 | Skill0 (arxiv:2604.02268) | intake-261 | Helpfulness-driven segment scoring, "free zone" threshold methodology |
| 2 | AgentOCR (arxiv:2601.04786) | intake-262 | Compression quality threshold (c_t ≤ 1.2 = free zone), task-type sensitivity data |
| 3 | Context-Folding (arxiv:2510.11967) | intake-154 | FoldGRPO process rewards |
| 3 | ReSum (arxiv:2509.13313) | intake-157 | Position-weighted advantage broadcasting |
| 3 | Skill0 (arxiv:2604.02268) | intake-261 | Role-aware compaction aggressiveness parameterization |
| 3 | AgentOCR (arxiv:2601.04786) | intake-262 | Intermittent reward scheduling (K=5 optimal, K=1 collapse) |

Additional context: intake-153 (Recursive Language Models, arxiv:2512.24601) — foundational RLM paper, EPYC implements 80% of RLM architecture.

---

## Dependency Graph

```
Phase 0 → Phase 1 → Phase 1+ (segment dedup extension)
                  → Phase 2 (parallel with Phase 3)
                  → Phase 3 (parallel with Phase 2)
Phase 2 informs Phase 3 (quality thresholds feed reward parameterization)
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

## Phase 1+ — Segment Hash Dedup & Caching

**Objective**: Add content-hash-based deduplication to the segment pipeline so that identical or near-identical tool outputs reuse cached consolidations instead of re-summarizing.

**Status**: Not started (introduced 2026-04-05 via intake-262 deep dive)

**Rationale**: AgentOCR (arxiv:2601.04786, intake-262) demonstrates that hash-based segment caching achieves a 20.79x speedup in their rendering pipeline and 26.82% peak memory savings. Their architecture: `Cache = {hash(segment_text): rendered_output}`, maintained per-episode with no within-episode eviction. In our orchestrator, repeated tool outputs are pervasive — `git status`, `pytest` results, file listings, and error traces recur across turns with identical or near-identical content. Re-summarizing these each time Tier 2 consolidation fires is wasted LLM compute.

**Literature basis**:
- AgentOCR (arxiv:2601.04786): `C^(e) = {(k(ℓ), I(ℓ))}` per-episode cache with content hash keys. Split(h) = (ℓ₁, ..., ℓ_k) partitions history into segments. Cache lookup before render; on miss, render and insert. Episode boundary resets cache. Achieves 20.79x speedup over uncached.
- RTK (intake-259): Achieves 60-90% reduction via deduplication with counts (e.g., "15 identical test outputs → 1 representative + count"). Validates that tool outputs are highly redundant.
- CONTEXT_COLLAPSE micro-compaction (intake-247): Surgical removal of low-value content maps to our "skip already-cached segment" pattern.

**Design**:

The dedup layer sits between Tier 1 block accumulation and Tier 2 consolidation. When consolidation triggers, each granular block is hashed before being sent to the summarizer. Cached summaries are reused; only novel blocks go through the LLM.

```python
import hashlib

@dataclass
class SegmentCache:
    """Per-session segment dedup cache."""
    _store: dict[str, str] = field(default_factory=dict)  # hash -> consolidated text
    _hits: int = 0
    _misses: int = 0

    def normalize(self, text: str) -> str:
        """Normalize for near-duplicate detection.
        Strip leading/trailing whitespace, collapse internal whitespace runs,
        remove ANSI escape codes, normalize paths to basenames."""
        # Remove ANSI escapes
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def key(self, text: str) -> str:
        return hashlib.sha256(self.normalize(text).encode()).hexdigest()[:16]

    def lookup(self, block: str) -> str | None:
        k = self.key(block)
        if k in self._store:
            self._hits += 1
            return self._store[k]
        self._misses += 1
        return None

    def insert(self, block: str, consolidated: str) -> None:
        self._store[self.key(block)] = consolidated

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
```

**Integration point**: In `_maybe_consolidate_segment()` (Phase 1), before calling `worker_explore` for Tier 2 consolidation:

```python
def _maybe_consolidate_segment(self, blocks: list[str], trigger: str) -> ConsolidatedSegment:
    # Check cache for each block
    cached_parts = []
    novel_blocks = []
    for block in blocks:
        cached = self.segment_cache.lookup(block)
        if cached is not None:
            cached_parts.append(cached)
        else:
            novel_blocks.append(block)

    # Only send novel blocks to LLM
    if novel_blocks:
        novel_consolidated = self._consolidate_via_llm(novel_blocks)
        # Cache individual block summaries for future reuse
        for block in novel_blocks:
            self.segment_cache.insert(block, novel_consolidated)
    else:
        novel_consolidated = ""

    # Merge cached + novel parts
    full_consolidated = "\n".join(filter(None, cached_parts + [novel_consolidated]))
    # ... construct ConsolidatedSegment as before
```

**Normalization rules** (critical for near-duplicate matching):
1. Strip ANSI escape codes (test output coloring)
2. Collapse whitespace runs (indentation variance)
3. Optionally: normalize absolute paths to basenames (same file, different CWD)
4. Do NOT normalize numbers or identifiers (commit hashes, line numbers matter)

**Cache lifecycle**:
- Scope: per-session (matches AgentOCR's per-episode scope)
- Eviction: none within session (AgentOCR validates this works; session-scoped caches are bounded by session length)
- Reset: on session start
- Serialization: not persisted across sessions (summary quality may change with model updates)

**Telemetry** (log via `agent_audit.log`):
- `segment_cache_hit_rate` per consolidation event
- `segment_cache_size` (number of entries)
- `llm_calls_saved` (count of blocks that matched cache)

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/graph/session_log.py` | Add `SegmentCache` class; add `segment_cache` field to session state; integrate cache lookup/insert into `_maybe_consolidate_segment()` |
| `epyc-orchestrator/src/features.py` | Add `segment_cache_dedup` flag (default off, env `ORCHESTRATOR_SEGMENT_CACHE_DEDUP`) |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for cache hit/miss, normalization rules, hit rate telemetry |

**Feature flag**: `segment_cache_dedup` (default off, env `ORCHESTRATOR_SEGMENT_CACHE_DEDUP`)

**Acceptance criteria**:
- Identical tool outputs (e.g., two consecutive `git status` with no changes) produce cache hits
- Near-identical outputs (whitespace/ANSI differences) also hit
- Cache hit rate logged at each consolidation boundary
- Zero behavior change when flag is off
- LLM call count measurably reduced on sessions with repeated tool patterns

**Risk**: Low — pure optimization layer, no change to consolidation quality. Cache miss falls through to normal Tier 2 path.

**Depends on**: Phase 1 (needs segment-based consolidation architecture)

---

## Phase 2 — Summarizer Quality Assessment & Segment Helpfulness Scoring

**Objective**: (a) Evaluate Tier 2 consolidation quality across model tiers, (b) establish the "free zone" compression threshold where compaction is quality-neutral, (c) implement segment-level helpfulness scoring to drive compaction prioritization, and (d) build SFT data collection infrastructure for future fine-tuning.

**Status**: Not started (scope expanded 2026-04-05 with helpfulness scoring from intake-261/262 deep dive)

**Rationale**: Context-Folding's FoldGRPO achieves its results partly through RL-trained summarizers. Before we can train, we need (a) evidence of which model tier produces adequate consolidation, and (b) a pipeline to collect consolidation I/O pairs. AgentFold used SFT on consolidation data — we build the collection infra here.

**New rationale (2026-04-05)**: Skill0 (arxiv:2604.02268, intake-261) demonstrates that helpfulness-driven selection — measuring which context segments actually improve performance vs. being dead weight — is the single most important component of their system. Removing helpfulness ranking caused -13.7% collapse in their ablations, far worse than any other component. AgentOCR (arxiv:2601.04786, intake-262) establishes that compression up to c_t ≤ 1.2 is essentially free (95% performance retention, ~55% token savings), with steep nonlinear degradation beyond c_t ≈ 1.5. Together these give us: (1) a methodology for scoring which segments to compact first, and (2) empirical thresholds for how aggressively to compact.

### Phase 2a — Summarizer Quality Evaluation

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

**Acceptance criteria (2a)**:
- Eval script runs end-to-end on at least 5 session logs
- Claude-as-Judge scores differentiate between model tiers
- SFT JSONL format: `{"input": [granular_blocks], "output": consolidated_text, "task_id": str, "turn_range": [start, end]}`
- SFT collection gated behind feature flag, zero overhead when off

### Phase 2b — Free-Zone Threshold Sweep

**Objective**: Establish the compression ratio at which consolidation quality degrades — the "free zone" boundary.

**Literature basis**:
- AgentOCR (arxiv:2601.04786, intake-262) found c_t ≤ 1.2 is free, c_t ≈ 1.5 is the knee, and task sensitivity varies: ALFWorld (scene understanding) retains 87.2% at 2x compression while Search-QA (text-sensitive) drops to 66.8%. Their reward schedule finding is critical: dense compression reward (K=1) caused collapse to 45.3%, while intermittent (K=5) achieved 78.2%.
- Skill0 (arxiv:2604.02268, intake-261) token efficiency: 0.38k tokens/step vs 2.21k for SkillRL (5.8x reduction) and 0.87k for GRPO (2.3x reduction). Achieved via progressive context withdrawal — validates that large compression is achievable without quality loss *if* the right content is targeted.

**Methodology**: Sweep consolidation aggressiveness at 5 levels and measure downstream task quality.

```
Compression levels:
  L1: 20% reduction (gentle — keep most detail, remove redundancy)
  L2: 40% reduction (moderate — summarize routine operations)
  L3: 60% reduction (aggressive — dense paragraph per segment)
  L4: 80% reduction (extreme — key-fact extraction only)
  L5: 95% reduction (maximum — single-sentence per segment)
```

For each level, on 20 real session logs:
1. Compact the session history at that level using `worker_explore` (7B)
2. Present the compacted history as context for a follow-up probe task
3. Measure: (a) probe task completion rate, (b) factual accuracy on session-specific questions, (c) code correctness if the probe involves code modification
4. Score with Claude-as-Judge: faithfulness (0-3), information retention (0-3)

**Expected output**: A curve of quality vs compression ratio, with the "free zone" boundary identified. Hypothesis based on AgentOCR data: L1-L2 (20-40%) should be near-lossless; L3 (60%) is the knee; L4+ degrades significantly for coding tasks.

**Critical finding to validate**: AgentOCR shows text-sensitive tasks degrade ~3x faster than scene-understanding tasks. Our orchestrator is primarily text-sensitive (code, error messages, exact identifiers). We should expect our "free zone" to be NARROWER than AgentOCR's — closer to 20-30% for `worker_coder` vs potentially 40-50% for `worker_explore`.

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-inference-research/scripts/benchmark/eval_compaction_sweep.py` | **CREATE** — sweep script parameterized by compression level, outputs quality-vs-ratio CSV |
| `epyc-inference-research/scripts/benchmark/prompts/compaction_probe.md` | **CREATE** — probe task template for post-compaction quality measurement |

**Acceptance criteria (2b)**:
- Sweep produces quality scores at all 5 compression levels for at least 10 session logs
- Free-zone boundary identified with 95% confidence interval
- Results broken down by session type (coding-heavy vs exploration-heavy)
- Output includes a recommendation for default compaction level per role

### Phase 2c — Segment Helpfulness Scoring

**Objective**: Implement a per-segment helpfulness metric (Δ_k) that scores how much each segment contributes to downstream task quality, enabling prioritized compaction — compact low-Δ segments first, preserve high-Δ segments.

**Literature basis**:
- Skill0 (arxiv:2604.02268, intake-261) defines helpfulness as: `Δ_k = Acc_with_context_k - Acc_without_context_k`. Their three-step algorithm: (1) Filter — retain only segments where Δ_k > 0; (2) Rank — sort by descending Δ_k; (3) Select — keep top-m under budget. Ablation shows ranking is THE critical component: removing it causes -13.7% performance collapse, far worse than any other ablation (-2.7% for filter removal, -13.3% for fixed budget). The budget schedule is aggressive: [6,3,0] stages (full → half → zero skills).
- Skill0 evaluates helpfulness every d=10 training steps on validation sub-tasks. d=10 found optimal; more frequent evaluation (d=1) is computationally wasteful without quality gain.

**Design**: Segment helpfulness scoring for our context-folding pipeline. Unlike Skill0 (which measures skill helpfulness during RL training), we measure segment helpfulness at inference time to decide compaction order.

**Approach A — Lightweight heuristic scoring (no LLM call)**:

Score each `ConsolidatedSegment` on 4 signals, each 0.0-1.0:

```python
def segment_helpfulness(segment: ConsolidatedSegment, current_turn: int) -> float:
    """Heuristic helpfulness score. Higher = more helpful = compact last."""

    # 1. Recency: recent segments are more likely to be referenced
    age = current_turn - segment.turn_range[1]
    recency = max(0.0, 1.0 - age / 20.0)  # linear decay over 20 turns

    # 2. Reference density: segments that contain identifiers/paths
    #    referenced in recent turns are more helpful
    # (requires tracking identifier overlap — see below)
    ref_density = compute_reference_overlap(segment, recent_turns)

    # 3. Outcome signal: segments from successful sub-tasks are more
    #    likely to contain reusable patterns
    outcome = segment.reward_signals.on_scope if hasattr(segment, 'reward_signals') else 0.5

    # 4. Content type: code/error segments are more text-sensitive
    #    than exploration/navigation segments
    content_sensitivity = estimate_text_sensitivity(segment)

    # Weighted combination
    return (0.3 * recency
          + 0.3 * ref_density
          + 0.2 * outcome
          + 0.2 * content_sensitivity)
```

**Reference overlap computation** (the key insight from Skill0's Δ_k):

```python
def compute_reference_overlap(segment: ConsolidatedSegment,
                               recent_turns: list[TurnRecord],
                               window: int = 5) -> float:
    """Measure how many identifiers in recent turns appear in this segment.
    High overlap = segment is actively referenced = high helpfulness."""
    # Extract identifiers: file paths, function names, variable names,
    # error codes, commit hashes
    segment_ids = extract_identifiers(segment.consolidated)
    recent_ids = set()
    for turn in recent_turns[-window:]:
        recent_ids.update(extract_identifiers(turn.raw_content))

    if not recent_ids:
        return 0.0
    return len(segment_ids & recent_ids) / len(recent_ids)
```

**Approach B — LLM-based scoring (expensive, for eval/calibration only)**:

For calibrating the heuristic weights, use Claude-as-Judge to score true helpfulness:
1. Present a follow-up task from the session
2. Provide all segments EXCEPT segment k → measure accuracy
3. Provide all segments INCLUDING segment k → measure accuracy
4. `Δ_k = accuracy_with - accuracy_without`

This mirrors Skill0's ground-truth Δ_k measurement. Run on the same 20 session logs used in Phase 2a to calibrate the heuristic weights against ground truth.

**Compaction priority algorithm** (adapted from Skill0 Algorithm 1):

```python
def prioritized_compaction(segments: list[ConsolidatedSegment],
                            budget_tokens: int,
                            current_turn: int) -> list[ConsolidatedSegment]:
    """Compact segments in order of ascending helpfulness until budget met.
    Mirrors Skill0's filter → rank → select pipeline."""

    # Step 1: Score all segments
    scored = [(seg, segment_helpfulness(seg, current_turn)) for seg in segments]

    # Step 2: Filter — never compact segments with Δ > threshold
    #   (threshold from Phase 2b free-zone sweep)
    PRESERVE_THRESHOLD = 0.8  # calibrate from Phase 2b
    compactable = [(seg, h) for seg, h in scored if h < PRESERVE_THRESHOLD]
    preserved = [seg for seg, h in scored if h >= PRESERVE_THRESHOLD]

    # Step 3: Rank — sort compactable by ascending helpfulness (least helpful first)
    compactable.sort(key=lambda x: x[1])

    # Step 4: Compact until budget satisfied
    tokens_freed = 0
    for seg, h in compactable:
        if tokens_freed >= budget_tokens:
            preserved.append(seg)
        else:
            compacted = aggressive_compact(seg)  # L3-L4 from Phase 2b sweep
            tokens_freed += len(seg.consolidated) - len(compacted)
            seg.consolidated = compacted

    return segments  # modified in-place
```

**Code Changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/graph/session_log.py` | Add `segment_helpfulness()`, `compute_reference_overlap()`, `extract_identifiers()`, `prioritized_compaction()` |
| `epyc-orchestrator/src/features.py` | Add `helpfulness_scoring` flag (default off, env `ORCHESTRATOR_HELPFULNESS_SCORING`) |
| `epyc-inference-research/scripts/benchmark/eval_helpfulness_calibration.py` | **CREATE** — LLM-based Δ_k ground truth measurement for calibrating heuristic weights |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for helpfulness scoring, reference overlap, prioritized compaction ordering |

**Feature flag**: `helpfulness_scoring` (default off, env `ORCHESTRATOR_HELPFULNESS_SCORING`)

**Acceptance criteria (2c)**:
- Heuristic scoring produces differentiated scores across segments (not all identical)
- Prioritized compaction compacts low-helpfulness segments first (verifiable from telemetry)
- LLM-based calibration script produces Δ_k ground truth for at least 10 session logs
- Heuristic scores correlate with LLM-based Δ_k (Spearman ρ > 0.5 on calibration set)
- Telemetry logs per-segment helpfulness scores at each compaction event

**Depends on**: Phase 1 (needs segment architecture), Phase 2a (needs quality evaluation infra), Phase 2b (free-zone thresholds feed PRESERVE_THRESHOLD)
**Cross-reference**: Shares eval methodology with `reasoning-compression.md` (TrimR evaluation uses same `eval_trimr.py` pattern and Claude-as-Judge scoring)

---

## Phase 3 — Process Reward Telemetry & Role-Aware Compaction

**Objective**: (a) Log FoldGRPO-analog process reward signals per turn, (b) compute position-weighted segment advantages at consolidation boundaries, (c) parameterize compaction aggressiveness by orchestrator role, and (d) implement intermittent reward scheduling informed by AgentOCR's findings. This is pure telemetry + policy configuration — no model training.

**Status**: Not started (scope expanded 2026-04-05 with role-aware compaction from intake-261/262 deep dive)

**Rationale**: Context-Folding's FoldGRPO uses three process reward signals to train fold/expand decisions. ReSum's advantage broadcasting solves credit assignment across summary boundaries. By logging these signals now, we build the training data needed for future RL-based compaction decisions, and provide a `segment_advantage` signal usable by MemRL Q-value enrichment (see routing-intelligence.md Phase 5).

**New rationale (2026-04-05)**: Two findings from the intake-261/262 deep dive expand this phase:

1. **Role-aware compaction aggressiveness**: AgentOCR (arxiv:2601.04786, intake-262) demonstrates that text-sensitive tasks degrade ~3x faster than scene-understanding tasks under compression: Search-QA drops to 66.8% at 2x compression while ALFWorld retains 87.2%. Our orchestrator roles have analogous sensitivity profiles — `worker_coder` handles exact identifiers, line numbers, and error messages (high text sensitivity), while `worker_explore` handles navigation and summarization (lower sensitivity). Compaction aggressiveness must be role-parameterized.

2. **Intermittent reward scheduling**: AgentOCR found that applying compression rewards every iteration (K=1) causes runaway compression collapse (45.3% success vs 78.2% at K=5). Both Skill0 and AgentOCR independently converge on the same reward structure: `r_compression = ln(c_t) * I_success` with λ weighting, applied intermittently. For our quality-aware compaction, this means: do NOT re-evaluate compaction quality every turn. Evaluate periodically (every K consolidation events) to avoid the system over-optimizing for compression at the expense of quality.

### Phase 3a — Process Reward Telemetry (unchanged)

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

### Phase 3b — Role-Aware Compaction Profiles

**Objective**: Define per-role compaction profiles that control how aggressively each orchestrator role compacts its session history. Roles handling text-sensitive work (coding, debugging) get conservative profiles; roles handling exploratory work get aggressive profiles.

**Literature basis**:
- AgentOCR (arxiv:2601.04786, intake-262): Task-type sensitivity data. At 2x compression: ALFWorld (visual/spatial) retains 87.2%, Search-QA (text reasoning) retains 66.8%. At 1.2x: both retain >95%. The gap widens with compression — text-sensitive tasks have a steeper degradation curve.
- Skill0 (arxiv:2604.02268, intake-261): Budget schedules are task-specific: [6,3,0] for ALFWorld (6 skills → 3 → 0), [5,3,0] for Search-QA. The tighter initial budget for Search-QA reflects its higher text sensitivity.

**Design**: A `CompactionProfile` per orchestrator role, keyed in config.

```python
@dataclass
class CompactionProfile:
    """Role-specific compaction parameters."""
    role: str
    # Maximum compression level (from Phase 2b sweep: L1-L5)
    max_compression_level: int  # 1-5
    # Free-zone threshold — compress up to this ratio without quality check
    free_zone_ratio: float  # e.g., 0.2 = 20% reduction is always safe
    # Helpfulness threshold — never compact segments scoring above this
    preserve_threshold: float  # 0.0-1.0
    # How many consolidation events between quality checks
    quality_check_interval: int  # K from AgentOCR (recommended: 5)

# Default profiles — calibrate from Phase 2b sweep results
COMPACTION_PROFILES = {
    "worker_coder": CompactionProfile(
        role="worker_coder",
        max_compression_level=2,   # max L2 (40%) — code is text-sensitive
        free_zone_ratio=0.20,      # 20% always safe for code
        preserve_threshold=0.7,    # aggressive preservation
        quality_check_interval=5,  # check every 5th consolidation
    ),
    "worker_explore": CompactionProfile(
        role="worker_explore",
        max_compression_level=3,   # L3 (60%) — exploration is less sensitive
        free_zone_ratio=0.40,      # 40% safe for navigation/search
        preserve_threshold=0.5,    # moderate preservation
        quality_check_interval=5,
    ),
    "worker_fast": CompactionProfile(
        role="worker_fast",
        max_compression_level=4,   # L4 (80%) — fast worker = short context
        free_zone_ratio=0.50,      # 50% safe for quick tasks
        preserve_threshold=0.3,    # minimal preservation
        quality_check_interval=3,  # more frequent for aggressive compression
    ),
    "architect": CompactionProfile(
        role="architect",
        max_compression_level=2,   # conservative — architect needs full picture
        free_zone_ratio=0.20,
        preserve_threshold=0.8,    # preserve most context
        quality_check_interval=7,  # less frequent
    ),
}
```

**Integration with Phase 2c helpfulness scoring**: The `preserve_threshold` from the profile feeds directly into `prioritized_compaction()`:

```python
def prioritized_compaction(segments, budget_tokens, current_turn, profile: CompactionProfile):
    # ... same as Phase 2c, but use profile.preserve_threshold
    PRESERVE_THRESHOLD = profile.preserve_threshold
    # ... and use profile.max_compression_level for aggressive_compact()
    compacted = compact_at_level(seg, profile.max_compression_level)
```

**Integration with Phase 1+ segment cache**: Cache entries are valid across roles — a `git status` output cached under `worker_coder` can be reused by `worker_explore`. The cache is role-agnostic; only the compaction policy is role-specific.

### Phase 3c — Intermittent Quality Monitoring

**Objective**: Implement periodic (not per-turn) quality monitoring for compaction decisions, informed by AgentOCR's finding that dense compression feedback causes collapse.

**Literature basis**:
- AgentOCR (arxiv:2601.04786, intake-262): Compression reward applied every iteration (K=1) → 45.3% success rate. Applied every 5th iteration (K=5) → 78.2%. This is a 72% improvement from simply reducing feedback frequency. The mechanism: dense feedback causes the policy to over-optimize for compression at the expense of task success, entering a degenerate low-quality equilibrium.
- Skill0 (arxiv:2604.02268, intake-261): Evaluates helpfulness every d=10 training steps. d=10 optimal; more frequent provides no quality gain and wastes compute.
- Both papers use the same reward shape: `r = ln(c_t) * I_success` — logarithmic (diminishing returns) and gated on task success (no reward for compression that breaks the task).

**Design**: A quality monitor that runs every K-th consolidation event, not every turn.

```python
class CompactionQualityMonitor:
    """Intermittent quality checker for compaction decisions.
    Runs every K consolidation events per role profile.
    Inspired by AgentOCR K=5 scheduling."""

    def __init__(self, profile: CompactionProfile):
        self.profile = profile
        self._consolidation_count = 0
        self._quality_history: list[float] = []

    def on_consolidation(self, segment: ConsolidatedSegment) -> None:
        """Called after each Tier 2 consolidation."""
        self._consolidation_count += 1

        if self._consolidation_count % self.profile.quality_check_interval != 0:
            return  # Skip — not a quality check turn

        # Compute quality signal (lightweight, no LLM call)
        quality = self._estimate_quality(segment)
        self._quality_history.append(quality)

        # Detect degradation trend
        if len(self._quality_history) >= 3:
            recent = self._quality_history[-3:]
            if all(q < 0.5 for q in recent):
                # Three consecutive low-quality consolidations
                # → reduce compression aggressiveness
                log_warning(f"Compaction quality degradation detected for "
                           f"{self.profile.role}: recent scores {recent}")
                # Signal to reduce max_compression_level by 1
                self._recommend_conservative()

    def _estimate_quality(self, segment: ConsolidatedSegment) -> float:
        """Lightweight quality estimation without LLM call.
        Uses compression ratio + information density heuristics."""
        input_tokens = sum(len(b.split()) for b in segment.granular_blocks)
        output_tokens = len(segment.consolidated.split())
        ratio = output_tokens / max(input_tokens, 1)

        # Suspiciously low ratio = likely lost information
        if ratio < 0.05:
            return 0.0
        # Ratio within expected range
        if 0.1 <= ratio <= 0.5:
            return 1.0
        # Borderline
        return 0.5
```

**Telemetry logged per quality check**:
- `compaction_quality_score` — estimated quality (0.0-1.0)
- `compaction_ratio` — actual compression ratio achieved
- `role` — which orchestrator role
- `consolidation_count` — how many consolidations since last check
- `degradation_alert` — boolean, True if trend detected

### Phase 3 Code Changes (all sub-phases)

| File | Change |
|------|--------|
| `epyc-orchestrator/src/features.py` | Add `process_reward_telemetry` flag (default off, env `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY`); add `role_aware_compaction` flag (default off, env `ORCHESTRATOR_ROLE_AWARE_COMPACTION`) |
| `epyc-orchestrator/src/graph/session_log.py` | Extend `TurnRecord` with `token_budget_ratio`, `on_scope`, `tool_success_ratio` fields; add `compute_segment_advantage()`; add `CompactionProfile`, `COMPACTION_PROFILES`, `CompactionQualityMonitor` |
| `epyc-orchestrator/src/graph/helpers.py` | Populate reward fields in `TurnRecord` construction; call `log_process_reward()` at consolidation boundaries; select `CompactionProfile` based on current role; instantiate `CompactionQualityMonitor` per session |
| `epyc-orchestrator/src/config/models.py` | Add `compaction_profiles_override: dict` for per-deployment profile tuning |
| `epyc-orchestrator/orchestration/repl_memory/progress_logger.py` | Add `log_process_reward()`, `log_compaction_quality()` (same pattern as `log_delegation()`) |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for reward computation, segment advantage, compaction profiles, quality monitor |

**Feature flags**:
- `process_reward_telemetry` (default off, env `ORCHESTRATOR_PROCESS_REWARD_TELEMETRY`) — Phase 3a
- `role_aware_compaction` (default off, env `ORCHESTRATOR_ROLE_AWARE_COMPACTION`) — Phase 3b+3c

**Acceptance criteria**:
- Feature flags off: zero behavior change, no reward computation, no role-aware logic
- `process_reward_telemetry` on: all three signals logged per turn via `log_process_reward()`; `segment_advantage` computed and logged at every Tier 2 consolidation boundary
- `role_aware_compaction` on: correct `CompactionProfile` selected per role; quality monitor fires every K-th consolidation event; degradation alerts logged when quality drops
- Telemetry visible in `logs/agent_audit.log` and inference tap
- No latency impact (all computation is O(1) per turn, no LLM calls; quality monitor runs on a subsampled schedule)
- Default profiles produce differentiated behavior: `worker_coder` compacts less aggressively than `worker_explore`

**Depends on**: Phase 1 (needs consolidation boundaries for segment advantage), Phase 2b (free-zone thresholds feed profile defaults), Phase 2c (helpfulness scores feed compaction priority)
**Parallel with**: Phase 2a (SFT data collection is independent of role-aware compaction)
**Cross-reference**: `segment_advantage` signal feeds into MemRL Q-value enrichment tracked in `routing-intelligence.md` Phase 5. ReSum-GRPO's position-weighted advantage broadcasting is applicable to delegation episode training.

---

## Cross-References

| Handoff | Relationship |
|---------|-------------|
| `reasoning-compression.md` | Phase 2a shares eval methodology (Claude-as-Judge scoring, `eval_trimr.py` pattern); SFT data collection mirrors TrimR pattern |
| `routing-intelligence.md` | Phase 3a `segment_advantage` feeds Phase 5 MemRL Q-value enrichment; advantage broadcasting applicable to delegation episodes |
| `tool-output-compression.md` | Phase 1+ segment dedup complements RTK upstream compression; both reduce redundant content but at different layers (RTK pre-context, dedup post-segment) |
| `orchestrator-conversation-management.md` | Phase 3b role-aware profiles must align with B2 context compression policy; CompactionProfile roles must match conversation management's role taxonomy |
| ~~`rlm-orchestrator-roadmap.md`~~ | ARCHIVED 2026-03-29 — D1 Context Compaction superseded by this handoff |
| `routing-and-optimization-index.md` | Phase 0-1 should precede autoresearch baseline (P5-AR-1); Phase 3 process rewards tracked as upstream dependency (concern #7) |

### Research Paper Cross-References

| Paper | arXiv | Intake | Phases | What we use |
|-------|-------|--------|--------|-------------|
| AgentFold | 2510.24699 | intake-155 | 0, 1, 2a | Delay compaction, two-level condensation, SFT collection |
| MemAgent | 2504.02861 | intake-156 | 1 | Segment-based reading with overwrite |
| Context-Folding | 2510.11967 | intake-154 | 2a, 3a | Summarizer quality eval, FoldGRPO process rewards |
| ReSum | 2509.13313 | intake-157 | 3a | Position-weighted advantage broadcasting |
| Skill0 | 2604.02268 | intake-261 | 2b, 2c, 3b | Helpfulness-driven scoring (Δ_k), free-zone methodology, role-aware budget schedules |
| AgentOCR | 2601.04786 | intake-262 | 1+, 2b, 3b, 3c | Hash-based segment dedup, free-zone threshold (c_t ≤ 1.2), task-type sensitivity, intermittent reward scheduling (K=5) |
| RLM | 2512.24601 | intake-153 | background | Foundational architecture (EPYC implements ~80%) |
| RTK | — | intake-259 | 1+ (context) | Upstream tool output compression, dedup-with-counts pattern |
| CC Repo Leak | — | intake-249 | 1 (context) | Prompt cache boundary engineering |
| CC Unshipped | — | intake-247 | 1 (context) | CONTEXT_COLLAPSE multi-strategy, HISTORY_SNIP surgical removal |

---

## Verification

```bash
# Phase 0: config change
python3 -c "from src.config import get_config; assert get_config().session_compaction_trigger_ratio == 0.75"

# Phase 1: two-level condensation tests
python3 -m pytest tests/unit/test_session_log.py -v -k "condensation or granular or consolidat"

# Phase 1+: segment cache dedup tests
python3 -m pytest tests/unit/test_session_log.py -v -k "cache or dedup or normalize"

# Phase 2a: eval script dry-run
python3 scripts/benchmark/eval_summarizer.py --dry-run

# Phase 2b: compaction sweep dry-run
python3 scripts/benchmark/eval_compaction_sweep.py --dry-run --levels 1,3,5

# Phase 2c: helpfulness scoring tests
python3 -m pytest tests/unit/test_session_log.py -v -k "helpfulness or reference_overlap or prioritized"

# Phase 2c: helpfulness calibration (expensive — LLM-based)
python3 scripts/benchmark/eval_helpfulness_calibration.py --sessions 5 --dry-run

# Phase 3a: reward telemetry tests
python3 -m pytest tests/unit/test_session_log.py -v -k "reward or advantage"

# Phase 3b: role-aware compaction profile tests
python3 -m pytest tests/unit/test_session_log.py -v -k "profile or role_aware"

# Phase 3c: quality monitor tests
python3 -m pytest tests/unit/test_session_log.py -v -k "quality_monitor or degradation"

# Full gate
python3 -m pytest tests/unit/ -x -q
```

## Research Intake Update — 2026-04-01

### New Related Research
- **[intake-249] "Claude Code Repo Leak Analysis — Prompt Cache Boundary Engineering"**
  - Pattern: **SYSTEM_PROMPT_DYNAMIC_BOUNDARY**. CC splits the system prompt into a stable front half (cached across turns) and a dynamic back half (varies per session). Two mechanisms: `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marks the split point; `DANGEROUS_uncachedSystemPromptSection` flags sections that change often and must not be cached blindly.
  - Delta from current approach: Our `resolve_prompt()` in `resolver.py` loads prompt templates on every request without optimizing for cache boundaries. For local llama.cpp inference, the analogue is KV cache prefix sharing — if the first N tokens of the prompt are identical across requests, the KV cache for those tokens can be reused. For API calls (autopilot controller using Claude), this directly reduces cost.
  - Concrete adoption (local inference): Structure `orchestration/prompts/*.md` so the stable content (role definition, tool descriptions, operating constraints) comes first and session-variable content (task description, user message, context window) comes last. This maximizes KV cache prefix hits across requests to the same model.
  - Concrete adoption (API calls): When the autopilot controller calls Claude API, ensure the system prompt prefix is identical across iterations. Move per-iteration content (current experiment, evaluation results) to the user message, not the system prompt.
  - Synergy with Phase 1: The two-level condensation (granular + deep) should preserve the stable prompt prefix when compacting — never fold role definitions or tool descriptions into the summary.
  - Effort: Low for prompt restructuring. Medium for llama.cpp prefix caching investigation (need to verify `--cache-reuse` or similar flag behavior).

- **[intake-247] "Claude Code Unshipped Features — Multi-Strategy Compaction"**
  - Pattern: **CONTEXT_COLLAPSE** — CC has 3 compaction strategies vs our 1. (1) Reactive: on-demand when context overflows. (2) Micro: incremental trimming of low-value content without full recompression. (3) Context inspection: a tool the agent can invoke to examine its own context state.
  - Pattern: **HISTORY_SNIP** — surgical removal of specific conversation history segments without full compaction. Removes a single large tool output or failed experiment trace while preserving everything else.
  - Delta: We have single-level compaction triggered at 60% context fill. No incremental trimming, no surgical removal, no agent-inspectable context state.
  - Relevance to Phase 1: HISTORY_SNIP maps to Phase 1's "segment-based reading with overwrite" from MemAgent (intake-156). Micro-compaction maps to the "granular condensation" tier. CONTEXT_COLLAPSE's 3-strategy approach validates the multi-tier direction this handoff is already pursuing.
  - Concrete adoption: Phase 1 should implement HISTORY_SNIP as a byproduct — the segment-based architecture naturally supports removing individual segments. Add a `trim_segment(segment_id)` API alongside the full `compact()` call.

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-259] "RTK — Rust Token Killer"** (https://github.com/rtk-ai/rtk)
  - Relevance: CLI proxy that reduces LLM token consumption by 60-90% on common dev commands (ls, git, cargo test, etc.) via smart filtering, grouping, truncation, and deduplication. 17.3k GitHub stars, active development.
  - Key technique: Pre-model input compression — rewrites shell command outputs before they enter the context window. Four strategies: noise removal, categorical grouping, smart truncation, line deduplication with counts. <10ms overhead per command.
  - Reported results: 80% reduction on file listings, 70% on file reads, 90% on test output. Typical 30-min session: 118K→24K tokens.
  - Delta from current approach: Our context-folding operates at the session level (compacting conversation history). RTK operates upstream — compressing tool outputs before they enter the context at all. These are complementary layers: RTK shrinks inputs, context-folding compresses the accumulation. Together they could multiplicatively reduce context pressure.
  - Integration path: RTK ships as a Claude Code PreToolUse hook. Could be deployed as a harness hook in our autopilot infrastructure to reduce token costs on Claude API calls. Also relevant for local llama.cpp sessions where context windows are constrained (8K-32K).

## Research Intake Update — 2026-04-05

### New Related Research
- **[intake-261] "Skill0: In-Context Agentic Reinforcement Learning for Skill Internalization"** (arxiv:2604.02268)
  - Relevance: Trains agents to internalize context-dependent skills into model parameters via RL, progressively removing skill context during training. Directly validates our multi-tier compaction direction — both approaches address the core tension between context-dependent and autonomous behavior.
  - Key technique: In-Context RL (ICRL) with helpfulness-driven dynamic curriculum. Skills are provided during training, then withdrawn when the policy no longer benefits. Achieves +9.7% ALFWorld, +6.6% Search-QA over baselines with ultra-low inference overhead (0.38k tokens/step vs 2.21k for SkillRL).
  - Delta from current approach: Our context-folding compresses accumulated history at inference time. Skill0 eliminates context dependency entirely via training-time internalization. These represent complementary strategies: context-folding for serving (where models are fixed), Skill0-style curriculum for fine-tuning (where models can be updated). The dynamic curriculum idea could inform how we schedule compaction aggressiveness.
- **[intake-262] "AgentOCR: Reimagining Agent History via Optical Self-Compression"** (arxiv:2601.04786)
  - Relevance: Converts textual agent histories to compact rendered images, reducing token consumption >50% while retaining >95% performance. Agent learns adaptive compression rates via RL.
  - Key technique: Segment optical caching decomposes history into hashable segments with visual cache (20x rendering speedup). Agentic self-compression lets the agent emit its own compression rate per step.
  - Delta from current approach: Our compaction produces text summaries. AgentOCR converts text to images — a radically different modality. Not directly applicable to our text-only llama.cpp stack, but the segment-based caching architecture and adaptive compression rate concepts are transferable to our segment-based compaction design.
