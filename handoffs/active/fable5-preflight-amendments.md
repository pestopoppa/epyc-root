# Fable 5 preflight amendments — corrections to the entry brief

**Date**: 2026-06-12. **Author**: Fable 5 (session preflight). **Verdict: the brief is sound; proceed under six amendments.** None of them invalidate the mandate — they sharpen it.

## A1. Freshness gate executed; one stale index found and fixed
`epyc-orchestrator`, `epyc-inference-research`, `llama.cpp` verified current (indexed commit == HEAD).
`epyc-root` (/workspace) was stale by 2 docs commits (indexed `4fdff4f`, HEAD `ea6f638`) — re-analysis
launched at session start via `scripts/gitnexus-analyze.sh /workspace`. `llama.cpp` confirmed queryable
as `--repo llama.cpp` (spec-dec flow query returned `proc_144_common_speculative_i` etc.).

## A2. The brief's system-state framing is stale — the review anchors on 2026-06-12 actuals
The brief describes the autopilot abstractly ("has run for hundreds of trials"). Actual current state
(`handoffs/active/autopilot-continuous-optimization.md` current-state header): **running, PID 2384026,
trial 776 of `--max-trials 1000`, codex-draft / claude-critic binding planner**, after a halt-and-recover
cycle (paused @711 on `critic_unavailable` 2026-06-07, planner timeout root-caused → `c425afc`).
More importantly, the brief omits that the "LLM planner" is **cloud CLI sessions (Claude / Codex) with
repo tool access and session resume**. This is architecturally load-bearing for facets 1–2: the @708
`critic_reject_loop` was caused by a *resumed planner session* carrying a stale narrative — i.e. part of
the self-optimizer's narrative state lives in cloud-session context **outside every store the team scrubs**.
The review will treat planner-session state as a first-class evidence store.

## A3. Three incident classes the brief lumps as "contamination" are metrologically distinct
1. **Measurement-validity defects** (the instrument lied): speed objective inflated 1.55–2× by token
   double-count until 2026-06-02 (whole-archive speed rebase required); per-suite score quantization
   0/1.5/3 making 1-question flips look like regressions; `tool_use` measured as 0 for the entire
   journal history because the trial path never sent tools (`tool-use-eval-contract.md`: "Across
   362/188/213 journal records `total_tool_calls` is uniformly 0").
2. **Decision-policy defects** (correct facts, wrong inference): MAD over-exclusion of reproduced wins;
   T0 audit rows polluting the frontier; gate run against a never-achieved baseline.
3. **Narrative re-injection** (refuted hypotheses resurrect): distilled strategy stories, journal
   `falsifier` fields, resumed planner sessions.
The brief's facet-1 question ("separation of measurement / policy / narrative") is right, but the review
will treat **metrology as its own layer with its own invariants**, not a sub-case of memory hygiene.

## A4. Facets 1+2 are one problem; the freed slot goes to statistical power
The brief half-admits this ("may be one combined target"). Confirmed: the optimizer↔evaluator game and
evidence integrity share one root — the eval tower's **resolution and sample size** (≈2 questions/suite
at T1, quantized scores, ~9% CV host noise on speed) sit below the effect sizes the planner chases. No
game-theoretic redesign fixes a measurement floor. The review adds measurement power as an explicit
sub-facet.

## A5. The master handoff index violates the project's own index governance
`master-handoff-index.md` header is a multi-thousand-word chronological accretion (newest-first session
log), and the priority queue retains many ~~struck-through completed~~ rows — both contrary to the
CLAUDE.md index contract ("actionable coordination point") and the recorded feedback memory ("indices
track only outstanding TODOs; chronology → progress logs"). This is itself evidence for deliverable #3
(index reorg) and will be treated as a symptom of the same narrative/measurement conflation as facet 1.

## A6. Session constraints
2.5 h wall-clock cap (launch prompt) overrides the brief's "no budget" language. Plan: parallel evidence
phase → adversarial synthesis → findings written incrementally to `handoffs/active/fable5-findings-*.md`.
Agent audit logging (`agent_log.sh`) does not source in this harness shell (BASH_SOURCE/env.sh mismatch);
proceeding without it — noted for transparency.
