# Fuzzy Workflow Authoring GUI — deterministic flow, fuzzy steps, one canvas

**Status**: stub (design idea from operator steering, 2026-09-17)
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: agent_architecture, tool_implementation, harness_optimization
**Parent index**: [user-facing-harness-index.md](user-facing-harness-index.md)
**Evidence**: intake-1460#record (operator digest: typed decisions; stage1-unverified), intake-1477#05 (compiled functions make fuzzy decisions while ordinary code handles exact operations — BM25, caching, branch control), intake-1481#record / intake-1482#record (compile-once specialists as candidate fuzzy nodes; gfx90a unproven — intake-1481#04), intake-1482#04 (confidence thresholding fails: the misses score 0.97–1.00), intake-1474#record (calibration warning: most wrong 7B fields are >0.90 confident)
**Related**: [`paw-compiled-specialists.md`](paw-compiled-specialists.md) PAW-5 (enumerates the ≤3 recurring fuzzy subtasks — **FW-1 consumes that enumeration, it does not repeat it**), [`typed-decision-plane.md`](typed-decision-plane.md) TD-2 (calibration gate) and TD-4 (closed-set tool-argument pilot), [`tool-use-eval-contract.md`](tool-use-eval-contract.md) TU-TD-1 (closed-set tool-argument arm — FW-1's tool-output-routing example links here rather than duplicating it), [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (HS-4: one router, no patches)

## Objective

Design a process-authoring GUI where the user draws a flow whose deterministic steps are ordinary code and
whose fuzzy steps are typed decision calls or compiled specialists. Operator steering: "a GUI for designing
high level processes that clearly separate deterministic flow from fuzzy LLM work in a meaningful way."
The GUI is an authoring surface, not a runtime. **Candidate runtimes**: the orchestrator's own graph
(`epyc-orchestrator/src/graph`, `decision_gates.py`) together with the durable-execution component adopted
from intake-847#record (LangGraph `adopt_component`) — available today; the typed-decision plane (RTG-56) once
TD-2 calibration lands; PAW compiled programs (INF-76) once PAW-2 proves gfx90a. Neither RTG-56 nor INF-76 is
assumed to be the runtime.

## Tasks

- [ ] **FW-1 — Requirement sketch + one worked example.** Take one recurring fuzzy subtask from PAW-5's
  enumeration (candidate: eval-triage or tool-output routing; the latter links to TD-4 / TU-TD-1), express it
  as a two-layer graph (deterministic nodes: code; fuzzy nodes: typed questions / compiled programs), and
  record what the GUI must expose. **The sketch opens with a pseudocode loop block** per
  [`docs/guides/agent-workflows/agent-loop-design.md`](../../docs/guides/agent-workflows/agent-loop-design.md):
  every actor and what it reads; every gate and its rejection grounds; where every rejection GOES — a
  dangling rejection edge is a **lint error** for the GUI, not a warning; the one step that costs real
  resources (every gate sits before it, or says why not); one independent budget per gate, none feeding
  another. The GUI's node/edge vocabulary is derived from that block. **Fuzzy-node contract**: typed output —
  `choice` / `score` / `null` (RTG-56 spells it Noul) — plus a probability; a fuzzy node may **not** branch on model confidence until
  RTG-56 TD-2 lands (intake-1474#record, intake-1482#04); schema-invalid output after the declared retry
  budget routes to a **declared** node (abstain / escalate / deterministic fallback), never off the canvas;
  every model call goes through `LLMPrimitives` (HS-4 "one router" — no side channels from the GUI runtime).
  Acceptance: the example runs end-to-end in a notebook or CLI harness with the GUI mocked, and the loop
  block is in the sketch with all four requirements and the budgets named.
- [ ] **FW-2 — Record placement (no operator choice remains).** HS-4 §2 admits shell plugins only for
  configuration, so a harness plugin is excluded; the dashboard plane rule (`dashboard/README.md`, RTG-47,
  ratified 2026-08-10) puts every **page** on the hub `:8100` with a `dashboard/registry.json` entry, a
  `health_path` probe (`/health` is transport-only; `/api/health` is the freshness fold) and a freshness
  envelope, while the **data contract** lives with the subsystem it observes. So: workflow document schema,
  executor and the `/dashboard/api/workflows/*` contract in `epyc-orchestrator`; authoring page, registry
  row, probe and freshness envelope on the hub; nothing in the shell. GUI-authored workflows that run on
  `/v1` wait for the P0.4 freeze (HS-5b). Acceptance: a contract stub (schema + endpoint list) in
  `epyc-orchestrator` and a registry-row draft handed to the owning hub session — the drafting is this
  handoff's; the row write is the owner's.
- [ ] **FW-3 — Survey prior art (≤1 day).** Flow-authoring UIs with LLM nodes (e.g. Dify/LangFlow-class) and
  compiled-function authoring (PAW playground) — what to borrow, what to refuse. No ingestion; a short note.
  Acceptance: the note lands in `docs/reference/harness-candidates/` (one file, named for this handoff) and
  FW-1 cites it.
- [ ] **FW-4 — Belief-kernel wiring, write side, prospective (CLAUDE.md → Belief Kernel).** Before the first
  FW-1 end-to-end run: a source-table row in `scripts/vidya/adapters/README.md` (class `measurement`;
  prospective; drafted here, written by that file's owner) plus an SC task in
  [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). Each run emits one `ClaimTuple`
  carrying the workflow document hash, the node types, the fuzzy-node model/pin (or compiled-program id), and
  every gate's outcome; `claim_tuple.grade()` decides the grade — no new ladder. Acceptance: row text +
  SC task drafted and the FW-1 harness refuses to run without the hook.

## Open Questions

- Does the GUI edit a declarative document (typed JSON/YAML graph) that the orchestrator executes, or generate code?
  (intake-847#record already points at the declarative answer: a graph the orchestrator executes durably, topology kept.)
- How are fuzzy-node contracts versioned when the underlying model or compiled program changes?
