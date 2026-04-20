# AutoPilot Iteration Strategy Synthesis (Deep Dive)

**Sources**: intake-413 (HCC / Cognitive Accumulation), intake-414 (Token Savior Recall), intake-415 (Context Mode)
**Target System**: `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/`
**Date**: 2026-04-20

## Problem Statement

AutoPilot's current iteration infrastructure accumulates knowledge without consolidating it. After 100+ trials, four compounding deficiencies emerge:

1. **Flat strategy memory** (`strategy_store.py`): FAISS-only retrieval returns semantically similar entries but cannot match on exact terms, has no staleness detection, and never consolidates repeated patterns into higher-level conventions.

2. **No knowledge decay**: Strategies stored under registry config A remain indexed after the model registry, prompt files, and structural flags have all changed. The system re-discovers that stale strategies are irrelevant by wasting trials on them.

3. **Context inflation**: The controller prompt template (`autopilot.py:74-165`) injects 14 sections. Each grows with trial count. No section has a token budget. At trial 200+, the prompt approaches context limits and the controller's reasoning quality degrades.

4. **Mutation quality plateau**: `prompt_forge.py` retrieves past strategy insights (lines 546-557) but does not track which mutation type worked for which failure pattern. Crossover and style_transfer mutations are available but underutilized because there is no knowledge of which prompt sections are strongest across the Pareto archive.

## Synthesis Framework

The three intake sources each address a different layer of the problem:

| Layer | Source | Key Mechanism | AutoPilot Application |
|-------|--------|---------------|----------------------|
| Knowledge structure | intake-413 (HCC) | L1/L2/L3 tiered distillation; cross-task wisdom consolidation | Strategy store: raw entries -> patterns -> conventions |
| Retrieval quality | intake-414 (Token Savior) | BM25+FAISS RRF fusion; content-hash staleness; Bayesian validity; MDL distillation | Strategy store: hybrid retrieval, auto-expire, validity scoring |
| Context budget | intake-415 (Context Mode) | 5KB threshold gating; FTS5 indexing; progressive disclosure; PreCompact snapshots | Controller prompt: token budgets, tiered injection, output gating |

The improvement plan chains these into four phases. Each phase is independently deployable but the full benefit compounds across all four.

---

## Phase 1: Strategy Memory Upgrade

**Target**: `strategy_store.py` (228 LoC currently)
**Estimated delta**: ~200 LoC additions/modifications
**Dependencies**: None (standalone)

### 1.1 Hybrid Retrieval (BM25 + FAISS with RRF)

The current `retrieve()` method (line 169) uses FAISS-only search. This fails when the query contains exact terms that matter (species names, file names, mutation types) because the hash-based embedding fallback has zero semantic fidelity.

**Design**: Add an FTS5 virtual table parallel to the existing `strategies` table. Query both stores, fuse results with Reciprocal Rank Fusion (RRF).

```python
# New schema addition in _init_schema()
def _init_schema(self) -> None:
    # ... existing strategies table ...

    # FTS5 parallel index for BM25 keyword retrieval
    self._conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS strategies_fts
        USING fts5(
            id UNINDEXED,
            description,
            insight,
            species,
            content='strategies',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)
    # Triggers to keep FTS5 in sync with strategies table
    self._conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS strategies_ai AFTER INSERT ON strategies BEGIN
            INSERT INTO strategies_fts(rowid, id, description, insight, species)
            VALUES (new.rowid, new.id, new.description, new.insight, new.species);
        END;
        CREATE TRIGGER IF NOT EXISTS strategies_ad AFTER DELETE ON strategies BEGIN
            INSERT INTO strategies_fts(strategies_fts, rowid, id, description, insight, species)
            VALUES ('delete', old.rowid, old.id, old.description, old.insight, old.species);
        END;
    """)
    self._conn.commit()
```

```python
# New method: BM25 retrieval via FTS5
def _retrieve_bm25(self, query_text: str, k: int = 10) -> list[tuple[str, float]]:
    """BM25 keyword retrieval via FTS5. Returns [(id, bm25_score), ...]."""
    rows = self._conn.execute(
        """SELECT id, rank FROM strategies_fts
           WHERE strategies_fts MATCH ?
           ORDER BY rank
           LIMIT ?""",
        (query_text, k),
    ).fetchall()
    return [(row[0], -row[1]) for row in rows]  # FTS5 rank is negative
```

```python
# Modified retrieve() with RRF fusion
def retrieve(
    self,
    query_text: str,
    k: int = 5,
    species: str | None = None,
    rrf_k: int = 60,
) -> list[StrategyEntry]:
    """Hybrid BM25 + FAISS retrieval with Reciprocal Rank Fusion."""
    if self._faiss.count == 0:
        return []

    fetch_k = k * 3 if species else k * 2

    # FAISS (vector similarity)
    embedding = self._embed(query_text)
    faiss_results = self._faiss.search(embedding, k=fetch_k)
    faiss_ranking = {mid: rank for rank, (mid, _) in enumerate(faiss_results)}

    # BM25 (keyword match)
    bm25_results = self._retrieve_bm25(query_text, k=fetch_k)
    bm25_ranking = {mid: rank for rank, (mid, _) in enumerate(bm25_results)}

    # RRF fusion: score = sum(1 / (rrf_k + rank)) across both retrievers
    all_ids = set(faiss_ranking.keys()) | set(bm25_ranking.keys())
    fused_scores: dict[str, float] = {}
    for mid in all_ids:
        score = 0.0
        if mid in faiss_ranking:
            score += 1.0 / (rrf_k + faiss_ranking[mid])
        if mid in bm25_ranking:
            score += 1.0 / (rrf_k + bm25_ranking[mid])
        fused_scores[mid] = score

    # Sort by fused score descending, filter by species, apply validity
    ranked = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

    entries: list[StrategyEntry] = []
    for memory_id, rrf_score in ranked:
        row = self._conn.execute(
            "SELECT * FROM strategies WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            continue
        if species and row["species"] != species:
            continue
        meta = json.loads(row["metadata_json"])
        validity = meta.get("validity_score", 0.5)
        # Weight RRF score by validity (Bayesian credibility)
        adjusted_score = rrf_score * (0.5 + validity)
        entries.append(StrategyEntry(
            id=row["id"],
            description=row["description"],
            insight=row["insight"],
            source_trial_id=row["source_trial_id"],
            species=row["species"],
            created_at=row["created_at"],
            metadata=meta,
            similarity_score=adjusted_score,
        ))
        if len(entries) >= k:
            break

    return entries
```

### 1.2 Staleness Detection (Content-Hash Invalidation)

When the model registry or active prompt files change, strategies derived under the old configuration become unreliable. intake-414's content-hash approach detects this automatically.

**Mechanism**: On `store()`, hash the current model_registry.yaml + active prompt file contents into a `context_hash` field. On `retrieve()`, compare the current context hash against each entry's stored hash. Entries with a stale hash get a validity penalty.

```python
import hashlib

# Context files that define the "configuration epoch"
_CONTEXT_FILES = [
    Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml"),
    Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/prompts/frontdoor.md"),
    Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/prompts/roles/worker_explore.md"),
]

def _compute_context_hash(self) -> str:
    """SHA256 of concatenated context files. Changes = new epoch."""
    h = hashlib.sha256()
    for p in _CONTEXT_FILES:
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:16]  # 16 hex chars = 64 bits, collision-safe
```

The `strategies` table gets a `context_hash TEXT` column. On `store()`, the current hash is recorded. On `retrieve()`, entries whose `context_hash` differs from the current hash receive a 0.5x validity multiplier (halved credibility, not deleted -- they may still contain transferable insights).

Schema migration:

```python
# In _init_schema(), after table creation:
try:
    self._conn.execute("ALTER TABLE strategies ADD COLUMN context_hash TEXT DEFAULT ''")
    self._conn.commit()
except sqlite3.OperationalError:
    pass  # Column already exists

try:
    self._conn.execute("ALTER TABLE strategies ADD COLUMN validity_score REAL DEFAULT 0.5")
    self._conn.commit()
except sqlite3.OperationalError:
    pass  # Column already exists

try:
    self._conn.execute("ALTER TABLE strategies ADD COLUMN entry_type TEXT DEFAULT 'raw'")
    self._conn.commit()
except sqlite3.OperationalError:
    pass  # Column already exists
```

### 1.3 Bayesian Validity Tracking

Each strategy entry gets a `validity_score` (0.0-1.0, default 0.5) that is updated after each trial:

- **Positive signal**: A trial references this strategy (retrieved in top-k) AND produces a Pareto improvement -> `validity_score += alpha * (1 - validity_score)` where alpha=0.15.
- **Negative signal**: A trial references this strategy AND fails the safety gate -> `validity_score -= beta * validity_score` where beta=0.10.
- **Decay**: Unreferenced strategies decay toward 0.3 at rate gamma=0.005 per trial cycle.

```python
def update_validity(self, entry_id: str, outcome: str) -> None:
    """Update Bayesian validity score based on trial outcome.

    Args:
        entry_id: Strategy entry UUID
        outcome: "positive" (Pareto frontier), "negative" (safety fail), or "decay"
    """
    row = self._conn.execute(
        "SELECT metadata_json, validity_score FROM strategies WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if row is None:
        return

    score = row["validity_score"] if row["validity_score"] is not None else 0.5

    if outcome == "positive":
        score += 0.15 * (1.0 - score)  # Approach 1.0 asymptotically
    elif outcome == "negative":
        score -= 0.10 * score  # Approach 0.0 asymptotically
    elif outcome == "decay":
        score += 0.005 * (0.3 - score)  # Decay toward prior of 0.3

    score = max(0.01, min(1.0, score))  # Clamp

    self._conn.execute(
        "UPDATE strategies SET validity_score = ? WHERE id = ?",
        (score, entry_id),
    )
    self._conn.commit()
```

**Integration point** in `autopilot.py` main loop (after line 1279 in the "Record" phase):

```python
# Update validity for strategies that were retrieved this trial
if strategy_store is not None and "_retrieved_strategies" in state:
    outcome = "positive" if pareto_status == "frontier" else (
        "negative" if not verdict.passed else "decay"
    )
    for sid in state.pop("_retrieved_strategies", []):
        strategy_store.update_validity(sid, outcome)
```

The `_retrieved_strategies` list is populated during `dispatch_action` when strategies are retrieved for PromptForge context (around line 548).

### 1.4 Phase 1 Migration Path

The schema changes use `ALTER TABLE ... ADD COLUMN` with `DEFAULT` values, so existing databases work without data migration. The FTS5 virtual table is created alongside the existing table and populated via triggers on new inserts. To backfill FTS5 for existing entries:

```python
def _backfill_fts(self) -> None:
    """One-time FTS5 backfill for pre-upgrade entries."""
    count = self._conn.execute(
        "SELECT COUNT(*) FROM strategies_fts"
    ).fetchone()[0]
    if count > 0:
        return  # Already populated
    self._conn.execute("""
        INSERT INTO strategies_fts(rowid, id, description, insight, species)
        SELECT rowid, id, description, insight, species FROM strategies
    """)
    self._conn.commit()
    logger.info("Backfilled FTS5 index for %d existing strategies", count)
```

---

## Phase 2: Knowledge Distillation Pipeline

**Target**: New file `knowledge_distiller.py` in `orchestration/repl_memory/`
**Estimated size**: ~300 LoC
**Dependencies**: Phase 1 (requires `entry_type` and `validity_score` fields)

### 2.1 Three-Tier Knowledge Hierarchy

Adapting intake-413's L1/L2/L3 hierarchy and intake-414's MDL distillation:

| Tier | Name | Description | Example |
|------|------|-------------|---------|
| L1 (raw) | Entry | Individual strategy from a single trial | "Disabling self-speculation improved Qwen3.5 quality by 0.08" |
| L2 (pattern) | Pattern | Cluster of 3+ similar L1 entries from same species/region | "Self-speculation is net-negative for hybrid SSM-dense models (N=5 trials, validity=0.78)" |
| L3 (convention) | Convention | Cross-species pattern appearing in 3+ species or 10+ trials | "Hybrid SSM-dense models require inference parameter tuning distinct from pure-dense models" |

All three tiers live in the same `strategies` table, differentiated by the `entry_type` column (`raw`, `pattern`, `convention`).

### 2.2 Distillation Triggers

Distillation runs at two trigger points:

1. **Periodic**: Every N=25 trials (aligned with the existing auto-checkpoint at `autopilot.py:1403`)
2. **On rebalance**: When MetaOptimizer rebalances (every 50 trials), distillation runs first to ensure the rebalance uses consolidated knowledge

### 2.3 L1 -> L2: Pattern Extraction

Group L1 entries by (species, objective_region). Within each group, cluster by embedding similarity. Clusters with 3+ members are consolidated into a single L2 pattern entry.

```python
"""Knowledge distiller: periodic consolidation of strategy memory.

Implements L1->L2->L3 hierarchy from intake-413 (HCC) with MDL
distillation from intake-414 (Token Savior).
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# MDL threshold: consolidate if N entries can be described by 1 pattern
# with residuals totaling less than the original entries
MDL_MIN_CLUSTER_SIZE = 3


class KnowledgeDistiller:
    """Periodic consolidation of raw strategy entries into patterns and conventions."""

    def __init__(self, strategy_store, similarity_threshold: float = 0.75):
        self.store = strategy_store
        self.sim_threshold = similarity_threshold

    def distill(self, trial_id: int) -> dict[str, Any]:
        """Run full distillation cycle: L1->L2, L2->L3.

        Returns summary dict with counts of new patterns/conventions.
        """
        stats = {"patterns_created": 0, "conventions_created": 0, "entries_consolidated": 0}

        # Phase A: L1 -> L2 (within-species pattern extraction)
        raw_entries = self._fetch_entries_by_type("raw")
        if len(raw_entries) >= MDL_MIN_CLUSTER_SIZE:
            grouped = self._group_by_species(raw_entries)
            for species, entries in grouped.items():
                new_patterns = self._extract_patterns(entries, species, trial_id)
                stats["patterns_created"] += len(new_patterns)
                stats["entries_consolidated"] += sum(
                    p["source_count"] for p in new_patterns
                )

        # Phase B: L2 -> L3 (cross-species convention promotion)
        patterns = self._fetch_entries_by_type("pattern")
        if len(patterns) >= MDL_MIN_CLUSTER_SIZE:
            new_conventions = self._extract_conventions(patterns, trial_id)
            stats["conventions_created"] += len(new_conventions)

        logger.info(
            "Distillation complete: %d patterns, %d conventions from %d entries",
            stats["patterns_created"],
            stats["conventions_created"],
            stats["entries_consolidated"],
        )
        return stats

    def _fetch_entries_by_type(self, entry_type: str) -> list[dict]:
        """Fetch all entries of a given type from strategy store."""
        rows = self.store._conn.execute(
            "SELECT * FROM strategies WHERE entry_type = ? AND validity_score > 0.1",
            (entry_type,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _group_by_species(self, entries: list[dict]) -> dict[str, list[dict]]:
        grouped = defaultdict(list)
        for e in entries:
            grouped[e["species"]].append(e)
        return dict(grouped)

    def _extract_patterns(
        self, entries: list[dict], species: str, trial_id: int
    ) -> list[dict]:
        """Cluster similar L1 entries and merge into L2 patterns.

        Uses embedding similarity for clustering. Entries in a cluster
        are soft-deleted (validity set to 0.01) and replaced by the
        pattern entry.
        """
        if len(entries) < MDL_MIN_CLUSTER_SIZE:
            return []

        # Build embedding matrix
        embeddings = []
        for e in entries:
            text = f"{e['description']} {e['insight']}"
            emb = self.store._embed(text)
            embeddings.append(emb)
        emb_matrix = np.stack(embeddings)

        # Greedy clustering by cosine similarity
        clusters = self._greedy_cluster(entries, emb_matrix)

        new_patterns = []
        for cluster in clusters:
            if len(cluster) < MDL_MIN_CLUSTER_SIZE:
                continue

            # MDL check: is the cluster compressible?
            # Pattern description length < sum of individual entry lengths
            total_entry_len = sum(
                len(entries[i]["description"]) + len(entries[i]["insight"])
                for i in cluster
            )
            avg_description = entries[cluster[0]]["description"]  # Seed from highest-validity
            if len(avg_description) * 2 >= total_entry_len:
                continue  # Not compressible under MDL

            # Merge: highest-validity entry becomes the pattern seed
            cluster_entries = [entries[i] for i in cluster]
            cluster_entries.sort(
                key=lambda e: json.loads(e.get("metadata_json", "{}")).get(
                    "validity_score", 0.5
                ),
                reverse=True,
            )
            seed = cluster_entries[0]

            # Compute mean validity across cluster
            validities = []
            for e in cluster_entries:
                meta = json.loads(e.get("metadata_json", "{}"))
                validities.append(meta.get("validity_score", 0.5))
            mean_validity = sum(validities) / len(validities)

            # Store the pattern
            pattern_id = self.store.store(
                description=f"[PATTERN] {seed['description']}",
                insight=(
                    f"Consolidated from {len(cluster)} trials "
                    f"(validity={mean_validity:.2f}). {seed['insight']}"
                ),
                source_trial_id=trial_id,
                species=species,
                metadata={
                    "entry_type": "pattern",
                    "validity_score": min(0.9, mean_validity + 0.1),
                    "source_count": len(cluster),
                    "source_ids": [e["id"] for e in cluster_entries],
                },
            )
            # Mark the new entry as type=pattern in the DB
            self.store._conn.execute(
                "UPDATE strategies SET entry_type = 'pattern' WHERE id = ?",
                (pattern_id,),
            )

            # Soft-delete consolidated entries (reduce validity, don't delete)
            for e in cluster_entries:
                self.store._conn.execute(
                    "UPDATE strategies SET validity_score = 0.01 WHERE id = ?",
                    (e["id"],),
                )

            self.store._conn.commit()
            new_patterns.append({
                "id": pattern_id,
                "source_count": len(cluster),
                "species": species,
            })

        return new_patterns

    def _extract_conventions(
        self, patterns: list[dict], trial_id: int
    ) -> list[dict]:
        """Promote cross-species patterns to L3 conventions.

        A convention is created when the same pattern appears across
        3+ species, indicating a general principle.
        """
        # Group patterns by embedding cluster (cross-species)
        embeddings = []
        for p in patterns:
            text = f"{p['description']} {p['insight']}"
            emb = self.store._embed(text)
            embeddings.append(emb)
        emb_matrix = np.stack(embeddings)

        clusters = self._greedy_cluster(patterns, emb_matrix)

        new_conventions = []
        for cluster in clusters:
            cluster_entries = [patterns[i] for i in cluster]
            species_set = {e["species"] for e in cluster_entries}

            # Convention requires 3+ species or 10+ total source entries
            total_sources = sum(
                json.loads(e.get("metadata_json", "{}")).get("source_count", 1)
                for e in cluster_entries
            )
            if len(species_set) < 3 and total_sources < 10:
                continue

            seed = cluster_entries[0]  # Highest-validity pattern
            convention_id = self.store.store(
                description=f"[CONVENTION] {seed['description'].replace('[PATTERN] ', '')}",
                insight=(
                    f"Cross-species convention from {len(species_set)} species, "
                    f"{total_sources} total trials. {seed['insight']}"
                ),
                source_trial_id=trial_id,
                species="all",
                metadata={
                    "entry_type": "convention",
                    "validity_score": 0.9,
                    "species_sources": list(species_set),
                    "total_source_trials": total_sources,
                    "source_pattern_ids": [e["id"] for e in cluster_entries],
                },
            )
            self.store._conn.execute(
                "UPDATE strategies SET entry_type = 'convention' WHERE id = ?",
                (convention_id,),
            )
            self.store._conn.commit()
            new_conventions.append({
                "id": convention_id,
                "species_count": len(species_set),
                "total_sources": total_sources,
            })

        return new_conventions

    def _greedy_cluster(
        self, entries: list[dict], emb_matrix: np.ndarray
    ) -> list[list[int]]:
        """Greedy agglomerative clustering by cosine similarity.

        Returns list of clusters, each a list of indices into entries.
        No external dependencies (no sklearn required).
        """
        n = len(entries)
        if n == 0:
            return []

        # Normalize for cosine similarity
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-9
        normed = emb_matrix / norms
        sim_matrix = normed @ normed.T

        assigned = [False] * n
        clusters: list[list[int]] = []

        for i in range(n):
            if assigned[i]:
                continue
            cluster = [i]
            assigned[i] = True
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                if sim_matrix[i, j] >= self.sim_threshold:
                    cluster.append(j)
                    assigned[j] = True
            clusters.append(cluster)

        return clusters
```

### 2.4 Integration with AutoPilot Main Loop

In `autopilot.py`, the distiller is triggered alongside the auto-checkpoint:

```python
# After line 1408 (auto-checkpoint block):
if trial_counter > 0 and trial_counter % 25 == 0 and strategy_store is not None:
    from orchestration.repl_memory.knowledge_distiller import KnowledgeDistiller
    distiller = KnowledgeDistiller(strategy_store)
    distill_stats = distiller.distill(trial_id=trial_counter)
    log.info("Knowledge distillation: %s", distill_stats)
```

---

## Phase 3: Controller Context Budget Management

**Target**: `autopilot.py` (controller prompt assembly, lines 1107-1156) + `eval_tower.py`
**Estimated delta**: ~150 LoC
**Dependencies**: Phase 2 (conventions must exist for tiered injection)

### 3.1 Fixed Token Budget Per Section

The controller prompt currently has 14 sections with no size limits. Define a token budget (approximated as chars/4) for each:

```python
# Token budgets per controller prompt section (approximate tokens)
SECTION_BUDGETS: dict[str, int] = {
    "program": 800,         # Human-editable strategy (trimmed if needed)
    "pareto_summary": 500,  # Pareto archive (fixed format, naturally bounded)
    "journal_summary": 1000, # Last 20 journal entries
    "seeder_status": 200,   # Convergence status JSON
    "species_effectiveness": 300, # Per-species rates
    "slot_memory": 200,     # Slot KV usage
    "budget": 150,          # Species budget JSON
    "suite_quality_trends": 400, # Per-suite quality over time
    "insights": 600,        # Cross-species insights
    "short_term_memory": 800, # Accumulated learnings (already capped at ~2000 tokens)
    "last_criticism": 400,  # Self-criticism from last trial
    "model_signatures": 300, # Model performance table
    "blacklist_text": 200,  # Failure blacklist
    "plot_paths": 100,      # Plot file paths
}
# Total: ~6050 tokens for state sections + ~2000 for program = ~8050 tokens
# Controller output budget: ~2000 tokens
# Total prompt: ~10,050 tokens -- well within any model's context window
```

```python
def _truncate_to_budget(text: str, budget_tokens: int) -> str:
    """Truncate text to approximate token budget (4 chars/token heuristic).

    Preserves complete lines. Adds truncation marker if trimmed.
    """
    max_chars = budget_tokens * 4
    if len(text) <= max_chars:
        return text
    lines = text.splitlines()
    result_lines = []
    char_count = 0
    for line in lines:
        if char_count + len(line) + 1 > max_chars - 40:  # Reserve space for marker
            break
        result_lines.append(line)
        char_count += len(line) + 1
    result_lines.append(f"  ... ({len(lines) - len(result_lines)} lines truncated)")
    return "\n".join(result_lines)
```

### 3.2 Progressive Disclosure for Strategy Injection

Replace the current flat strategy injection (used in `dispatch_action` for PromptForge context at line 546-557) with tiered disclosure following intake-414's 15/60/200 token model:

| Entry Type | Injection Format | Token Budget |
|------------|-----------------|--------------|
| Convention | Full detail: description + insight + validity + source count | ~200 tokens each, up to 3 |
| Pattern | Summary: description + validity score | ~60 tokens each, up to 5 |
| Raw | One-line reference: description only | ~15 tokens each, up to 10 |

```python
def format_strategies_tiered(entries: list["StrategyEntry"]) -> str:
    """Format strategy entries with progressive disclosure by tier.

    Conventions get full detail, patterns get summaries, raw entries
    get one-line references. This replaces the flat list injection
    currently used in dispatch_action (line 550-556).
    """
    conventions = [e for e in entries if e.metadata.get("entry_type") == "convention"]
    patterns = [e for e in entries if e.metadata.get("entry_type") == "pattern"]
    raw = [e for e in entries if e.metadata.get("entry_type", "raw") == "raw"]

    lines = []

    if conventions:
        lines.append("### Conventions (high-confidence cross-species principles)")
        for c in conventions[:3]:
            lines.append(
                f"- **{c.description}** (validity={c.metadata.get('validity_score', 0.5):.2f}, "
                f"from {c.metadata.get('total_source_trials', '?')} trials)\n"
                f"  {c.insight}"
            )

    if patterns:
        lines.append("### Patterns (within-species consolidations)")
        for p in patterns[:5]:
            lines.append(
                f"- {p.description} (v={p.metadata.get('validity_score', 0.5):.2f})"
            )

    if raw:
        lines.append("### Recent observations")
        for r in raw[:10]:
            lines.append(f"- {r.description[:80]}")

    return "\n".join(lines) if lines else "(no strategy insights available)"
```

### 3.3 Eval Tower Output Gating

intake-415's 5KB threshold gating applies directly to eval tower output before it enters the controller context. Currently, `eval_result.details` can be arbitrarily large (full per-question scoring breakdowns). Gate this:

```python
def gate_eval_output(eval_result: "EvalResult", threshold_bytes: int = 5120) -> str:
    """Apply 5KB threshold gating to eval result details.

    If details are small, pass through. If large, summarize to
    per-suite aggregates + worst-case examples only.
    """
    details_text = json.dumps(eval_result.details or {}, indent=2)

    if len(details_text.encode()) <= threshold_bytes:
        return details_text

    # Large output: summarize
    summary = {
        "quality": eval_result.quality,
        "speed": eval_result.speed,
        "per_suite": eval_result.per_suite_quality or {},
        "reliability": eval_result.reliability,
        "note": f"Full details suppressed ({len(details_text)} chars > {threshold_bytes} byte threshold)",
    }
    # Include worst 3 suite results for diagnostic value
    if eval_result.per_suite_quality:
        worst = sorted(eval_result.per_suite_quality.items(), key=lambda x: x[1])[:3]
        summary["worst_suites"] = dict(worst)

    return json.dumps(summary, indent=2)
```

### 3.4 Section Assembly with Budgets

Modify the prompt assembly block in the main loop (lines 1135-1156) to apply truncation:

```python
prompt = CONTROLLER_PROMPT_TEMPLATE.format(
    program=_truncate_to_budget(program_text, SECTION_BUDGETS["program"]),
    pareto_summary=_truncate_to_budget(archive.summary_text(), SECTION_BUDGETS["pareto_summary"]),
    journal_summary=_truncate_to_budget(journal.summary_text(20), SECTION_BUDGETS["journal_summary"]),
    seeder_status=_truncate_to_budget(
        json.dumps(seeder.convergence_status(), indent=2),
        SECTION_BUDGETS["seeder_status"],
    ),
    # ... etc for all sections ...
)
```

---

## Phase 4: Mutation Knowledge Graph

**Target**: Enhancement to `prompt_forge.py` + `strategy_store.py`
**Estimated delta**: ~150 LoC across both files
**Dependencies**: Phase 1 (validity tracking), Phase 2 (pattern entries)

### 4.1 Mutation Outcome Triples

Track structured `(mutation_type, failure_pattern, outcome)` triples in a new SQLite table alongside the strategy store:

```python
# New table in strategy_store._init_schema()
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS mutation_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trial_id INTEGER NOT NULL,
        mutation_type TEXT NOT NULL,
        target_file TEXT NOT NULL,
        failure_pattern TEXT,
        outcome TEXT NOT NULL,  -- 'pareto_improvement', 'neutral', 'regression', 'safety_fail'
        quality_delta REAL,
        speed_delta REAL,
        created_at TEXT NOT NULL
    )
""")
self._conn.execute(
    "CREATE INDEX IF NOT EXISTS idx_mo_mutation ON mutation_outcomes(mutation_type)"
)
self._conn.execute(
    "CREATE INDEX IF NOT EXISTS idx_mo_pattern ON mutation_outcomes(failure_pattern)"
)
```

### 4.2 Recording Mutation Outcomes

After each prompt_mutation or code_mutation trial in `dispatch_action`, record the outcome:

```python
def record_mutation_outcome(
    strategy_store: "StrategyStore",
    trial_id: int,
    mutation_type: str,
    target_file: str,
    failure_pattern: str,
    outcome: str,
    quality_delta: float,
    speed_delta: float,
) -> None:
    """Record a mutation outcome triple for knowledge graph queries."""
    strategy_store._conn.execute(
        """INSERT INTO mutation_outcomes
           (trial_id, mutation_type, target_file, failure_pattern, outcome,
            quality_delta, speed_delta, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (trial_id, mutation_type, target_file, failure_pattern, outcome,
         quality_delta, speed_delta,
         datetime.now(timezone.utc).isoformat()),
    )
    strategy_store._conn.commit()
```

### 4.3 Informed Mutation Proposal

When PromptForge proposes a mutation, it queries the mutation outcomes table first:

```python
def query_mutation_history(
    strategy_store: "StrategyStore",
    mutation_type: str,
    target_file: str,
    limit: int = 10,
) -> list[dict]:
    """Query past outcomes for a specific mutation type + target.

    Returns sorted by recency, with success rates.
    """
    rows = strategy_store._conn.execute(
        """SELECT mutation_type, target_file, failure_pattern, outcome,
                  quality_delta, speed_delta
           FROM mutation_outcomes
           WHERE mutation_type = ? AND target_file = ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (mutation_type, target_file, limit),
    ).fetchall()

    results = [dict(row) for row in rows]

    # Compute success rate
    if results:
        successes = sum(1 for r in results if r["outcome"] == "pareto_improvement")
        total = len(results)
        results.insert(0, {
            "_summary": f"{mutation_type} on {target_file}: "
                        f"{successes}/{total} Pareto-improving ({100*successes/total:.0f}%)"
        })

    return results
```

### 4.4 Crossover Enhancement

The current crossover mutation type in PromptForge is underutilized. With the mutation knowledge graph, we can identify the strongest-performing prompt sections from Pareto-best configs:

```python
def find_strongest_sections(
    strategy_store: "StrategyStore",
    target_file: str,
) -> list[str]:
    """Find mutation descriptions from Pareto-improving trials on this file.

    These describe which sections were modified and how. Used to guide
    crossover and style_transfer mutations.
    """
    rows = strategy_store._conn.execute(
        """SELECT s.description, s.insight, mo.quality_delta
           FROM mutation_outcomes mo
           JOIN strategies s ON s.source_trial_id = mo.trial_id
           WHERE mo.target_file = ?
             AND mo.outcome = 'pareto_improvement'
           ORDER BY mo.quality_delta DESC
           LIMIT 5""",
        (target_file,),
    ).fetchall()

    return [
        f"Delta +{row['quality_delta']:.3f}: {row['description']} -- {row['insight']}"
        for row in rows
    ]
```

This list is injected into the PromptForge mutation prompt as a "## Known Effective Patterns" section, enabling crossover to copy proven patterns rather than guessing.

---

## Phase 5: Expected Impact Analysis

### Trial Efficiency (fewer wasted trials)

| Phase | Mechanism | Expected Improvement |
|-------|-----------|---------------------|
| 1 (Hybrid retrieval) | BM25 catches exact-match queries that FAISS hash fallback misses | 10-15% fewer redundant trials (strategies that would have been missed are now found) |
| 1 (Staleness) | Auto-invalidation prevents re-testing strategies from stale configs | 5-10% fewer wasted trials in the first 20 trials after a config change |
| 1 (Validity) | Low-validity strategies deprioritized in retrieval ranking | Gradual: 5% improvement after 50 trials with validity data |
| 2 (Distillation) | Conventions provide higher-level guidance, reducing random exploration | 15-20% after sufficient patterns are extracted (requires ~75 raw entries) |
| 3 (Context budget) | Controller receives cleaner signal, proposes better actions | 10% fewer incoherent proposals at high trial counts (200+) |
| 4 (Mutation graph) | Mutation type x failure pattern lookup avoids known-bad combinations | 10-15% fewer failed mutations |

**Composite estimate**: At trial 200+, total trial waste reduction of ~30-40% compared to current flat-memory baseline.

### Knowledge Retention (less repeated exploration)

| Phase | Mechanism | Metric |
|-------|-----------|--------|
| 2 (Patterns) | Repeated findings consolidated; new entries point to existing patterns | Unique strategy count grows sub-linearly after distillation (target: 50% fewer raw entries at trial 200) |
| 2 (Conventions) | Cross-species knowledge survives species budget rebalancing | Convention entries persist across rebalance cycles (currently, species-filtered retrieval misses cross-species lessons) |
| 1 (Staleness) | Old entries decay rather than pollute retrieval results | Effective strategy count stays bounded as configs evolve |

### Context Budget Utilization

| Phase | Mechanism | Metric |
|-------|-----------|--------|
| 3 (Token budgets) | Fixed per-section caps prevent any single section from dominating | Controller prompt stays under 10K tokens regardless of trial count (currently can exceed 15K at trial 200+) |
| 3 (Progressive disclosure) | Conventions: 600 tokens, patterns: 300 tokens, raw: 150 tokens | Strategy section: ~1050 tokens max (currently unbounded) |
| 3 (Eval gating) | Eval details truncated above 5KB | Eval section: ~1300 tokens max (currently can exceed 5K for complex evals) |

### Time to Pareto Improvement

| Phase | Mechanism | Expected Speedup |
|-------|-----------|-----------------|
| 4 (Mutation graph) | Known-effective mutation types tried first | 2-3x faster for prompt optimization campaigns (fewer wasted mutation trials) |
| 2 (Conventions) | High-level guidance reduces search space from trial 1 of each session | Faster warm-start after session restart or config change |
| 1 (Validity) | High-validity strategies prioritized | Marginal (~5%) but compounds with other phases |

---

## Phase 6: Dependency Chain and Implementation Order

```
Phase 1 (strategy_store.py)
  |
  ├── 1.1 FTS5 + RRF retrieval  ──> standalone, deploy first
  ├── 1.2 Staleness detection    ──> standalone, parallel with 1.1
  ├── 1.3 Validity tracking      ──> needs schema from 1.2
  └── 1.4 Migration/backfill     ──> after 1.1-1.3
  |
Phase 2 (knowledge_distiller.py)  ──> requires entry_type field from Phase 1
  |
  ├── 2.1 L1->L2 pattern extraction  ──> needs Phase 1 complete
  ├── 2.2 L2->L3 convention promotion ──> needs 2.1
  └── 2.3 Integration with main loop  ──> needs 2.1+2.2
  |
Phase 3 (autopilot.py context)  ──> can start in parallel with Phase 2
  |
  ├── 3.1 Token budgets           ──> standalone
  ├── 3.2 Progressive disclosure  ──> needs Phase 2 conventions to exist
  ├── 3.3 Eval output gating      ──> standalone, parallel with 3.1
  └── 3.4 Section assembly        ──> integrates 3.1+3.3
  |
Phase 4 (mutation knowledge graph)  ──> requires Phase 1 validity + Phase 2 patterns
  |
  ├── 4.1 Mutation outcomes table  ──> standalone
  ├── 4.2 Recording outcomes       ──> needs 4.1
  ├── 4.3 Informed proposals       ──> needs 4.1+4.2
  └── 4.4 Crossover enhancement    ──> needs 4.3
```

**Parallelizable work streams**:
- Phase 1 + Phase 3.1/3.3 (context budgets and eval gating are independent of strategy store changes)
- Phase 2 + Phase 4.1 (new table creation is independent of distillation logic)

**Critical path**: Phase 1.1 -> Phase 1.3 -> Phase 2.1 -> Phase 2.2 -> Phase 3.2 -> Phase 4.4

**Estimated implementation time**:
- Phase 1: 2-3 hours (schema changes + retrieval rewrite + validity methods)
- Phase 2: 3-4 hours (new file + clustering logic + integration)
- Phase 3: 1-2 hours (truncation utility + template modification)
- Phase 4: 2-3 hours (new table + recording + query + crossover integration)
- **Total**: 8-12 hours of focused implementation

---

## Phase 7: Risk Register

### Phase 1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| FTS5 tokenization mismatch: Porter stemmer over-conflates domain terms (e.g., "model" = "models" = "modeling") | Medium | Low | Use `unicode61` tokenizer alongside Porter; test with actual strategy descriptions before deploying |
| RRF k parameter sensitivity: wrong k value over-weights one retriever | Low | Medium | Default k=60 is well-studied (Cormack et al. 2009); validate with A/B comparison on first 50 retrievals |
| Schema migration on existing DB: ALTER TABLE on large database blocks reads | Low | Low | Strategy DB is small (<10K rows); migration takes <1s. Add explicit transaction timeout |
| Hash fallback embedding creates non-semantic FAISS results that dominate RRF | Medium | Medium | BM25 leg compensates; the combined score is always better than either alone. Long-term: migrate to real embedder |

### Phase 2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Over-consolidation: clustering merges genuinely distinct strategies | Medium | High | Conservative similarity threshold (0.75); soft-delete (validity=0.01) rather than hard delete; add `source_ids` list for audit trail and potential un-merge |
| Convention promotion from insufficient data: patterns promoted to conventions prematurely | Medium | Medium | Require 3+ species OR 10+ total source trials; conventions can be demoted if validity decays below 0.3 |
| Distillation cost: LLM invocation for pattern summarization adds latency | Low | Low | Pattern extraction uses embedding clustering (no LLM); only the EvolutionManager distill_knowledge action uses LLM. KnowledgeDistiller is purely algorithmic |
| Stale conventions: a convention formed at trial 100 may not apply at trial 300 | Medium | Medium | Conventions inherit the context_hash of their source patterns; staleness detection (Phase 1.2) applies equally to conventions |

### Phase 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Budget too tight: important information truncated before controller sees it | Medium | High | Start with generous budgets (2x the estimates above); monitor controller action quality for regression after enabling budgets; add escape hatch for "full context" mode during debugging |
| Line-level truncation breaks JSON or markdown tables | Low | Medium | Truncation function preserves complete lines; JSON sections are pre-formatted to a known size before insertion |
| Eval gating hides diagnostic details needed for controller reasoning | Medium | Medium | Gate includes worst-3-suite breakdown and truncation note; full details remain in the journal for human review |

### Phase 4 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sparse mutation history: few trials per mutation_type x target_file combination | High (early) | Medium | Return empty/no-op when history is sparse; fall back to current behavior (no mutation history injection); benefit grows with trial count |
| Outcome attribution error: mutation credited/blamed for quality change caused by other factors | Medium | Medium | Single-variable enforcement (AP-9) reduces confounding; validity Bayesian update is conservative (alpha=0.15, beta=0.10) |
| Knowledge graph query latency: JOIN across mutation_outcomes and strategies | Low | Low | Both tables are small (<10K rows); indexes on mutation_type and trial_id ensure sub-ms queries |

### Cross-Phase Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Interaction effects: validity scoring + distillation + context budgets compound in unexpected ways | Medium | Medium | Deploy phases incrementally with A/B comparison (run 50 trials with Phase N vs Phase N-1). Each phase has independent rollback |
| Increased complexity of strategy_store.py: harder to debug retrieval issues | Medium | Low | Add structured logging to retrieval path (log BM25 rank, FAISS rank, RRF score, validity, entry_type for each result); add `explain_retrieval()` method for debugging |
| Memory/disk growth from distillation: pattern and convention entries accumulate indefinitely | Low | Low | Strategy DB is text-only with embeddings in FAISS; even 100K entries would be <100MB. Add periodic vacuum if needed |

---

## Implementation Checklist

### Phase 1 (strategy_store.py)
- [ ] Add FTS5 virtual table + sync triggers to `_init_schema()`
- [ ] Add `_retrieve_bm25()` method
- [ ] Modify `retrieve()` to use RRF fusion
- [ ] Add `context_hash`, `validity_score`, `entry_type` columns with migration
- [ ] Add `_compute_context_hash()` method
- [ ] Record `context_hash` in `store()` method
- [ ] Apply staleness penalty in `retrieve()`
- [ ] Add `update_validity()` method
- [ ] Add `_backfill_fts()` method
- [ ] Wire validity updates into autopilot.py main loop (after Record phase)
- [ ] Wire `_retrieved_strategies` tracking into dispatch_action
- [ ] Tests: verify RRF outperforms FAISS-only on known queries; verify staleness detection triggers on registry change

### Phase 2 (knowledge_distiller.py)
- [ ] Create `knowledge_distiller.py` with `KnowledgeDistiller` class
- [ ] Implement `_greedy_cluster()` for embedding-based clustering
- [ ] Implement `_extract_patterns()` with MDL check
- [ ] Implement `_extract_conventions()` with cross-species promotion
- [ ] Wire distillation trigger into autopilot.py (every 25 trials)
- [ ] Tests: verify pattern extraction from synthetic entries; verify convention promotion requires 3+ species

### Phase 3 (autopilot.py + eval_tower.py)
- [ ] Define `SECTION_BUDGETS` dict
- [ ] Implement `_truncate_to_budget()` utility
- [ ] Apply budgets to all 14 template sections in main loop
- [ ] Implement `format_strategies_tiered()` for progressive disclosure
- [ ] Replace flat strategy injection in dispatch_action with tiered version
- [ ] Implement `gate_eval_output()` in eval_tower.py
- [ ] Apply eval gating before controller prompt assembly
- [ ] Tests: verify prompt size stays under 10K tokens with synthetic 200-trial history

### Phase 4 (prompt_forge.py + strategy_store.py)
- [ ] Add `mutation_outcomes` table to strategy_store schema
- [ ] Implement `record_mutation_outcome()` function
- [ ] Wire recording into dispatch_action after prompt_mutation and code_mutation trials
- [ ] Implement `query_mutation_history()` function
- [ ] Implement `find_strongest_sections()` for crossover guidance
- [ ] Inject mutation history into PromptForge `_build_mutation_prompt()`
- [ ] Tests: verify mutation outcome recording and retrieval; verify crossover prompt includes strongest sections

---

## Key File Reference

| File | Current LoC | Phase(s) | Change Type |
|------|-------------|----------|-------------|
| `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/strategy_store.py` | 228 | 1, 4 | Modify (~200 LoC added) |
| `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/knowledge_distiller.py` | 0 (new) | 2 | Create (~300 LoC) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/autopilot.py` | ~1450 | 1, 2, 3 | Modify (~100 LoC added) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` | ~500 | 3 | Modify (~30 LoC added) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` | 814 | 4 | Modify (~40 LoC added) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/meta_optimizer.py` | 162 | 2 (trigger integration) | Modify (~10 LoC added) |
