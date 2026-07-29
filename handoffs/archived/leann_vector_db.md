# LEANN Vector Database - Handoff Document

**Goal**: Evaluate LEANN for MemRL episodic memory scaling (persistent, grows across all sessions).

**Status**: MEDIUM PRIORITY - MemRL is persistent and will grow significantly

**Priority**: MEDIUM - MemRL episodic memory is NOT per-session; it accumulates forever

**Last Updated**: 2026-01-26

**Source**: https://github.com/yichuan-w/LEANN

---

## Resume Command

```bash
# Check current REPL memory size
python3 -c "
from orchestration.repl_memory import EpisodicStore
store = EpisodicStore()
stats = store.get_stats()
print(f'Memory entries: {stats.get(\"total_memories\", 0)}')
print(f'Embedding file size: {stats.get(\"embedding_file_mb\", 0):.1f} MB')
"

# If >50K entries, consider exploring LEANN
# Read this handoff
cat /mnt/raid0/llm/claude/handoffs/active/leann_vector_db.md
```

---

## Why This Matters

### Two Memory Systems (Important Distinction)

| System | Scope | Growth | LEANN Relevance |
|--------|-------|--------|-----------------|
| **Per-session REPL** | Single task | Small (10s-100s) | Low - too small |
| **MemRL Episodic** | **Persistent forever** | **Unbounded** | **HIGH - this is the target** |

The MemRL episodic memory (`orchestration/repl_memory/episodic.db` + `embeddings.npy`) stores:
- Every routing decision across all sessions
- Every escalation pattern
- Every REPL exploration strategy
- Q-values learned from outcomes

This grows **indefinitely** as the orchestrator runs. After months/years of use, this WILL hit 100K+ entries.

### Current MemRL Memory Architecture

| Component | Implementation | Performance |
|-----------|----------------|-------------|
| Storage | SQLite + NumPy mmap | ~1ms linear scan |
| Embeddings | 896-dim float32 | ~3.5KB per entry |
| Retrieval | Two-phase (cosine + Q-value) | Fast at 1K-10K entries |
| Index | None (linear scan) | Scales O(n) |

### At Scale Problem

| Entries | Embedding Size | Scan Time (est.) |
|---------|----------------|------------------|
| 1,000 | 3.5 MB | ~1ms |
| 10,000 | 35 MB | ~10ms |
| 100,000 | 350 MB | ~100ms |
| 1,000,000 | 3.5 GB | ~1s |

**Trigger point**: When retrieval latency impacts UX (~50-100ms), optimize.

### LEANN Solution

- **97% storage reduction**: Graph-based selective recomputation
- **60M chunks in 6GB** (vs 201GB traditional)
- **On-demand embedding compute**: Store graph structure, not all vectors
- **Preserves search accuracy**: Claims no quality loss

---

## Current System Analysis

### REPL Memory Files

```
orchestration/repl_memory/
├── episodic.db           # SQLite (metadata)
├── embeddings.npy        # NumPy mmap (vectors)
├── embedder.py           # Qwen2.5-0.5B embeddings
├── retriever.py          # Two-phase retrieval
└── q_scorer.py           # Q-value updates
```

### Why Linear Scan Works Now

1. **Small scale**: ~5000 memories currently (seeded + organic)
2. **NumPy mmap**: Memory-mapped, no load time
3. **Vectorized cosine**: NumPy batch dot product is fast
4. **Two-phase**: Only top-20 candidates go to Q-ranking

### When to Act

MemRL is **persistent** — it will grow. Plan proactively:

| Entries | Timeline (est.) | Action |
|---------|-----------------|--------|
| ~5,000 | Now | Current state, works fine |
| ~20,000 | 3-6 months | Monitor latency |
| ~50,000 | 6-12 months | **Begin LEANN evaluation** |
| ~100,000+ | 12+ months | Migration required |

**Trigger conditions:**
- Memory count > 50,000
- Retrieval latency > 50ms (measurable impact)
- Embedding file > 500MB

---

## Phase 1: Benchmark Current System at Scale

Before adopting LEANN, verify scaling assumptions:

```bash
# Synthetic scale test
python3 << 'EOF'
import numpy as np
import time

# Simulate different scales
for n in [1000, 10000, 50000, 100000, 500000]:
    embeddings = np.random.randn(n, 896).astype(np.float32)
    query = np.random.randn(896).astype(np.float32)
    query = query / np.linalg.norm(query)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    start = time.perf_counter()
    for _ in range(100):
        scores = embeddings @ query
        top_k = np.argsort(scores)[-20:]
    elapsed = (time.perf_counter() - start) / 100 * 1000

    print(f"n={n:,}: {elapsed:.2f}ms per query")
EOF
```

Expected results (EPYC 9655):
- 1K: <1ms
- 10K: ~2ms
- 100K: ~15ms
- 500K: ~70ms

---

## Phase 2: LEANN Evaluation (When Triggered)

### Install LEANN

```bash
cd /mnt/raid0/llm
git clone https://github.com/yichuan-w/LEANN
cd LEANN

# Install
pip install -e .

# Verify
python -c "import leann; print('LEANN OK')"
```

### API Compatibility Test

```python
# Test if LEANN can replace NumPy embedding store
import leann
import numpy as np

# Create index
index = leann.Index(dim=896)

# Add embeddings (should support incremental add)
embeddings = np.random.randn(1000, 896).astype(np.float32)
for i, emb in enumerate(embeddings):
    index.add(emb, id=i)

# Search
query = np.random.randn(896).astype(np.float32)
results = index.search(query, k=20)
print(results)  # Should return (ids, scores)
```

### Migration Plan

If LEANN proves beneficial:

1. **Keep SQLite** for metadata (action, context, q_value, timestamps)
2. **Replace NumPy mmap** with LEANN index for embeddings
3. **Preserve two-phase retrieval** (LEANN for phase 1, Q-ranking for phase 2)
4. **Incremental migration**: Test on shadow index first

```python
# Modified EpisodicStore
class EpisodicStore:
    def __init__(self, use_leann: bool = False):
        if use_leann:
            self.embedding_store = LEANNEmbeddingStore(dim=896)
        else:
            self.embedding_store = NumpyEmbeddingStore(path="embeddings.npy")
```

---

## Phase 3: Benchmark Comparison

### Metrics

| Metric | NumPy (current) | LEANN (target) |
|--------|-----------------|----------------|
| Storage (1M entries) | ~3.5 GB | ~100 MB (97% less) |
| Query latency (1M) | ~1s | <50ms |
| Add latency | O(1) | O(log n) |
| Build time | None | Graph construction |
| Accuracy | 100% (exact) | ~99% (approx) |

### Quality Verification

```python
# Ensure LEANN doesn't degrade retrieval quality
def compare_retrieval(numpy_store, leann_store, queries, k=20):
    """Compare top-k results between stores."""
    matches = []
    for q in queries:
        numpy_ids = set(numpy_store.search(q, k))
        leann_ids = set(leann_store.search(q, k))
        overlap = len(numpy_ids & leann_ids) / k
        matches.append(overlap)
    return np.mean(matches)

# Should be >0.95 (95% overlap)
```

---

## Exploration Checklist

- [ ] Benchmark current system at 10K, 50K, 100K synthetic entries
- [ ] Identify latency threshold for optimization trigger
- [ ] Install LEANN and verify API
- [ ] Test API compatibility with episodic store interface
- [ ] Benchmark LEANN at same scales
- [ ] Verify retrieval quality preservation
- [ ] Design migration path (incremental, shadow index)
- [ ] Implement if/when triggered

---

## Success Criteria

1. **Latency**: <50ms retrieval at 500K entries
2. **Storage**: >90% reduction vs NumPy
3. **Quality**: >95% overlap with exact search
4. **Compatibility**: Drop-in replacement for embedding store

---

## Blockers

None - but this is **not optional long-term**. MemRL is persistent and WILL grow.

**Proactive timeline**: Begin evaluation at ~20K memories, implement by ~50K.

**Current state**: ~5K memories (seeded), system working well.

---

## References

- LEANN: https://github.com/yichuan-w/LEANN
- Technique: Graph-based selective recomputation with high-degree preserving pruning
- Claim: 60M chunks in 6GB (vs 201GB traditional)
- Platforms: Python 3.9-3.13, Ubuntu, Arch, WSL, macOS
