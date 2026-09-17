# Harness Improvement Loop — self-improvement for orchestrator-side harness features

**Status**: stub — preliminary, not started (deferred by operator 2026-09-16)
**Created**: 2026-09-16 (operator question during HS-4: "if we want an agent loop for improving the user-facing harness, would it need to be folded into autopilot?")
**Categories**: agent_architecture, autopilot, context_management
**Related (up)**: [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (HS-4 decision: thin off-the-shelf shell, Hermes-style features built **inside the orchestrator** and exposed as MCP tools / API behaviour)
**Related (substrate)**: [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`promptforge-mutation-safety-contract.md`](promptforge-mutation-safety-contract.md), [`objective-task-rate-goodput.md`](objective-task-rate-goodput.md), [`episodic-memory-integrity.md`](episodic-memory-integrity.md) (M-12 memory instruments)
**Design inputs**: `docs/design/hs4-harness-decision-package-20260916.md`, `docs/design/hs4-shell-and-orchestrator-features-20260916.md` (feature map, in progress 2026-09-16)

## Why this exists

HS-4 put the user-facing features (user-profile memory, notes, session search, background review,
delegation, compaction, skills) in the orchestrator so every model call stays on our router and every
feature is measurable. A consequence: those features become **files the improvement machinery can
mutate and measure**. This stub records how a future improvement loop over them should be built, so
the decision is not re-derived.

## Framing (from the 2026-09-16 discussion)

The loop does **not** have to be folded into AutoPilot, but it should **reuse AutoPilot's substrate**
rather than rebuild it. The substrate already provides everything such a loop needs, and each piece
was hard-won:

- mutation proposal (prompt / code / GEPA species) with the MHS-3/4 leakage and risk guards;
- journal + W3 snapshots; AP-55 infra fingerprint / regime digest and comparability verdicts;
- the promotion gate with live-scope frontier, empty-frontier reproduction rule, fail-closed guard,
  file-sha content identity (gate-frontier, 2026-09-16);
- AP-53 re-proposal ledger, AP-54 eval knowledge fence, belief-kernel write-side adapters.

| Option | Shape | Tradeoff |
|---|---|---|
| A — new AutoPilot species/tier | harness features as another mutation target with their own objective | max reuse; AutoPilot grows a new objective axis + eval suite |
| **B — sibling loop on shared substrate (preferred)** | separate "harness loop" process importing AutoPilot's journal/gate/guards/fingerprints; own proposer, objective, schedule | clean ownership, no churn in live AutoPilot, same safety/evidence rules; needs the substrate refactored into importable components |
| C — fully separate loop | its own journal/gate/guards | fastest start, but re-lives the fail-open / stale-frontier / leakage / comparability bugs already fixed — **not recommended** |

Out of scope for any loop: pure shell surface (OpenCode/pi TUI, permission rules, plugin config) —
config-tunable only, manual.

## Open tasks (not started)

- [ ] **HIL-1** — once `hs4-shell-and-orchestrator-features-20260916.md` lands, list which orchestrator
      homes are loop-friendly (mutable as files, deterministic to evaluate) and which are not.
- [ ] **HIL-2** — define the objective axes per feature (e.g. M-12 recall accuracy for memory, task
      success on shell-session suites, latency, token cost) and the eval suite each needs; check
      MEASUREMENT.md for which need a protocol (human-amendment-only).
- [ ] **HIL-3** — substrate-extraction plan for option B: which AutoPilot modules must become
      importable (journal, safety gate, prompt_forge guards, infra fingerprint, AP-53 ledger, AP-54
      fence) and the refactor cost; confirm no behaviour change to live AutoPilot.
- [ ] **HIL-4** — decision package A vs B (vs C) with costs, for the operator.
- [ ] **HIL-5** — belief-kernel wiring for the loop's measurements (write side first).

**Preconditions before starting**: HS-4 shell integrated (Phase 0), at least one orchestrator-side
harness feature built, and the 2026-09-16 AutoPilot merge train (safety → gate-frontier → AP-54 →
AP-55 → VB writers) merged.
