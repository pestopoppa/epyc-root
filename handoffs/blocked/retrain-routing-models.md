# Retrain Routing Models

**Status**: BLOCKED
**Blocked on**: Accumulate ~500+ routing memories via seeding
**Created**: 2026-04-01

## Context
Episodic memory was reset. The routing classifier weights, GraphRouter GAT
weights, and SkillBank skills were all invalidated. Normal FAISS retrieval
is active as fallback. Once enough new episodic memories are collected
(~500+ routing memories), retrain routing models and re-distill skills.

## Steps

### 1. Verify memory count
```bash
python3 -c "from orchestration.repl_memory.episodic_store import EpisodicStore; s = EpisodicStore(); print(s.count('routing'))"
```

### 2. Retrain routing classifier (MLP)
```bash
python3 scripts/graph_router/extract_training_data.py
python3 scripts/graph_router/train_routing_classifier.py
```

### 3. Retrain GraphRouter (GAT)
```bash
python3 scripts/graph_router/train_graph_router.py --epochs 100
python3 scripts/graph_router/onboard_model.py \
    --role test_new_model \
    --description "Validation model" \
    --port 9999 --tps 60.0 --memory-tier HOT --memory-gb 10
```

### 4. Re-distill SkillBank
```bash
# Dry-run to check trajectory volume
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher mock --dry-run

# Real distillation (needs ~500 trajectories)
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher claude

# Verify
sqlite3 /mnt/raid0/llm/tmp/skills.db "SELECT skill_type, COUNT(*) FROM skills GROUP BY skill_type;"
```

### 5. Enable features
Set in `orchestrator_stack.py` or environment:
```bash
export ORCHESTRATOR_ROUTING_CLASSIFIER=1
export ORCHESTRATOR_GRAPH_ROUTER=1
export ORCHESTRATOR_SKILLBANK=1
```

### 6. Delete this handoff
test
