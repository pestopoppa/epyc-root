# X-MAS Heterogeneous Text-MAS Routing Spike

**Status**: ready-to-claim (2-3 dev-days + 1 day compute)
**Created**: 2026-05-19 (post-latent-MAS-cluster deep-dive)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology, routing_intelligence
**Priority**: HIGH (zero-infra-change immediate win — replaces ad-hoc role mapping with empirical (domain × function) lookup)
**Depends on**: `routing-intelligence.md`, `routing-and-optimization-index.md`, `meta-harness-optimization.md`, `hermes-outer-shell.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`](../../research/deep-dives/2026-05-19-latent-mas-cluster.md)

## Objective

Replicate the X-MAS (intake-557, arxiv:2505.16997, `github.com/MASWorks/X-MAS`) (domain × function) optimal-model methodology on our 4-model production stack (qwen3.6 frontdoor, gemma4-26B-A4B worker_general, coder-30B, Qwen3-1.7B drafter), build a (domain × function) → winner lookup table, and use it to override the current ad-hoc `model_registry.yaml` role defaults.

This is the only entry in the May 2026 latent-MAS cluster that's deployable on the current orchestrator with **zero llama.cpp changes** — pure text-mediated MAS with no hidden-state surfacing, no projection layer, no fork patches.

## Research Context

| Intake ID | Title | Relevance | Notes |
|-----------|-------|-----------|-------|
| intake-557 | X-MAS (arxiv:2505.16997) — 1.7M-eval heterogeneous MAS sweep across 27 LLMs × 5 domains × 5 functions | high | text-MAS, no infra change |
| intake-544 | RMAS (arxiv:2604.25917) | medium | latent-MAS — requires llama.cpp fork |
| intake-555 | LatentMAS (arxiv:2511.20639, ICML 2026 Spotlight) | high | training-free latent — requires llama.cpp fork |
| intake-558 | Dead Weights (arxiv:2604.08335) | high | cross-architecture frozen composition — keystone for unlocking RMAS/LatentMAS but credibility-weakest (3-author preprint, no code) |

## Key Findings from Deep-Dive

- **X-MAS is the only deployable-today path** in the latent-MAS cluster. RMAS / LatentMAS / Dead Weights all require llama.cpp HTTP server fork to surface last-layer hidden states across server boundaries — 4-8 weeks of engineering + 2× rebase debt against ik_llama.cpp PR #1744 worker_pool branch.
- **Reported magnitudes**: MATH +8.4% with heterogeneous chatbot-only configuration, AIME +47% with mixed chatbot-reasoner setup. Even with 50% magnitude attenuation from their 27-model sweep down to our 4-model stack, this is meaningful.
- **LatentMAS heterogeneity claim is overstated**: paper Section C.3 admits "all agents share the same shape of transformer layers"; all experiments use only Qwen3 4B/8B/14B (same family, same tokenizer). X-MAS is the only cluster entry with genuine cross-family empirical evidence.
- **GitHub**: `MASWorks/X-MAS` exists (29 stars, **no license** — treat methodology as inspiration, do NOT vendor code).

## Spike Plan (single phase)

### X-MAS-style heterogeneous text-MAS routing (~2-3 dev-days + 1 nightshift)

**Goal**: build a 5×5 (domain × function) → winner-model lookup table for our specific stack, use it to route incoming orchestrator tasks.

**Steps**:
1. **Replicate X-MAS-Bench task layout**: pull the 5-domain × 5-function cell layout from `github.com/MASWorks/X-MAS` (treat as methodology, not code reuse — no license).
2. **Bench sweep on our 4 production models**:
   - 10-20 representative tasks per (domain × function) cell
   - 5 domains × 5 functions × 4 models × ~15 tasks = ~1500 evals
   - Use existing eval-tower harness in `epyc-inference-research/scripts/benchmark/`
3. **Build per-stack winner table**: 5×5 cells, each cell records the winning model. Compare to X-MAS-published winners as a shape sanity check.
4. **Orchestrator integration**: add a coarse (domain, function) classifier on the frontdoor; each incoming task is classified, then routed to the cell winner. Fall back to current ad-hoc routing for unclassified tasks.
5. **Hermes outer-shell agent uses the same routing for sub-task delegation** (`hermes-outer-shell.md`).

**Gate criteria**:
- The 5×5 table shows ≥2 distinct winners across the 25 cells (i.e., heterogeneity actually exists in our stack — if gemma4-26B-A4B wins everything per its `project_worker_general_swap_2026_05_08` dominance, the spike kills itself early).
- A/B test on a held-out 100-task suite shows ≥5pp accuracy improvement on at least one domain, no regression on others.
- Decode wall-time per task within ±10% of baseline (no latency cost from added classification step).

**Dev cost**: ~2-3 dev-days (1 day routing code + 1 day classifier + 1 day eval-harness reuse).
**Compute cost**: 1 nightshift (~12 hours) for the 1500-eval sweep at our standard 49-76 t/s rates. Requires `feedback_no_concurrent_inference` per-bench approval.

**Failure mode** (cheap kill): if the 5×5 table shows the same winner across most cells (likely gemma4-26B-A4B given tool_compliance dominance), X-MAS heterogeneity doesn't apply to our stack and we skip Spike 2/3 of the latent-MAS plan entirely.

## Why Not the Other Latent-MAS Entries

| Entry | Why deferred |
|-------|--------------|
| RMAS (intake-544) | Requires RecursiveLink fine-tuning + cross-tokenizer projection — no path on frozen GGUF stack without llama.cpp fork |
| LatentMAS (intake-555) | Training-free but requires hidden-state surfacing across server boundaries (4-8 weeks of llama.cpp fork work + 2× rebase debt against ik_llama PR #1744) |
| Thought Communication (intake-556) | Theoretical identifiability framework; no engineering hook |
| Dead Weights (intake-558) | The keystone if cross-tokenizer projection works — but 3-author preprint, no code, no independent reproduction. **GPU-rental Spike 2 (~$200-500) DEFERRED per user direction 2026-05-19.** |

## Non-Goals

- **Latent handoff**: this spike is explicitly text-mediated. Do not surface hidden states.
- **Cross-tokenizer projection**: Dead Weights territory — deferred.
- **New benchmark suite**: reuse existing eval-tower; do not build X-MAS-Bench from scratch.

## Open Questions for User

1. **Domain × function taxonomy**: X-MAS uses 5 domains (math / coding / science / commonsense / world-knowledge or similar) × 5 functions (planner / coder / verifier / executor / summarizer or similar). Map to our orchestrator's actual task taxonomy or keep X-MAS taxonomy verbatim for replication parity?
2. **Classifier choice**: coarse (domain, function) classification step on frontdoor — small MLP, embedding-based nearest-neighbor, or LLM-judge? Cheapest path: nearest-neighbor over (domain, function) prototype embeddings using existing TEI service from `internal-kb-rag.md`.
3. **Fallback policy**: when the classifier confidence is low, do we route via current ad-hoc heuristics (safest) or via the most-frequent X-MAS winner (simpler)?
4. **Composability with learned MLP router** (`learned-routing-controller.md` Phase 1 @ 92% val acc): does X-MAS routing replace the MLP, sit before it, or sit after it? My read: X-MAS provides the *prior* (domain × function → winner), MLP provides the *posterior* refinement on specific task features. They compose.

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`
- X-MAS paper: `https://arxiv.org/abs/2505.16997`
- X-MAS repo: `https://github.com/MASWorks/X-MAS` (no license — methodology only)
- Related handoffs: `routing-intelligence.md`, `routing-and-optimization-index.md`, `learned-routing-controller.md`, `hermes-outer-shell.md`, `meta-harness-optimization.md`
