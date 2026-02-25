# MemRL Fading Memory - Handoff Document

**Goal**: Add access timestamps and Q-value decay to MemRL episodic memory for fading/forgetting experiments.

**Status**: READY - Infrastructure exists, decay mechanism missing

**Priority**: MEDIUM - Enables memory management experiments

**Last Updated**: 2026-01-26

---

## Resume Command

```bash
# Check current MemRL schema
grep -A 20 "class MemoryEntry" /mnt/raid0/llm/claude/orchestration/repl_memory/episodic_store.py

# Check memory age distribution
python3 << 'EOF'
from orchestration.repl_memory import EpisodicStore
from datetime import datetime, timedelta

store = EpisodicStore()
stats = store.get_stats()
print(f"Total memories: {stats.get('total_memories', 0)}")

# Age distribution would go here once we have access to raw entries
EOF

# Read this handoff
cat /mnt/raid0/llm/claude/handoffs/active/memrl_fading_memory.md
```

---

## Why This Matters

### Problem: Infinite Memory Growth

MemRL episodic memory is **persistent** and grows forever:
- Every routing decision stored
- Every escalation pattern stored
- Every REPL exploration stored
- No forgetting mechanism

### Risks Without Decay

| Risk | Impact |
|------|--------|
| **Stale patterns** | Old routing decisions may no longer be optimal |
| **Concept drift** | Codebase/tasks evolve; old memories mislead |
| **Storage bloat** | Unbounded growth (see LEANN handoff) |
| **Retrieval noise** | Old, low-value memories compete with recent, high-value ones |

### Solution: Fading Memory

Decay Q-values over time so:
- Recent successes have high influence
- Old memories fade unless reinforced
- Retrieval naturally prefers recent + high-value
- Storage can be pruned (Q < threshold → delete)

---

## Current Schema

```python
@dataclass
class MemoryEntry:
    id: str
    embedding: np.ndarray          # 896-dim vector
    action: str                    # Routing decision / REPL code
    action_type: str               # "routing", "escalation", "exploration"
    context: dict                  # Original task context
    outcome: str                   # "success", "failure", None
    q_value: float                 # Learned utility (0-1)
    created_at: datetime           # ✅ EXISTS
    updated_at: datetime           # ✅ EXISTS (Q-value updates)
    update_count: int              # ✅ EXISTS
    # last_accessed_at: datetime   # ❌ MISSING - need to add
    # access_count: int            # ❌ MISSING - optional
```

---

## Phase 1: Add Access Tracking

### Schema Changes

```python
@dataclass
class MemoryEntry:
    # ... existing fields ...
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
```

### SQLite Migration

```sql
-- Add columns to existing table
ALTER TABLE memories ADD COLUMN last_accessed_at TEXT;
ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;

-- Backfill existing entries
UPDATE memories SET last_accessed_at = updated_at WHERE last_accessed_at IS NULL;
UPDATE memories SET access_count = update_count WHERE access_count = 0;
```

### Update on Retrieval

```python
# In retriever.py - TwoPhaseRetriever.retrieve_*()
def _update_access_time(self, memory_ids: List[str]):
    """Update last_accessed_at for retrieved memories."""
    now = datetime.utcnow().isoformat()
    self.store.conn.executemany(
        "UPDATE memories SET last_accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
        [(now, mid) for mid in memory_ids]
    )
    self.store.conn.commit()
```

---

## Phase 2: Q-Value Decay Strategies

### Strategy 1: Time-Based Exponential Decay

```python
def decay_by_time(q: float, days_since_access: float, half_life: float = 30.0) -> float:
    """Exponential decay with configurable half-life."""
    decay_factor = 0.5 ** (days_since_access / half_life)
    return q * decay_factor

# Example: Q=0.9, 30 days → 0.45, 60 days → 0.225
```

### Strategy 2: Access-Based Reinforcement

```python
def decay_with_reinforcement(q: float, days_since_access: float, access_count: int) -> float:
    """Decay slowed by frequent access (reinforcement)."""
    base_half_life = 30.0
    reinforced_half_life = base_half_life * (1 + 0.1 * access_count)  # More access = slower decay
    decay_factor = 0.5 ** (days_since_access / reinforced_half_life)
    return q * decay_factor
```

### Strategy 3: Soft Threshold Pruning

```python
def should_prune(memory: MemoryEntry, min_q: float = 0.1, max_age_days: float = 365) -> bool:
    """Mark for deletion if decayed Q below threshold AND old enough."""
    age_days = (datetime.utcnow() - memory.last_accessed_at).days
    decayed_q = decay_by_time(memory.q_value, age_days)
    return decayed_q < min_q and age_days > max_age_days
```

### Strategy 4: Adaptive Decay (Outcome-Dependent)

```python
def adaptive_decay(memory: MemoryEntry, days_since_access: float) -> float:
    """Failures decay faster than successes."""
    if memory.outcome == "failure":
        half_life = 15.0  # Forget failures faster
    elif memory.outcome == "success":
        half_life = 60.0  # Remember successes longer
    else:
        half_life = 30.0  # Unknown outcomes: neutral

    return memory.q_value * (0.5 ** (days_since_access / half_life))
```

---

## Phase 3: Decay Scheduler

### Background Decay Job

```python
class QDecayScheduler:
    """Periodically apply decay to all memories."""

    def __init__(self, store: EpisodicStore, strategy: str = "exponential"):
        self.store = store
        self.strategy = strategy
        self.decay_interval_hours = 24  # Run daily

    async def run_decay_pass(self):
        """Apply decay to all memories."""
        now = datetime.utcnow()
        updated = 0
        pruned = 0

        for memory in self.store.get_all_memories():
            days_since = (now - memory.last_accessed_at).total_seconds() / 86400

            if self.strategy == "exponential":
                new_q = decay_by_time(memory.q_value, days_since)
            elif self.strategy == "adaptive":
                new_q = adaptive_decay(memory, days_since)

            if should_prune(memory._replace(q_value=new_q)):
                self.store.delete_memory(memory.id)
                pruned += 1
            elif abs(new_q - memory.q_value) > 0.01:
                self.store.update_q_value(memory.id, new_q)
                updated += 1

        return {"updated": updated, "pruned": pruned}
```

### Integration with Orchestrator Stack

```python
# In orchestrator_stack.py
async def start_decay_scheduler():
    scheduler = QDecayScheduler(episodic_store, strategy="adaptive")
    while True:
        await asyncio.sleep(24 * 3600)  # Daily
        result = await scheduler.run_decay_pass()
        logger.info(f"Decay pass: {result}")
```

---

## Phase 4: Experimentation Framework

### Config for Decay Experiments

```yaml
# orchestration/model_registry.yaml
memrl:
  decay:
    enabled: false  # Start disabled, enable for experiments
    strategy: "exponential"  # exponential | adaptive | reinforcement
    half_life_days: 30
    min_q_threshold: 0.1
    prune_after_days: 365
    run_interval_hours: 24
```

### A/B Testing Decay Strategies

```python
def run_decay_experiment(strategies: List[str], eval_tasks: List[TaskIR]) -> dict:
    """Compare retrieval quality with different decay strategies."""
    results = {}

    for strategy in strategies:
        # Clone memory store
        test_store = clone_episodic_store(original_store)

        # Apply decay
        scheduler = QDecayScheduler(test_store, strategy=strategy)
        scheduler.run_decay_pass()

        # Evaluate retrieval quality
        retriever = TwoPhaseRetriever(test_store, embedder)
        scores = []
        for task in eval_tasks:
            memories = retriever.retrieve_for_routing(task)
            # Score based on actual task outcome
            scores.append(evaluate_retrieval_quality(memories, task))

        results[strategy] = {
            "mean_score": np.mean(scores),
            "memories_after_decay": test_store.count(),
        }

    return results
```

---

## Phase 5: Monitoring & Alerts

### Metrics to Track

| Metric | Purpose |
|--------|---------|
| `memrl_memory_count` | Total memories (should stabilize with decay) |
| `memrl_avg_q_value` | Average Q-value (expect gradual decline with decay) |
| `memrl_avg_age_days` | Average memory age (expect stabilization) |
| `memrl_prune_count` | Memories pruned per decay pass |
| `memrl_retrieval_avg_q` | Avg Q-value of retrieved memories (quality signal) |

### Grafana Dashboard (Conceptual)

```
┌─────────────────────────────────────────────────────────┐
│  MemRL Memory Health                                     │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ Memory Count    │  │ Avg Q-Value     │               │
│  │     52,341      │  │      0.67       │               │
│  │  ▁▂▃▄▅▅▅▅▅▅    │  │  ▇▆▅▄▄▄▄▄▄▄    │               │
│  └─────────────────┘  └─────────────────┘               │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ Pruned (24h)    │  │ Avg Age (days)  │               │
│  │       127       │  │       45        │               │
│  └─────────────────┘  └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## Exploration Checklist

- [ ] Add `last_accessed_at` and `access_count` to MemoryEntry
- [ ] Write SQLite migration script
- [ ] Update retriever to track access times
- [ ] Implement decay strategies (exponential, adaptive, reinforcement)
- [ ] Create QDecayScheduler class
- [ ] Add decay config to model_registry.yaml
- [ ] Integrate scheduler with orchestrator stack
- [ ] Create A/B testing framework for strategies
- [ ] Add monitoring metrics
- [ ] Run baseline (no decay) vs decay experiments
- [ ] Document optimal decay parameters

---

## Success Criteria

1. **Memory stabilization**: Count plateaus instead of growing linearly
2. **Retrieval quality**: Decayed memories don't hurt retrieval accuracy
3. **Storage efficiency**: Pruning keeps storage bounded
4. **No performance regression**: Decay overhead < 1% of total time

---

## Blockers

None - this is an enhancement to existing infrastructure.

**Dependency**: Should implement after LEANN evaluation (if LEANN adopted, decay reduces urgency of storage optimization).

---

## References

- MemRL Paper: arXiv:2601.03192 (Zhang et al. 2025)
- Existing schema: `orchestration/repl_memory/episodic_store.py`
- Q-scorer: `orchestration/repl_memory/q_scorer.py`
- Related: `handoffs/active/leann_vector_db.md` (storage scaling)
