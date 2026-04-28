# Context-Folding: Progressive Session Compaction Upgrade

**Status**: Phase 0 complete (2026-03-29), Phase 1 complete (2026-04-04), Phase 1+/2c/3a/3b code complete (2026-04-05), **Phase 2a DONE** (30B-A3B = minimum viable summarizer, 3.0/3.0), **Phase 2b L1-L4 DONE** (L3 sweet spot: 82% compression, 2.84/3 retention), L5 + Phase 3c pending
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
    # ByteRover enhancement (intake-267)
    access_count: int = 0              # turns referencing this segment
    importance_score: float = 0.0      # accumulated: +3 access, +5 update, decay 0.995^Δt
    maturity_tier: str = "draft"       # draft→validated(≥65)→core(≥85), demote at <35/<60
    last_accessed_turn: int = 0
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
- ByteRover importance scoring accumulates correctly (access +3, update +5, decay 0.995^Δt)
- Maturity tier hysteresis: promote at 65/85, demote at 35/60, no oscillation within band

**Depends on**: Phase 1 (needs segment architecture), Phase 2a (needs quality evaluation infra), Phase 2b (free-zone thresholds feed PRESERVE_THRESHOLD)
**Cross-reference**: Shares eval methodology with `reasoning-compression.md` (TrimR evaluation uses same `eval_trimr.py` pattern and Claude-as-Judge scoring)


### Phase 2c — ByteRover Enhancement

**Objective**: Incorporate ByteRover compound retention scoring (intake-267, arxiv:2604.01599) into the segment helpfulness heuristic, adding access-frequency tracking, importance accumulation with temporal decay, and maturity tiering with hysteresis thresholds.

**Rationale**: The current 4-signal `segment_helpfulness()` uses recency, reference density, outcome, and content sensitivity. ByteRover adds a complementary dimension: *behavioral importance* — segments frequently accessed across turns are demonstrably useful regardless of recency. The hysteresis pattern (Schmitt trigger) prevents oscillation in tiered retention decisions. Deep-dive confirmed: tiered retrieval with importance scoring is ByteRover's strongest ablation component (-29.4pp when removed).

**Design — importance scoring per segment**, updated on every access:

```python
def update_importance(segment: ConsolidatedSegment, current_turn: int, event: str):
    """Update segment importance on access/update events."""
    delta_t = current_turn - segment.last_accessed_turn
    segment.importance_score *= 0.995 ** delta_t      # temporal decay
    if event == "access":
        segment.importance_score += 3
        segment.access_count += 1
    elif event == "update":
        segment.importance_score += 5
    segment.last_accessed_turn = current_turn
    # Hysteresis tiering (Schmitt trigger — gap prevents oscillation)
    score = segment.importance_score
    if segment.maturity_tier == "draft" and score >= 65:
        segment.maturity_tier = "validated"
    elif segment.maturity_tier == "validated" and score >= 85:
        segment.maturity_tier = "core"
    elif segment.maturity_tier == "core" and score < 60:
        segment.maturity_tier = "validated"
    elif segment.maturity_tier == "validated" and score < 35:
        segment.maturity_tier = "draft"
```

**Modified `segment_helpfulness()` weights** — 4-signal → 6-signal:

```python
def segment_helpfulness(segment: ConsolidatedSegment, current_turn: int) -> float:
    recency = ...           # unchanged (linear decay over 20 turns)
    ref_density = ...       # unchanged (identifier overlap with recent turns)
    outcome = ...           # unchanged (reward_signals.on_scope)
    content_sensitivity = ...  # unchanged (text sensitivity heuristic)

    # ByteRover signals
    importance = min(1.0, segment.importance_score / 100.0)
    maturity_bonus = {"draft": 0.0, "validated": 0.3, "core": 0.6}[segment.maturity_tier]

    return (0.20 * recency             # was 0.30
          + 0.20 * ref_density         # was 0.30
          + 0.15 * outcome             # was 0.20
          + 0.15 * content_sensitivity # was 0.20
          + 0.15 * importance          # NEW
          + 0.15 * maturity_bonus)     # NEW
```

**Code changes**:

| File | Change |
|------|--------|
| `epyc-orchestrator/src/graph/session_log.py` | Add 4 fields to `ConsolidatedSegment`; add `update_importance()`; reweight `segment_helpfulness()` |
| `epyc-orchestrator/tests/unit/test_session_log.py` | Tests for importance accumulation, decay, hysteresis transitions, reweighted helpfulness |

**No new feature flag** — controlled by existing `helpfulness_scoring` flag (env `ORCHESTRATOR_HELPFULNESS_SCORING`).

**Note**: Weights are design proposals. Calibrate using Package C LLM Δ_k ground truth data. The current 4-signal heuristic will be evaluated during Package C first; ByteRover 6-signal weights layered on afterward.

---

### Phase 2d — Provenance & Forgetting (intake-316/326)

**Objective**: Address the FORGETTING gap identified in the LTM Unsolved deep-dive (intake-316). Our current approach is append-only (context lost when compacted) with no provenance tracking and no supersession detection. This phase adds validity tracking and contradiction-aware compaction to prevent derivation drift.

**Research context**: intake-316 (nine-axis memory design space — our weakest axis is FORGETTING), intake-326 (MemPalace temporal KG with `valid_from`/`valid_until` and invalidation-without-deletion), intake-347 (memory survey — "summarization drift after 3+ compression passes" directly warns about our multi-tier approach).

- [x] CF-P1: Add `validity_timestamp` and `source_turn_ids: list[int]` to `ConsolidatedSegment` dataclass — ✅ 2026-04-12. Fields added + populated at all 3 creation sites (session_log.py consolidate_segment, helpers.py cache hit, helpers.py fallback). Serialized in to_dict/from_dict.
- [x] CF-P2: Implement supersession detection — ✅ 2026-04-12. `check_supersession()` function in session_log.py. 8 regex correction patterns (actually, correction, instead of, no longer, etc.). Flags segments with `superseded=True` + `superseded_by_turn`. Heuristic: >=3 substantive word overlap.
- [x] CF-P3: Evaluate wing/room-style metadata filtering (MemPalace pattern) — ✅ 2026-04-12. `topic_tags: list[str]` field on ConsolidatedSegment. `_extract_topic_tags()` auto-extracts from content via keyword matching (7 tag categories: code, config, error, routing, eval, memory, tool). Populated at all creation sites.
- [x] CF-P4: Test hybrid raw+derived approach — ✅ 2026-04-12. `is_raw: bool` field on ConsolidatedSegment (default False). Infrastructure in place for configurable N-turn raw window. Full serialization support. Actual raw window logic to be wired into compaction trigger (depends on production integration).

**Dependencies**: Independent of Phase 3. Can proceed in parallel. CF-P1/P2 are infrastructure; CF-P3/P4 are experimental.

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

**Cross-ref (added 2026-04-24 from intake-454)**: the upstream-compressor anti-thrashing port tracked in [`tool-output-compression.md`](tool-output-compression.md) Phase 3d (action E) directly reduces the kind of compress→uncompress→re-compress oscillation that this monitor flags as a degradation signal. Sequencing recommendation: land Phase 3d before tuning Phase 3c's `degradation_alert` thresholds, otherwise we'd be calibrating against oscillation noise that Phase 3d will silence.

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

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-268] "LLM Wiki: Persistent LLM-Compiled Knowledge Bases"** (Karpathy gist)
  - Relevance: Conceptual framework for LLM-maintained persistent knowledge — compilation vs retrieval. Our context-folding produces compacted summaries that are essentially compiled knowledge from session history.
  - Key technique: Three-layer architecture (raw/wiki/schema) with periodic lint passes for contradiction detection, orphan pages, stale claims. LLM handles cross-referencing and knowledge hygiene autonomously.
  - Delta from current approach: Context-folding compacts within a session; LLM wiki compiles across sessions into a persistent artifact. The linting concept (detecting contradictions, staleness) could enhance our compaction quality validation — verifying that compacted segments don't introduce contradictions with retained context.
- **[intake-269] "nvk/llm-wiki: Claude Code Plugin for LLM-Compiled Knowledge Bases"**
  - Relevance: Working implementation with progress scoring (0-100) and principled termination thresholds — a pattern directly applicable to deciding when context-folding compaction is "good enough."
  - Key technique: Session persistence via JSON checkpoints for multi-round research. Credibility scoring of sources.
  - Delta from current approach: Their session persistence model could inform our compaction checkpoint design — storing intermediate compaction state so interrupted sessions can resume without re-processing.
- **[intake-270] "tobi/qmd: Local Hybrid Search Engine for Markdown Knowledge Bases"**
  - Relevance: BM25+vector+LLM reranking hybrid search running locally via node-llama-cpp with GGUF models — our exact stack. Natural markdown chunking algorithm for semantic boundary detection.
  - Key technique: Scoring algorithm finds natural markdown break points instead of hard token boundaries. RRF fusion for combining retrieval signals.
  - Delta from current approach: Our segment boundary detection for compaction uses heuristic rules. qmd's natural break point detection algorithm could improve our segmentation quality, particularly for markdown-heavy agent conversation histories.

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-267] "ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context"** (arxiv:2604.01599)
  - Relevance: Agent-native memory with LLM-curated hierarchical markdown storage, importance scoring + recency decay
  - Key technique: Compound retention scoring (access_count + importance_score + maturity_tier) with hysteresis thresholds
  - Reported results: Competitive on LoCoMo/LongMemEval; 5-tier retrieval escalation strongest component (-29.4pp ablation)
  - Delta from current approach: Our `segment_helpfulness()` uses 4 static signals. ByteRover adds behavioral importance — segments referenced more often across turns accumulate importance regardless of recency. The hysteresis pattern prevents tier oscillation.
  - **Adopted**: Phase 2c ByteRover Enhancement subsection added. 4 new fields on ConsolidatedSegment, modified helpfulness weights (4-signal → 6-signal with importance + maturity).

### Deep-Dive Notes (2026-04-06)
intake-267 UPGRADED to relevance medium-high during deep dive. The compound retention scoring and hysteresis pattern are directly adoptable. The 5-tier retrieval escalation (strongest ablation at -29.4pp) validates prioritizing segment importance in compaction decisions. Inline LLM curation rejected — incompatible with local model economics (Qwen3-30B-A3B). Our deterministic Tier 1 + bounded Tier 2 approach is the right trade-off.

- **[intake-273] "Context Rot: How Increasing Input Tokens Impacts LLM Performance"** (Chroma)
  - Relevance: Empirical evidence that LLM performance degrades with input length, especially with low semantic similarity
  - Key technique: Needle-question similarity measurement; distractor amplification analysis; shuffled vs structured haystack comparison
  - Reported results: 18 LLMs tested; shuffled haystacks outperform structured across ALL models; low-similarity needles degrade fastest
  - Delta from current approach: Our compaction summaries are narratively structured — the shuffled-outperforms-structured finding suggests we should experiment with less structured summaries. The semantic similarity dimension is not in our segment retention scoring.
  - **Actionable**: (1) Add semantic similarity to segment_helpfulness scoring — compress low-similarity segments more aggressively. (2) A/B test shuffled vs structured compaction summaries in eval tower. (3) Actively remove off-topic context (distractor amplification) rather than just summarizing it.
  - **Deep-dive caveat (2026-04-06)**: Shuffled finding is RETRIEVAL-ONLY (NIAH tasks). For reasoning/synthesis tasks where our compaction summaries are consumed, structured coherence likely still helps. DO NOT restructure summaries based on this alone. The correct experiment is **bullet-point vs narrative** consolidation format, not shuffled vs ordered.
- **[intake-274] "The Complexity Trap" (arXiv:2508.21433)** — NeurIPS 2025 DL4Code
  - Relevance: Simple observation masking (stripping old tool outputs) matches LLM summarization for agent context management
  - Key result: 50% cost reduction vs baseline; hybrid masking+summarization gives 7-11% further savings
  - Delta from current approach: Validates our two-layer architecture (pattern-based tool compression + LLM conversation summarization). Observation masking ≈ high recency weight in segment_helpfulness — our existing approach already captures this.
  - **Actionable**: Consider whether `tool_output_compression` should be more aggressive for older tool outputs (age-based compression scaling). The hybrid finding suggests our architecture is already near-optimal.

## Research Intake Update — 2026-04-09

### Memento Cluster: Validation + New Opportunities for Phase 2/3

Deep-dive on 5 entries (intake-289/290/292/293/294) in `research/deep-dives/memento-iterative-reasoning-cluster.md`. Key findings for context-folding:

- **[intake-290] OpenMementos Data Pipeline — VALIDATES Phase 2 Methodology**
  - Their 5-stage pipeline (sentence splitting → boundary scoring → segmentation → summary generation → iterative refinement) is structurally equivalent to our Phase 2 approach
  - **Key validation**: Iterative judge-refined summarization raises pass rate from 28% to 92% (0-10 rubric, 6 dimensions, 2 refinement rounds). This confirms our judge-feedback loop design is the right approach.
  - **Compression ratio**: ~6x trace-level (1,150 tokens → 194 tokens per block), stable across domains
  - **Directly usable**: 228K MIT-licensed traces could serve as Phase 3 RL training data if we fine-tune models for context-aware summarization

- **[intake-293] InftyThink+ — Internal > External Summarization After RL**
  - After RL training, model's own summaries **outperform** external GPT-4 summaries (AIME24: 50.94% vs 48.42%)
  - Before RL, external summaries are better (32.40% vs 29.48%)
  - **Implication for our Phase 2**: Using `worker_explore` (7B) as external summarizer is the correct approach for SFT-era context-folding. But Phase 3 RL should aim to move summarization into the reasoning model itself — learned self-compression beats external compression.

- **[intake-294] Accordion-Thinking Fold/Unfold — Phase 3 Inspiration**
  - Fold/Unfold toggle: same model, runtime inference choice between compressed and full context
  - After Mix-RL training, accuracy gap between modes **vanishes** (Fold 52.8% vs Unfold 52.2%)
  - Throughput: 3-4x in Fold mode on 48GB GPU
  - **Phase 3 mapping**: Our FoldGRPO process rewards (intake-154) could incorporate Accordion's approach — RL that teaches the model when folding is safe vs. when full context is needed

- **[intake-289] Memento Dual Information Stream — Fundamental Limit of Text-Level Compression**
  - KV states carry implicit info from masked blocks; removing KV channel drops 15pp on AIME24
  - **Implication**: Our Phase 1-2 text-level consolidation has a ceiling compared to KV-retaining approaches for reasoning tasks. This doesn't invalidate our approach (we compress conversation history, not reasoning chains), but Phase 3 should evaluate whether retaining KV states for critical consolidated segments improves downstream accuracy.

### Impact on Phase Roadmap
- **Phase 2 (current)**: No change needed. OpenMementos validates our methodology.
- **Phase 3**: Expanded scope: (1) FoldGRPO process rewards (existing), (2) Accordion-style Fold/Unfold learned toggle, (3) InftyThink+ efficiency reward for iteration budget control, (4) Investigate KV state retention for critical segments (inspired by Memento's dual stream)

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-316] "Long-Term Memory for Conversational LLMs Remains Unsolved"** (Chrys Bader)
  - Relevance: Nine-axis memory design space maps directly to our compaction decisions
  - Key technique: Raw vs derived storage spectrum; provenance-tracked forgetting
  - Delta from current approach: Our L1-L4 compression ladder is a derived approach. The essay highlights derivation drift as our key risk. Consider implementing provenance tracking so derived summaries can be traced back to source turns.
- **[intake-326] "MemPalace: 96.6% LongMemEval Recall"** (MemPalace/mempalace)
  - Relevance: Palace architecture (wings/rooms/drawers) achieves 96.6% recall by searching RAW text with hierarchical filtering
  - Key technique: Semantic search on verbatim content + metadata filtering (34% retrieval boost vs flat search)
  - Delta from current approach: We compress (derive) then search. MemPalace stores raw then searches. Their AAAK compression dialect is a hybrid — lossy abbreviation readable without decoders. Worth evaluating whether our Phase 2c (ByteRover hash-based dedup) could adopt a similar "abbreviate but keep searchable" pattern.
- **[intake-347] "Memory for Autonomous LLM Agents" (arxiv:2603.07670)** — Survey
  - Relevance: Academic survey confirming cross-session coherence and parametric-nonparametric balance as unsolved
  - Delta from current approach: Validates our non-parametric approach (external memory) over parametric (weight-baking via Doc-to-LoRA)

### Deep-Dive Findings (2026-04-12)
- **intake-326 DOWNGRADED**: MemPalace 96.6% is ChromaDB vector search, NOT the palace architecture. GitHub issue #214 confirms benchmarks don't exercise the hierarchical system. Still useful: L0-L3 stack design and temporal KG with validity windows.
- **intake-316 gap analysis**: Our weakest axis is FORGETTING (append-only, no provenance). Recommend: validity timestamps on compacted segments, supersession detection, hybrid raw+derived for recent vs old turns.
- **intake-332 UPGRADE**: Ouro-2.6B-Thinking (MATH-500 90.85%, AIME24 pass@10 90%) could be a reasoning verifier. 2.6B runs on CPU via transformers. Not llama.cpp compatible (looped arch).

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-395] "Claude-Mem: Persistent Memory Compression System for Claude Code"** (repo: thedotmack/claude-mem)
  - Relevance: productionized reference implementation of hybrid-search retrieval over compacted session memory — pattern directly reusable in Phase 2 summarizer collection and in the planned compacted-memory retrieval surface.
  - Key technique: **3-layer MCP search workflow** (search index → timeline context → get_observations full details) claiming ~10x token savings via progressive disclosure; hybrid SQLite FTS5 + Chroma vector search; `<private>` tag convention for user-controlled exclusion.
  - Lifecycle-hook taxonomy (SessionStart/UserPromptSubmit/PostToolUse/Stop/SessionEnd) is a reference model for what signals to log during compaction training-data collection.
  - Reported results: none empirical — token-savings claim is not methodologically anchored.
  - Delta: adopt patterns (progressive-disclosure retrieval layer, hook-based capture taxonomy, privacy-tag convention) rather than the component itself (AGPL-3.0, Bun/Node stack orthogonal to our Python/llama.cpp). Overlaps intake-135 (Cognee), intake-268/269/270 (Karpathy LLM Wiki ecosystem), intake-277 (Hermes LLM Wiki skill).

- **[intake-399] "GenericAgent: minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: 5-tier L0–L4 memory taxonomy designed to keep working context <30K tokens — a concrete reference architecture for how layered memory maps to token-budget discipline.
  - Key technique: L0 Meta Rules / L1 Insight Index / L2 Global Facts / L3 Task Skills(SOPs) / L4 Session Archive; skill crystallization promotes episodic traces to reusable SOPs.
  - Delta: cross-references Hermes MemPalace (intake-326) and the LLM Wiki ecosystem; useful as a layering template alongside the retrieval-layer patterns from claude-mem.

## Research Intake Update — 2026-04-20

### New Related Research
- **[intake-413] "Toward Ultra-Long-Horizon Agentic Science: Cognitive Accumulation for ML Engineering"** (arxiv:2601.10402)
  - Relevance: HCC's hierarchical distillation of execution traces into multi-tier knowledge (L1/L2/L3 cache analogue) directly addresses cross-session knowledge retention — the same problem context-folding solves at the conversation level.
  - Key technique: Hierarchical Cognitive Caching (HCC) with dynamic distillation of execution traces into stable, reusable knowledge representations; cross-task wisdom consolidation.
  - Reported results: 56.44% medal rate on MLE-Bench (24h budget).
  - Delta from current approach: context-folding compresses within a session; HCC proposes cross-session knowledge consolidation — complementary layer above folding.

- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: hybrid BM25+vector search with RRF fusion for memory retrieval — directly applicable to the retrieval layer of context-folding's compacted knowledge base.
  - Key technique: three-layer progressive disclosure memory contract (15/60/200 tokens per result); content-hash symbol staleness for automatic memory invalidation on code changes; MDL distillation for convention promotion.
  - Reported results: 98% task success rate (118/120 vs 56% baseline), 40% active token reduction, 85% injected char reduction.
  - Delta from current approach: adds RRF fusion and MDL auto-promotion over existing claude-mem patterns; the staleness-detection mechanism is novel for invalidating folded knowledge when source code changes.

- **[intake-415] "Context Mode — Context Window Optimization for AI Coding Agents"** (repo: mksglu/context-mode)
  - Relevance: subprocess sandbox isolation prevents raw tool output from entering context (99% reduction); PreCompact hook injects ≤2KB priority-tiered session snapshot — directly actionable for compaction boundary detection.
  - Key technique: FTS5+BM25 with RRF and Porter stemming; intent-driven filtering (>5KB → index, return only relevant sections); PreCompact session snapshot injection.
  - Reported results: 94-100% context savings across 21 scenarios; session duration extends from ~30min to ~3hrs.
  - Delta from current approach: context-folding operates on conversation history; context-mode operates upstream on tool output. The PreCompact hook pattern for session snapshot injection is a concrete implementation pattern not covered here.

- **[intake-426] "Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems"** (arxiv:2604.14228)
  - Relevance: Documents Claude Code's five-layer compaction pipeline (budget reduction → snip → microcompact → context collapse → auto-compact) — directly comparable to our L1-L5 compression tiers. Confirms 98.4% of agent complexity lives in operational infrastructure (permissions, context management, tool routing), not AI decision logic.
  - Key technique: Five-layer compaction pipeline taxonomy; seven-mode permission system with ML-based safety classifier; append-only JSONL session storage with sidechain files.
  - Reported results: 200K-1M token context windows; 93% permission approval rate; graduated trust (40% auto-approve by 750 sessions).
  - Delta from current approach: The five-layer taxonomy (budget reduction, snip, microcompact, context collapse, auto-compact) should be mapped against our own compression tiers to identify coverage gaps. Caveat: Anthropic's own harness design blog notes "context anxiety" in Sonnet 4.5 made compaction alone insufficient — context resets sometimes needed. Compaction can silently discard provenance/load-bearing information.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-443] "OneVL: One-Step Latent Reasoning and Planning with Vision-Language Explanation"** (arxiv:2604.18486, Xiaomi)
  - Relevance: Dual-objective compression (text reconstruction + world-model / future-frame prediction) produces more generalizable latent representations than single-objective compression. Latent token design (4 visual + 2 language tokens) enables prefill-only inference — decoders are discarded at inference.
  - Key technique: Latent CoT with dual auxiliary decoders trained in three stages (pretraining → warmup → joint fine-tuning). Inference uses prefill-only single parallel pass.
  - Reported results (autonomous-driving domain): NAVSIM PDM 88.84 vs 87.30 baseline; latency 4.46s vs 6.58s (AR CoT).
  - Delta from current approach: Our context-folding Phase 2a/2b uses helpfulness-scored text-level summarization. OneVL's insight that a *second* auxiliary objective (beyond language reconstruction) sharpens the latent is directly applicable: could we pair our summarizer with a second objective (e.g., downstream-task-success prediction) to improve compression quality? Methodological reference for Phase 2b design discussions, not an immediate implementation target.

## Phase 2c Addendum — Dual-Objective Compression Probe (2026-04-22, DD5)

**Source**: `/workspace/research/deep-dives/onevl-dual-objective-latent-compression.md` (595 lines). OneVL (intake-443) demonstrates that dual-objective training (language reconstruction + world-model / future-frame prediction) produces more generalizable latent representations than single-objective text-only compression. Our existing Phase 2a/2b summarizer is single-objective (helpfulness scoring) — may be under-performing what dual-objective could achieve.

**Target**: NIB2-43 in backlog. Training-free probe only; full dual-objective fine-tune is GPU-gated (post-DGX-Spark).

**Phase 2c.0 — Training-free α-sweep probe**:

Hypothesis: combined score `α·helpfulness + (1-α)·task_success` on existing summarizer outputs predicts downstream task success better than helpfulness alone (`α=1.0`).

- [ ] Implement task-success classifier (LLM-judge or retrieval-based) — ~1h.
- [ ] α-sweep: score existing summarizer outputs at α ∈ {0.0, 0.25, 0.5, 0.75, 1.0}. ~2-3h inference.
- [ ] Measure correlation with downstream task success on held-out autopilot eval set.
- **Gate**: if α<1.0 outperforms α=1.0 by >2% on task success, promote to Phase 2b design variant. If α=1.0 optimal, single-objective sufficient — park dual-objective entirely.

**Phase 2c.1 — Full dual-objective fine-tune (GPU-gated, deferred)**:

Post-DGX-Spark: train a summarizer whose summarization head is training-only and discarded at inference (prefill-only pattern per OneVL). Inference cost identical to current path; summary quality implicitly encoded in backbone.

## Compaction-Pipeline Gap Analysis (2026-04-22, DD8 / intake-426)

**Target**: NIB2-40 in backlog. 4h design task.

Map Claude Code's 5-layer pipeline against EPYC L1-L5:

| Claude Code layer | Operates at | EPYC equivalent | Gap? |
|---|---|---|---|
| budget-reduction | Per-message output size cap | ??? | **likely gap** |
| snip | Strategic content excision | L3 segment trimming | similar |
| microcompact | Per-tool output compression | L2 tool output compression | similar |
| context-collapse | Multi-block summarization | L4 two-level condensation | similar |
| auto-compact | Threshold-based full compaction | L5 threshold-based compaction | similar |

**Decision needed**: does EPYC need a "budget-reduction" equivalent? Anthropic's harness-design blog notes "context anxiety" in Sonnet 4.5 — compaction alone was insufficient; per-message output caps became necessary. Our current pipeline has no equivalent per-response size cap beyond token_budget at task level.

### Cross-references

- `/workspace/research/deep-dives/onevl-dual-objective-latent-compression.md` (Phase 2c.0 α-sweep detail)
- `/workspace/research/deep-dives/intake-trio-202604-references.md` (W-RAC / PersonaVLM / 1D-Tokens reference note)
- Intake sources: 443 (OneVL), 426 (Claude Code compaction pipeline)

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: upstream compressor gains smart collapse, dedup, anti-thrashing, language-respecting collapse, and fallback-to-main-model chain — direct primitives for progressive session compaction.
  - Key technique: **anti-thrashing** (prevents the "compress → uncompress → re-compress" oscillation that can degrade retention scores across folds); **language-aware collapse** (preserves code-block structure through compaction — relevant to L3/L4 where we currently risk collapsing code fences); **fallback chain** on compressor failure prevents context-corruption retries that would poison the fold history.
  - Delta from current approach: Phase 3c pending on our side. Evaluate whether to port upstream compressor patches vs. continue our independent implementation. Anti-thrashing in particular addresses a hypothesized failure mode at L5 (the still-pending level); language-aware collapse is a natural extension to the existing L3 sweet-spot compressor.

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-473] "@mariozechner/pi-agent-core — Stateful TypeScript Agent Runtime"** (`github.com/badlogic/pi-mono/tree/main/packages/agent`)
  - Relevance: defines a **per-turn `transformContext` hook** — `(messages: AgentMessage[], signal?: AbortSignal) => Promise<AgentMessage[]>` — that runs every turn, before the messages are converted to the LLM-strict payload shape. Operates at the agent-message level (custom types still in scope) so pruning/compaction logic doesn't need to know about LLM-specific roles. This is the natural shape for our progressive-folding work.
  - Key technique: **two-stage pipeline** — `transformContext` (optional, agent-level, runs every turn) → `convertToLlm` (required, role-strict, LLM-payload-shaped). The split is exactly the boundary where progressive folding belongs: fold operates on agent state with full type information; the LLM sees the post-fold projection. Custom message types (notifications, artifacts, fold checkpoints) survive `transformContext` and are filtered/coerced only at the `convertToLlm` step.
  - Delta from current approach: our progressive-folding code currently mixes "decide what to fold" (agent-level, semantic) with "render the payload the LLM sees" (LLM-strict, role-coerced). The pi-agent-core split is a clean factoring — pull our fold-decision logic into a per-turn `transform_context` step in the orchestrator and keep the LLM-shaping work in a separate stage. Naming + factoring lift; no code port required. Applies even before we tackle L5.
  - Implementation refs:
    - `agent-loop.ts:248-254` — the only place transformContext + convertToLlm are invoked, every turn.
    - `types.ts:103-154` — contract docs for both hooks (must not throw, return safe fallback on failure).
  - Deep-dive: `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-494] "Contexts are Never Long Enough: Structured Reasoning for Scalable Question Answering over Long Document Sets"** (arxiv:2604.22294, Stanford OVAL/Genie, Joshi/Shethia/Dao/Lam)
  - **Framing**: parallel architecture, NOT a folding-pipeline evolution. SLIDERS shares the cross-source aggregation framing but its mechanism (DB+SQL over extracted state) is disjoint from text-folding.
  - Relevance: SLIDERS targets long-document QA over 3.9M–36M-token corpora; progressive-folding targets dialog-turn compression. The "aggregation bottleneck" vocabulary is shared but the failure regimes are different — SLIDERS' bottleneck is across *documents*, folding's is across *turns*.
  - Reported results (concrete): +6.6 pp avg on FinanceBench/Loong/Oolong; WikiCeleb100 (3.9M) +~19 pp; FinQ100 (36M) abstract ~32 / README ~50 pp (unresolved discrepancy).
  - Critical adoption blocker (Tier 2b): code released (github.com/stanford-oval/sliders, MIT) but **GPT-4.1-only by construction** — no local-model code path. Local adoption would require both endpoint substitution and SQL-agent-loop revalidation.
  - Delta from progressive-folding: track as **parallel architecture for the cross-document aggregation problem**, not a folding-evolution. They could compose as side-by-side subsystems if a future workload needed both, but neither is on the other's roadmap.
  - Caveats (Tier 2b): schema hallucination is #1 LLM-to-SQL production failure; long-context relational reasoning underpredicts (arxiv:2510.03611); single-source Stanford results; per-query reconciliation cost is heavy; not directly portable to our corpus scale.

- **[intake-492] "Flywheel — local-first MCP memory layer for AI agents over Obsidian/Markdown vaults"** (`github.com/velvetmonkey/flywheel-memory`)
  - Relevance: Flywheel's `memory(action=brief)` is a **read-side, token-budgeted assembler** over already-persisted vault content with confidence decay — NOT a "promote to persistent memory" action. The persistence happens via Flywheel's separate write tools. Earlier intake framing as "fold-into-persistent-memory action" was inaccurate.
  - The portable pattern for progressive-folding is **token-budgeted brief-assembly with confidence decay**, not a promotion primitive. Useful as a design reference for how a folded-summary side-car could be queried.
  - Key technique: token-budgeted brief assembly with confidence decay; structure-preserving safe writes (hash-before-write conflict, atomic rollback, one-call undo) as a portable abstract contract; YAML "policies" as a declarative search-then-write abstraction.
  - Delta from current approach: progressive-folding currently has no explicit query-side abstraction over folded state. Flywheel's confidence-decay assembler is a candidate factoring for L5+ when folded summaries should be queryable rather than serialized into the prompt.
  - Caveat (Tier 2b): credibility 3 (engineering-rigor signals via 1,092 commits + 3,292 tests, capped by no peer review or independent replication); self-reported benchmarks with ~1pp LLM-non-determinism variance band.
