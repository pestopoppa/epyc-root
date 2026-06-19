# X-MAS Heterogeneous Text-MAS Routing Spike

**Status**: classifier/table scaffold, guarded default-off enforce path, true function-axis 5x5 sweep, enforce-eligible `orchestration/xmas_winner_table.yaml`, live A/B harness, and machine-readable held-out verdict reporting are all landed. The 2026-06-18 held-out A/B returned `decision: hold`; enforce remains OFF. Next work is diagnosing over-routing/regressions before any new flip attempt.
**Created**: 2026-05-19 (post-latent-MAS-cluster deep-dive)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology, routing_intelligence
**Priority**: HIGH (empirical heterogeneous-routing artifact exists, but promotion is currently blocked by held-out regression evidence)
**Depends on**: `routing-intelligence.md`, `routing-and-optimization-index.md`, `meta-harness-optimization.md`, `hermes-outer-shell.md`
**History**: [x-mas-text-routing-history-through-2026-06-19.md](../archived/x-mas-text-routing-history-through-2026-06-19.md) preserves the completed scaffold/sweep/A-B chronology compacted out of this active handoff.
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`](../../research/deep-dives/2026-05-19-latent-mas-cluster.md)

## Objective

Replicate the X-MAS (intake-557, arxiv:2505.16997, `github.com/MASWorks/X-MAS`) domain x function optimal-model methodology on the EPYC production stack, build a domain/function winner table, and only route live traffic through it if held-out production evidence beats current routing without unacceptable latency or domain regressions.

## Current Evidence

- The deterministic 5-domain x 5-function classifier and winner-table loader are implemented in `epyc-orchestrator/src/classifiers/xmas_routing.py`.
- The production hook is default-off and guarded: enforce requires a complete evidence-backed table, confident classification, no forced role, and downstream guard pass/fail semantics still get final say.
- The true function-axis sweep completed in `epyc-inference-research` from 500 rows and produced the enforce-eligible `epyc-orchestrator/orchestration/xmas_winner_table.yaml`.
- The live A/B harness exists at `epyc-orchestrator/scripts/benchmark/xmas_live_ab.py` and now emits machine-readable `decision` summaries without rerunning inference.
- The 25-prompt held-out rerun (`benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun`) returned `decision: hold`: overall score delta `-0.35`, latency ratio `16.18x`, no lift domain, and regressions in `code`, `math`, and `reasoning`.

## Current Gate

- [ ] Keep `ORCHESTRATOR_XMAS_ROUTING_MODE=off` and `ORCHESTRATOR_XMAS_WINNER_TABLE_PATH` empty in production until a future held-out run passes the verdict gates.
- [ ] Diagnose why the function-axis table over-routes held-out solve/refine/extract traffic to `worker_general` and why X-MAS enforce regressed score/latency against baseline.
- [ ] If diagnostics produce a revised table, classifier threshold, or policy, rerun the held-out A/B with `--host-quiet-confirmed` and preserve baseline restore checks.
- [ ] Do not spend effort on RMAS/LatentMAS/Dead Weights hidden-state paths until this text-mediated route has either a passing decision or a documented kill.

## Validation Commands

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run pytest -q tests/unit/test_xmas_live_ab.py tests/unit/test_validate_xmas_winner_table.py tests/classifiers/test_xmas_routing.py
python scripts/validate/validate_xmas_winner_table.py --table orchestration/xmas_winner_table.yaml
python scripts/benchmark/xmas_live_ab.py --summarize-results benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun/results.jsonl
```

## Non-Goals

- Hidden-state or latent-agent handoff work.
- Cross-tokenizer projection or Dead Weights reproduction.
- Production enforce flips without a passing held-out decision.

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`
- X-MAS paper: `https://arxiv.org/abs/2505.16997`
- X-MAS repo: `https://github.com/MASWorks/X-MAS` (no license — methodology only)
- Related handoffs: `routing-intelligence.md`, `routing-and-optimization-index.md`, `learned-routing-controller.md`, `hermes-outer-shell.md`, `meta-harness-optimization.md`
