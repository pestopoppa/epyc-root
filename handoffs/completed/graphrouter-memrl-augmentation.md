# GraphRouter MemRL Augmentation

**Created**: 2026-02-20
**Completed**: 2026-03-05
**Status**: COMPLETE

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
| H: GAT training | `graph_router_weights.npz` | DONE |
| I: Reset safety | `scripts/session/reset_episodic_memory.sh` | DONE |
| Tests | `tests/unit/test_{routing_graph,lightweight_gat,graph_router_*}.py` | 49 PASS |

## GAT Training Results (2026-03-05)

- **Episodic store**: 32,486 memories
- **Graph structure**: 17 task types, 17 clusters, 7 performance edges, 6 LLM roles
- **Training**: 20 epochs (early stopped, patience=20), 32.8s
- **Edge prediction accuracy**: 54.9% (above 50% random baseline)
- **Weights**: `orchestration/repl_memory/graph_router_weights.npz` (111K params)
- **Onboarding validated**: test_new_model integrated, routing predictions produced

### Fixes applied during training
- `_clear_graph()`: No longer deletes LLMRole nodes (populated externally)
- `_compute_performance_edges()`: Handles `escalate:X->Y` action format (extracts target role Y)
- `sync_from_episodic_store()`: Falls back to task_type-based clustering when per-memory embeddings unavailable

## Reset Safety

`reset_episodic_memory.sh` now deletes both classifier AND GAT weights on reset, and creates
a unified `retrain-routing-models.md` handoff covering retraining of both models.

## How to Enable

```bash
# 1. Train GAT weights (requires 500+ episodic memories)
python3 scripts/graph_router/train_graph_router.py --epochs 100

# 2. Enable feature flag
export ORCHESTRATOR_GRAPH_ROUTER=1

# 3. Start orchestrator
python3 scripts/server/orchestrator_stack.py start --dev
```

## Architecture

- Blend weight anneals 0.1->0.3 by episodic store size (500->2000 memories)
- Feature-gated: `graph_router` requires `specialist_routing` requires `memrl`
- Graceful degradation: empty graph / no weights / not ready -> silent skip
- TTL cache (60s) for sub-millisecond inference on warm cache

## Related: Routing Classifier Distillation (2026-03-05)

A complementary offline routing classifier was implemented in ColBERT-Zero Track 2. Unlike the GAT (which generalizes through graph structure for cold-start), the routing classifier distills episodic Q-values into a fast MLP for high-confidence routing decisions. Both integrate into `HybridRouter`:
- **GraphRouter**: Parallel signal blended at 10-30% weight, cold-start optimization
- **Routing Classifier**: Fast first-pass, skips retrieval entirely at ≥0.8 confidence

See `orchestration/repl_memory/routing_classifier.py` and `docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`.
