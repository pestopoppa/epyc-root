# Graphiti MemRL Enhancement Research Track

**Created**: 2026-01-27
**Status**: Implementation Complete + Performance Optimized
**Priority**: Medium (valuable but not blocking)
**Effort**: 2-3 days (Option A: Kuzu graph layer only)
**Agent**: YOLO Agent eligible
**Tests**: 52 passing

---

## Summary

Enhance current MemRL episodic store with relationship graphs for:
1. **Failure Anti-Memory (A2)**: Track failure patterns, symptoms, mitigations
2. **Hypothetical Reasoning (A3)**: Track hypothesis confidence, accumulate evidence

**Source**: https://github.com/getzep/graphiti (inspiration, not direct use)

---

## Motivation: Why Failure Anti-Memory?

**Core insight**: Current Q-learning optimizes for repeating success. But in debugging/optimization work, avoiding known failure modes is often more valuable.

Current MemRL gap - flat memory can't answer:
- "What failures preceded this failure?" (causality chains)
- "Which mitigations have we tried for this pattern?" (failure graph)
- "What hypotheses should we test next?" (counterfactual reasoning)

**Example use case**: When a benchmark shows "0% acceptance rate", the failure graph should return "check BOS token mismatch" and "check SWA incompatibility" based on prior failures with those symptoms.

## Current Architecture

```
orchestration/repl_memory/
├── episodic_store.py   # SQLite + FAISS: (embedding, action, q_value)
├── faiss_store.py      # FAISS IndexFlatIP for O(log n) similarity search
├── q_scorer.py         # TD-learning: Q ← Q + α(reward - Q)
├── retriever.py        # Semantic retrieval: top-k by similarity × Q-value
└── embedder.py         # Qwen2.5-Coder-0.5B embeddings
```

**Gap**: Flat memory, no relationships. Can't answer:
- "What failures preceded this failure?"
- "Which mitigations worked for this pattern?"
- "What hypotheses should we test next?"

## Proposed Architecture

```
orchestration/repl_memory/
├── episodic_store.py   # UNCHANGED
├── faiss_store.py      # UNCHANGED
├── failure_graph.py    # NEW: Kuzu graph for failure patterns
├── hypothesis_graph.py # NEW: Kuzu graph for hypothesis tracking
├── retriever.py        # MODIFIED: query FAISS + Kuzu
└── kuzu_db/            # NEW: Graph storage directory
```

### Unified Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       Enhanced MemRL                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ EpisodicStore   │  │ FailureGraph    │  │ HypothesisGraph │  │
│  │ (SQLite+FAISS)  │  │ (Kuzu)          │  │ (Kuzu)          │  │
│  │                 │  │                 │  │                 │  │
│  │ - embeddings    │  │ - FailureModes  │  │ - Hypotheses    │  │
│  │ - actions       │  │ - Symptoms      │  │ - Evidence      │  │
│  │ - q_values      │  │ - Mitigations   │  │ - Predictions   │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └──────────┬─────────┴────────────────────┘           │
│                      │                                          │
│              ┌───────▼───────┐                                  │
│              │ UnifiedRetriever                                 │
│              │                                                  │
│              │ 1. FAISS similarity search                       │
│              │ 2. Failure graph check (penalize risky actions)  │
│              │ 3. Hypothesis check (warn on low confidence)     │
│              │ 4. Return ranked actions with explanations       │
│              └───────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Latency Budget

| Phase | Original | With Graphs | **Optimized (2026-01-27)** |
|-------|----------|-------------|----------------------------|
| Embedding | ~50ms | ~50ms | **~3ms** (HTTP server) |
| FAISS retrieval | ~5ms | ~5ms | ~5ms (unchanged) |
| Graph queries | - | ~10-20ms | **<1ms** (TTL cache) |
| Ranking | ~1ms | ~5ms | ~5ms (unchanged) |
| **Total retrieval** | ~56ms | ~80ms | **<15ms** |
| Graph updates (async) | - | ~50-100ms | ~50-100ms (async) |

Graph updates are async - they happen AFTER the response is returned.

**Performance optimizations applied:** Embedding server (HOT tier port 8090), write-behind FAISS, TTL caching for graph penalties.

## Implementation Phases

### Phase 1: Kuzu Setup (0.5 day)

```bash
pip install kuzu
```

Create `orchestration/repl_memory/kuzu_db/` directory for graph storage.

### Phase 2: Failure Graph (1 day)

**File**: `orchestration/repl_memory/failure_graph.py`

**Schema**:
```cypher
CREATE NODE TABLE FailureMode(id STRING, description STRING, severity INT, first_seen TIMESTAMP, last_seen TIMESTAMP, PRIMARY KEY(id))
CREATE NODE TABLE Symptom(id STRING, pattern STRING, detection_method STRING, PRIMARY KEY(id))
CREATE NODE TABLE Mitigation(id STRING, action STRING, success_rate FLOAT, PRIMARY KEY(id))
CREATE REL TABLE HAS_SYMPTOM(FROM FailureMode TO Symptom)
CREATE REL TABLE MITIGATED_BY(FROM FailureMode TO Mitigation)
CREATE REL TABLE TRIGGERED(FROM MemoryEntry TO FailureMode, memory_id STRING)
CREATE REL TABLE RECURRED_AFTER(FROM FailureMode TO Mitigation)
CREATE REL TABLE PRECEDED_BY(FROM FailureMode TO FailureMode)
```

**API**:
```python
class FailureGraph:
    def record_failure(self, memory_id: str, symptoms: List[str]) -> str
    def find_matching_failures(self, symptoms: List[str]) -> List[FailureMode]
    def record_mitigation(self, failure_id: str, action: str, worked: bool)
    def get_failure_chain(self, failure_id: str, depth: int = 5) -> List[FailureMode]
    def get_failure_risk(self, action: str) -> float  # 0.0-1.0 penalty
```

**Example Cypher Queries**:
```cypher
// What mitigations worked for "BOS token mismatch" failures?
MATCH (f:FailureMode)-[:HAS_SYMPTOM]->(s:Symptom {pattern: "BOS mismatch"})
MATCH (f)-[:MITIGATED_BY]->(m:Mitigation)
WHERE NOT EXISTS { MATCH (f)-[:RECURRED_AFTER]->(m) }
RETURN m.action, m.success_rate

// What failure chain led to this outcome?
MATCH path = (f1:FailureMode)-[:PRECEDED_BY*1..5]->(f2:FailureMode)
WHERE f1.id = $current_failure
RETURN path

// Get failure risk for an action (count unmitigated failures)
MATCH (m:MemoryEntry {action: $action})-[:TRIGGERED]->(f:FailureMode)
WHERE NOT EXISTS { MATCH (f)-[:MITIGATED_BY]->(:Mitigation) }
RETURN count(f) as unmitigated_failures
```

### Phase 3: Hypothesis Graph (1 day)

**File**: `orchestration/repl_memory/hypothesis_graph.py`

**Schema**:
```cypher
CREATE NODE TABLE Hypothesis(id STRING, claim STRING, confidence FLOAT, created_at TIMESTAMP, tested BOOL, PRIMARY KEY(id))
CREATE NODE TABLE Evidence(id STRING, type STRING, source STRING, timestamp TIMESTAMP, PRIMARY KEY(id))
CREATE REL TABLE SUPPORTS(FROM Evidence TO Hypothesis)
CREATE REL TABLE CONTRADICTS(FROM Evidence TO Hypothesis)
CREATE REL TABLE GENERATED_FROM(FROM Hypothesis TO MemoryEntry, memory_id STRING)
```

**API**:
```python
class HypothesisGraph:
    def create_hypothesis(self, claim: str, memory_id: str) -> str
    def add_evidence(self, hypothesis_id: str, outcome: str, source: str) -> float  # returns new confidence
    def get_confidence(self, action: str, task_type: str) -> float
    def get_untested_hypotheses(self, min_confidence: float = 0.7) -> List[Hypothesis]
    def get_low_confidence_warnings(self, action: str, task_type: str) -> List[str]
```

**Confidence Update Formula**:
```python
# On success: confidence increases (asymptotic toward 1.0)
new_confidence = old_confidence + 0.1 * (1 - old_confidence)

# On failure: confidence decreases (asymptotic toward 0.0)
new_confidence = old_confidence - 0.1 * old_confidence
```

**Example Cypher Queries**:
```cypher
// What untested hypotheses have low confidence due to accumulated evidence?
MATCH (h:Hypothesis)
WHERE h.tested = false AND h.confidence < 0.3
MATCH (e:Evidence)-[:CONTRADICTS]->(h)
RETURN h.claim, h.confidence, collect(e.source) as contradicting_evidence
ORDER BY h.confidence ASC

// Which hypotheses should we test next? (high confidence, untested)
MATCH (h:Hypothesis)
WHERE h.tested = false AND h.confidence > 0.7
RETURN h.claim, h.confidence
ORDER BY h.confidence DESC

// Get confidence for action+task_type combination
MATCH (h:Hypothesis)
WHERE h.claim CONTAINS $action AND h.claim CONTAINS $task_type
RETURN h.confidence
```

### Phase 4: Retriever Integration (0.5 day)

**Modify**: `orchestration/repl_memory/retriever.py`

```python
def retrieve(self, query_embedding, k=5):
    # 1. FAISS similarity search (existing)
    candidates = self.episodic_store.retrieve_by_similarity(query_embedding, k=20)

    # 2. Failure graph penalty (NEW)
    for c in candidates:
        failure_penalty = self.failure_graph.get_failure_risk(c.action)
        c.adjusted_score = c.similarity_score * c.q_value * (1 - failure_penalty)

    # 3. Hypothesis confidence check (NEW)
    for c in candidates:
        confidence = self.hypothesis_graph.get_confidence(c.action, task_type)
        if confidence < 0.2:
            c.warnings.append(f"Low confidence ({confidence:.2f}), contradicting evidence exists")
        c.adjusted_score *= confidence

    # 4. Return top-k with explanations
    return sorted(candidates, key=lambda x: x.adjusted_score, reverse=True)[:k]
```

### Phase 5: Async Updates (0.5 day)

**Modify**: `orchestration/repl_memory/episodic_store.py`

```python
def store_with_graphs(self, embedding, action, action_type, context, outcome):
    # Existing store
    memory_id = self.store(embedding, action, action_type, context, outcome)

    # Async graph updates (don't block response)
    asyncio.create_task(self._update_graphs(memory_id, action, action_type, outcome))
    return memory_id

async def _update_graphs(self, memory_id, action, action_type, outcome):
    if outcome == "failure":
        symptoms = await self._extract_symptoms(context, outcome)
        self.failure_graph.record_failure(memory_id, symptoms)

    # Update hypothesis regardless of outcome
    self.hypothesis_graph.add_evidence(
        action=action,
        task_type=action_type,
        outcome=outcome,
        source=memory_id
    )
```

**Symptom Extraction** (start simple, enhance later):
```python
async def _extract_symptoms(self, context: dict, outcome: str) -> List[str]:
    """Extract failure symptoms - start with regex, add LLM later."""
    symptoms = []
    error_text = str(context.get("error", "")) + str(outcome)

    # Regex patterns for common failures
    patterns = {
        "timeout": r"timeout|timed out|deadline exceeded",
        "0% acceptance": r"0%.*accept|acceptance.*0",
        "SIGSEGV": r"sigsegv|segmentation fault|signal 11",
        "OOM": r"out of memory|oom|memory exhausted",
        "BOS mismatch": r"bos.*mismatch|token.*mismatch",
        "SWA incompatibility": r"swa|sliding window",
    }

    for symptom, pattern in patterns.items():
        if re.search(pattern, error_text, re.IGNORECASE):
            symptoms.append(symptom)

    # TODO: Add LLM extraction for novel symptoms
    # symptoms.extend(await self._llm_extract_symptoms(error_text))

    return symptoms or ["unknown"]
```

---

## High-Level Flow: When Graphs Update

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TASK ARRIVES                                  │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 1. EMBED TASK (Qwen2.5-Coder-0.5B, ~50ms)                            │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. RETRIEVAL PHASE (parallel queries)                                │
│                                                                      │
│    ┌─────────────────────┐  ┌─────────────────────┐                  │
│    │ FAISS k-NN          │  │ Kuzu Graph Queries  │                  │
│    │ → top 20 memories   │  │ A. Failure risk     │                  │
│    └──────────┬──────────┘  │ B. Hypothesis conf  │                  │
│               │             └──────────┬──────────┘                  │
│               └────────────┬───────────┘                             │
│                            ▼                                         │
│    score = similarity × Q_value × (1 - failure_penalty)              │
│            × hypothesis_confidence                                   │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. SELECT & EXECUTE ACTION                                           │
│    → Route to appropriate agent tier                                 │
│    → Observe outcome: success / failure / partial                    │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4. ASYNC UPDATE PHASE (after response returned)                      │
│                                                                      │
│    A. EpisodicStore: store memory, TD-update Q-value                 │
│                                                                      │
│    B. FailureGraph (if outcome == "failure"):                        │
│       - Extract symptoms via regex/LLM                               │
│       - Query: "Have we seen these symptoms before?"                 │
│       - Create/link FailureMode + Symptom nodes                      │
│                                                                      │
│    C. HypothesisGraph (always):                                      │
│       - Find/create hypothesis for action+task_type                  │
│       - Create Evidence node, link SUPPORTS or CONTRADICTS           │
│       - Update confidence with formula                               │
└──────────────────────────────────────────────────────────────────────┘
```

### Graph Update Triggers

| Event | Failure Graph | Hypothesis Graph |
|-------|---------------|------------------|
| Task fails | Create/update FailureMode + Symptoms | Evidence CONTRADICTS hypothesis |
| Task succeeds | Create Mitigation if resolves prior failure | Evidence SUPPORTS hypothesis |
| New action tried | — | Create hypothesis if none exists |
| Pattern detected | Link to prior failures (PRECEDED_BY) | — |

## Validation Gates

| Gate | Target | Measurement |
|------|--------|-------------|
| Failure detection accuracy | > 70% | Manual review of 50 failures |
| Hypothesis-outcome correlation | r > 0.5 | Compare confidence vs actual success |
| Retrieval latency | < 100ms | Benchmark on 1000 queries |
| Graph storage size | < 100MB | After 10K memories |

## Dependencies

```toml
# pyproject.toml additions
kuzu = "^0.8"  # Embedded graph DB
```

No cloud dependencies. Local LLM (Qwen2.5-Coder-0.5B) for symptom extraction.

## Key Design Decisions

1. **Kuzu over Neo4j**: Embedded C++, no JVM, ~50MB memory
2. **Keep SQLite+FAISS**: Already fast, add graphs on top, don't replace
3. **Async updates**: Graph updates after response, no latency impact
4. **Link by ID**: Graph nodes link to episodic store IDs, no data duplication
5. **Local symptom extraction**: Use existing 0.5B model, not cloud API

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Kuzu query latency | Benchmark before integrating; fallback to SQLite relations |
| Symptom extraction quality | Start with regex patterns, add LLM later |
| Graph maintenance overhead | Prune old data; set TTL on Evidence nodes |
| Complexity creep | Phase 1 test: add failure graph only, measure value before hypothesis graph |

## Resume Commands

```bash
# 1. Install Kuzu
cd /mnt/raid0/llm/claude
pip install kuzu

# 2. Create graph directory
mkdir -p orchestration/repl_memory/kuzu_db

# 3. Verify Kuzu installation
python3 -c "import kuzu; print(f'Kuzu version: {kuzu.__version__}')"

# 4. Run tests after implementation
pytest tests/unit/test_failure_graph.py tests/unit/test_hypothesis_graph.py -v

# 5. Benchmark latency
python scripts/benchmark/bench_retriever.py --with-graphs

# 6. Run full test suite to ensure no regressions
cd /mnt/raid0/llm/claude && make test-all
```

## Test Specifications

### test_failure_graph.py

```python
def test_record_failure():
    """Recording a failure creates FailureMode + Symptom nodes."""

def test_find_matching_failures():
    """Given symptoms, find similar past failures."""

def test_record_mitigation():
    """Recording successful mitigation links to FailureMode."""

def test_failure_chain():
    """Get causal chain of failures via PRECEDED_BY edges."""

def test_failure_risk():
    """get_failure_risk returns 0.0-1.0 based on unmitigated failures."""
```

### test_hypothesis_graph.py

```python
def test_create_hypothesis():
    """Creating hypothesis stores claim with initial confidence 0.5."""

def test_add_supporting_evidence():
    """Supporting evidence increases confidence asymptotically."""

def test_add_contradicting_evidence():
    """Contradicting evidence decreases confidence asymptotically."""

def test_get_confidence():
    """Retrieve confidence for action+task_type combination."""

def test_low_confidence_warnings():
    """Low confidence (<0.2) returns warning with cited evidence."""
```

### test_retriever_integration.py

```python
def test_retrieval_with_failure_penalty():
    """Actions linked to failures are penalized in ranking."""

def test_retrieval_with_hypothesis_confidence():
    """Low-confidence actions include warnings."""

def test_combined_scoring():
    """score = similarity × Q_value × (1 - failure_penalty) × hypothesis_confidence."""

def test_latency_under_100ms():
    """Full retrieval completes in <100ms with both graph queries."""
```

## Related Documents

| Document | Path | Purpose |
|----------|------|---------|
| **Plan file** | `/home/daniele/.claude/plans/atomic-strolling-tower.md` | Full analysis with 9 alternative ideas |
| **Graphiti source** | https://github.com/getzep/graphiti | Inspiration (not direct use) |
| **Episodic store** | `/mnt/raid0/llm/claude/orchestration/repl_memory/episodic_store.py` | Current implementation to modify |
| **FAISS store** | `/mnt/raid0/llm/claude/orchestration/repl_memory/faiss_store.py` | Embedding index (unchanged) |
| **Retriever** | `/mnt/raid0/llm/claude/orchestration/repl_memory/retriever.py` | Modify for graph queries |
| **Q-scorer** | `/mnt/raid0/llm/claude/orchestration/repl_memory/q_scorer.py` | Reference for TD-learning pattern |
| **Model registry** | `/mnt/raid0/llm/claude/orchestration/model_registry.yaml` | repl_memory section config |
| **Kuzu docs** | https://docs.kuzudb.com/ | Graph DB API reference |

### Current EpisodicStore Interface (for reference)

Key methods to integrate with:
```python
# orchestration/repl_memory/episodic_store.py
class EpisodicStore:
    def store(embedding, action, action_type, context, outcome, initial_q) -> str
    def retrieve_by_similarity(query_embedding, k, action_type, min_q_value) -> List[MemoryEntry]
    def update_q_value(memory_id, reward, learning_rate) -> float
    def get_by_id(memory_id) -> MemoryEntry
    def count(action_type) -> int
    def get_stats() -> Dict
```

### Model Registry Config (repl_memory section)

```yaml
# orchestration/model_registry.yaml lines 62-99
repl_memory:
  enabled: true
  database:
    path: /mnt/raid0/llm/claude/orchestration/repl_memory/sessions
    use_faiss: true
  embedding:
    model_path: /mnt/raid0/llm/models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf
    dim: 896
  retrieval:
    semantic_k: 20
    min_similarity: 0.3
    min_q_value: 0.3
    q_weight: 0.7
  scoring:
    learning_rate: 0.1
    success_reward: 1.0
    failure_reward: -0.5
```

## Completion Checklist

- [x] Phase 1: Kuzu installed and configured (kuzu 0.11.3)
- [x] Phase 2: failure_graph.py with tests (17 tests)
- [x] Phase 3: hypothesis_graph.py with tests (18 tests)
- [x] Phase 4: retriever.py integration (GraphEnhancedRetriever)
- [x] Phase 5: Async update hooks (GraphEnhancedStore)
- [x] Validation: All 52 tests pass
- [x] **Performance Optimization (6 phases)** - See below
- [x] Documentation: Update model_registry.yaml with graph settings

---

## Performance Optimization (2026-01-27)

**Goal:** Reduce episodic memory latency from 61-255ms to <15ms

### Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Embedding | 50-200ms | 2-5ms | **40x faster** |
| Storage | 10-50ms | ~0ms (async) | **Async batch** |
| Retrieval | 9-50ms | <5ms | **10x faster** |

### Changes Implemented

| # | Change | File | Impact |
|---|--------|------|--------|
| 1 | Embedding server (HOT tier, port 8090) | `scripts/server/orchestrator_stack.py` | 50-200ms → 2-5ms |
| 2 | HTTP client for embeddings | `repl_memory/embedder.py` | HTTP > subprocess > hash fallback |
| 3 | Write-behind FAISS (10s flush) | `repl_memory/episodic_store.py` | Blocking → async |
| 4 | store_immediate() for ACID | `repl_memory/episodic_store.py` | Optional sync flush |
| 5 | O(1) id_to_idx dict | `repl_memory/faiss_store.py` | O(n) → O(1) lookup |
| 6 | SQLite compound indexes | `repl_memory/episodic_store.py` | Filtered queries ~1ms |
| 7 | TTLCache for graph penalties | `repl_memory/retriever.py` | 5-20ms → <1ms (80%+ cache hit) |

### Server Topology Update

| Port | Role | Model | Tier |
|------|------|-------|------|
| 8090 | embedder | Qwen2.5-Coder-0.5B-Q8_0 | **HOT** |

### Key Design Decisions

1. **Embedding server in HOT tier** - Same robustness as frontdoor/coder, always available
2. **10s write-behind interval** - Maximum throughput, SIGTERM handler ensures flush
3. **store_immediate()** - Available for ACID-critical memories when needed
4. **TTLCache (60s TTL, 500 max)** - Acceptable staleness for graph penalties

### Verification

```bash
# Benchmark latency (with embedding server running)
uv run python -c "
from orchestration.repl_memory import EpisodicStore, TaskEmbedder
import time

store = EpisodicStore(use_faiss=True)
embedder = TaskEmbedder()

# Storage latency
t0 = time.perf_counter()
emb = embedder.embed_text('test query')
t1 = time.perf_counter()
store.store(emb, 'test', 'test_type', {'test': True})
t2 = time.perf_counter()

print(f'Embedding: {(t1-t0)*1000:.1f}ms')
print(f'Storage: {(t2-t1)*1000:.1f}ms')
print(f'Total: {(t2-t0)*1000:.1f}ms')
"
# Expected: Embedding ~3ms, Storage ~5ms, Total <15ms
```
