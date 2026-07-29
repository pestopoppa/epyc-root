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
      trusted-code only) — now tracked as its own checkbox **2a-iv** below (was prose here, invisible to the
      dashboard progress metric).
- [x] **2a-iii. Bound the scorer's descendant processes — landed as process-group kill + docstring
      correction (NOT `RLIMIT_NPROC`).** ✅ 2026-07-29 — `scripts/benchmark/code_exec_scorer.py`
      (**`epyc-inference-research`**, not the orchestrator). Two changes: (a) `start_new_session=True` +
      `os.killpg(os.getpgid(proc.pid), SIGKILL)` on timeout, closing a **confirmed orphan leak** —
      `subprocess.run`'s timeout path killed only the direct child, so anything the scored code spawned
      survived it; (b) the module docstring, which **claimed `RLIMIT_NPROC` was set when it never was**, now
      states why that mechanism is wrong here. **`RLIMIT_NPROC` deliberately NOT implemented**: it is enforced
      **per real UID, not per process tree**, and this host runs ~9,534 threads under uid 1000 (5,688 of them
      llama-server) — any per-scorer cap would fail the child's *first* fork under normal fleet load, and would
      fail NONDETERMINISTICALLY as load varies, turning the scorer into an instrument whose results track how
      busy the box is. Verified **by execution: 9/9 checks**, including the real orphan case.
- [ ] **2a-iii-followon. Bound process/thread COUNT via cgroup v2 `pids.max`** — the correct mechanism (counts
      only the scorer's own subtree, unaffected by co-tenants). Verified available on this host: `pids`
      controller present, child cgroup creatable; needs `+pids` in `cgroup.subtree_control`. Pair it with
      `cpuset.cpus`/`memory.max` pinned to the eval quadrant (cpuset 112-119) so the whole bound is enforced at
      the cgroup rather than per-process. Concrete blow-up this bounds: numpy sizes its pool to nproc (192 here).
- [ ] **2a-iv. Harden isolation** — wrap `code_exec_scorer.py` in bubblewrap (`--unshare-net`, read-only root,
      tmpfs `/tmp`). `unshare` + unprivileged userns are already available; `bwrap` is one apt package. MicroVM
      substrate (AgentENV) is recorded EVALUATED-AND-DECLINED: cannot run here (no kvm group, ublk unloaded) and
      its 2 vCPU × 1 GiB default with no cpuset knob would delete the fail-closed cpuset-112-119 guarantee we
      attest.
- [x] **2b. Coding ladder COMPLETE — all four rungs, all arms.** ✅ 2026-07-24. HumanEval n=164 (A4 95.7 /
      A1 95.1 / A3 92.1, tied/saturated); LCB-hard n=53 (A4 54.7 / A1 47.2 / A3 45.3, A4 +9.4pp ns);
      BCB-hard n=90 (A3 31.1 / A4 27.8 / A1 26.7, ns); **SWE-oracle n=40 (A3 52.5 / A1 37.5 / A4 35.0 —
      A3 vs A4 +17.5pp p=0.039 SIG uncorrected, disc 8/1)**. **Pooled 4-rung n=347: 64.8 / 64.6 / 63.4 — dead
      tied (all p≥0.53).** Read: aggregate coding TIED on discriminative suites (real null, not saturation);
      skill texture = A4 contest-algorithmics, **A3 realistic tiers (library-API + repo bug-fix)**; patch
      discipline A1 34 > A3 32 > A4 27 non-empty. ~1,050 GPU inferences, 0 request errors. Artifacts
      `architect-code-eval-20260724/` (pq.jsonl + predictions + harness reports, re-scorable).
- [x] **2b-swe. SWE-bench Verified oracle rung DONE end-to-end.** ✅ 2026-07-24 — gold-calibration 40/40;
      oracle patch-gen (SEARCH/REPLACE → diff conversion) + official docker eval for all three arms; results
      in 2b above. Harness caveat for paired stats: empty-patch instances are absent from the report's
      resolved/unresolved lists — score over the FULL slice (empty = fail) or the pairing silently shrinks.
- [ ] **2b-confirm. SWE A3-vs-A4 expansion (SEQUENCED AFTER Laguna, operator 2026-07-24).** Expand the
      gold-calibrated slice 40→150+ (docker gold-validation CPU-side), rerun A3+A4 only → decision-grade
      confirmation of the +17.5pp p=0.039 (uncorrected, ~12 comparisons today — needs confirmation).
- [ ] **2b-laguna. Fold Laguna-S-2.1 into the candidate process — ⛔ BLOCKED (operator 2026-07-24): needs a
      small llama.cpp kernel upgrade first (inference-research work, OPERATOR-OWNED — do NOT start bring-up
      until the operator green-lights; experimental-branch workflow applies per CLAUDE.md).** On disk:
      `models/Laguna-S-2.1-GGUF/` — UD-IQ2_M **34.7GB (fits MI210)**, Q4_K_M 70GB (CPU-side), and a 2.1GB
      **DFlash BF16 drafter** (own spec-dec path!). Steps: (1) runbook §3 config discovery — bring-up, MTP/
      DFlash spec-dec sweep, optimal serving block → registry; (2) **SWE-oracle 40-slice first** (the
      architect-relevant rung); (3) LCB-hard, then decide BCB-hard; full runbook later if warranted.
- [x] **2b-agentic-build. Agentic SWE harness BUILT + mock-tested (subagent).** ✅ 2026-07-24 — research
      `d476b318`: `scripts/benchmark/agentic_swe_harness.py` + tests (16/16 green, verified independently).
      Multi-turn bash/edit(SR)/done loop in the instance container, NO-oracle prompting, turn/wall/cmd
      budgets, history compaction (150k chars), tracked-only git-diff patch extraction, in-container
      timeouts, resume-safe predictions consumable by the official harness. Bonus: caught a latent
      `lstrip("ab/")` path-mangling bug in `convert_sr_to_patch.py` (fixed; 0 shipped-run impact, verified).
- [x] **2b-agentic-0. Reset `/testbed` between trials — silent cross-trial contamination path closed.**
      ✅ 2026-07-29 — `DockerEnv.reset_testbed(base_commit)` in `scripts/benchmark/agentic_swe_harness.py`
      (**`epyc-inference-research`**, not the orchestrator), called **fail-closed at the top of `run_instance`**
      (on error: status `testbed_reset_failed`, zero turns, empty patch — a silently-failed reset is exactly
      the contamination this fixes). Reset runs **before** each trial, so a crashed trial cannot poison its
      successor. Command is `git reset --hard <base_commit> && git clean -fd` — **deliberate deviation from
      `-fdx`**: `-x` also deletes IGNORED files, which in a SWE-bench testbed includes the `.egg-info`/build
      artifacts left by `pip install -e .`; deleting those breaks imports and would manufacture false failures.
      `reset --hard` (not `checkout -- .`) so an agent *commit* is undone too. Verified **by execution: 14/14
      checks**, including that the ignored artifact survives and that an agent commit is rolled back.
- [ ] **2b-agentic-0-verify. Re-verify the clean-at-base assumption (2b-agentic-smoke, below) now that the
      reset exists** — the two were always coupled: confirm `git status --porcelain` is empty inside the
      container at the start of trial 2 when the same instance runs twice in one sweep.
- [ ] **2b-agentic-smoke. LIVE smoke of the agentic harness (parent session, GPU-gated).** One instance
      (e.g. django__django-11099 container from the cached gold images) + one served arm via the provided
      CLI (`--dry-run` first); verify /testbed clean-at-base assumption; then a 10-instance pilot before any
      3-arm agentic comparison. Waits for GPU free post-Laguna-kernel work.
      Orchestrator-REPL variant (audit Q3) remains the production-path option.
- [x] **2b-agentic-capture. Lossless trajectory evidence + live integrity gate.** ✅ 2026-07-26 — Full
      assistant replies and pre-context-truncation tool observations are now always persisted with UTF-8
      sizes and SHA-256 identities. Per-turn live status exposes anomalies; a companion `capture-status.json`
      binds every patch, trajectory, and runner source. Over-budget/legacy/mismatched evidence remains
      observable but exits nonzero and is scoring-ineligible; ordinary resume fails closed. The default
      research smoke targets cover the contract (`make test`: 43 passed; `make lint`: clean).
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
- [ ] **2b-agentic-1. Pin and verify the tool-call parser before any Jackrong-family bench.** That family emits
      JSON inside `<tool_call>`, **NOT** Qwen's XML `<function=…><parameter=…>` form, and the chat template
      differs between v2 (6,994 B) and Coder (4,718 B). Verify **per model, not per family** — a cross-arm
      parse-failure gap reads as a quality gap ([[feedback_parse_failure_rate_is_a_scoring_artifact]]).
- [ ] **2b-swe-hygiene. Adopt the six-point SWE-bench disclosure standard** (harness identity + version pinned;
      the **model-harness pair** as the unit of report; denominator + split; dataset mutation disclosed;
      n/reps/seeds; contamination posture). Apply to intake-916/917/924 together. No external SWE-bench figure
      gates a decision without all six.

## Reporting
Update this handoff + progress after each phase. Per-phase commits. 1c and 2b do not start without an operator
gate (production reward path / agentic build). See [[project_architect_model_selection_bench]],
[`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) §7 (pre-verdict scoring gate),
[[feedback_parse_failure_rate_is_a_scoring_artifact]].


## 2026-07-25 — intake Stage-2a dive: ordered-subsequence verifier (BOTH metrics)

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md)._

- [ ] Add an **`ordered_subsequence`** verifier to the canonical `answer_scoring` library: given an ordered concept list, lemmatize the completion and check all concepts appear as an ordered subsequence; return graded coverage in [0,1] plus a binary all-in-order flag. Must land in the canonical library — not an 11th bespoke scorer — with unit tests for lemma-boundary and repeated-concept cases.
- [ ] **Implement BOTH Ordered Rate and Coverage-with-order, not one.** An earlier note called them redundant; the dive **overturned** that — they diverge by up to **26.5 pts** on weak models (Qwen2-0.5B 30.84 vs 57.34; Phi3-mini 49.54 vs 62.04) and converge only at 405B, so both carry distinct signal exactly in the small/quantized regime we care about.
- [ ] Source is **ACL 2025 Main and an Outstanding Paper** (arXiv 2506.15629) — our 43-question `instruction_precision` suite has **no ordering/sequence verifier of any kind**. Known fragility: spaCy-lemmatization dependence (same class as the substring/comma brittleness). **Confound to record**: the paper's leaderboard runs 32 open models at 4-bit against full-precision API arms — do not cite that table itself as quant-quality evidence.
