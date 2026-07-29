# Deep Dive: HCC Cognitive Accumulation for AutoPilot Iteration Strategy

**Paper**: Toward Ultra-Long-Horizon Agentic Science: Cognitive Accumulation for Machine Learning Engineering (arxiv:2601.10402)
**Authors**: Xinyu Zhu, Yuzhu Cai, Zexi Liu, Bingyang Zheng, Cheng Wang, Rui Ye, Yuzhi Zhang, Linfeng Zhang, Weinan E, Siheng Chen, Yanfeng Wang
**Intake**: intake-413
**Date**: 2026-04-20
**Relevance**: Direct upgrade path for AutoPilot's memory hierarchy -- StrategyStore is flat where HCC is hierarchical, and the distillation pipeline maps cleanly onto existing infrastructure

---

## Paper Architecture: Hierarchical Cognitive Caching (HCC)

### Three-Tier Knowledge Hierarchy

**L1 Cache (Evolving Experience)** -- volatile, high-fidelity:
- Stores raw execution traces: current research plans, code patches, terminal outputs
- Formal definition: L1(t) = E_t0-1 U P_p-1 U E_tp-1+1:t
- Retains only active-phase traces to prevent context saturation
- Analogous to CPU L1 cache: fast access, small capacity, ephemeral

**L2 Cache (Refined Knowledge)** -- semi-stable, condensed:
- Stores LLM-summarized phase completion summaries: key judgments, experimental insights, progress rationale
- Formal definition: L2(t) = {kappa_tp-1+1:tp-1} for r=1 to p-1
- Verbose execution details are stripped; only strategic conclusions survive
- Updated via promotion operator P1 at phase boundaries

**L3 Cache (Prior Wisdom)** -- persistent, cross-task:
- Stores embedding-value pairs (h_n, w_n) where h_n = E(d_n) is a semantic embedding of the task descriptor and w_n contains distilled task-level wisdom
- Persists across experiments/sessions
- Retrieved via cosine similarity: Omega_t = {w_n | cos(q, h_n) > delta}
- Updated via promotion operator P2 at task completion

### Promotion Pipeline

**P1 (Phase-level promotion)**: When a phase completes, parallel exploration trajectories are compressed via LLM summarization into refined knowledge kappa_p. Raw trajectories are removed from L1 and the summary is added to L2.

**P2 (Task-level promotion)**: At task completion, wisdom is distilled from the combined L1/L2/L3 state and final solution. The result is stored in L3 as a transferable embedding-value pair.

Both promotions are LLM-mediated (no hand-crafted rules) and trigger deterministically at phase/task boundaries.

### Context Constructor

The agent uses a cache-hit policy: for any historical step k, prefer L1 raw events if available, fall back to L2 summaries. This implements `C_t-1 = g(E_t-1) = concat{Psi_t(k)} for k=0..t-1`, where Psi_t(k) routes to the appropriate tier.

### Results

| Configuration | Valid Rate | Medal Rate |
|---|---|---|
| No L1 (only L2+L3) | 54.5% | 22.7% |
| No L2 (only L1+L3) | 95.5% | 59.1% |
| No L3 (only L1+L2) | 95.5% | 54.5% |
| **Full HCC (L1+L2+L3)** | **95.5%** | **72.7%** |

Key finding: L1 is foundational (removing it crashes validity), L2 is critical for complex medal solutions (removing it costs 13.6pp), L3 provides cross-task wisdom that avoids redundant exploration (removing it costs 18.2pp vs full).

On the full 75-task MLE-Bench: **56.44% medal rate** (75.8% low, 50.9% medium, 42.2% high complexity). Context growth is bounded at ~70K tokens with HCC vs >200K unbounded without it.

---

## Architecture Mapping: HCC to AutoPilot

### Current Memory Landscape

AutoPilot has multiple memory-like components, but they serve different roles and none implements hierarchical distillation:

| HCC Tier | AutoPilot Component | Alignment |
|---|---|---|
| L1 (Evolving Experience) | `short_term_memory.py` | **Partial** -- STM stores hypotheses/directions/failures as bullet points per trial, but has no raw execution trace retention |
| L1 (Evolving Experience) | `experiment_journal.py` | **Partial** -- stores full trial metadata (JSONL) but is append-only with no summarization or tier promotion |
| L2 (Refined Knowledge) | `self_criticism.py` | **Weak** -- generates per-trial criticism but it is consumed once and then only persisted as a text field in the journal; never distilled into patterns |
| L2 (Refined Knowledge) | *No equivalent* | **Gap** -- nothing consolidates multiple trials into phase-level strategic summaries |
| L3 (Prior Wisdom) | `strategy_store.py` | **Structural match, functional gap** -- has FAISS+SQLite for semantic retrieval, but entries are flat (no tier distinction, no consolidation, no staleness tracking) |
| L3 (Prior Wisdom) | `pareto_archive.py` | **Different purpose** -- tracks what works (Pareto frontier) but not why or when the wisdom expires |

### The Core Gap

AutoPilot's memory architecture is **flat and append-only**. Knowledge flows in one direction:

```
trial execution -> journal.record() -> strategy_store.store() [on Pareto improvement only]
                -> short_term_memory.update() [per-trial bullet points]
                -> self_criticism [consumed once, then persisted as text]
```

What is missing:

1. **No consolidation**: 100 trial entries never get summarized into "in the last 50 trials, prompt compression mutations on frontdoor.md consistently hurt coder suite quality." Individual entries are stored but patterns are never extracted.

2. **No tier promotion**: A strategy entry created at trial 10 lives forever at the same level of abstraction as one created at trial 500. There is no mechanism for promoting frequently-validated insights to a higher-confidence tier.

3. **No staleness detection**: Strategy entries never expire or get re-evaluated. A strategy from an early session where the model stack was different still gets retrieved with the same weight.

4. **No cross-session wisdom**: When AutoPilot restarts (new session_id), `short_term_memory.py` loads from disk but the markdown file has a MAX_LINES=120 cap. Accumulated wisdom from 500+ trials is reduced to the last ~30 entries. The journal survives but is only used for the controller's last-20 summary window.

5. **No phase-boundary triggers**: AutoPilot has implicit phases (seeding -> optimization -> training) driven by the meta_optimizer's budget rebalancing, but phase transitions do not trigger knowledge consolidation.

---

## Gap Analysis: Specific Code Paths

### `strategy_store.py` -- Flat Storage, No Hierarchy

The current store is a flat FAISS+SQLite implementation. Every entry has the same schema:

```python
# strategy_store.py line 40-50
@dataclass
class StrategyEntry:
    id: str
    description: str
    insight: str
    source_trial_id: int
    species: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    similarity_score: float = 0.0
```

Missing fields for HCC alignment: `tier` (L1/L2/L3), `confidence` (how many trials validated this), `last_validated` (staleness), `consolidation_source_ids` (which lower-tier entries were distilled into this one), `validity_window` (when does this expire).

Retrieval is a single-level vector search:

```python
# strategy_store.py line 169-206
def retrieve(self, query_text, k=5, species=None):
    embedding = self._embed(query_text)
    faiss_results = self._faiss.search(embedding, k=fetch_k)
    # ... filter by species, return entries
```

No tier-aware retrieval: all entries are treated equally regardless of their consolidation level or recency.

### `autopilot.py` -- No Distillation Triggers

The main loop's Record phase (line 1254-1371) stores data in the journal and strategy store, but the only distillation action is the explicit `distill_knowledge` action type (line 903-916), which the controller must proactively request. There are no automatic triggers at phase boundaries.

The distillation action dispatches to `EvolutionManager.distill()`, which processes the last N raw entries -- it does not implement hierarchical consolidation:

```python
# evolution_manager.py line 78-159
def distill(self, journal_entries, strategy_store, last_n=10, trial_id=0):
    entries = journal_entries[-last_n:]
    # ... build prompt with raw trial summaries
    # ... invoke LLM
    # ... parse insights
    # ... store each insight flat in strategy_store
```

This is equivalent to HCC's P1 operator (phase summarization), but it stores results at the same level as raw insights -- no L2/L3 distinction.

### `meta_optimizer.py` -- Budget Rebalancing Ignores Accumulated Wisdom

The rebalance logic at line 68-134 uses only:
- `species_effectiveness` (Pareto improvement rates)
- `hv_slope` (hypervolume stagnation)
- `memory_count` (routing memory count)
- `is_converged` (Q-value convergence)

It does not consult the strategy store. A system that has accumulated 200 insights about prompt mutation patterns will allocate the same budget to PromptForge as one with zero insights. HCC's wisdom-informed planning would adjust exploration budgets based on accumulated knowledge: if L3 wisdom says "prompt compression never works for frontdoor.md," the budget should shift away from that combination.

### `short_term_memory.py` -- Per-Session, No Consolidation

STM is a markdown file with four sections (Running Hypotheses, Optimization Directions, Failure Patterns, Working Context) capped at MAX_LINES=120. It is trimmed by recency only (`self._hypotheses[-max_per_section:]`), with no consolidation of recurring patterns.

When 10 trials all produce the direction "investigate declining coder suite," STM retains 10 identical bullets rather than consolidating to "coder suite has been declining across 10 trials, root cause likely related to [X]."

---

## Concrete Implementation Plan

### Phase 1: Tiered Strategy Store

Upgrade `strategy_store.py` to support three tiers with promotion tracking.

**Schema changes:**

```python
@dataclass
class StrategyEntry:
    id: str
    description: str
    insight: str
    source_trial_id: int
    species: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    similarity_score: float = 0.0
    # --- HCC additions ---
    tier: int = 1                          # 1=L1 (raw), 2=L2 (phase), 3=L3 (wisdom)
    confidence: float = 0.5                # validated_count / total_relevant_trials
    last_validated: str = ""               # ISO timestamp of last trial that confirmed this
    consolidation_sources: list[str] = field(default_factory=list)  # IDs of entries distilled into this
    superseded_by: str | None = None       # ID of higher-tier entry that replaced this
    validation_count: int = 0              # times confirmed by subsequent trials
    contradiction_count: int = 0           # times contradicted by subsequent trials
    validity_window: int = 100             # expires after N trials without validation
```

**SQLite migration:**

```sql
ALTER TABLE strategies ADD COLUMN tier INTEGER DEFAULT 1;
ALTER TABLE strategies ADD COLUMN confidence REAL DEFAULT 0.5;
ALTER TABLE strategies ADD COLUMN last_validated TEXT DEFAULT '';
ALTER TABLE strategies ADD COLUMN consolidation_sources TEXT DEFAULT '[]';
ALTER TABLE strategies ADD COLUMN superseded_by TEXT DEFAULT NULL;
ALTER TABLE strategies ADD COLUMN validation_count INTEGER DEFAULT 0;
ALTER TABLE strategies ADD COLUMN contradiction_count INTEGER DEFAULT 0;
ALTER TABLE strategies ADD COLUMN validity_window INTEGER DEFAULT 100;
CREATE INDEX idx_strategies_tier ON strategies(tier);
CREATE INDEX idx_strategies_confidence ON strategies(confidence);
```

**Tier-aware retrieval:**

```python
def retrieve(self, query_text, k=5, species=None, min_tier=1, prefer_higher_tier=True):
    """Retrieve strategies with tier-aware ranking.

    Higher-tier entries get a retrieval boost. Superseded entries are excluded.
    Expired entries (trial_counter - source_trial_id > validity_window and
    validation_count == 0) are deprioritized.
    """
    embedding = self._embed(query_text)
    fetch_k = k * 5  # over-fetch for filtering
    faiss_results = self._faiss.search(embedding, k=fetch_k)

    entries = []
    for memory_id, score in faiss_results:
        row = self._get_row(memory_id)
        if row is None or row["superseded_by"] is not None:
            continue
        if row["tier"] < min_tier:
            continue
        if species and row["species"] != species:
            continue

        # Tier boost: L2 gets 1.2x, L3 gets 1.5x similarity score
        tier_boost = {1: 1.0, 2: 1.2, 3: 1.5}.get(row["tier"], 1.0)
        # Confidence boost
        conf_boost = 0.8 + 0.4 * row["confidence"]  # range [0.8, 1.2]
        adjusted_score = score * tier_boost * conf_boost

        entries.append(self._row_to_entry(row, adjusted_score))

    entries.sort(key=lambda e: e.similarity_score, reverse=True)
    return entries[:k]
```

### Phase 2: Knowledge Distiller (New File)

Create `knowledge_distiller.py` as the consolidation engine -- the component that implements HCC's P1 and P2 operators.

```python
"""Knowledge distiller: hierarchical consolidation for AutoPilot strategy memory.

Implements HCC-inspired P1 (phase consolidation) and P2 (wisdom extraction)
operators. Runs as part of the main loop at phase boundaries and periodically.

Source: ML-Master 2.0 (arxiv:2601.10402, intake-413).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("autopilot.distiller")

# Consolidation thresholds
MIN_ENTRIES_FOR_CONSOLIDATION = 5    # minimum L1 entries before L2 promotion
MIN_L2_ENTRIES_FOR_WISDOM = 3        # minimum L2 entries before L3 promotion
STALENESS_THRESHOLD = 100            # trials without validation before deprioritization
CONTRADICTION_RATIO_THRESHOLD = 0.4  # if contradicted > 40% of the time, flag as unreliable

CONSOLIDATION_PROMPT = """\
You are analyzing a cluster of {n} related experiment insights from an LLM
orchestration optimization system (AutoPilot).

## Related Insights (from trials {trial_range})

{entries_text}

## Task

These insights share a common theme. Consolidate them into a SINGLE higher-level
strategic principle that:

1. Captures the core pattern across all entries
2. Is actionable for future experiments
3. Notes any contradictions or exceptions
4. Specifies which species/action types this applies to

Respond with a JSON object:

```json:consolidated
{{
  "description": "One-line description of the consolidated principle",
  "insight": "Detailed actionable guidance (2-3 sentences)",
  "species": "most relevant species or 'all'",
  "confidence": 0.0-1.0,
  "exceptions": "any noted contradictions or edge cases",
  "applicable_when": "conditions under which this wisdom applies"
}}
```
"""

WISDOM_EXTRACTION_PROMPT = """\
You are extracting cross-session wisdom from {n} consolidated phase-level insights
gathered over {trial_span} trials of AutoPilot optimization.

## Phase-Level Insights (L2 tier)

{entries_text}

## Current System Context

- Stack configuration: {stack_context}
- Pareto frontier size: {pareto_size}
- Total trials completed: {total_trials}

## Task

Extract 1-3 durable strategic principles that should persist across AutoPilot sessions.
These should be high-confidence, well-validated patterns that future sessions should
know from the start. Discard anything that is stack-configuration-specific or likely
to change with model updates.

```json:wisdom
[
  {{
    "description": "One-line cross-session principle",
    "insight": "Why this is durable and how to apply it",
    "species": "applicable species or 'all'",
    "confidence": 0.0-1.0,
    "applicable_when": "conditions under which this holds"
  }}
]
```
"""


@dataclass
class ConsolidationResult:
    """Result of a consolidation operation."""
    tier_promoted_to: int
    new_entry_id: str
    source_ids: list[str]
    description: str
    confidence: float


class KnowledgeDistiller:
    """Hierarchical knowledge consolidation engine.

    Implements two promotion operators:
    - P1: Clusters related L1 entries and consolidates to L2
    - P2: Extracts durable wisdom from L2 entries into L3

    Also handles:
    - Staleness detection and confidence decay
    - Contradiction tracking
    - Validation updates when new trials confirm/contradict existing entries
    """

    def __init__(
        self,
        strategy_store: Any,  # StrategyStore
        journal: Any,         # ExperimentJournal
        llm_invoker: callable = None,
        similarity_threshold: float = 0.75,
    ):
        self.store = strategy_store
        self.journal = journal
        self._invoke_llm = llm_invoker
        self.similarity_threshold = similarity_threshold

    # ── P1: Phase-Level Consolidation ────────────────────────────

    def consolidate_l1_to_l2(
        self,
        current_trial: int,
        species: str | None = None,
    ) -> list[ConsolidationResult]:
        """Cluster related L1 entries and promote to L2 via LLM summarization.

        Groups L1 entries by semantic similarity, then for each cluster with
        >= MIN_ENTRIES_FOR_CONSOLIDATION members, generates a consolidated
        L2 entry and marks the L1 entries as superseded.
        """
        # Retrieve all active L1 entries
        l1_entries = self.store.retrieve_by_tier(tier=1, species=species)
        if len(l1_entries) < MIN_ENTRIES_FOR_CONSOLIDATION:
            return []

        # Cluster by semantic similarity using FAISS
        clusters = self._cluster_entries(l1_entries)
        results = []

        for cluster in clusters:
            if len(cluster) < MIN_ENTRIES_FOR_CONSOLIDATION:
                continue

            # Build consolidation prompt
            entries_text = "\n".join(
                f"- [Trial #{e.source_trial_id}, {e.species}] {e.description}: {e.insight}"
                for e in cluster
            )
            trial_ids = [e.source_trial_id for e in cluster]
            prompt = CONSOLIDATION_PROMPT.format(
                n=len(cluster),
                trial_range=f"{min(trial_ids)}-{max(trial_ids)}",
                entries_text=entries_text,
            )

            response = self._invoke_llm(prompt)
            consolidated = self._parse_consolidated(response)
            if not consolidated:
                continue

            # Store L2 entry
            source_ids = [e.id for e in cluster]
            new_id = self.store.store(
                description=consolidated["description"],
                insight=consolidated["insight"],
                source_trial_id=current_trial,
                species=consolidated.get("species", "all"),
                metadata={
                    "confidence": consolidated.get("confidence", 0.7),
                    "exceptions": consolidated.get("exceptions", ""),
                    "applicable_when": consolidated.get("applicable_when", ""),
                },
                tier=2,
                consolidation_sources=source_ids,
            )

            # Mark L1 entries as superseded
            for entry in cluster:
                self.store.mark_superseded(entry.id, new_id)

            results.append(ConsolidationResult(
                tier_promoted_to=2,
                new_entry_id=new_id,
                source_ids=source_ids,
                description=consolidated["description"],
                confidence=consolidated.get("confidence", 0.7),
            ))

        return results

    # ── P2: Wisdom Extraction ────────────────────────────────────

    def extract_l2_to_l3(
        self,
        current_trial: int,
        stack_context: str = "",
        pareto_size: int = 0,
    ) -> list[ConsolidationResult]:
        """Extract durable wisdom from L2 entries into L3.

        Runs less frequently than P1 (e.g., every 100 trials or at session end).
        Only promotes high-confidence L2 entries that have been validated across
        multiple phases.
        """
        l2_entries = self.store.retrieve_by_tier(tier=2, min_confidence=0.6)
        if len(l2_entries) < MIN_L2_ENTRIES_FOR_WISDOM:
            return []

        entries_text = "\n".join(
            f"- [{e.species}, confidence={e.metadata.get('confidence', 0.5):.1f}] "
            f"{e.description}: {e.insight}"
            for e in l2_entries
        )

        prompt = WISDOM_EXTRACTION_PROMPT.format(
            n=len(l2_entries),
            trial_span=current_trial,
            entries_text=entries_text,
            stack_context=stack_context,
            pareto_size=pareto_size,
            total_trials=current_trial,
        )

        response = self._invoke_llm(prompt)
        wisdom_list = self._parse_wisdom(response)
        results = []

        for w in wisdom_list:
            source_ids = [e.id for e in l2_entries]
            new_id = self.store.store(
                description=w["description"],
                insight=w["insight"],
                source_trial_id=current_trial,
                species=w.get("species", "all"),
                metadata={
                    "confidence": w.get("confidence", 0.8),
                    "applicable_when": w.get("applicable_when", ""),
                },
                tier=3,
                consolidation_sources=source_ids,
            )
            results.append(ConsolidationResult(
                tier_promoted_to=3,
                new_entry_id=new_id,
                source_ids=source_ids,
                description=w["description"],
                confidence=w.get("confidence", 0.8),
            ))

        return results

    # ── Validation & Staleness ───────────────────────────────────

    def validate_against_trial(
        self,
        trial_entry: Any,  # JournalEntry
        current_trial: int,
    ) -> None:
        """After each trial, check if results confirm or contradict existing strategies.

        A trial confirms a strategy if:
        - The strategy was retrieved for the trial's species/action_type
        - The trial passed the safety gate AND improved on the Pareto frontier

        A trial contradicts if:
        - The strategy was retrieved but the trial failed or regressed
        """
        # Retrieve strategies relevant to this trial
        query = f"{trial_entry.species} {trial_entry.action_type} {trial_entry.hypothesis}"
        relevant = self.store.retrieve(query, k=5, min_tier=1)

        for entry in relevant:
            if entry.similarity_score < self.similarity_threshold:
                continue

            if trial_entry.pareto_status == "frontier":
                self.store.increment_validation(entry.id, current_trial)
            elif trial_entry.failure_analysis:
                self.store.increment_contradiction(entry.id)

    def decay_stale_entries(self, current_trial: int) -> int:
        """Reduce confidence of entries that haven't been validated recently.

        Returns number of entries affected.
        """
        return self.store.decay_stale(
            current_trial=current_trial,
            staleness_threshold=STALENESS_THRESHOLD,
            decay_factor=0.9,  # 10% confidence reduction per staleness check
        )

    # ── Clustering ───────────────────────────────────────────────

    def _cluster_entries(
        self,
        entries: list,
        threshold: float = 0.70,
    ) -> list[list]:
        """Cluster entries by embedding similarity (greedy single-linkage)."""
        if not entries:
            return []

        # Get embeddings for all entries
        embeddings = []
        for e in entries:
            emb = self.store._embed(f"{e.description} {e.insight}")
            embeddings.append(emb)

        import numpy as np
        embeddings_matrix = np.array(embeddings)

        # Cosine similarity matrix
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        normalized = embeddings_matrix / (norms + 1e-9)
        sim_matrix = normalized @ normalized.T

        # Greedy single-linkage clustering
        assigned = [False] * len(entries)
        clusters = []

        for i in range(len(entries)):
            if assigned[i]:
                continue
            cluster = [entries[i]]
            assigned[i] = True
            for j in range(i + 1, len(entries)):
                if assigned[j]:
                    continue
                if sim_matrix[i][j] >= threshold:
                    cluster.append(entries[j])
                    assigned[j] = True
            clusters.append(cluster)

        return clusters

    # ── Parsing ──────────────────────────────────────────────────

    def _parse_consolidated(self, response: str) -> dict | None:
        marker = "```json:consolidated"
        if marker in response:
            start = response.index(marker) + len(marker)
            end = response.index("```", start)
            try:
                return json.loads(response[start:end].strip())
            except json.JSONDecodeError:
                pass
        # Fallback
        if "```json" in response:
            start = response.index("```json") + len("```json")
            end = response.index("```", start)
            try:
                data = json.loads(response[start:end].strip())
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def _parse_wisdom(self, response: str) -> list[dict]:
        marker = "```json:wisdom"
        if marker in response:
            start = response.index(marker) + len(marker)
            end = response.index("```", start)
            try:
                data = json.loads(response[start:end].strip())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        if "```json" in response:
            start = response.index("```json") + len("```json")
            end = response.index("```", start)
            try:
                data = json.loads(response[start:end].strip())
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        return []
```

### Phase 3: Main Loop Integration

Add distillation trigger points to `autopilot.py`:

**After the Record phase (line ~1392), add consolidation hooks:**

```python
# ── 5b. Knowledge Consolidation (HCC-inspired) ──────────
# P1 trigger: consolidate L1 -> L2 every 25 trials
if (trial_counter > 0 and trial_counter % 25 == 0
        and strategy_store is not None and distiller is not None):
    log.info("P1 consolidation trigger at trial %d", trial_counter)
    p1_results = distiller.consolidate_l1_to_l2(
        current_trial=trial_counter,
        species=None,  # all species
    )
    for r in p1_results:
        log.info(
            "P1: consolidated %d L1 entries -> L2 '%s' (confidence=%.2f)",
            len(r.source_ids), r.description, r.confidence,
        )

# P2 trigger: extract wisdom every 100 trials or at session end
if (trial_counter > 0 and trial_counter % 100 == 0
        and strategy_store is not None and distiller is not None):
    log.info("P2 wisdom extraction at trial %d", trial_counter)
    p2_results = distiller.extract_l2_to_l3(
        current_trial=trial_counter,
        stack_context=json.dumps(meta.budget.as_dict()),
        pareto_size=len(archive._frontier),
    )
    for r in p2_results:
        log.info(
            "P2: extracted L3 wisdom '%s' from %d L2 entries",
            r.description, len(r.source_ids),
        )

# Validation: check if this trial confirms/contradicts existing strategies
if strategy_store is not None and distiller is not None:
    distiller.validate_against_trial(
        trial_entry=journal.recent(1)[-1],
        current_trial=trial_counter,
    )

# Staleness decay: every 50 trials
if (trial_counter > 0 and trial_counter % 50 == 0
        and strategy_store is not None and distiller is not None):
    n_decayed = distiller.decay_stale_entries(trial_counter)
    if n_decayed > 0:
        log.info("Staleness decay: %d entries confidence-reduced", n_decayed)
```

**Initialize the distiller in `_run_loop_inner()` (after strategy_store initialization, around line 1035):**

```python
# HCC-inspired knowledge distiller
distiller: KnowledgeDistiller | None = None
if strategy_store is not None:
    from knowledge_distiller import KnowledgeDistiller
    distiller = KnowledgeDistiller(
        strategy_store=strategy_store,
        journal=journal,
        llm_invoker=evo._invoke_llm,  # reuse EvolutionManager's LLM backend
    )
    log.info("Knowledge distiller initialized (HCC mode)")
```

**At shutdown (line ~1437), add final wisdom extraction:**

```python
# Shutdown: final P2 wisdom extraction
if distiller is not None and strategy_store is not None:
    log.info("Final P2 wisdom extraction at shutdown")
    p2_results = distiller.extract_l2_to_l3(
        current_trial=trial_counter,
        stack_context=json.dumps(meta.budget.as_dict()),
        pareto_size=len(archive._frontier),
    )
    log.info("Final wisdom: %d entries extracted", len(p2_results))
```

### Phase 4: Wisdom-Informed Budget Rebalancing

Add accumulated knowledge awareness to `meta_optimizer.py`:

```python
def rebalance(
    self,
    species_effectiveness: dict[str, dict[str, float]],
    hv_slope: float,
    memory_count: int,
    is_converged: bool,
    wisdom_summary: dict[str, Any] | None = None,  # NEW
) -> SpeciesBudget:
    """Rebalance with optional wisdom from strategy store.

    wisdom_summary: {
        "species_insights": {"prompt_forge": 12, "seeder": 3, ...},
        "high_confidence_count": 5,
        "contradicted_species": ["numeric_swarm"],
        "recommended_focus": "prompt_forge",
    }
    """
    # ... existing phase-based logic ...

    # Wisdom-informed adjustment (NEW)
    if wisdom_summary:
        # If accumulated wisdom strongly favors a species, boost it
        focus = wisdom_summary.get("recommended_focus")
        if focus and hasattr(self.budget, focus):
            current = getattr(self.budget, focus)
            setattr(self.budget, focus, min(0.40, current + 0.05))
            log.info("Wisdom boost: %s +5%% (accumulated evidence)", focus)

        # If a species has high contradiction rate, reduce its budget
        for species in wisdom_summary.get("contradicted_species", []):
            if hasattr(self.budget, species):
                current = getattr(self.budget, species)
                setattr(self.budget, species, max(0.05, current - 0.05))
                log.info("Wisdom penalty: %s -5%% (high contradiction rate)", species)

    self.budget.normalize()
```

---

## Distillation Pipeline Design

### Flow: Raw Trial Data -> Phase Patterns -> Cross-Session Wisdom

```
Trial Execution (every trial)
    |
    v
L1 Storage: strategy_store.store(tier=1)
    - Raw insight: "prompt_mutation targeted_fix on frontdoor.md improved coder 2.1->2.4"
    - Source: Pareto frontier improvements + EvolutionManager distill_knowledge
    |
    v (every 25 trials)
P1 Consolidation: distiller.consolidate_l1_to_l2()
    - Cluster related L1 entries by FAISS embedding similarity
    - LLM summarizes each cluster into L2 strategic principle
    - L1 entries marked superseded (excluded from future retrieval)
    - Example L2: "targeted_fix mutations on frontdoor.md consistently improve coder
      suite quality (+0.2-0.4) when they add model-specific routing hints. Compression
      mutations on the same file degrade quality. Exception: few_shot_evolution works
      when targeting thinking suite."
    |
    v (every 100 trials, or at session shutdown)
P2 Wisdom Extraction: distiller.extract_l2_to_l3()
    - Select high-confidence L2 entries (confidence >= 0.6)
    - LLM extracts durable, stack-independent principles
    - Example L3: "Prompt mutations that add per-model behavioral hints to routing
      prompts consistently outperform generic instruction changes. This pattern holds
      across different model stacks and is robust to model swaps."
    |
    v (every trial, passive)
Validation: distiller.validate_against_trial()
    - For each trial outcome, check if relevant strategies were confirmed or contradicted
    - Update validation_count / contradiction_count on matching entries
    - Confidence = validation_count / (validation_count + contradiction_count)
    |
    v (every 50 trials)
Staleness Decay: distiller.decay_stale_entries()
    - Entries not validated in > 100 trials: confidence *= 0.9
    - Eventually, stale entries get deprioritized in retrieval
    - L3 entries have higher validity_window (500 trials) since they represent durable patterns
```

### Concrete Example Walk-Through

**Trials 1-25**: AutoPilot runs seeding and prompt mutations. The EvolutionManager distills 15 L1 entries into strategy_store, including:
- L1-a: "targeted_fix on frontdoor.md adding coder routing hints: q=2.1->2.4"
- L1-b: "compress on frontdoor.md: q=2.3->2.0 (regression, reverted)"
- L1-c: "targeted_fix on frontdoor.md adding thinking mode hints: q=2.3->2.5"
- L1-d: "few_shot_evolution on frontdoor.md: q=2.4->2.4 (neutral)"
- L1-e: "targeted_fix on frontdoor.md refining model dispatch: q=2.4->2.6"

**Trial 25 (P1 trigger)**: The distiller clusters L1-a, L1-c, L1-e (all "targeted_fix on frontdoor.md" with positive results) and consolidates:
- L2-1: "targeted_fix mutations adding model-specific behavioral hints to frontdoor.md consistently improve quality (+0.2-0.3). Success pattern: add per-suite routing guidance rather than generic instructions."

L1-b is in a separate cluster with other failed compression attempts, producing:
- L2-2: "compress mutations on frontdoor.md degrade quality (average -0.2). Root cause: compression removes model-specific routing hints that are load-bearing for quality."

**Trial 100 (P2 trigger)**: After 4 P1 cycles, the distiller has 8 L2 entries. It extracts:
- L3-1: "Adding model-specific behavioral hints to routing prompts is the highest-impact prompt mutation pattern. Confidence: 0.85. Applies regardless of which target file."

**Trial 150 (new session)**: AutoPilot loads strategy_store from disk. When PromptForge proposes its next mutation, it retrieves L3-1 first (tier-boosted), and the mutation prompt includes "Past wisdom: adding model-specific behavioral hints is the highest-impact pattern." The mutation is more likely to succeed on the first attempt.

---

## Integration with PromptForge

### Current Retrieval (autopilot.py lines 546-557)

```python
# B1: Strategy store retrieval -- add past strategy insights
if strategy_store is not None:
    query = f"{target} {mutation_type} {description}"
    strategies = strategy_store.retrieve(query, k=3)
    if strategies:
        strategy_lines = "\n".join(
            f"- Trial #{s.source_trial_id} ({s.species}): {s.description} -> {s.insight}"
            for s in strategies
        )
        failure_context = (
            f"## Past Strategy Insights\n{strategy_lines}\n\n"
            + failure_context
        )
```

### Proposed Enhancement

```python
# HCC: Tier-aware strategy retrieval for PromptForge
if strategy_store is not None:
    query = f"{target} {mutation_type} {description}"

    # First, retrieve L3 wisdom (highest value, broadest applicability)
    wisdom = strategy_store.retrieve(query, k=2, min_tier=3)
    # Then, retrieve L2 phase patterns (specific to this mutation pattern)
    phase_knowledge = strategy_store.retrieve(query, k=3, min_tier=2)
    # Finally, retrieve L1 raw insights (most recent, most specific)
    raw_insights = strategy_store.retrieve(query, k=3, min_tier=1)

    context_sections = []
    if wisdom:
        context_sections.append(
            "## Cross-Session Wisdom (high confidence)\n" +
            "\n".join(f"- [L3, conf={w.metadata.get('confidence', 0):.1f}] {w.insight}"
                     for w in wisdom)
        )
    if phase_knowledge:
        context_sections.append(
            "## Phase-Level Patterns\n" +
            "\n".join(f"- [L2] {p.description}: {p.insight}" for p in phase_knowledge)
        )
    if raw_insights:
        context_sections.append(
            "## Recent Trial Insights\n" +
            "\n".join(f"- [Trial #{r.source_trial_id}] {r.insight}" for r in raw_insights)
        )

    if context_sections:
        failure_context = "\n\n".join(context_sections) + "\n\n" + failure_context
```

This gives the LLM mutation prompt a hierarchical context: durable wisdom first, then phase-specific patterns, then recent raw observations. The LLM can weight its mutation decisions accordingly -- following proven high-confidence patterns by default, but using recent observations to identify deviations.

### PromptForge Mutation Types: Wisdom-Specific Guidance

Each mutation type benefits differently from HCC tiers:

| Mutation Type | Most Valuable Tier | Why |
|---|---|---|
| `targeted_fix` | L2 (phase patterns) | Needs specific knowledge about what fixes work for which files/suites |
| `compress` | L3 (wisdom) | Needs durable knowledge about which prompt sections are load-bearing |
| `few_shot_evolution` | L1 (raw insights) | Needs recent per-suite quality data to select relevant examples |
| `crossover` | L2 (phase patterns) | Needs knowledge about which prompt sections from different files are compatible |
| `style_transfer` | L3 (wisdom) | Needs broad patterns about which writing styles correlate with quality |
| `gepa` | L2 (phase patterns) | GEPA's evolutionary search benefits from knowing which search regions have been explored |

---

## Risks and Mitigations

### 1. Stale Wisdom Ossification

**Risk**: L3 wisdom from an early session persists indefinitely and guides mutations toward patterns that no longer work after model stack changes (e.g., swapping worker from Gemma to 30B-A3B).

**Mitigation**: The validation/contradiction tracking system addresses this directly. Each trial validates or contradicts relevant strategies. The `decay_stale_entries()` method reduces confidence of unvalidated entries over time. Additionally, L3 entries should include `applicable_when` metadata (e.g., "when frontdoor model is Qwen3.5") so that stack changes can trigger targeted invalidation.

**Implementation**: Add a `invalidate_for_stack_change(old_stack, new_stack)` method to KnowledgeDistiller that marks L2/L3 entries referencing changed models as needing re-validation (reset confidence to 0.5, reset validation_count to 0).

### 2. Overfitting to Past Patterns

**Risk**: Accumulated wisdom biases exploration too strongly toward known-good patterns, preventing discovery of novel improvement directions. HCC's ablation shows that removing L3 only costs 18.2pp -- meaning the system can still function without it. Over-reliance on L3 could be worse than having no L3 at all if the wisdom is wrong.

**Mitigation**: The meta_optimizer's stagnation detection (hv_slope < 0.001) already boosts exploration species. When stagnation is detected AND L3 wisdom is being consumed, the system should temporarily reduce the tier boost for L3 retrieval (drop from 1.5x to 1.0x), effectively "forgetting" accumulated wisdom to enable novel exploration.

**Implementation**: Add a `stagnation_mode` flag to the retrieval method. When hypervolume stagnation is detected, retrieval returns L1/L2 entries with equal weight to L3, breaking the wisdom-bias.

### 3. LLM Consolidation Hallucination

**Risk**: The LLM that performs P1/P2 consolidation may fabricate patterns that don't exist in the source data, or may over-generalize from limited evidence. A hallucinated L3 entry would persist and bias hundreds of future trials.

**Mitigation**: Three defenses:
- **Source tracing**: Every L2/L3 entry records `consolidation_sources` -- the specific L1/L2 entry IDs that were distilled. Downstream analysis can verify the consolidation.
- **Minimum evidence thresholds**: MIN_ENTRIES_FOR_CONSOLIDATION=5 for L2, MIN_L2_ENTRIES_FOR_WISDOM=3 for L3. No single-trial observations get promoted.
- **Contradiction sensitivity**: If a newly promoted entry gets contradicted by its first 3 validation checks (contradiction_count > validation_count early), auto-demote by resetting confidence to 0.1 and flagging for human review.

### 4. Context Budget Bloat

**Risk**: Injecting L1+L2+L3 context into every species prompt could significantly increase token usage, especially for PromptForge which already uses 200K token budgets.

**Mitigation**: Cap the injection at fixed token budgets per tier: L3 (150 tokens max, 2 entries), L2 (300 tokens max, 3 entries), L1 (200 tokens max, 3 entries). Total overhead: ~650 tokens -- less than 0.5% of PromptForge's budget. The tier-aware retrieval naturally limits volume since L2/L3 entries are already condensed summaries.

### 5. Consolidation Compute Cost

**Risk**: P1 and P2 require LLM invocations. At P1 every 25 trials, this adds 4 LLM calls per 100 trials (assuming ~4 clusters per consolidation). P2 every 100 trials adds 1 call.

**Mitigation**: Reuse EvolutionManager's existing LLM backend (which already uses local model at port 8082 for cost-efficient distillation). P1 consolidation prompts are small (~2K tokens input, ~500 output). Total cost: ~5 extra LLM calls per 100 trials, comparable to the existing EvolutionManager budget.

### 6. Paper's Unaddressed Gaps

The paper does not describe:
- **Contradiction resolution**: What happens when L3 wisdom contradicts new evidence? Our implementation adds contradiction tracking and confidence decay, which goes beyond the paper.
- **Knowledge invalidation**: The paper's P1/P2 operators are purely additive. We add staleness detection and stack-change invalidation.
- **Multi-objective context**: HCC was designed for single-metric optimization (medal rate). Our 4D Pareto archive means wisdom needs to be qualified by which objective it improves -- "this pattern improves quality but costs speed" is more useful than "this works."

---

## Intake Verdict Delta

### Current Verdict: `worth_investigating` (medium novelty, medium relevance)

### Reassessment: **Upgrade to `high_relevance`, keep `medium_novelty`**

**Relevance upgrade justification**: After mapping HCC to the actual AutoPilot codebase, the alignment is stronger than the intake assessment suggested:

1. **StrategyStore already exists** -- it has FAISS+SQLite, embedding-based retrieval, and integration with both EvolutionManager and PromptForge. Adding tiers is a schema migration, not a new system.

2. **EvolutionManager already implements crude P1** -- it distills raw journal entries into strategy entries via LLM summarization. The gap is that it stores results flat (no tier distinction) and never consolidates further.

3. **The validation loop is trivial to add** -- the journal already records `pareto_status` and `failure_analysis` for every trial. Cross-referencing against strategy entries for confirmation/contradiction requires a few lines per trial.

4. **The main loop already has natural phase boundaries** -- auto-checkpoints at trial 25 multiples (line 1403), meta_optimizer rebalancing at trial 50 multiples (line 1393), plot generation at trial 10 multiples (line 1411). Adding P1/P2 triggers at these same boundaries is zero architectural change.

5. **The ablation results quantify the value** -- removing L3 alone costs 18.2pp on medal rate. Even if our improvement is a fraction of that, it represents meaningful acceleration of convergence.

**Novelty stays medium**: As the original assessment noted, multi-level memory for agents is well-explored (MemRL, Graphiti, EvoScientist). HCC's contribution is the computer-memory-hierarchy framing and the MLE-Bench validation, not a fundamentally new mechanism. Our related deep dive on EvoScientist (intake-108) already identified the knowledge distillation gap and proposed the EvolutionManager species -- HCC refines the "how" of distillation with explicit tiers, which is a useful but incremental advance.

**Bottom line**: HCC provides the missing hierarchical structure for the EvolutionManager + StrategyStore system that was built from the EvoScientist deep dive. The EvoScientist deep dive identified WHAT was needed (dedicated distillation + retrievable strategy memory). The HCC paper specifies HOW to organize it (L1/L2/L3 tiers with promotion operators, validation tracking, and staleness decay). Implementation requires changes to 3 existing files and 1 new file, with no architectural refactoring.

### Recommended Implementation Order

1. **Schema migration** for strategy_store.py (add tier, confidence, validation columns) -- 1 session
2. **KnowledgeDistiller** module with P1 consolidation -- 1 session
3. **Main loop integration** (P1 trigger at trial 25, validation per trial) -- 0.5 session
4. **Tier-aware PromptForge retrieval** -- 0.5 session
5. **P2 wisdom extraction + staleness decay** -- 1 session
6. **Wisdom-informed meta_optimizer** -- 0.5 session
7. **Stagnation-mode wisdom bypass** -- 0.5 session

Total estimated effort: 5 sessions. Can be incrementally validated -- each phase provides independent value.
