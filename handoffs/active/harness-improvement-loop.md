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

- [x] **HIL-7 — add the matched-budget and held-out gate to the HIL evaluation design (intake-2006, zero inference)**: amend `docs/design/harness-improvement-loop-design-20261006.md` HIL-2 with a pre-first-suite-run checklist: (1) a task-level baseline at the identical rollout count (parallel sampling, sequential refinement, per-task harness scaling) beside the paired incumbent-vs-candidate arm; (2) count proposer, meta-agent and summariser tokens in the budget; (3) disjoint train/validation/test split with selection on validation only; (4) report with and without the verification signal; (5) at least two runs, a CI and a stated minimum detectable effect; (6) an unmodified-harness control on the same split. Label items 2, 5 and 6 as EPYC additions beyond the paper protocol, map every item to its existing P-AB-1 / P-QUAL-PROMO hook or list it as a human-amendment candidate under MEASUREMENT.md section 5 (do not apply it), and state that no HIL suite run (HIL-6 onward) starts before this is satisfied. ✅ 2026-10-20
  - 2026-10-20 note: amended `docs/design/harness-improvement-loop-design-20261006.md` with the HIL-2 pre-first-suite-run checklist (six items; items 2, 5 and 6 labelled EPYC additions; each item mapped to P-AB-1 / P-QUAL-PROMO or listed as a human-amendment candidate under MEASUREMENT.md section 5, none applied; no HIL suite run from HIL-6 onward before it is satisfied). Zero inference. Checkbox left open pending review.
- [x] **HIL-8 — corrected the stale arXiv 2607.12227 v1/v2 citations in the intake index and wiki to the v4 reading (intake-2006)**: intake-921, -926, -1323, -1339 and -1341 carry insert-only CORRECTED markers plus a dated dive_corrections paragraph (held-out average +0.0 over three models, n=34, no CI, not +0.6; the v1/v2 abstract sentence is not in the v4 abstract; the intake-1341#record line pointers into intake-908 re-pointed), and `wiki/benchmark-methodology.md` narrows "none of them is budget-matched" for that paper; this lane cites `intake-1323#record` and `intake-1339#record`. ✅ 2026-10-20
- [x] **HIL-9 — append items 7-22 to the HIL-2 pre-first-suite-run checklist (harness-cluster intake 2026-10-20, zero inference).** Amend `docs/design/harness-improvement-loop-design-20261006.md` after item 6 with the sixteen consolidated items: isolation of executor and proposer from answer keys and labels; context-policy A/B reporting contract; arrival split and commitment; harness growth; validation power; the feature was actually exercised; headroom and failure decomposition; pinned arm identity; exclusions and slices; token-cost columns; label-free and judged arms; regression readout; per-role and per-feature arm design; memory-accumulating legs; attempt ledger and protected layer; arm prompt lint. Each item is labelled an EPYC addition and loop-local: an item that names a P-AB-1 or P-QUAL-PROMO hook stays run-local and is not a MEASUREMENT.md amendment proposal. State again that no HIL suite run (HIL-6 onward) starts before every item is satisfied by that run's design. Decision-package items (lifetime promotion budget, sequential e-process, rolling-window alpha budget, equivalence margin, stateful-vs-stateless gain) are not applied. ✅ 2026-10-20
- [x] **HIL-10 — add the harness-cluster evidence note to the HIL-4 decision package (preparation only; selects no option).** Append to `docs/design/harness-improvement-loop-design-20261006.md` HIL-4 a dated 2026-10-20 evidence note: (1) Harness^2 and the Adaptive Auto-Harness cross-cycle workspace both keep a per-step record with an explicit adopt/keep decision (`intake-1995#record`, `intake-2147#02`), which maps onto ExperimentJournal columns and AP-53 rejected-mutation ledger entries; (2) ReHarness adapts memory content, not the improvement architecture (`intake-1999#record`); (3) component and context-policy value is conditional on served model and budget (`intake-1991#03`, `intake-2157#01`, `intake-2144#02`, `intake-2172#record`), so under any of A, B or C every mutation arm is evaluated per role and model and never promoted across roles; (4) the theory and system papers are weakly consistent with B and do not discriminate B from C (`intake-2164#record`, `intake-2166#record`). State that the evidence is neutral between A, B and C, that OP-HIL4 stays open, and that no loop is started. ✅ 2026-10-20
- [x] **HIL-11 — record the HIL-6 pilot design requirements (design text only; the 2026-09-16 deferment on running a loop stays).** Append a 'HIL-6 pilot requirements' section to `docs/design/harness-improvement-loop-design-20261006.md`: (1) at least two cycles with an arriving split between them (cycle 1 tunes on T1; evaluate T1+T2 with no further tuning; cycle 2 re-tunes on T1+T2 from the cycle-1 harness), a stalled round 2 (all candidates worse) is a KEEP_BASE outcome and not a failure, and a one-cycle gain is not evidence that the loop compounds (`intake-2143#00`); (2) an editor-capability arm comparing a local editor (30B-A3B class served on EPYC) with a reference editor on the same split, executor and typed failure dossier, reporting gain with run-to-run noise and claiming no local feasibility from the sources, which show only weak evidence that small evolvers can match large ones in single cells (`intake-2144#00`, `intake-2165#04`); (3) a judge arm whose judge is a different model from the proposer, to test the correlated-error concern behind the label-free selection loss (`intake-2145#03`); (4) if the chosen feature is memory-accumulating, HIL-2 item 20 applies at the evaluation step; (5) HIL-2 items 7-22 all apply. ✅ 2026-10-20

**Harness-evolution primary-read queue (2026-10-20, closed 2026-10-20 by the harness-cluster intake).** intake-1995 (Harness^2), intake-1999 (Recurrent Harness) and intake-2008 (cross-component interference) are now dive-verified; their consequences are HIL-9 items 7-22, HIL-10 and HIL-11 and are not repeated here. intake-1992 (Harness Learning Enables Generalizable Test-Time Adaptation) stays Stage-1-only (operator ruling 2026-10-20); trigger recorded as M14. HIL-7 applies regardless of which architecture is adopted.

**Scratch**: `/mnt/raid0/llm/tmp/hil-design-proposals-20261006.md` (reviewed proposal, retained).

## Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M2 (monitor, 2026-10-20) — DP-B pending: sequential paired e-process for P-AB-1.** Trigger: The operator decides, or a HIL or orchestrator A/B whose planned discordant count makes early stopping valuable is designed. First step when it fires: Re-open DP-B with the planned discordant count. No immediate step remains: Fixed-N plus item 11 is the immediate step; sequential stopping costs 25-30 points of power in the dive's scratch simulation.
- **M4 (monitor, 2026-10-20) — Fine-tuning lane for a worker role, parametric continual-learning references, joint harness-weight co-evolution (Harness-Zero, EvoHarness-RL, HarnessForge, Co-Harness, HASE, WHALE, SIEVE, SEAL, sparse memory finetuning).** Trigger: The operator opens a fine-tuning or weight-update lane for any worker role. First step when it fires: Ingest-and-dive the listed sources against the lane's actual recipe. No immediate step remains: No lane exists; serving weights are frozen; mechanism-level content is kept in HIL-9 item 19.
- **M9 (monitor, 2026-10-20) — HIL-loop follow-ons (HIL-6 pilot extras, near-ceiling suite power statement, zero-adoption diagnosis, reference-trajectory diagnosis arm, offline-then-freeze design, local-editor port of published prompts, planner self-modification, regression-set definition).** Trigger: The operator selects an architecture and the HIL-6 pilot is designed, or the first HIL run completes. First step when it fires: Add the named arm or diagnostic to the pilot. No immediate step remains: HIL-11 already records the pilot requirements that can be written now; the rest needs a pilot.
- **M13 (monitor, 2026-10-20; updated 2026-10-21) — DP-F: retrospective dive of nine benched cluster intakes.** operator chose dive 2026-10-21; dives in flight; actionables return as a Stage-3 amendment. Targets: intake-1132, 1321, 1313, 1133, 1011, 1806, 1354, 1361, 117.
- **M14 (monitor, 2026-10-20) — Sources left unread at the wave cap and Stage-1-only siblings of the cluster (operator ruling 2: others refrained).** Trigger: Any bearing task is about to cite one of them, or the operator selects it. First step when it fires: Run a Stage-2b dive of that source before it is cited. No immediate step remains: They are unread; nothing in this plan cites them.
- **M15 (monitor, 2026-10-20) — DP-E pending: stateful-versus-stateless gain and equivalence-margin amendment candidates.** Trigger: The operator decides, or CME-6 reports a headroom or replication problem worth a protocol, or a no-regression claim needs a margin. First step when it fires: Draft the chosen candidate as a decision package. No immediate step remains: Protocol changes are human-only and have no consumer yet.
- **M16 (monitor, 2026-10-20) — DP-D pending: operator disposition of the flagged sources.** Trigger: The operator answers DP-D. First step when it fires: Apply the chosen row dispositions to the bearing entries' dive_corrections. No immediate step remains: Default is the recommendation column, already recorded.
- **K1 (knowledge, 2026-10-20) — HIL-2 worked examples and citing discipline (improver tokens must be charged; matched-budget; base-harness control; selection on validation only; stream-order caveats).** Retained use: Cited beside items 1-5 when a HIL run is designed.
- **K5 (knowledge, 2026-10-20) — Index records already applied at f436edc58 (intake-886/1995 notes, Harness^2 novelty narrowing, intake-1991/2007 corrections, SEA cross-notes, title record, cross-reference to intake-140).** Retained use: Stage 4 re-verifies each by grep rather than re-applying.
- **K6 (knowledge, 2026-10-20) — External-claim hygiene (do not cite: TTHE accumulation, AAH accuracy as skill gain, A-Evolve margins, 38.4 versus 36, Table 1 effect sizes, uplift as 79 points, validation-test correlation, SEA composite ranking, 9B-parity as more than within noise, ReHarness and CL-Bench as independent).** Retained use: Reader rules for any task citing those entries.
- **K7 (knowledge, 2026-10-20) — Portability and feasibility facts (local-model scaffolds need a shell/REPL; small evolvers help in single cells only; plugin components are proposal-only; cue-indexed flat index precedent; EvoHarness interface idea; DCP-4 advisory bundle precedent; four-stage pipelines buy tokens not accuracy).** Retained use: Context for HIL-11 and DCP-6.
- **K8 (knowledge, 2026-10-20) — Defects found during discovery, reported to their owners and not fixed here (duplicate IDs M-17c/d/e in episodic-memory-integrity.md; REPL-EMB-2.2 ticked while its result bullet says not ticked; promptforge handoff Notes say six rows and a prepared index row; `SEQ-4` duplicated in autopilot-sequential-allocation.md; stale anchors in CF:85 and EMB:237; the TOC-SP-3 anchors are corrected by its refinement; the `eval_tower.py:5972` comment is corrected by EV-18).** Retained use: Each owner session fixes its own file; none is in this plan's scope.
