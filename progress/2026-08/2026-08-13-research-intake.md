# 2026-08-13 — research-intake: PARL / Kimi agent-swarm sweep, Stages 1–4

**Session type**: interactive (no roster lane worktree; operated directly on `main` in
`/workspace`, the shared clone). No roster id assigned — filed under `research-intake` rather
than a mainA–D/auditor/inference alias.

## Problem

Operator submitted `github.com/The-Swarm-Corporation/PARL` while studying Kimi's agent swarm,
and asked whether it held principles for operating our own orchestrator better.

## What happened, by stage

**Stage 1** — ingested the repo + 10 expansion sources (intake-1105…1115). Unbounded dedup
sweep found the primary source (Kimi K2.5, arXiv:2602.02276) had been cited twice inside our
own index (intake-869, intake-933) but never itself ingested — referenced ≠ read.

**Stage 2** — 6 operator-selected dives (intake-1106, 1107, 1109, 1110, 1111, 1115). **4 of 6
overturned.** Highlights: OrchBench's headline r=0.816 turned out to be simulated-quality-vs-
real-quality (n=6 model-level averages), not makespan — its own simulated-time-vs-real-time
correlation is r=−0.264; "expert-architected MAS" in the Illusion-of-Multi-Agent-Advantage paper
turned out to mean deleting the LLM from the control plane entirely, not hand-written role files;
Kimi's own Figure 7 collapses its headline 17.8-point BrowseComp gap to ~3.6 once the
single-agent arm gets a fair context-management baseline.

**Stage 2b** — 13 more sources ingested-and-dived in one combined pass (intake-1116…1127,
operator-selected, uncapped). **6 of 13 overturned.** The session's one `adopt_component`:
AdaMAST (intake-1127), Apache-2.0, runs against our own Codex/Claude transcript corpus at ~1
LLM call/trace with no success/failure oracle required — overturning an earlier dive's own
claim that an oracle was "the real blocker."

**Mid-round correction (material, caught before propagating further):** the intake-1110 (MAST)
dive agent later re-audited its own report, found 5 of its 7 delegated subagents had never
returned, and that it had substituted fabricated figures with the same confidence as sourced
ones — including a "36.9% is stale, should be 32.15%" finding. Re-derived firsthand against the
released dataset, that finding was **wrong**: 36.9% is defensible (36.3% by flag-share
denominator). This was caught and reconciled in-session, before Stage 3 planning locked it in —
see Verification below.

**Stage 3** — plan mode. Verified frozen/pointer status on every candidate handoff owner before
naming it (two of five candidates were disqualified: `outer-coordinator-learned-head.md` is
`TERMINAL not_pursued`, `tri-role-coordinator-architecture.md` has TR-4/5 frozen — both take
prose corrections only, no new checkboxes). One operator-delegated decision reversed by the plan
itself mid-flight (see Verification).

**Stage 4** — applied. See commit table below.

## Root cause / lesson

Nothing in the *tooling* failed — the intake skill's Stage-2 dive contract worked exactly as
designed: an agent that later distrusts its own output is supposed to re-verify and correct
before the finding is used downstream, and that's what happened. The near-miss was procedural:
the correction notifications arrived as five near-duplicate task-notifications *after* Stage 3
planning had already been approved with the wrong figure baked into item A1. Caught by re-reading
the notification stream before executing Stage 4, not by any gate that would have caught it
automatically. Worth a standing note: a Stage-2 dive's self-correction must be checked against
whatever plan/commit is about to use its output, not just filed.

## Changes made

| Repo | Files | Type |
|---|---|---|
| epyc-root | `research/intake_index.yaml` | +23 new entries (intake-1105…1127), 63 claim anchors, 75 claim_corrections, 1 mid-round retraction recorded in `dive_corrections` |
| epyc-root | `handoffs/active/outer-coordinator-learned-head.md`, `handoffs/completed/routing-intelligence-completed-through-2026-05-28.md` | prose fix: "production failures/breakdowns" → correct benchmark-run provenance; percentage (36.9%) left unchanged per the retraction |
| epyc-root | `handoffs/active/coordinator-role-failure-modes-and-refactor.md` | F-15 stale line-pointer fix (2620→2688) + self-report evidence caveat; +R-23 (test R-17's premise, don't reopen), +R-24 (MAST cross-walk) |
| epyc-root | `handoffs/active/session-bus-thin-dispatcher.md` | +1 task: adopt "serial collapse" as a name/pointer only |
| epyc-root | `handoffs/active/repl-turn-efficiency.md` | +3 tasks: 7K context knee, width-taper-with-phase, Critical Steps as shape-only |
| epyc-root | `handoffs/active/agent-collab-rnd-harness.md` | +1 task: hard A/B design constraints (matched cost axis, control arm, paired design) |
| epyc-root | `handoffs/active/fleet-fanout-measurement.md` (new), `handoffs/active/decomposition-to-batch-mapping.md` (new) | 2 new stubs, RTG-49/RTG-50 |
| epyc-root | `handoffs/active/routing-and-optimization-index.md`, `handoffs/active/master-handoff-index.md` | +2 index rows, regenerated master rollup |

**Checkbox flip count**: 13 new `- [ ]` (1 session-bus + 2 coordinator-refactor + 3 repl-turn +
1 agent-collab + 6 across the 2 new stubs: FM-1..FM-4, DB-1..DB-2), 0 flipped to `- [x]` —
nothing landed this round is already done, all filed as open work. (Verified against this
session's actual commit, `f9c93887..0479434c`: an earlier in-session count of 7 covered only the
4 amended existing handoffs and undercounted the new stubs' own tasks.)

**Derived-actionables gate**: every "we could/should" from the 18 dived entries' actionables
ledgers was given a disposition — filed as one of the 7 tasks above, or an explicit decline
(listed in the Stage-3 plan's Explicit Declines section: PARL reward shaping, literal CriticalSteps
adoption, OrchBench simulator, the 45% saturation gate as a numeric threshold, the 285% figure,
programmatic-tool-calling conversion, the agent cascade, the MAST repo annotator, Agent Teams,
the MAS-Orchestra orchestrator, recitation-as-production-default, full AdaMAST induction,
re-running the SpecStory scraper — 13 declines, each with a one-line reason in the plan file).

**Initially blocked, handed to operator, since applied by the operator**: `agents/shared/OPERATING_CONSTRAINTS.md`
fan-out doctrine amendment (adding negative conditions to the fan-out-by-default rule) — refused by
the `check_trust_boundary_edit.sh` hook, `agents/shared/*.md` being an enumerated human-only write
path. Exact diff was handed to the operator in-conversation as a standalone script
(`tmp/apply-fanout-doctrine-amendment.sh`); the operator ran it directly and committed it as
`541d5d4c` on 2026-08-13. This progress log's wiki reference to that landing is corrected below.

## Verification

- `bash scripts/validate/validate_intake.sh` → exit 0 throughout (checked after every write this
  session, including after two YAML-escaping repairs mid-session — nested single-quotes in
  agent-authored `quote:` scalars twice broke the parser; fixed with a targeted doubling pass,
  verified zero pre-existing lines were altered via `git diff` showing 0 deletions until the
  final Stage-4 commit).
- `python3 scripts/handoffs/index_state.py` (regen) then `--check` → **0 problem(s)**.
- Checkbox accounting verified mechanically: `git diff -U0` grep for `^+- \[ \]` = 7, for
  `^+.*\[x\]` = 0, across the four amended handoffs.
- **Mid-session correction applied before Stage 4 executed**: the Stage-3 plan's item A1
  originally read "FIX at two severities" based on the intake-1110 dive's claim that 36.9% was
  stale. That dive later retracted the staleness claim (verified firsthand against
  `MAD_full.json`: FC2 = 36.3% of positive flags, closely matching 36.9%). The plan file was
  edited to reflect the retraction — A1 narrowed from a four-file numeric correction to a
  two-file provenance-word-only correction — **before** any handoff was touched, so no wrong
  correction ever reached a committed file.

## Deferred work — named blocker

- ~~`agents/shared/OPERATING_CONSTRAINTS.md` fan-out-doctrine amendment~~ — **RESOLVED 2026-08-13**,
  landed as `541d5d4c` (see above). No longer deferred; `wiki/agent-architecture.md`'s
  2026-08-13 Compiled Update was corrected in the same follow-up push to stop asserting the rule
  "encodes none of the negative conditions."
- **`fleet-fanout-measurement.md` FM-1/FM-2/FM-3/FM-4 and `decomposition-to-batch-mapping.md`
  DB-1/DB-2**: filed as open stubs, zero code landed — correctly so; Stage 4 scope was filing
  the work, not building it.
- Nothing else. No item recurs from a prior wrap-up under an unchanged blocker.
