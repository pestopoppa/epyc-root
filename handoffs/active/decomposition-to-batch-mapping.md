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
- `intake-1125#02` (arxiv:2602.07359, dive-verified) found optimal *tool-call* width falls as the step
  budget rises, and a descending schedule beat any constant width — a shape that may or may not transfer
  to instance-level placement; untested here.
- The REPL is the mechanism that currently keeps per-thread context down regardless of placement
  (operator, steering-ledger seq 5) — any decomposition-to-batch design must not assume it away.

## Tasks

- [x] **DB-1 — Establish whether the mapping is coherent.** Before any implementation: can a task
  decomposition emitted by an orchestrating model be expressed as a set of np-batch slots distributed
  across CPU and GPU instances, given current placement constraints (`src/scheduling/placement.py`
  WP-2 topology-overlap veto, quarter-instance fleet sizing)? Name the representation a decomposition
  would need to emit (e.g. a DAG with a placement hint per node) and check it against what
  `src/runtime/concurrency.py` and the quarter-fleet scheduler can actually consume today. This is a
  feasibility question, not a build. ✅ 2026-10-24
- [x] **DB-2 — Scope the boundary with `fleet-fanout-measurement.md`.** RTG-49 measures agent-fleet
  fan-out (Claude Code / Codex mains and subagents); this stub is about serving-plane instance
  placement for the executor side. Confirm the two are actually disjoint and do not silently overlap
  (e.g. if `worker_general` execution is itself dispatched via the agent fleet rather than direct
  inference calls) before either stub grows further. ✅ 2026-10-24 — Source review confirms the
  serving executor and Claude/Codex agent lifecycle are distinct. External harness children may
  load `/v1`, but transcript counts do not prove serving request, endpoint, or slot reservations.

## Notes

No `Research Context` intake table is populated — deliberately, since no ingested source addresses this
question. If a future intake surfaces one, add it here rather than opening a new stub.

## DB-1 feasibility review (source-only, 2026-10-24)

**Finding:** the mapping is coherent as a scheduling design, but there is no end-to-end consumer for it today. Existing task planning already represents DAG steps and coarse role choices; serving already enforces CPU-region placement and per-instance `-np` capacity. The missing bridge is a typed node-placement contract plus a scheduler that resolves ready nodes to capacity on compatible CPU/GPU role fleets. This is a software-plumbing gap, not a feasibility veto. This review inspected source only; it makes no runtime or performance claim.

**Representation.** Each DAG node should carry a stable ID, dependencies and input/output references, logical role/model requirement, workload/batch cohort key, context/request shape, priority/deadline, and typed placement constraints: allowed device class (`cpu`/`gpu`, distinguishing hard constraint from preference) and compatible role/fleet/model identities. The orchestrator may choose roles, but the runtime should choose ports, topology indices, and actual `-np` slots only after checking current capacity and safety locks. Cohorting is valid only for independent requests compatible with the same model endpoint and serving shape.

**Current path and gap.** `src/orchestration/task_ir.py` admits plan steps with `id`, `actor`, `action`, and `depends_on`; `src/orchestration/dispatcher.py` maps the actor to a registry role and creates `StepExecution` with dependencies and `parallel_group`; `src/runtime/executor.py` schedules ready dependencies and runs a parallel group only when all steps are small-worker steps and the worker cap permits it. Thus a DAG and role-level CPU/GPU split can be expressed coarsely, but there is no node-level device/fleet/endpoint/slot hint passed into serving placement. Each role binding resolves to one fleet.

At serving time, `src/scheduling/placement.py:evaluate_placement` filters the request's CPU-region candidates and returns safe placements or a `topology_overlap` queue result; `ConcurrencyAwareBackend._dispatch` consumes it and takes the region lock before one backend inference call. `src/runtime/concurrency.py:get_role_max_concurrency` is an opt-in role semaphore cap (flag default off) derived from the number of realized non-full endpoints in the bound fleet. It counts endpoints, not each endpoint's `-np` slots. `-np` itself is resolved per port from compiled `slots_by_port` in `scripts/server/orchestrator_stack.py`. There is a narrow certified native-slot sharing path for `eval_batch` requests with a `batch_id` on an aligned full CPU endpoint; it does not reserve slots for arbitrary DAG nodes or spread one cohort across endpoints.

The device model and contention seam do include a resolved CPU/GPU axis; GPU placements do not claim CPU regions exclusively, while aggregate VRAM fit is handled separately. These are useful admission inputs, not a node-placement scheduler. The configured topology in source records quarter instances retired in favor of one full plus two halves. `scripts/server/quarter_scheduler.py` still declares four fixed quarters but is explicitly parked with zero runtime importers by design; it assigns role slots and coordinates a burst drain/reassign operation, not per-node DAG placement. Its current drain check also does not inspect backend active counts. The old class therefore is not evidence of live cross-device capacity.

**Feasible next engineering steps:** extend TaskIR/`StepExecution` with validated typed node requirements and cohort keys; schedule dependency-ready nodes by compatible role/model and endpoint slot capacity; admit only through existing CPU overlap locks plus resolved device and aggregate VRAM checks; then add contract fixtures for DAG dependencies, incompatible cohorts, overlapping CPU candidates, and exhausted per-port slots. Source review alone does not support a duration estimate. The DB-2 boundary finding is recorded separately below.

**Source pins and caller references:** handoff text is epyc-root `origin/main` `ff5c63e26992d8315f478048da524db95ca8c856`; orchestrator sources are epyc-orchestrator `origin/main` `e0ba98fe6f7be12a77eeac3a487261da17f5ea5c`. Task DAG fields/role dispatch: `src/orchestration/task_ir.py:136-153`, `src/orchestration/dispatcher.py:276-319`; dependency execution and small-worker parallel gate: `src/runtime/executor.py:288-327,621-639`. Placement caller: `src/backends/concurrency_aware.py:1374-1428,1656-1664` → `src/scheduling/placement.py:116-219`. Fleet concurrency and shapes: `src/runtime/concurrency.py:38-83`, `src/fleet.py:131-183,207-222`, `src/llm_primitives/backend.py:438-460`. Per-port `-np` resolution/launch: `scripts/server/orchestrator_stack.py:329-375,1567-1613`; native batch path/certification: `src/backends/concurrency_aware.py:1430-1475`, `src/llm_primitives/backend.py:10-81`. Device axis: `src/scheduling/device_model.py:130-171`, `src/scheduling/contention.py:547-605,779-798`. Topology and parked scheduler: `scripts/server/stack_numa.py:50-60`, `scripts/server/quarter_scheduler.py:1-47,159-175,195-230,329-419`; the module explicitly says it has zero runtime importers, corroborated by a fresh `git grep` of `origin/main`. Cached GitNexus status/context/query were navigation only (graph at older local `fd1a894`); fresh source searches confirmed the callers above. No code or tests were changed.

## DB-2 boundary review (source-only, 2026-10-24)

DB-2 is resolvable by source inspection; RTG-49 runtime measurement is not a prerequisite. In the proactive executor, actor/step roles resolve to registry roles (fallback `worker_general`) and call `LLMPrimitives.llm_call` directly (`src/proactive_delegation/delegator.py:517-542`). API real-mode primitives are configured with serving URLs and admission/health components (`src/api/routes/chat_pipeline/routing.py:535-552`; `/v1`: `src/api/routes/openai_compat.py:1447-1465`). Worker-pool routing is a separate optional local llama-server batch path: constructor defaults `use_worker_pool=False` and requires a pool (`src/llm_primitives/primitives.py:65-117`); batch dispatch checks that flag and role (`src/llm_primitives/inference.py:1853-1863`); the pool describes local llama-server workers (`src/services/worker_pool.py:1-19`). The audited `worker_general` call is therefore serving-plane inference, not Claude/Codex agent-fleet spawning.

RTG-49 measures agent lifecycle from Claude/Codex transcripts offline (`/workspace/scripts/coordination/fanout_timing.py:1-24`; handoff corpus description: `/workspace/handoffs/active/fleet-fanout-measurement.md`). An external harness child can itself make a concurrent `/v1` request: `src/api/routes/v1_subagent_link.py:1-15` describes the OpenCode child-session case. Link capture is default-off (`src/features.py:213-218,735-738`). Thus workload overlap is possible: one harness child can be an RTG-49 agent and generate serving-plane load. These are distinct units; the collector does not join transcript agent records to serving requests or placement. Do not infer all transcript agents use this API.

Serving admission, per-role concurrency, configured topology/region locks, and placement govern serving dispatches (`src/llm_primitives/primitives.py:652-664`; `src/llm_primitives/inference.py:1408-1444`; `src/scheduling/placement.py`). The source review found no automatic join from a harness session/child ID through fan-out records to serving request, endpoint, or slot reservations. The operational compute calendar/FILLERS policy and serving locks are separate coordination layers; their existence does not create that code-level join or make transcript fan-out a serving-capacity measurement. Shared physical resource demand is possible.

Source pins: epyc-root `origin/main` `15675cbdec8209f36bd0a4334f689653528d8182`; epyc-orchestrator `origin/main` `f279d2debddd978a2a97d42dcad4e37662bbdc09`. Source-only review; no runtime, performance, or measurement claim.
