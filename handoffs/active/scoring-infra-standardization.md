# Scoring Infrastructure Standardization + Tool-Use Eval Harness

**Status (2026-07-24): STARTED — Phase 1a + 2a in progress (operator-approved "both, tracked").**
**Owner:** GPU-bench session (this one) for 1a/2a; **1c and 2b are production-touching / large and gated.**

## Why this exists (the trigger)

The 2026-07-24 architect keep/drop analysis was nearly derailed by a **scorer artifact**: `gpqa_diamond` was
scored with a stale `extract_letter_answer` that dropped bare-letter answers, giving verbose **A4 15% false
parse-failures vs A1's 0%** — which manufactured a *significant* A1/A3 > A4 result that vanished (→ NULL) once
re-scored canonically (A4 gpqa 43.4→53.0%). Root cause is **fragmentation**: the stack has **~10+ independent
answer-scoring implementations**, each rolling its own extraction, each a latent copy of the same
verbose-penalty bug. Operator directive: *standardize scoring infra across the stack; you can't have
independent custom builds per sector.* Plus: there is **no runnable tool-use/coding eval harness**, which the
architect keep/drop decision actually needs (QA can't decide the architect's real job).

## The fragmentation (audit 2026-07-24)

**Research repo:** `v7_quality_gate_runner` (canonical, tested — the one to promote) · `lib/scorer` (registry) ·
`score_benchmarks` · `score_aa_omniscience_run` · `xmas_function_axis_sweep` · `xmas_cheap_kill` ·
`score_with_claude` (judge) · `short_mk_voting` · adapter-local extractors (`_extract_gsm8k_answer`, …).
**Orchestrator:** `pipeline_monitor/model_grader.grade_answer` (eval-tower LLM-judge; `_extract_classification`) ·
**`api/services/memrl.score_completed_task` (autopilot RL reward path — HIGH RISK if it shares the bug)** ·
`proactive_delegation/rubric_review.grade_candidate` · `graph/answer_resolution.resolve_answer` (agentic flow;
already has bare-letter handling).

## Phases

### Track 1 — Scorer standardization
- [x] **1a. Canonical `answer_scoring` library (ADDITIVE, safe).** ✅ 2026-07-24 — DONE. Promoted v7's 15
      validated primitives verbatim into `scripts/benchmark/answer_scoring.py` (single source, module dep = `re`
      only; sympy/Fraction lazy); `v7_quality_gate_runner` imports + re-exports them (−331 lines duplication,
      public API unchanged, external importers intact). `test_answer_scoring.py` locks the bare-letter and
      truncated-boxed regressions. Research `bc33cb76`.
- [ ] **1b. Migrate research consumers** to import the canonical lib; delete each duplicate extractor; test
      each. (score_benchmarks, lib/scorer, score_aa_omniscience, xmas_*, short_mk_voting, adapters.)
- [ ] **1c. Orchestrator audit + fix (PRODUCTION-TOUCHING, GATED).** Verify `memrl.score_completed_task`,
      `model_grader._extract_classification`, `rubric_review` against the shared contract for the
      verbose-penalty bug. `memrl` is the autopilot RL reward path — a bug there has been biasing production
      routing reward against verbose models. Fix behind the shared lib; regression-test; operator-reviewed.
      Cross-repo code sharing (research lib → orchestrator) needs a packaging decision (dependency-map has
      orchestrator→research as DATA, not CODE).

### Track 2 — Tool-use / coding eval harness
- [x] **2a-i. `datasets` + code-execution scorer scaffold.** ✅ 2026-07-24 — DONE. Installed the `benchmark`
      extra (`datasets 5.0.0`; LiveCodeBench loads 2360 items). Built `code_exec_scorer.py` (`extract_code` +
      `score_code`) running generated code vs stdin/stdout or assert-style tests in an isolated subprocess
      (fresh temp cwd, RLIMIT_CPU/AS/CORE/NPROC, wall timeout, minimal env); smoke-tested correct/wrong/runaway/
      functional. Replaces the adapter's placeholder `substring "def "` check. Research `e12149b9`.
- [ ] **2a-ii. Wire it to the suites.** Surface LiveCodeBench/BigCodeBench actual test cases in the adapter
      (`scoring_config`); add `scoring_method="code_execution"` dispatch to `score_response`/runner; validate a
      reference solution scores 100%. Then **harden isolation (unshare/nsjail/container)** — required before
      at-scale/untrusted runs; the current scaffold is trusted-code only.
- [ ] **2b. Run A1/A3/A4 on the coding harness** → the actual keep/drop capability signal (GPU-gated). Then
      the **agentic SWE-bench/tau-bench** multi-turn tool-loop harness (a real build) for true planning/tool-use.

## Reporting
Update this handoff + progress after each phase. Per-phase commits. 1c and 2b do not start without an operator
gate (production reward path / agentic build). See [[project_architect_model_selection_bench]],
[`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) §7 (pre-verdict scoring gate),
[[feedback_parse_failure_rate_is_a_scoring_artifact]].
