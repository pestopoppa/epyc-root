# GraphRouter MemRL Augmentation

**Created**: 2026-02-20
**Status**: READY — 1,640 episodic memories available, GAT training unblocked
**Priority**: MEDIUM (cold-start optimization)

## Summary

GNN-based parallel routing signal for MemRL HybridRouter. Solves cold-start problem
when new models join the fleet (hours -> minutes of onboarding).

Based on GraphRouter (ICLR 2025, arxiv 2410.03834).

## Implementation Status

| Phase | File | Status |
|-------|------|--------|
| A: BipartiteRoutingGraph | `orchestration/repl_memory/routing_graph.py` | DONE |
| B: LightweightGAT | `orchestration/repl_memory/lightweight_gat.py` | DONE |
| C: GraphRouterPredictor | `orchestration/repl_memory/graph_router_predictor.py` | DONE |
| D: HybridRouter integration | `orchestration/repl_memory/retriever.py` | DONE |
| E: Feature flag + init | `src/features.py`, `src/api/services/memrl.py` | DONE |
| F: Training pipeline | `scripts/graph_router/train_graph_router.py` | DONE |
| G: Onboarding script | `scripts/graph_router/onboard_model.py` | DONE |
| Tests | `tests/unit/test_{routing_graph,lightweight_gat,graph_router_*}.py` | 49 PASS |

## How to Enable

```bash
# 1. Train GAT weights (requires 500+ episodic memories)
python3 scripts/graph_router/train_graph_router.py --epochs 100

# 2. Enable feature flag
export ORCHESTRATOR_GRAPH_ROUTER=1

# 3. Start orchestrator
python3 scripts/server/orchestrator_stack.py start --dev
```

## Onboard New Model

```bash
python3 scripts/graph_router/onboard_model.py \
    --role new_coder \
    --description "Qwen4-Coder-32B, 55 t/s" \
    --port 8086 --tps 55.0 --memory-tier HOT --memory-gb 20
```

## Architecture

- Blend weight anneals 0.1->0.3 by episodic store size (500->2000 memories)
- Feature-gated: `graph_router` requires `specialist_routing` requires `memrl`
- Graceful degradation: empty graph / no weights / not ready -> silent skip
- TTL cache (60s) for sub-millisecond inference on warm cache

## Remaining Task: Train Graph Router

**DO NOT ARCHIVE** — This handoff stays active until GAT training is complete.

**Current state** (as of 2026-03-04):
- Memory threshold met: 1,640 episodic memories (500 required)
- All 49 unit tests passing
- No trained weights file exists yet (`graph_router_weights.npz`)
- `ORCHESTRATOR_GRAPH_ROUTER` not yet set in `orchestrator_stack.py`

**Next steps**:

```bash
# 1. Train GAT weights
python3 scripts/graph_router/train_graph_router.py --epochs 100

# 2. Validate
python3 scripts/benchmark/feature_validation.py --feature graph_router --tier 3

# 3. Test cold-start onboarding
python3 scripts/graph_router/onboard_model.py \
    --role test_new_model \
    --description "Fast code generation model, 60 t/s" \
    --port 9999 --tps 60.0 --memory-tier HOT --memory-gb 10

# 4. Enable in production
export ORCHESTRATOR_GRAPH_ROUTER=1
```

**After training passes**: Update status to COMPLETE, archive this handoff.

## Related: Routing Classifier Distillation (2026-03-05)

A complementary offline routing classifier was implemented in ColBERT-Zero Track 2. Unlike the GAT (which generalizes through graph structure for cold-start), the routing classifier distills episodic Q-values into a fast MLP for high-confidence routing decisions. Both integrate into `HybridRouter`:
- **GraphRouter**: Parallel signal blended at 10-30% weight, cold-start optimization
- **Routing Classifier**: Fast first-pass, skips retrieval entirely at ≥0.8 confidence

See `orchestration/repl_memory/routing_classifier.py` and `docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`.
