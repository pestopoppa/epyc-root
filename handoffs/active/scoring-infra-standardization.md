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
- [x] **1c-audit. Orchestrator scoring + tool-use audit (read-only, subagent).** ✅ 2026-07-24 — report:
      [`research/deep-dives/2026-07-24-autopilot-scoring-tooluse-audit.md`](../../research/deep-dives/2026-07-24-autopilot-scoring-tooluse-audit.md)
      (59 file:line citations). **Verdicts:** (Q1) **memrl reward NOT AFFECTED** — the live TD reward does zero
      regex answer-extraction (structural success flag + telemetry/prior cost terms; latency length-normalized);
      externally-injected eval rewards use the B7-hardened `debug_scorer` (bare-letter-safe). (Q2) judge-parse
      bug class present but **every affected path dormant or reward-decoupled** (`model_grader` has no callers;
      proactive-review gating flags declared off). (Q3) **tool use IS production-live** via the bespoke Python-REPL
      protocol (`TOOL()/CALL()/FINAL()`) — NOT llama-server native function calling; `ChatRequest.tools` is
      accepted-but-never-consumed (wired-but-dead). An architect tool-use eval can run through the orchestrator
      TODAY via `call_orchestrator_forced(force_role="architect_general", force_mode="repl")`. (Q4) 10 independent
      extraction impls inventoried. **No ⚠ production finding.**
- [ ] **1c-fix (PRODUCTION-TOUCHING, GATED — scoped by the audit).** (a) Vendor the canonical `answer_scoring`
      contract into the orchestrator + a **shared golden-corpus drift test** (data-only coupling, consistent with
      orchestrator→research being a DATA dependency). (b) Fix the latent verbose bias: `review_service.review()`
      truncates the candidate to **500 chars** before judging (`review_service.py:420`) feeding `all_approved` →
      memrl reward — dormant only while `parallel_execution`/`architect_delegation` stay off, and re-enterable via
      per-request `allow_delegation=True`. (c) `debug_scorer.py:269-272` last-standalone-letter fallback is a
      false-*POSITIVE* (score-inflation) risk vs the canonical lib — re-score a recent eval batch before/after
      consolidation to quantify. (d) Decide fate of dead `ChatRequest.tools` (consume or remove).

### Track 2 — Tool-use / coding eval harness
- [x] **2a-i. `datasets` + code-execution scorer scaffold.** ✅ 2026-07-24 — DONE. Installed the `benchmark`
      extra (`datasets 5.0.0`; LiveCodeBench loads 2360 items). Built `code_exec_scorer.py` (`extract_code` +
      `score_code`) running generated code vs stdin/stdout or assert-style tests in an isolated subprocess
      (fresh temp cwd, RLIMIT_CPU/AS/CORE/NPROC, wall timeout, minimal env); smoke-tested correct/wrong/runaway/
      functional. Replaces the adapter's placeholder `substring "def "` check. Research `e12149b9`.
- [x] **2a-ii. Wire it to the suites.** ✅ 2026-07-24 — `code_execution` dispatch added to canonical
      `score_response` (functional check() / unittest / stdin-stdout styles); HumanEval oracle validated
      **164/164 canonicals**; BCB unittest oracle validated **90/148** (drops = long-tail deps/env, equal for
      all arms); real-LCB stdin/stdout materialized from the cached contest dataset (the shipped adapter's
      "code_execution" was a stub — commented-out asserts). Research `5b7a1696`, `1d490c26`. Remaining
      sub-item → **harden isolation (unshare/nsjail/container)** before at-scale/untrusted runs (scaffold is
      trusted-code only) — still open, carried in 2b-agentic prep.
- [~] **2b. Run A1/A3/A4 on the coding ladder** — RUNNING 2026-07-24. **HumanEval DONE** (validation rung;
      paired n=164: A4 95.7 / A1 95.1 / A3 92.1, all p≥0.15 — saturated as predicted; **IQ2 costs nothing on
      executable code**, A1≈A4 p=1.0). **LCB-hard running** (53 hard contest problems, stdin/stdout oracle,
      window 2023-05→2024-03; contamination caveat: window likely overlaps training). **BCB-hard chained**
      (90 verified-scorable of 148; exec venv py3.12 + dep stack). Artifacts `architect-code-eval-20260724/`.
- [~] **2b-swe. SWE-bench Verified harness (official, docker).** Mechanics ✅; **gold-calibration filter
      VALIDATED ✅ 2026-07-24: 40/40 instances resolve gold** (django 24 + mpl/sklearn/sphinx/sympy 4 each;
      psf/requests excluded as non-hermetic). Oracle patch-gen rung BUILT + CHAINED: prompts materialized
      (40, windowed oracle files, SEARCH/REPLACE protocol; med 11k chars), `convert_sr_to_patch.py` converts
      to unified diffs, arms generate at -c 49152 after BCB. **Remaining:** run the official harness eval on
      each arm's `predictions.json` (docker, after generation) → per-arm resolve-rate + paired stats.
- [ ] **2c. Eval-tower pool registration decision package (OPERATOR).** Once LCB-hard/BCB-hard/SWE-oracle
      prove discriminative: present options+tradeoffs for registering them into the E7 eval pool (era-sensitive
      instrument change — new-era row vs supplementary-pool vs bench-only). Operator asked for the package
      when the time comes; do NOT register unilaterally.
- [ ] **2d. LCB contamination-window refresh.** The cached LCB snapshot spans 2023-05→2024-03 (likely inside
      these models' training windows). Pull a newer LiveCodeBench release (v5/v6 date-window) for a
      post-cutoff hard slice; re-validate oracle; compare to the current window's scores (a large drop =
      contamination signal on the old window).
- [ ] **2e. Runbook: replace the P2 placeholder with the built coding ladder** (HumanEval=validation rung →
      LCB-hard → BCB-hard → SWE-oracle → agentic; validate-on-canonical/gold gates; model-major residency +
      SMT-sibling affinity for GPU serving) once the arms' results land.
      *(Declined as separate tasks: model-major driver restructure — captured in
      [[feedback_mi210_host_threads_smt_siblings]] and folds into 2e; promoting the SWE scripts from
      artifacts/ into scripts/benchmark/ — already covered by the standing runbook §10 promotion task.)*
- [ ] **2b-agentic. SWE-bench/tau-bench multi-turn harness** for true planning/tool-use. Audit Q3 unblocks a
      cheaper first rung: run a tool-use eval **through the orchestrator's live REPL loop**
      (`call_orchestrator_forced(force_role="architect_general", force_mode="repl")`) — exercises the production
      tool path with no new harness; full SWE-bench (per-instance repo envs) remains the big build.

## Reporting
Update this handoff + progress after each phase. Per-phase commits. 1c and 2b do not start without an operator
gate (production reward path / agentic build). See [[project_architect_model_selection_bench]],
[`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) §7 (pre-verdict scoring gate),
[[feedback_parse_failure_rate_is_a_scoring_artifact]].
