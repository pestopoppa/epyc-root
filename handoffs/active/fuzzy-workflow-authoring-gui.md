# Fuzzy Workflow Authoring GUI — deterministic flow, fuzzy steps, one canvas

**Status**: stub (design idea from operator steering, 2026-09-17)
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: agent_architecture, tool_implementation, harness_optimization
**Parent index**: [user-facing-harness-index.md](user-facing-harness-index.md)
**Evidence**: intake-1460#record (operator essay: typed decisions), intake-1477 §6.1 (compiled functions make fuzzy decisions while ordinary code handles exact operations), intake-1481#00 / intake-1482 (compile-once specialists as the fuzzy nodes)

## Objective

Design a process-authoring GUI where the user draws a flow whose deterministic steps are ordinary code and
whose fuzzy steps are typed decision calls or compiled specialists. Operator steering: "a GUI for designing
high level processes that clearly separate deterministic flow from fuzzy LLM work in a meaningful way."
The GUI is an authoring surface; the runtime is the typed-decision plane (RTG-56) and/or compiled programs (INF-76).

## Tasks

- [ ] **FW-1 — Requirement sketch + one worked example.** Take a real recurring workflow (candidate: eval-triage
  or tool-output routing), express it as a two-layer graph (deterministic nodes: code; fuzzy nodes: typed
  questions / compiled programs), and record what the GUI must expose. Acceptance: the example runs end-to-end
  in a notebook or CLI harness with the GUI mocked.
- [ ] **FW-2 — Decide the build posture against HS-4.** HS-4 settled on a thin shell (OpenCode) with Hermes
  features inside the orchestrator; state whether this GUI is (a) an orchestrator page, (b) a harness plugin,
  or (c) deferred. Operator decision required before implementation.
- [ ] **FW-3 — Survey prior art (≤1 day).** Flow-authoring UIs with LLM nodes (e.g. Dify/LangFlow-class) and
  compiled-function authoring (PAW playground) — what to borrow, what to refuse. No ingestion; a short note.

## Open Questions

- Does the GUI edit a declarative document (typed JSON/YAML graph) that the orchestrator executes, or generate code?
- How are fuzzy-node contracts versioned when the underlying model or compiled program changes?
