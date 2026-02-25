# MemRL Episodic Memory Implementation

**Created:** 2026-01-13
**Updated:** 2026-01-28
**Status:** PHASES 1-8 COMPLETE - Memory recovery + Graph seeding done
**Priority:** HIGH
**Blocking:** None
**Blocked By:** None

---

## Summary

Implemented MemRL-inspired episodic memory system for learned orchestration. The system enables runtime learning of task routing, escalation policies, and REPL exploration strategies without modifying model weights.

**Paper Reference:** arXiv:2601.03192 - "MemRL: Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory" (Zhang et al., 2025)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MEMRL IMPLEMENTATION                                  │
└──────────────────────────────────────────────────────────────────────────┘

INFERENCE PATH (synchronous, latency-critical):
  Query → TaskEmbedder → TwoPhaseRetriever → HybridRouter
                              ↓
                    EpisodicStore (pre-scored DB)
                              ↓
                    Routing decision + fallback to rules

LOGGING PATH (lightweight, real-time):
  All Tiers → ProgressLogger → JSONL files (lab book)

SCORING PATH (asynchronous, runs offline):
  ProgressReader → QScorer → EpisodicStore updates
                      ↓
              (Optional) ClaudeAsJudge for graded rewards
```

**Key insight:** Q-value computation is decoupled from the inference path. A dedicated "scorekeeper" agent monitors progress logs and updates Q-values asynchronously, eliminating latency concerns for interactive Tier-A routing.

---

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `orchestration/repl_memory/__init__.py` | Module exports | 30 |
| `orchestration/repl_memory/episodic_store.py` | SQLite + FAISS/numpy memory store | 450 |
| `orchestration/repl_memory/faiss_store.py` | FAISS embedding store + NumPy fallback | 340 |
| `orchestration/repl_memory/embedder.py` | Task embedding via 0.5B model | 240 |
| `orchestration/repl_memory/retriever.py` | Two-phase retrieval + hybrid router | 275 |
| `orchestration/repl_memory/progress_logger.py` | Structured JSONL logging | 310 |
| `orchestration/repl_memory/q_scorer.py` | Async Q-value update agent | 400 |
| `orchestration/repl_memory/failure_graph.py` | Kuzu failure pattern tracking | 420 |
| `orchestration/repl_memory/hypothesis_graph.py` | Kuzu hypothesis confidence tracking | 500 |
| `orchestration/repl_memory/graph_seeds.yaml` | Failure modes + hypotheses from QUIRKS.md | 250 |
| `benchmarks/prompts/v1/orchestrator_planning.yaml` | Claude-as-Judge benchmark | 350 |
| `src/repl_environment.py` | REPL with exploration logging (Phase 5) | ~1000 |
| `scripts/migrate_to_faiss.py` | NumPy → FAISS migration tool | 230 |
| `scripts/seed_success_patterns.py` | Parallel routing/tool pattern seeding | 350 |
| `scripts/backfill_faiss_embeddings.py` | SQLite→FAISS embedding sync | 150 |
| `scripts/seed_remaining_phase_b.py` | Parallel Phase B seeding wrapper | 200 |
| `tests/unit/test_faiss_store.py` | FAISS store unit tests (24 tests) | 350 |

**Configuration added to:** `orchestration/model_registry.yaml` (repl_memory section)

---

## Component Details

### 1. EpisodicStore (`episodic_store.py`)

SQLite-backed memory with numpy embeddings:

```python
from orchestration.repl_memory import EpisodicStore

store = EpisodicStore()

# Store memory
memory_id = store.store(
    embedding=task_embedding,
    action="coder_primary,worker_general",
    action_type="routing",
    context={"task_type": "code", "objective": "..."},
)

# Retrieve by similarity
candidates = store.retrieve_by_similarity(query_embedding, k=20)

# Update Q-value
new_q = store.update_q_value(memory_id, reward=0.8, learning_rate=0.1)
```

**Storage layout (FAISS backend - default):**
- `episodic.db`: SQLite metadata (action, context, q_value, timestamps)
- `embeddings.faiss`: FAISS IndexFlatIP index for O(log n) search
- `id_map.npy`: memory_id → FAISS index mapping

**Storage layout (NumPy backend - legacy/fallback):**
- `episodic.db`: SQLite metadata
- `embeddings.npy`: Memory-mapped numpy array (O(n) search)

### 2. TaskEmbedder (`embedder.py`)

Generates embeddings via Qwen2.5-Coder-0.5B:

```python
from orchestration.repl_memory import TaskEmbedder

embedder = TaskEmbedder()

# Embed TaskIR for routing
embedding = embedder.embed_task_ir({
    "task_type": "code",
    "objective": "Fix the login bug",
    "priority": "interactive"
})

# Embed failure context for escalation
embedding = embedder.embed_failure_context({
    "error_type": "lint_error",
    "gate_name": "lint",
    "failure_message": "..."
})
```

**Fallback:** Hash-based pseudo-embeddings if model unavailable (preserves identity, loses similarity).

### 3. TwoPhaseRetriever (`retriever.py`)

MemRL-style two-phase retrieval:

```python
from orchestration.repl_memory import TwoPhaseRetriever

retriever = TwoPhaseRetriever(store, embedder)

# Phase 1: Semantic filtering (top-k by cosine similarity)
# Phase 2: Q-value ranking (sort by learned utility)
results = retriever.retrieve_for_routing(task_ir)

# Check if learned routing should be used
if retriever.should_use_learned(results, min_samples=3):
    action, confidence = retriever.get_best_action(results)
else:
    # Fall back to rules
    ...
```

### 4. HybridRouter (`retriever.py`)

Combines learned and rule-based routing:

```python
from orchestration.repl_memory.retriever import HybridRouter, RuleBasedRouter

rule_router = RuleBasedRouter(routing_hints)
hybrid = HybridRouter(retriever, rule_router)

routing, strategy = hybrid.route(task_ir)
# strategy is "learned" or "rules"
```

### 5. ProgressLogger (`progress_logger.py`)

Lightweight structured logging:

```python
from orchestration.repl_memory import ProgressLogger

logger = ProgressLogger()

# Log task start with routing
logger.log_task_started(
    task_id="uuid",
    task_ir=task_ir,
    routing_decision=["coder_primary"],
    routing_strategy="learned"
)

# Log gate result
logger.log_gate_result(
    task_id="uuid",
    gate_name="lint",
    passed=False,
    agent_tier="B1",
    agent_role="coder",
    error_message="..."
)

# Log task completion
logger.log_task_completed(task_id="uuid", success=True)
```

**Log format:** JSONL files by date (`progress/2026-01-13.jsonl`)

### 6. QScorer (`q_scorer.py`)

Async Q-value update agent:

```python
from orchestration.repl_memory import QScorer, ProgressReader

reader = ProgressReader()
scorer = QScorer(store, embedder, logger, reader)

# Score all pending tasks (run periodically)
results = scorer.score_pending_tasks()
# {"tasks_processed": 5, "memories_updated": 3, "memories_created": 2}
```

**Reward formula:**
- Base: success=1.0, failure=-0.5
- Gate failure penalty: -0.1 per failure
- Escalation penalty: -0.15 per escalation

---

## Configuration Reference

Added to `model_registry.yaml`:

```yaml
repl_memory:
  enabled: true
  database:
    path: /mnt/raid0/llm/claude/orchestration/repl_memory/episodic.db
    embeddings_path: /mnt/raid0/llm/claude/orchestration/repl_memory/embeddings.npy
  embedding:
    model_path: /mnt/raid0/llm/models/Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf
    dim: 896
    threads: 8
    fallback_enabled: true
  retrieval:
    semantic_k: 20
    min_similarity: 0.3
    min_q_value: 0.3
    q_weight: 0.7
    top_n: 5
    confidence_threshold: 0.6
  scoring:
    learning_rate: 0.1
    success_reward: 1.0
    failure_reward: -0.5
    min_interval_seconds: 300
    batch_size: 50
  cold_start:
    min_samples: 3
    fallback_to_rules: true
    bootstrap_days: 30
```

---

## Cold Start Strategy

The system defaults to rule-based routing while the Q-database builds:

| Phase | Timeframe | Behavior |
|-------|-----------|----------|
| Bootstrap | Day 0-30 | System runs normally, Q-scorer observes |
| Hybrid | Day 30-90 | Learned suggestions supplement rules |
| Mature | Day 90+ | Learned routing dominates for common patterns |
| Always | - | Fall back to rules for novel/rare task types |

**Key principle:** No degradation during cold start. The system starts functional and improves over time.

---

## Integration Checklist

### Phase 1: Wire Up Logging (COMPLETE - 2026-01-13)

1. [x] Add `ProgressLogger` calls to dispatcher
2. [x] Log routing decisions in Front Door
3. [x] Log gate results in GateRunner
4. [x] Log escalations in FailureRouter

### Phase 2: Enable Hybrid Routing (COMPLETE - 2026-01-13)

1. [x] Replace hard-coded routing with `HybridRouter`
2. [x] Add confidence logging for monitoring
3. [x] Q-scorer integrated (real-time + idle cleanup in API)

### Lazy Loading (Added 2026-01-14)

MemRL components (TaskEmbedder, QScorer, HybridRouter) are now **lazy-loaded** to prevent memory exhaustion during testing:
- Only initialize on first `real_mode=True` request
- Mock mode tests never trigger model loading
- See `src/api.py:_ensure_memrl_initialized()`

### Phase 3: Add Escalation Learning (COMPLETE - 2026-01-14)

1. [x] Store failure contexts with escalation decisions
2. [x] Implement `LearnedEscalationPolicy` in `src/failure_router.py`
3. [x] Wire into FailureRouter with retriever and progress_logger

### Phase 4: Episodic Memory Seeding (COMPLETE - 2026-01-14)

Comprehensive seeding of ~5,000 memories for learned routing:

| Memory Type | Count | Script |
|-------------|-------|--------|
| Hierarchical decomposition | 70 | `seed_decomposition_memories.py` |
| Coding failures | 100 | `seed_failure_memories.py` |
| Diverse failures | 240 | `seed_diverse_failures.py` |
| Template failures | ~1,000 | Inline generation |
| Probabilistic strategies | ~450 | `seed_probabilistic_memories.py` |
| Success patterns | ~2,700 | Various scripts |

**Distribution:** 67% success / 33% failure (2:1 ratio)

**Q-Value Buckets:**
- Reliable (Q>0.9): 64%
- Often fails (Q 0.1-0.3): 27%
- Critical fail (Q<0.1): 4%
- Mixed/probabilistic: 5%

**Key Anti-Patterns Encoded:**
- Worker for architecture tasks (Q=0.10)
- Frontdoor for complex code (Q=0.05)
- No escalation after failures (Q=0.0)
- Unsafe code execution (Q=0.0)

### Phase 5: Add REPL Exploration Learning (COMPLETE - 2026-01-15)

1. [x] Log exploration strategies in REPLEnvironment
2. [x] Implement `EpisodicREPL.suggest_exploration()` with episodic memory queries
3. [x] Track token efficiency metrics

**Implementation details:**
- Added `progress_logger` and `task_id` parameters to REPLEnvironment
- Added `log_exploration_completed()` method - logs strategy and efficiency to ProgressLogger
- Enhanced `suggest_exploration()` to use `TwoPhaseRetriever.retrieve_for_exploration()`
- Added `ExplorationLog.get_token_efficiency()` for efficiency ratio calculation
- Token efficiency = result_tokens / exploration_tokens (higher is better)

### Phase 6: Enable Claude-as-Judge (Optional)

1. [ ] Run orchestrator_planning.yaml benchmark
2. [ ] Evaluate baseline scores
3. [ ] Enable graded rewards if beneficial

### Phase 7: FAISS Migration (COMPLETE - 2026-01-27)

Replaced NumPy mmap with FAISS for O(log n) embedding search:

### Phase 8: Memory Recovery + Graph Seeding (COMPLETE - 2026-01-28)

**Problem:** All ~5,000 memories from Phase 4 (Jan 14) were lost. Diagnostic showed only 48 exploration memories remained with 0 FAISS embeddings.

**Root causes:**
1. Path mismatch: DEFAULT_DB_PATH changed from parent dir to `sessions/` during refactor
2. FAISS embeddings not persisted: Old seeding scripts didn't call `store.flush()` or `_embedding_store.save()`
3. Graph path collision: Both FailureGraph and HypothesisGraph used same `kuzu_db/` path

**Fixes applied:**
1. Fixed `failure_graph.py:26` - changed DEFAULT_KUZU_PATH to `kuzu_db/failure_graph`
2. Fixed `hypothesis_graph.py:25` - changed DEFAULT_KUZU_PATH to `kuzu_db/hypothesis_graph`
3. Fixed `seed_loader.py` - proper FAISS backend handling + flush/save calls

**Recovery:**
- Started 8 parallel embedding servers (ports 8090-8097) for 8x faster seeding
- Created `scripts/backfill_faiss_embeddings.py` - syncs SQLite→FAISS
- Created `scripts/seed_success_patterns.py` - parallel routing/tool/escalation patterns
- Created `scripts/seed_remaining_phase_b.py` - parallel seeding wrapper

**Final state (verified 2026-01-28):**
| Component | Count | Status |
|-----------|-------|--------|
| SQLite memories | 2,714 | ✓ |
| FAISS embeddings | 2,714 | ✓ Synced |
| FailureGraph modes | 13 | ✓ From graph_seeds.yaml |
| FailureGraph symptoms | 45 | ✓ |
| FailureGraph mitigations | 16 | ✓ |
| HypothesisGraph hypotheses | 15 | ✓ From RESULTS.md |

**Memory distribution by action_type:**
| Type | Count | Avg Q |
|------|-------|-------|
| routing | 1,617 | 0.65 |
| decomposition | 510 | 0.96 |
| exploration | 305 | 0.88 |
| tool_use | 266 | 0.89 |
| escalation | 16 | 0.87 |


1. [x] Create `FAISSEmbeddingStore` class (`orchestration/repl_memory/faiss_store.py`)
2. [x] Add `use_faiss` flag to `EpisodicStore` (default: True)
3. [x] Create `NumpyEmbeddingStore` for migration/fallback
4. [x] Add migration script (`scripts/migrate_to_faiss.py`)
5. [x] Add `faiss-cpu>=1.7.4` to `pyproject.toml`
6. [x] Create unit tests (24 tests passing)

**Performance expectations:**
| Entries | NumPy (old) | FAISS (new) |
|---------|-------------|-------------|
| 5K | ~1ms | ~0.5ms |
| 50K | ~10ms | ~1ms |
| 500K | ~70ms | ~2ms |
| 1M | ~150ms | ~3ms |

**Backend selection:**
```python
# FAISS (default)
store = EpisodicStore(db_path="/path/to/data", use_faiss=True)

# NumPy (fallback)
store = EpisodicStore(db_path="/path/to/data", use_faiss=False)
```

**Migration:**
```bash
python scripts/migrate_to_faiss.py --db-path /path/to/data --compare
```

---

## Benchmark Suite

Created `benchmarks/prompts/v1/orchestrator_planning.yaml` with:

| Category | Questions | Purpose |
|----------|-----------|---------|
| Routing T1 | 5 | Basic routing decisions |
| Routing T2 | 3 | Nuanced multi-specialist routing |
| Routing T3 | 3 | Complex/ambiguous routing |
| Planning T1 | 2 | Basic feature/bugfix plans |
| Planning T2 | 2 | Moderate refactoring plans |
| Planning T3 | 2 | Complex migration/architecture plans |
| Escalation T1 | 2 | Should-escalate scenarios |
| Escalation T2 | 2 | Should-NOT-escalate scenarios |

**Claude-as-Judge scoring rubric (0-3):**
- 3 = Perfect routing/plan
- 2 = Acceptable, could be optimized
- 1 = Suboptimal, likely hurt performance
- 0 = Completely wrong

---

## Success Metrics

| Integration Point | Metric | Target |
|-------------------|--------|--------|
| Task Routing | % tasks completing without manual intervention | >95% |
| Escalation Policy | % escalations that resolve on first try | >80% |
| REPL Exploration | Avg tokens spent on exploration per task | -30% from baseline |
| Claude-as-Judge | Orchestrator planning score | >2.5/3.0 avg |

---

## Resume Commands

```bash
# Verify complete system
source .venv/bin/activate && python3 -c "
from orchestration.repl_memory import EpisodicStore
from orchestration.repl_memory.failure_graph import FailureGraph
from orchestration.repl_memory.hypothesis_graph import HypothesisGraph
store = EpisodicStore()
fg = FailureGraph()
hg = HypothesisGraph()
stats = store.get_stats()
print(f'SQLite: {stats[\"total_memories\"]} | FAISS: {store._embedding_store.count}')
print(f'FailureGraph: {fg.get_stats()}')
print(f'HypothesisGraph: {hg.get_stats()}')
"

# Start parallel embedding servers (for fast seeding)
for port in 8090 8091 8092 8093; do
  numactl --interleave=all /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-0.5B-GGUF/Qwen2.5-Coder-0.5B-Q8_0.gguf \
    --host 0.0.0.0 --port $port -c 2048 -t 8 -np 4 --embedding > /tmp/embed_$port.log 2>&1 &
done

# Backfill FAISS if SQLite/FAISS mismatch
python3 scripts/backfill_faiss_embeddings.py --servers http://127.0.0.1:8090,http://127.0.0.1:8091,http://127.0.0.1:8092,http://127.0.0.1:8093

# Seed success patterns (parallel)
python3 scripts/seed_success_patterns.py --servers http://127.0.0.1:8090,http://127.0.0.1:8091,http://127.0.0.1:8092,http://127.0.0.1:8093

# Seed more memories (legacy scripts - use parallel versions above)
python3 scripts/seed_decomposition_memories.py 20     # Hierarchical task patterns
python3 scripts/seed_failure_memories.py 10           # Coding anti-patterns

# Run Q-scorer manually
python3 -c "
from orchestration.repl_memory import EpisodicStore, TaskEmbedder, ProgressLogger, ProgressReader, QScorer
store = EpisodicStore()
embedder = TaskEmbedder()
logger = ProgressLogger()
reader = ProgressReader()
scorer = QScorer(store, embedder, logger, reader)
print(scorer.score_pending_tasks())
"
```

---

## Related Documents

| Document | Relationship |
|----------|--------------|
| `research/rlm_analysis.md` | RLM paper analysis (predecessor research) |
| `handoffs/active/rlm-orchestrator-roadmap.md` | 8-phase orchestrator roadmap |
| `orchestration/model_registry.yaml` | Configuration (repl_memory section) |
| `benchmarks/prompts/v1/orchestrator_planning.yaml` | Claude-as-Judge benchmark |

---

## Notes

- All paths on `/mnt/raid0/` per CLAUDE.md requirements
- Memory-mapped embeddings for efficient similarity search
- Hash-based fallback ensures system works without embedding model
- JSONL format enables streaming reads for large log files
- Q-scorer respects minimum interval to prevent thrashing
