# Harness Improvement Loop — self-improvement for orchestrator-side harness features

**Status**: HIL-1..5 design complete; architecture choice pending; runtime loop not started (operator 2026-09-16 deferment retained)
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

## Design tasks and next boundary

- [x] **HIL-1** — ✅ 2026-10-06 MAIN accepted [reviewed design](../../docs/design/harness-improvement-loop-design-20261006.md). — from `hs4-shell-and-orchestrator-features-20260916.md` §3 (landed), list which orchestrator
      homes are loop-friendly (mutable arm: files the suite measures, deterministic to evaluate) and which
      are policy documents (proposal-only). Acceptance: a two-column table in this handoff, one row per §3.x home.
- [x] **HIL-2** — ✅ 2026-10-06 MAIN accepted [reviewed design](../../docs/design/harness-improvement-loop-design-20261006.md). — define the objective axes per feature (e.g. M-12 recall accuracy for memory, task
      success on shell-session suites, latency, token cost) and the eval suite each needs; check
      MEASUREMENT.md for which need a protocol (human-amendment-only). HS-5b ordering: no tuning before the
      P0.4 freeze (intake-1323#record, intake-1339#record).
- [x] **HIL-3** — ✅ 2026-10-06 MAIN accepted [reviewed design](../../docs/design/harness-improvement-loop-design-20261006.md). — substrate-extraction plan for option B: which AutoPilot modules must become
      importable (journal, safety gate, prompt_forge guards, infra fingerprint, AP-53 ledger, AP-54
      fence) and the refactor cost; confirm no behaviour change to live AutoPilot. RTG-55's completed
      ledger forbids new task boxes there — the refactor items live here and in RTG-02, and link back.
- [x] **HIL-4** — ✅ 2026-10-06 MAIN accepted [reviewed design](../../docs/design/harness-improvement-loop-design-20261006.md). — decision package A vs B (vs C) with costs, for the operator. The draft is the table
      above; closable once HIL-2/HIL-3 fill in the costs.
- [x] **HIL-5** — ✅ 2026-10-06 MAIN accepted [reviewed design](../../docs/design/harness-improvement-loop-design-20261006.md). — belief-kernel wiring for the loop's measurements, write side, **prospective row filed
      now** (CLAUDE.md → Belief Kernel: not "when the substrate is ready"): a source-table row in
      `scripts/vidya/adapters/README.md` (class `measurement`; carrier: feature id, prompt/parameter
      file-sha, suite id, objective axis, verdict) drafted here and written by that file's owner, plus an
      SC task in [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). Grading by
      `claim_tuple.grade()`, no new ladder. Acceptance: row text + SC task drafted before HIL-2's first suite run.

**Preconditions before starting the loop itself** (HIL-1..HIL-5 are zero-inference design tasks and
need none of these): HS-4 shell integrated (Phase 0 — P0.1–P0.3 landed, P0.4 live run pending), at least
one orchestrator-side harness feature built, and the 2026-09-16 AutoPilot merge train (safety →
gate-frontier → AP-54 → AP-55 → VB writers) merged (VB writers wired 2026-09-16, VB-WIRE-1).


## HIL-1 accepted home classification

| HS-4 §3 home | Loop-mutable measured arm vs proposal-only/policy boundary |
|---|---|
| §3.1 User-profile memory — `src/user_modeling/` / `ProfileStore`, `/v1` prompt injection, memory tools | Candidate arm may tune only the measured profile-injection prompt or declared retrieval/selection parameters; identify each by file/config digest and compare with `x_memory=off`. Profile contents, user writes, schemas, injection-scan policy, typed `x_*` precedence, and `AGENTS.md`/`SKILL.md`/`HARNESS_RUN_POLICY.md` are never autonomous mutation targets; policy changes can only be proposed for human application. |
| §3.2 Agent notes — bounded notes scope in `ProfileStore` and injection | Candidate arm may tune a measured notes-injection prompt/selection parameter only after the §3.1 arm justifies separation. Notes content and any project/repository policy documents are proposal-only; repository facts remain in versioned `AGENTS.md`, not mutable memory. |
| §3.3 Session search — `src/trace/` search/read surface and MCP `ms.search`/`ms.expand` | Candidate arm may tune a measured deterministic ranking/limit parameter or a measured prompt only if one exists in the suite. Transcript events, source/session identity, inclusion/exclusion fence, tool authorization, and data-retention policy are fixed inputs/policy, not mutation targets. Search returns snippets; no per-search LLM summary is introduced. |
| §3.4 Background review — `src/user_modeling/deriver.py`, idle/background admission | Candidate arm may tune the measured derivation prompt or declared cadence/threshold parameter. Trigger safety (idle-only), admission priority, suppression during a region claim/measured run or with `x_memory=off`, injection scanning, and proposal-only write/approval semantics remain fixed policy. Generated proposals are data, never policy. |
| §3.5 Delegation/sub-agents — `src/proactive_delegation/`, `/api/delegate`, routing and delegation tools | Candidate arm may tune a measured delegation prompt or declared per-role parameter after suite identity is fixed. Router policy, role/model choice, child tool/workspace permissions, routing parity, and escalation authority are protected policy/control surfaces; the loop may propose edits, but cannot write them. |
| §3.6 Compaction — `src/context_compression.py`, graph/session fold and thresholds | Candidate arm may tune the measured summarization prompt or declared fold threshold/ratio parameter. Session identity, fold-cache boundary and byte-identity rule, failure accounting, truthful `usage`, shell autonomy settings, and measurement/truncation policy are invariants, not mutation targets. No code-path change is implied by this prompt/parameter scope. |
| §3.7 Skills — shell-native `SKILL.md` consumer; `src/skill_hub_interop.py` export | No autonomous policy mutation. A skill document is proposal-only and human-applied; B3 export may only produce a reviewable diff/commit after the separately gated M-11a/M-12 SkillBank A/B. Shell `skills.paths` is manual configuration. |
| §3.8 Explicitly not rebuilt | No loop home or mutation arm: Honcho cloud modeling, session re-keying, search-time LLM summaries, autonomous skill creation, iteration-limit summary, multi-platform gateway. Preserve the stated boundaries; do not create new feature tasks from this section. |

- [ ] **HIL-6 — apply the operator-selected architecture**: choose A/B/C using [the reviewed costs and tradeoffs](../../docs/design/harness-improvement-loop-design-20261006.md#hil-4--completed-option-decision-package-recommend-b), then implement only the approved source/API seams. No selection is implied by the recommendation; runtime scheduling/tuning still requires the named loop preconditions.

**Scratch**: `/mnt/raid0/llm/tmp/hil-design-proposals-20261006.md` (reviewed proposal, retained).
