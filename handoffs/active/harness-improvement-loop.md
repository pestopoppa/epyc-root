# Harness Improvement Loop — self-improvement for orchestrator-side harness features

**Status**: stub — preliminary, not started (deferred by operator 2026-09-16)
**Created**: 2026-09-16 (operator question during HS-4: "if we want an agent loop for improving the user-facing harness, would it need to be folded into autopilot?")
**Categories**: agent_architecture, autopilot, context_management
**Related (up)**: [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (HS-4 decision: thin off-the-shelf shell, Hermes-style features built **inside the orchestrator** and exposed as MCP tools / API behaviour)
**Related (substrate)**: [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`promptforge-mutation-safety-contract.md`](promptforge-mutation-safety-contract.md), [`objective-task-rate-goodput.md`](objective-task-rate-goodput.md), [`episodic-memory-integrity.md`](episodic-memory-integrity.md) (M-12 memory instruments)
**Design inputs**: `docs/design/hs4-harness-decision-package-20260916.md`, `docs/design/hs4-shell-and-orchestrator-features-20260916.md` (feature map §3, landed 2026-09-16)

## Why this exists

HS-4 put the user-facing features (user-profile memory, notes, session search, background review,
delegation, compaction, skills) in the orchestrator so every model call stays on our router and every
feature is measurable. A consequence: those features become **files the improvement machinery can
mutate and measure**. This stub records how a future improvement loop over them should be built, so
the decision is not re-derived.

**The mutation object is bounded.** The **mutable arm** is the feature prompts and parameters the eval
suite measures (summarisation/review/delegation prompts, compaction thresholds, memory-recall knobs).
**Policy documents** — `AGENTS.md`, `SKILL.md` folders, `HARNESS_RUN_POLICY.md` — are **proposal-only
and human-applied**: the loop may draft a diff, never write one, exactly as P5's skill export is a
reviewed commit (HS-4 §3.7 "do not rebuild autonomous skill creation", HS-7 re-targetability, HS-5b
freeze-before-tuning; intake-1323#record, intake-1339#record).

## Framing (from the 2026-09-16 discussion)

The loop does **not** have to be folded into AutoPilot, but it should **reuse AutoPilot's substrate**
rather than rebuild it. The substrate already provides everything such a loop needs, and each piece
was hard-won:

- mutation proposal (prompt / code / GEPA species) with the MHS-3/4 leakage and risk guards;
- journal + W3 snapshots; AP-55 infra fingerprint / regime digest and comparability verdicts;
- the promotion gate with live-scope frontier, empty-frontier reproduction rule, fail-closed guard,
  file-sha content identity (gate-frontier, 2026-09-16);
- AP-53 re-proposal ledger, AP-54 eval knowledge fence, belief-kernel write-side adapters.

**HIL-4 decision-package draft** (options + tradeoffs; recommendation B). The package is complete
when HIL-3 attaches the substrate-extraction cost to row B and HIL-2 attaches the objective axes to row A.

| Option | Shape | Tradeoff |
|---|---|---|
| A — new AutoPilot species/tier | harness features as another mutation target with their own objective | max reuse; AutoPilot grows a new objective axis + eval suite |
| **B — sibling loop on shared substrate (preferred)** | separate "harness loop" process importing AutoPilot's journal/gate/guards/fingerprints; own proposer, objective, schedule | clean ownership, no churn in live AutoPilot, same safety/evidence rules; needs the substrate refactored into importable components |
| C — fully separate loop | its own journal/gate/guards | fastest start, but re-lives the fail-open / stale-frontier / leakage / comparability bugs already fixed — **not recommended** |

Out of scope for any loop: pure shell surface (OpenCode/pi TUI, permission rules, plugin config) —
config-tunable only, manual.

## Open tasks (not started)

- [ ] **HIL-1** — from `hs4-shell-and-orchestrator-features-20260916.md` §3 (landed), list which orchestrator
      homes are loop-friendly (mutable arm: files the suite measures, deterministic to evaluate) and which
      are policy documents (proposal-only). Acceptance: a two-column table in this handoff, one row per §3.x home.
- [ ] **HIL-2** — define the objective axes per feature (e.g. M-12 recall accuracy for memory, task
      success on shell-session suites, latency, token cost) and the eval suite each needs; check
      MEASUREMENT.md for which need a protocol (human-amendment-only). HS-5b ordering: no tuning before the
      P0.4 freeze (intake-1323#record, intake-1339#record).
- [ ] **HIL-3** — substrate-extraction plan for option B: which AutoPilot modules must become
      importable (journal, safety gate, prompt_forge guards, infra fingerprint, AP-53 ledger, AP-54
      fence) and the refactor cost; confirm no behaviour change to live AutoPilot. RTG-55's completed
      ledger forbids new task boxes there — the refactor items live here and in RTG-02, and link back.
- [ ] **HIL-4** — decision package A vs B (vs C) with costs, for the operator. The draft is the table
      above; closable once HIL-2/HIL-3 fill in the costs.
- [ ] **HIL-5** — belief-kernel wiring for the loop's measurements, write side, **prospective row filed
      now** (CLAUDE.md → Belief Kernel: not "when the substrate is ready"): a source-table row in
      `scripts/vidya/adapters/README.md` (class `measurement`; carrier: feature id, prompt/parameter
      file-sha, suite id, objective axis, verdict) drafted here and written by that file's owner, plus an
      SC task in [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). Grading by
      `claim_tuple.grade()`, no new ladder. Acceptance: row text + SC task drafted before HIL-2's first suite run.

**Preconditions before starting the loop itself** (HIL-1..HIL-5 are zero-inference design tasks and
need none of these): HS-4 shell integrated (Phase 0 — P0.1–P0.3 landed, P0.4 live run pending), at least
one orchestrator-side harness feature built, and the 2026-09-16 AutoPilot merge train (safety →
gate-frontier → AP-54 → AP-55 → VB writers) merged (VB writers wired 2026-09-16, VB-WIRE-1).
