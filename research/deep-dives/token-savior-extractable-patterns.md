# Deep Dive — intake-414 Token Savior Recall: Extractable Patterns for EPYC Strategy Memory

**Date**: 2026-04-20
**Repo**: https://github.com/mibayy/token-savior (v2.6.0, MIT license)
**Intake status**: novelty=medium, relevance=medium, verdict=worth_investigating (pre-deep-dive)
**Cross-refs**: intake-395 (claude-mem), intake-301 (AXI progressive disclosure), intake-302 (SkillReducer), intake-259 (context folding)
**Focus**: Extractable patterns for `strategy_store.py` and AutoPilot infrastructure — not a full system review

This deep dive examines four specific patterns from Token Savior's memory engine — RRF hybrid retrieval, content-hash staleness detection, MDL convention promotion, and progressive disclosure — and designs concrete implementations for EPYC's AutoPilot strategy store. Unlike the intake-395 (claude-mem) deep dive which assessed a full system, this analysis is narrowly scoped to extraction and adaptation.

---

## 1. RRF Hybrid Retrieval for strategy_store.py

### 1a. What Token Savior Actually Does

Source: `src/token_savior/memory/search.py`

Token Savior's `hybrid_search` function is clean and minimal:

1. Caller provides pre-computed FTS5 rows (BM25-ranked keyword matches).
2. If vector search is available (`sqlite-vec` extension loaded + embeddings exist), run k-NN against `obs_vectors` table.
3. Fuse both lists with Reciprocal Rank Fusion using `k=60` (the Cormack et al. 2009 standard constant).
4. If vector search is unavailable, return FTS rows untouched — graceful degradation.

The RRF merge itself is 20 lines:

```python
RRF_K = 60

def rrf_merge(*ranked_lists, limit=20, k=RRF_K):
    scores = {}
    metadata = {}
    for rows in ranked_lists:
        for rank, row in enumerate(rows, start=1):
            oid = row["id"]
            scores[oid] = scores.get(oid, 0.0) + 1.0 / (k + rank)
            if oid not in metadata:
                metadata[oid] = row
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [dict(metadata[oid]) | {"_rrf_score": score}
            for oid, score in ranked[:limit]]
```

Key design choice: Token Savior uses `sqlite-vec` (SQLite native vector extension) rather than a separate vector DB, keeping everything in one SQLite file. EPYC's strategy store already uses FAISS externally, which is fine — the RRF fusion is DB-agnostic.

### 1b. Current strategy_store.py Retrieval Path

The current `retrieve()` method in `strategy_store.py` (lines 169-206) does:

1. Embed query text via `TaskEmbedder` (BGE-large-en-v1.5, 1024d).
2. FAISS `IndexFlatIP` search for top `k*3` candidates.
3. Filter by species if requested.
4. Return top `k` by FAISS score only.

**What is missing**: No keyword matching at all. A query like "disable self-speculation for dense models" will match semantically similar strategies, but will miss strategies that happen to use different vocabulary for the same concept (e.g., "turn off speculative decoding for non-MoE architectures"). BM25 catches exact-term matches that semantic search can miss, and vice versa.

### 1c. Concrete Design: FTS5 + RRF for strategy_store.py

**Schema change** — add an FTS5 virtual table alongside the existing `strategies` table:

```python
def _init_schema(self) -> None:
    self._conn.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            insight TEXT NOT NULL,
            source_trial_id INTEGER,
            species TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}'
        )
    """)
    # NEW: FTS5 virtual table for keyword search
    self._conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS strategies_fts USING fts5(
            id UNINDEXED,
            description,
            insight,
            species UNINDEXED,
            content='strategies',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)
    # Triggers to keep FTS in sync with main table
    self._conn.execute("""
        CREATE TRIGGER IF NOT EXISTS strategies_ai AFTER INSERT ON strategies BEGIN
            INSERT INTO strategies_fts(rowid, id, description, insight, species)
            VALUES (new.rowid, new.id, new.description, new.insight, new.species);
        END
    """)
    self._conn.execute("""
        CREATE TRIGGER IF NOT EXISTS strategies_ad AFTER DELETE ON strategies BEGIN
            INSERT INTO strategies_fts(strategies_fts, rowid, id, description, insight, species)
            VALUES ('delete', old.rowid, old.id, old.description, old.insight, old.species);
        END
    """)
    self._conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_strategies_species ON strategies(species)"
    )
    self._conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_strategies_trial ON strategies(source_trial_id)"
    )
    self._conn.commit()
```

**FTS5 keyword search method**:

```python
def _fts_search(
    self,
    query_text: str,
    k: int = 20,
    species: str | None = None,
) -> list[tuple[str, float]]:
    """BM25-ranked keyword search over strategy descriptions and insights."""
    # Escape FTS5 special characters, keep meaningful terms
    terms = query_text.replace('"', '').replace("'", "")
    # Use OR matching so partial hits still surface
    fts_query = " OR ".join(terms.split()[:10])  # cap at 10 terms
    if not fts_query.strip():
        return []

    sql = """
        SELECT s.id, rank AS bm25_score
        FROM strategies_fts
        JOIN strategies s ON strategies_fts.id = s.id
        WHERE strategies_fts MATCH ?
    """
    params: list = [fts_query]
    if species:
        sql += " AND s.species = ?"
        params.append(species)
    sql += " ORDER BY rank LIMIT ?"
    params.append(k)

    try:
        rows = self._conn.execute(sql, params).fetchall()
        # FTS5 rank is negative (lower = better match), negate for scoring
        return [(row[0], -row[1]) for row in rows]
    except Exception as e:
        logger.warning("FTS5 search failed: %s", e)
        return []
```

**RRF fusion in retrieve()**:

```python
RRF_K = 60  # Standard constant from Cormack et al. 2009

def retrieve(
    self,
    query_text: str,
    k: int = 5,
    species: str | None = None,
) -> list[StrategyEntry]:
    """Retrieve strategies by hybrid BM25 + vector search with RRF fusion."""
    if self._faiss.count == 0:
        return []

    fetch_k = k * 4  # Over-fetch for both paths

    # Path 1: FAISS vector search
    embedding = self._embed(query_text)
    faiss_results = self._faiss.search(embedding, k=fetch_k)
    # Apply species filter to FAISS results
    if species:
        faiss_results = [
            (mid, score) for mid, score in faiss_results
            if self._get_species(mid) == species
        ]

    # Path 2: FTS5 keyword search
    fts_results = self._fts_search(query_text, k=fetch_k, species=species)

    # RRF fusion
    scores: dict[str, float] = {}
    for rank, (mid, _) in enumerate(faiss_results, start=1):
        scores[mid] = scores.get(mid, 0.0) + 1.0 / (RRF_K + rank)
    for rank, (mid, _) in enumerate(fts_results, start=1):
        scores[mid] = scores.get(mid, 0.0) + 1.0 / (RRF_K + rank)

    # Sort by RRF score, take top k
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]

    # Hydrate entries from SQLite
    entries: list[StrategyEntry] = []
    for mid, rrf_score in ranked:
        row = self._conn.execute(
            "SELECT * FROM strategies WHERE id = ?", (mid,)
        ).fetchone()
        if row is None:
            continue
        entries.append(StrategyEntry(
            id=row["id"],
            description=row["description"],
            insight=row["insight"],
            source_trial_id=row["source_trial_id"],
            species=row["species"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
            similarity_score=float(rrf_score),
        ))

    return entries

def _get_species(self, memory_id: str) -> str | None:
    """Look up species for a strategy ID. Cached by SQLite row factory."""
    row = self._conn.execute(
        "SELECT species FROM strategies WHERE id = ?", (memory_id,)
    ).fetchone()
    return row["species"] if row else None
```

**Migration path for existing stores**: The FTS5 virtual table can be populated from existing data with a one-time backfill:

```python
def _backfill_fts(self) -> None:
    """One-time FTS5 backfill from existing strategies table."""
    count = self._conn.execute(
        "SELECT COUNT(*) FROM strategies_fts"
    ).fetchone()[0]
    if count > 0:
        return  # Already populated
    self._conn.execute(
        "INSERT INTO strategies_fts(rowid, id, description, insight, species) "
        "SELECT rowid, id, description, insight, species FROM strategies"
    )
    self._conn.commit()
    logger.info("Backfilled FTS5 index with %d strategies", self.count())
```

### 1d. Why RRF Over Alternatives

- **vs. linear combination of scores** (`alpha * vector_score + (1-alpha) * bm25_score`): Requires score normalization across different scales. BM25 scores are unbounded; FAISS cosine similarities are [-1,1]. RRF is rank-based, so normalization is free.
- **vs. Chroma/Qdrant hybrid**: Adds external dependency. FTS5 is built into SQLite, zero-dependency. EPYC already has SQLite in the strategy store path.
- **vs. the TwoPhaseRetriever's Q-value approach**: The two-phase retriever (used for episodic memory) ranks by learned utility. Strategy memory is younger and has fewer training signals for Q-values. RRF provides a strong baseline until enough trial outcomes accumulate to train a Q-model over strategy entries specifically.

---

## 2. Content-Hash Staleness Detection for Strategy Entries

### 2a. What Token Savior Actually Does

Source: `src/token_savior/memory/consistency.py`

Token Savior links observations to **code symbols** (function names, class names) and checks staleness via `git log -S`:

```python
def check_symbol_staleness(project_root, symbol, obs_created_epoch):
    """True if git log shows symbol was modified after obs was created."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "-S", symbol, "--", "."],
        cwd=project_root, capture_output=True, text=True, timeout=3,
    )
    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip()) > int(obs_created_epoch)
    return False
```

When staleness is detected, the observation's Bayesian validity score is updated (beta incremented), and observations below a threshold (0.40) are quarantined — excluded from search results. A second threshold (0.60) marks entries as "stale-suspected" with a visual warning.

This is a **content-addressed invalidation** pattern: the "address" is the symbol name, and the "content" is the file containing it. When the content changes (detected via git pickaxe), cached knowledge about that symbol is marked suspect.

### 2b. Translating to AutoPilot Strategy Context

AutoPilot strategies are not linked to code symbols. They are linked to **system state**: model registry entries, server configurations, prompt templates, benchmark parameters. A strategy like "Disable self-speculation for dense models" becomes stale when:

1. The model registry changes (a model is swapped or its parameters updated).
2. The orchestrator configuration changes (new server flags, changed NUMA bindings).
3. The llama.cpp binary changes (new features make old advice obsolete).
4. Benchmark baselines shift (recalibration invalidates comparative insights).

**Content hash targets for strategy staleness**:

| Hash Source | File(s) | Invalidates |
|-------------|---------|-------------|
| `registry_hash` | `orchestration/model_registry.yaml` | Strategies referencing model names, quants, or role assignments |
| `config_hash` | `orchestration/orchestrator_config.yaml` | Strategies about server params, threading, batch sizes |
| `binary_hash` | llama.cpp build version (commit hash from `llama-server --version`) | Strategies about llama.cpp features or bugs |
| `prompt_hash` | `orchestration/prompt_templates/*.yaml` | Strategies about prompt engineering or template tuning |
| `benchmark_hash` | Most recent Pareto frontier checkpoint | Strategies with comparative performance claims |

### 2c. Implementation Design

**Schema addition** — add staleness tracking columns to `strategies`:

```python
def _init_schema(self) -> None:
    # ... existing CREATE TABLE ...

    # Add staleness tracking
    self._conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_validity (
            strategy_id TEXT PRIMARY KEY REFERENCES strategies(id),
            validity_alpha REAL DEFAULT 2.0,
            validity_beta REAL DEFAULT 1.0,
            context_hash TEXT NOT NULL,
            hash_sources TEXT NOT NULL,  -- JSON list of file paths hashed
            last_checked_at TEXT,
            stale_suspected INTEGER DEFAULT 0,
            quarantined INTEGER DEFAULT 0
        )
    """)
    self._conn.commit()
```

**Context hash computation** — hash the system state at strategy creation time:

```python
import hashlib
from pathlib import Path

HASH_SOURCES = {
    "registry": Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml"),
    "config": Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/orchestrator_config.yaml"),
}

def _compute_context_hash(self, sources: list[str] | None = None) -> tuple[str, list[str]]:
    """Hash relevant config files to capture system state.

    Returns (hash_hex, list_of_source_paths).
    """
    if sources is None:
        sources = list(HASH_SOURCES.keys())

    hasher = hashlib.sha256()
    resolved_paths = []
    for key in sorted(sources):
        path = HASH_SOURCES.get(key)
        if path and path.exists():
            hasher.update(path.read_bytes())
            resolved_paths.append(str(path))

    return hasher.hexdigest()[:16], resolved_paths
```

**Store with context hash** — capture state at creation time:

```python
def store(self, description, insight, source_trial_id, species,
          metadata=None, hash_sources=None):
    entry_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    metadata = metadata or {}

    embed_text = f"{description} {insight}"
    embedding = self._embed(embed_text)
    self._faiss.add(entry_id, embedding)
    self._faiss.save()

    self._conn.execute(
        "INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?)",
        (entry_id, description, insight, source_trial_id, species,
         created_at, json.dumps(metadata)),
    )

    # Record context hash at creation time
    ctx_hash, paths = self._compute_context_hash(hash_sources)
    self._conn.execute(
        "INSERT INTO strategy_validity "
        "(strategy_id, context_hash, hash_sources, last_checked_at) "
        "VALUES (?, ?, ?, ?)",
        (entry_id, ctx_hash, json.dumps(paths), created_at),
    )
    self._conn.commit()
    return entry_id
```

**Staleness check** — run periodically or before retrieval:

```python
STALENESS_QUARANTINE_THRESHOLD = 0.40
STALENESS_SUSPECT_THRESHOLD = 0.60

def check_staleness(self, batch_size: int = 50) -> dict:
    """Check strategies against current system state, update validity."""
    current_hash, _ = self._compute_context_hash()

    rows = self._conn.execute(
        "SELECT sv.strategy_id, sv.context_hash, sv.validity_alpha, sv.validity_beta "
        "FROM strategy_validity sv "
        "ORDER BY sv.last_checked_at ASC NULLS FIRST "
        "LIMIT ?",
        (batch_size,),
    ).fetchall()

    checked = 0
    invalidated = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        sid = row["strategy_id"]
        old_hash = row["context_hash"]
        alpha = row["validity_alpha"]
        beta = row["validity_beta"]

        if old_hash != current_hash:
            # Context has changed — this strategy MAY be stale
            beta += 1.0
            invalidated += 1
        else:
            # Context unchanged — reinforce validity
            alpha += 0.5  # Smaller increment for "no change" confirmation

        validity = alpha / (alpha + beta)
        quarantined = 1 if validity < STALENESS_QUARANTINE_THRESHOLD else 0
        stale = 1 if (not quarantined and validity < STALENESS_SUSPECT_THRESHOLD) else 0

        self._conn.execute(
            "UPDATE strategy_validity SET "
            "validity_alpha=?, validity_beta=?, last_checked_at=?, "
            "stale_suspected=?, quarantined=? "
            "WHERE strategy_id=?",
            (alpha, beta, now, stale, quarantined, sid),
        )
        checked += 1

    self._conn.commit()
    return {"checked": checked, "invalidated": invalidated}
```

**Filter quarantined strategies from retrieval**:

```python
def retrieve(self, query_text, k=5, species=None, include_stale=False):
    # ... RRF search as above ...

    # After hydrating entries, filter quarantined unless explicitly requested
    if not include_stale:
        entries = [
            e for e in entries
            if not self._is_quarantined(e.id)
        ]
    return entries[:k]

def _is_quarantined(self, strategy_id: str) -> bool:
    row = self._conn.execute(
        "SELECT quarantined FROM strategy_validity WHERE strategy_id=?",
        (strategy_id,),
    ).fetchone()
    return bool(row and row["quarantined"])
```

### 2d. Design Choice: Why Bayesian Over Binary Invalidation

Token Savior's Bayesian approach (alpha/beta tracking) is superior to binary invalidation for AutoPilot because:

- A model registry change does NOT necessarily invalidate all strategies. Only strategies that referenced the changed model are affected. But we cannot always determine which strategies reference which models (the text is free-form insight language).
- Bayesian decay gives multiple "config changed but strategy was still confirmed useful" events time to rescue a falsely-invalidated strategy.
- The quarantine threshold (0.40) means a strategy needs ~4 consecutive "context changed" signals without any "still useful" confirmations before being excluded. This is the right ballpark for AutoPilot's trial cadence.

A strategy confirmed useful by a subsequent trial should have its alpha incremented, resurrecting it even if config changed. This hooks into the existing `pareto_status == "frontier"` code path in `autopilot.py` line 1269.

---

## 3. MDL Convention Promotion for AutoPilot

### 3a. What Token Savior Actually Does

Source: `src/token_savior/mdl_distiller.py` + `src/token_savior/memory/distillation.py`

Token Savior implements Rissanen's (1978) Minimum Description Length principle:

```
minimize: sum_j [ L(abstraction_j) + sum_{o in cluster_j} L(o | abstraction_j) ]
```

Pipeline:
1. **Group by type** — only cluster observations of the same type.
2. **Agglomerative clustering** — Jaccard similarity on tokenized `title + content[:100]`. Single-link with threshold 0.4.
3. **For each cluster >= min_size (3)**: compute shared tokens across members, propose an abstraction from the most representative sentence, delta-encode each member against the abstraction.
4. **MDL test**: if `(mdl_before - mdl_after) / mdl_before >= compression_required (0.2)`, the cluster is a distillation candidate.
5. **Apply**: create a new "convention" observation with the abstraction, tag original observations as "mdl-distilled", replace their content with the delta, and link via `observation_links.supersedes`.

The `description_length` approximation is `len(text) / 4.0` (chars to tokens).

Auto-promotion rules (from README): `note x5 accesses -> convention`, `warning x5 -> guardrail`. The ROI module (`memory/roi.py`) tracks `access_count * type_weight` to determine which observations are worth keeping.

### 3b. AutoPilot Strategy Conventions

AutoPilot already has a manual knowledge distillation step via `EvolutionManager` (Species 4), which runs every ~5 trials and produces 3-7 insights per invocation. Over 100+ trials, the strategy store accumulates many entries that repeat the same finding in different words:

- "HSD net-negative on Qwen3.5 hybrid; only viable for dense-only"
- "Self-speculation hurts on hybrid SSM-Dense architectures"
- "Disable speculative decoding for models with attention+SSM layers"

These three entries are semantically the same insight. MDL distillation would compress them into one convention with three delta-encoded specifics.

### 3c. Implementation: Convention Promotion for strategy_store.py

**New table for conventions**:

```python
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS strategy_conventions (
        id TEXT PRIMARY KEY,
        abstraction TEXT NOT NULL,
        dominant_species TEXT NOT NULL,
        member_count INTEGER NOT NULL,
        shared_tokens TEXT NOT NULL,  -- JSON list
        mdl_compression REAL NOT NULL,
        created_at TEXT NOT NULL,
        access_count INTEGER DEFAULT 0,
        decay_immune INTEGER DEFAULT 1
    )
""")
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS strategy_convention_members (
        convention_id TEXT REFERENCES strategy_conventions(id),
        strategy_id TEXT REFERENCES strategies(id),
        delta_text TEXT NOT NULL,
        PRIMARY KEY (convention_id, strategy_id)
    )
""")
```

**Distillation algorithm adapted for strategies**:

```python
import re
from collections import Counter

_WORD_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b")

def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]

def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)

def find_convention_candidates(
    self,
    min_cluster_size: int = 3,
    jaccard_threshold: float = 0.35,
    compression_required: float = 0.20,
) -> list[dict]:
    """Detect clusters of similar strategies eligible for convention promotion."""
    rows = self._conn.execute(
        "SELECT id, description, insight, species FROM strategies "
        "WHERE id NOT IN (SELECT strategy_id FROM strategy_convention_members)"
    ).fetchall()

    if len(rows) < min_cluster_size:
        return []

    # Group by species first (strategies within same species are more likely duplicates)
    by_species: dict[str, list] = {}
    for row in rows:
        by_species.setdefault(row["species"], []).append(dict(row))

    candidates = []
    for species, bucket in by_species.items():
        if len(bucket) < min_cluster_size:
            continue

        # Tokenize description + insight for Jaccard comparison
        sigs = [set(_tokenize(r["description"] + " " + r["insight"])) for r in bucket]

        # Single-link agglomerative clustering
        n = len(bucket)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for i in range(n):
            for j in range(i + 1, n):
                if _jaccard(sigs[i], sigs[j]) >= jaccard_threshold:
                    union(i, j)

        groups: dict[int, list[int]] = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(i)

        for indices in groups.values():
            if len(indices) < min_cluster_size:
                continue

            members = [bucket[i] for i in indices]
            texts = [m["description"] + " " + m["insight"] for m in members]

            # Compute shared tokens (present in >= 70% of members)
            threshold = max(1, int(0.7 * len(texts)))
            counter: Counter = Counter()
            for t in texts:
                counter.update(set(_tokenize(t)))
            shared = [tok for tok, cnt in counter.most_common(20)
                       if cnt >= threshold and len(tok) > 2]

            # Propose abstraction
            shared_set = set(shared)
            best_text = ""
            best_overlap = -1
            for text in texts:
                toks = set(_tokenize(text))
                overlap = len(toks & shared_set)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_text = text[:200]

            core = " + ".join(shared[:5]) if shared else "general"
            abstraction = f"[Convention:{species}] {core} -- {best_text}"

            # MDL test
            mdl_before = sum(len(t) / 4.0 for t in texts)
            abs_len = len(abstraction) / 4.0
            deltas = []
            for text in texts:
                abs_tokens = set(_tokenize(abstraction))
                novel = [w for w in _tokenize(text) if w not in abs_tokens]
                delta = " ".join(novel[:30]) if novel else ""
                deltas.append(delta)
            mdl_after = abs_len + sum(len(d) / 4.0 for d in deltas)
            compression = (mdl_before - mdl_after) / mdl_before if mdl_before > 0 else 0

            if compression >= compression_required:
                candidates.append({
                    "member_ids": [m["id"] for m in members],
                    "species": species,
                    "abstraction": abstraction,
                    "shared_tokens": shared,
                    "mdl_before": mdl_before,
                    "mdl_after": mdl_after,
                    "compression": compression,
                    "deltas": deltas,
                })

    return candidates

def promote_conventions(self, dry_run: bool = True) -> dict:
    """Find and optionally apply convention promotions."""
    candidates = self.find_convention_candidates()

    if dry_run or not candidates:
        return {
            "candidates": len(candidates),
            "applied": 0,
            "dry_run": dry_run,
            "preview": [
                {"members": c["member_ids"], "species": c["species"],
                 "compression": f"{c['compression']:.0%}",
                 "abstraction": c["abstraction"][:120]}
                for c in candidates[:5]
            ],
        }

    applied = 0
    now = datetime.now(timezone.utc).isoformat()
    for c in candidates:
        conv_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO strategy_conventions VALUES (?,?,?,?,?,?,?,?,?)",
            (conv_id, c["abstraction"], c["species"], len(c["member_ids"]),
             json.dumps(c["shared_tokens"]), c["compression"], now, 0, 1),
        )
        for mid, delta in zip(c["member_ids"], c["deltas"]):
            self._conn.execute(
                "INSERT INTO strategy_convention_members VALUES (?,?,?)",
                (conv_id, mid, delta),
            )
        applied += 1

        # Embed convention for retrieval
        embedding = self._embed(c["abstraction"])
        self._faiss.add(conv_id, embedding)

    self._faiss.save()
    self._conn.commit()
    return {"candidates": len(candidates), "applied": applied, "dry_run": False}
```

**Convention-aware retrieval** — conventions should rank higher than individual strategies:

```python
def retrieve(self, query_text, k=5, species=None, include_stale=False):
    # ... existing RRF search ...

    # Also search conventions
    conv_entries = self._retrieve_conventions(query_text, k=k, species=species)

    # Conventions get a 1.5x score boost (consolidated knowledge is more reliable)
    for ce in conv_entries:
        ce.similarity_score *= 1.5

    # Merge and sort
    all_entries = entries + conv_entries
    all_entries.sort(key=lambda e: e.similarity_score, reverse=True)
    return all_entries[:k]
```

### 3d. When to Run Distillation

Token Savior runs MDL distillation on-demand (user calls `memory_distill` MCP tool). For AutoPilot, hook it into the `EvolutionManager` cadence:

- Run `promote_conventions(dry_run=True)` every 10 trials (after EvolutionManager distillation).
- If candidates are found with compression > 0.30, auto-apply.
- Log to `agent_audit.log`: "MDL promotion: N strategies -> M conventions, compression X%".

---

## 4. Progressive Disclosure for Controller Prompt Injection

### 4a. What Token Savior Actually Does

Token Savior's three-layer contract:

| Layer | Tool | Tokens/result | Content |
|-------|------|---------------|---------|
| 1 | `memory_index` | ~15 | Type + title + citation URI |
| 2 | `memory_search` | ~60 | + excerpt (160 chars) + validity badge |
| 3 | `memory_get` | ~200 | Full narrative + facts + metadata |

The client always starts at Layer 1 and escalates only if the previous layer matched. Each layer returns `ts://obs/{id}` URIs that the next layer can resolve.

### 4b. Applying to AutoPilot Strategy Injection

Currently, `autopilot.py` (lines 546-557) injects ALL retrieved strategies as full text:

```python
strategies = strategy_store.retrieve(query, k=3)
if strategies:
    strategy_lines = "\n".join(
        f"- Trial #{s.source_trial_id} ({s.species}): {s.description} -> {s.insight}"
        for s in strategies
    )
    failure_context = f"## Past Strategy Insights\n{strategy_lines}\n\n" + failure_context
```

Each strategy line is ~50-80 tokens. With k=3, that is ~150-240 tokens of strategy context. This is small today, but will grow as the strategy store scales past hundreds of entries and conventions are added.

**Three-tier progressive disclosure for strategy injection**:

```python
def format_strategy_injection(
    strategies: list[StrategyEntry],
    max_tokens: int = 200,
    detail_threshold: float = 0.025,  # RRF score above which to show full detail
) -> str:
    """Format strategies with progressive detail based on relevance score.

    Tier 1 (all results): one-line summary (~15 tokens each)
    Tier 2 (score > threshold * 0.7): + insight text (~40 tokens each)
    Tier 3 (score > threshold): + metadata, trial context (~80 tokens each)
    """
    if not strategies:
        return ""

    lines = []
    token_budget = max_tokens
    tier2_threshold = detail_threshold * 0.7

    for s in strategies:
        if token_budget <= 0:
            break

        if s.similarity_score >= detail_threshold:
            # Tier 3: Full detail
            line = (
                f"- **[T#{s.source_trial_id}]** ({s.species}) "
                f"{s.description} -> {s.insight}"
            )
            if s.metadata.get("confidence"):
                line += f" [confidence: {s.metadata['confidence']}]"
            token_budget -= 80
        elif s.similarity_score >= tier2_threshold:
            # Tier 2: Description + insight, no metadata
            line = f"- ({s.species}) {s.description} -> {s.insight}"
            token_budget -= 40
        else:
            # Tier 1: One-line summary only
            line = f"- ({s.species}) {s.description[:60]}"
            token_budget -= 15

        lines.append(line)

    if not lines:
        return ""
    return "## Past Strategy Insights\n" + "\n".join(lines)
```

This replaces the flat formatting in `autopilot.py`. The token budget ensures strategy context never dominates the controller prompt, even as the store scales to hundreds of strategies.

**Convention entries get automatic Tier 2 minimum** — a convention represents distilled multi-trial knowledge and should never be shown as a Tier 1 one-liner:

```python
# In format_strategy_injection, for convention entries:
if hasattr(s, 'is_convention') and s.is_convention:
    # Conventions always get at least Tier 2
    line = f"- **[Convention]** ({s.species}) {s.description} -> {s.insight}"
    token_budget -= 50
```

---

## 5. Applicability Assessment

### Pattern A: RRF Hybrid Retrieval

| Dimension | Assessment |
|-----------|------------|
| **Implementation complexity** | **Low**. FTS5 is built into SQLite (already a dependency). RRF merge is ~20 lines. Schema migration is additive (virtual table + triggers). No new dependencies. |
| **Expected impact on AutoPilot improvement rate** | **Medium**. Today's pure-vector retrieval works well for semantically similar queries but misses exact-term matches. FTS5 will catch strategies containing specific model names, parameter names, or error messages that the embedding model might not map closely. Expect 10-20% improvement in strategy recall for technical queries. |
| **Dependencies** | None. SQLite FTS5 is available in Python's built-in `sqlite3` module. No new pip packages required. |
| **Risk** | Very low. Graceful degradation — if FTS5 fails, FAISS results are returned untouched (same as current behavior). |
| **Estimated effort** | 2-3 hours. Schema change + method additions + backfill script + tests. |

### Pattern B: Content-Hash Staleness Detection

| Dimension | Assessment |
|-----------|------------|
| **Implementation complexity** | **Medium**. Requires defining which files to hash (registry, config, prompts), adding the `strategy_validity` table, wiring staleness checks into the retrieval path, and deciding on appropriate Bayesian update rates. |
| **Expected impact on AutoPilot improvement rate** | **High**. This is the highest-value pattern. Currently, stale strategies (e.g., "use self-speculation on model X" when model X has been swapped out) actively degrade AutoPilot's decision quality. The system wastes trials re-discovering that old advice no longer applies. Staleness detection eliminates this failure mode. |
| **Dependencies** | Access to model registry file path (already defined in constants). The Bayesian update logic requires hooking into trial outcomes — strategies confirmed useful by frontier trials get alpha-bumped, strategies that led to failed trials get beta-bumped. This hooks into `autopilot.py` line 1269 (Pareto frontier) and the failure analysis path. |
| **Risk** | Medium. Over-aggressive invalidation could discard useful strategies whose relevance survives a config change. The Bayesian approach mitigates this, but the thresholds (0.40/0.60) need tuning. Start with `dry_run=True` logging for 50 trials before enabling quarantine. |
| **Estimated effort** | 4-6 hours. Schema + hash computation + staleness sweep + integration with trial outcomes + dry-run logging. |

### Pattern C: MDL Convention Promotion

| Dimension | Assessment |
|-----------|------------|
| **Implementation complexity** | **Medium-High**. The Jaccard clustering is straightforward but the abstraction quality depends on how well simple token overlap captures strategy semantics. Token Savior's MDL distiller uses LLM-free text operations (shared tokens + representative sentence). For AutoPilot strategies, which are LLM-generated and already concise, the compression ratio may be lower than for raw observations. |
| **Expected impact on AutoPilot improvement rate** | **Medium**. Benefit scales with strategy store size. At <50 entries, little value. At 200+ entries (which AutoPilot will reach after ~100 trials at 3-7 insights per EvolutionManager run), conventions will reduce retrieval noise and surface consolidated patterns. The convention boost in retrieval scoring is the real value — the LLM controller sees "this insight was confirmed across 5 trials" rather than 5 individual entries. |
| **Dependencies** | Requires Pattern A (FTS5) for conventions to be searchable by keyword. Depends on EvolutionManager cadence for triggering. |
| **Risk** | Low-medium. The `dry_run=True` default means conventions can be previewed before committing. Bad abstractions waste storage but do not corrupt the store (original strategies are preserved via delta encoding, not deleted). |
| **Estimated effort** | 6-8 hours. Convention schema + clustering algorithm + MDL testing + convention-aware retrieval + EvolutionManager hook + tests. |

### Pattern D: Progressive Disclosure for Prompt Injection

| Dimension | Assessment |
|-----------|------------|
| **Implementation complexity** | **Low**. Pure formatting logic over existing data structures. No schema changes. |
| **Expected impact on AutoPilot improvement rate** | **Low-Medium**. With k=3 strategies, the token savings are minimal (~100 tokens saved). Impact grows when k is increased or conventions are added. The real value is future-proofing: prevents strategy context from growing unboundedly as the store scales. |
| **Dependencies** | None standalone. Benefits from Pattern C (conventions get automatic Tier 2 minimum). |
| **Risk** | Very low. Worst case: the controller LLM sees less detail for a low-scoring strategy it would have found useful. Mitigated by the tier thresholds being tunable. |
| **Estimated effort** | 1-2 hours. Replace formatting block in `autopilot.py` + test. |

### Implementation Priority Order

1. **Pattern B: Staleness Detection** — highest impact, addresses a known AutoPilot failure mode (stale strategies wasting trials). Ship first.
2. **Pattern A: RRF Hybrid Retrieval** — low effort, low risk, immediate retrieval improvement. Ship alongside or immediately after Pattern B.
3. **Pattern D: Progressive Disclosure** — trivial effort, future-proofs prompt injection. Ship with Pattern A.
4. **Pattern C: MDL Convention Promotion** — highest effort, benefits scale with store size. Ship after 100+ strategies accumulate (probably after ~30-50 more AutoPilot trials).

---

## 6. Intake Verdict Delta

### Pre-deep-dive intake (2026-04-20)
- novelty: medium
- relevance: medium
- credibility_score: 3
- verdict: worth_investigating

### Post-deep-dive proposed delta

| Dimension | Before | After | Reason |
|-----------|--------|-------|--------|
| novelty | medium | **medium** (unchanged) | Token Savior's individual techniques (RRF, FTS5, Bayesian validity, MDL) are well-established in IR literature. The novelty is in their composition into a coherent memory engine with graceful degradation at every layer. The `search.py` implementation is notably clean — 20-line RRF merge, graceful fallback when sqlite-vec is unavailable. |
| relevance | medium | **high** | Four specific patterns map directly to known gaps in `strategy_store.py`. Staleness detection (Pattern B) addresses a confirmed AutoPilot failure mode. RRF hybrid retrieval (Pattern A) plugs a known gap in pure-vector search. The claude-mem deep dive (intake-395) found no directly actionable patterns for strategy memory — Token Savior delivers four. |
| credibility_score | 3 | **4** | MIT license (no adoption barriers). Source code inspected — implementations are sound. tsbench is self-produced but methodology is documented with per-task breakdowns. The memory subsystem is well-tested (1318/1318 tests passing). No consistency bugs found in the memory engine code (unlike claude-mem's SQLite/Chroma desync issues). The Bayesian validity system and MDL distiller are genuine implementations, not marketing wrappers. |
| verdict | worth_investigating | **adopt_patterns** | Four concrete, implementable patterns with code sketches. No licensing barriers (MIT). Patterns B and A should ship within the next AutoPilot development cycle. |

### Key Insights Not in Original Intake

1. **Token Savior's RRF implementation is cleaner than claude-mem's retrieval**. Claude-mem (intake-395) uses a 2-path cascade (Chroma OR SQLite, never both). Token Savior fuses both lists with RRF. This is the architecturally correct approach for EPYC's strategy store where both keyword precision and semantic recall matter.

2. **The Bayesian validity system is a real implementation, not a stub**. Source inspection confirms alpha/beta tracking with configurable quarantine/stale thresholds, applied via consistency sweeps. This is materially different from claude-mem's "no decay, no recency weighting" (per the intake-395 deep dive section 5).

3. **MDL distillation uses Rissanen's principle faithfully** — description length approximation, Jaccard agglomerative clustering, delta encoding, compression ratio testing. The `find_distillation_candidates` function is a genuine MDL implementation, not a heuristic labeling exercise.

4. **Token Savior's ROI module provides the auto-promotion math** that should inform the convention promotion threshold: `ROI = tokens_saved_per_hit * P(hit) * horizon * type_multiplier - tokens_stored`, with `P(hit) = exp(-lambda * days_since_access) * (1 + 0.1 * access_count)`. This can be adapted directly for strategy entries.

5. **The graceful degradation pattern is exemplary and should be adopted structurally**. Every feature (vector search, FTS5, MDL, consistency checks) degrades to a functional fallback. EPYC's strategy store should mirror this — RRF degrades to FAISS-only, staleness degrades to "all valid", conventions degrade to flat strategies.

### Comparison to intake-395 (claude-mem)

Token Savior is a strict superset of claude-mem's memory capabilities (as its own README documents). For EPYC's strategy store specifically:

| Capability | claude-mem | Token Savior | EPYC strategy_store (current) |
|------------|-----------|-------------|-------------------------------|
| Vector search | Chroma (external) | FAISS or sqlite-vec | FAISS |
| Keyword search | FTS5 (no hybrid) | FTS5 + RRF hybrid | None |
| Staleness | None | Bayesian + content-hash | None |
| Convention promotion | None | MDL distillation | None (manual via EvolutionManager) |
| Progressive disclosure | 3-layer client convention | 3-layer with token budgets | Flat injection |
| Decay/eviction | None | LRU + ROI + TTL | None |
| License | AGPL-3.0 (blocking) | MIT (adoptable) | N/A |

The intake-395 deep dive correctly identified claude-mem's limitations. Token Savior addresses every one of them. The MIT license removes the adoption barrier that made claude-mem patterns require clean-room reimplementation.

### Proposed Handoff Updates

- **`context-folding-progressive.md`**: Add reference to Token Savior's progressive disclosure contract as validation of the tiered-injection approach. Note RRF as a retrieval option for the compacted knowledge base.
- **`tool-output-compression.md`**: No direct update — Token Savior's memory engine is orthogonal to tool output compression.
- **New work item for `strategy_store.py`**: Implement Patterns A, B, D in a single PR. Pattern C deferred until strategy count exceeds 100.

---

## 7. One-Line Summary

Token Savior's memory engine provides four concretely extractable patterns — RRF hybrid retrieval, Bayesian staleness detection, MDL convention promotion, and progressive disclosure — that directly address known gaps in AutoPilot's strategy store; all four are implementable in Python with no new dependencies, and MIT licensing removes adoption barriers that blocked claude-mem pattern reuse.
