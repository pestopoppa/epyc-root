# Decomposition-to-Batch Mapping — orchestrator decisions onto np/instance slots

**Status**: stub — operator hypothesis, no external source backing, no code landed.
**Created**: 2026-08-13 (via `/research-intake` Stage 3, operator-approved plan; source round intake-1105…intake-1127, PARL/Kimi-agent-swarm sweep)
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Categories**: hardware_optimization, agent_architecture, inference_serving

## Objective

Operator hypothesis, recorded verbatim during the intake round (steering-ledger seq 3–4, 2026-08-12):
PARL's frozen-subagent / trainable-orchestrator split has an EPYC-native analogue — the intelligent
model decides task decomposition, execution runs on `worker_general` (a fast, cheap executor chosen so
the actual fan-out threads aren't bound by the bandwidth-per-token cost of the intelligent model), and
the decomposition should be able to target **np batching × multi-instance activation across CPU and
GPU** rather than a single instance's batch slots.

**This stub is filed honestly as operator-originated.** No source in the sweep that produced it models
placement-aware decomposition — every parallel-tool-calling and multi-agent paper ingested treats
"width" as a count, never as a mapping onto heterogeneous hardware instances. The research value here is
in establishing whether the mapping is coherent at all, not in importing an external method.

## Context from the source round

- Hardware constraint as stated by the operator: fan-out width is currently `-np 2` on the full CPU
  instance, `-np 8` on the GPU `architect_general` role — both well below the doctrinal "3-5 subagents"
  and further below any of the swarm-scale figures in the ingested literature.
- `intake-1118` (arxiv:2510.05381, dive-verified) found most context-length degradation lands inside
  the first ~7K tokens, independent of retrieval quality — relevant because per-thread context budget
  and instance placement interact: a decomposition that is placement-aware may also need to be
  context-budget-aware per placed thread.
- `intake-1125` (arxiv:2602.07359, dive-verified) found optimal *tool-call* width falls as the step
  budget rises, and a descending schedule beat any constant width — a shape that may or may not transfer
  to instance-level placement; untested here.
- The REPL is the mechanism that currently keeps per-thread context down regardless of placement
  (operator, steering-ledger seq 5) — any decomposition-to-batch design must not assume it away.

## Tasks

- [ ] **DB-1 — Establish whether the mapping is coherent.** Before any implementation: can a task
  decomposition emitted by an orchestrating model be expressed as a set of np-batch slots distributed
  across CPU and GPU instances, given current placement constraints (`src/scheduling/placement.py`
  WP-2 topology-overlap veto, quarter-instance fleet sizing)? Name the representation a decomposition
  would need to emit (e.g. a DAG with a placement hint per node) and check it against what
  `src/runtime/concurrency.py` and the quarter-fleet scheduler can actually consume today. This is a
  feasibility question, not a build.
- [ ] **DB-2 — Scope the boundary with `fleet-fanout-measurement.md`.** RTG-49 measures agent-fleet
  fan-out (Claude Code / Codex mains and subagents); this stub is about serving-plane instance
  placement for the executor side. Confirm the two are actually disjoint and do not silently overlap
  (e.g. if `worker_general` execution is itself dispatched via the agent fleet rather than direct
  inference calls) before either stub grows further.

## Notes

No `Research Context` intake table is populated — deliberately, since no ingested source addresses this
question. If a future intake surfaces one, add it here rather than opening a new stub.
