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
- [x] **1b. Migrate research consumers** to import the canonical lib; delete each duplicate extractor; test
      each. (score_benchmarks, lib/scorer, score_aa_omniscience, xmas_*, short_mk_voting, adapters.)
      ✅ 2026-08-12 (`auditor`, adjudicated closed **by exhaustion**): every migratable consumer IS
      migrated — 1b.1/1b.2 below, with tests — and mainC's 08-11 per-consumer pass proved each
      remaining candidate NOT a duplicate (mechanisms on record in the sub-bullets). Both claimed
      cross-reference comments verified landed at HEAD in git, not just on disk: research
      `answer_scoring.py` (four deltas) and orchestrator `scripts/benchmark/debug_scorer.py`
      (`f8eb36f7`). The one remaining unification candidate (`_extract_multiple_choice_letter`) is
      a gated SCORING CHANGE already tracked at **1c-fix (c)** — closing this row drops nothing.
      Reader hazard found while verifying: the research repo has an UNRELATED
      `scripts/benchmark/debug_scorer.py` (numeric/pattern scorer, no letter extraction) — the
      divergent extractor lives at the ORCHESTRATOR path of that same name.
  - **ADDITIVE PASS 2026-08-11 (`mainC`, operator-authorised: no deletions). Result: NO remaining
    consumer is a safe migration target, and each verdict is PROVEN per consumer, not assumed.**
    The two that genuinely were duplicates are already done as 1b.1/1b.2. Corrections to this row's
    own consumer list, which is partly stale: **`score_benchmarks` does not exist** under that name
    in either repo, and **`lib/scorer` is in `epyc-orchestrator`, not research** — so this list
    spans two repos and reads as if it spans one.
    - **`score_aa_omniscience_run.py` — NOT a duplicate.** Its `extract_answer` is tag-based and
      configurable (`<answer>…</answer>`), not letter extraction, and it feeds `token_f1` rather
      than a boolean match. Two concrete blockers to delegating it to canonical
      `extract_exact_answer`: canonical's single-pattern path compiles with **no flags**, so it
      loses `re.DOTALL` and would stop matching a multi-line `<answer>` block; and canonical falls
      back to the **whole stripped response** where AA falls back to the **last non-empty line** —
      which changes precision/recall/F1 on every unparsed response. This is the "AA configurable
      token-F1" the blast-radius warning named; the mechanism is now on record.
    - **`review_f1/scorer.py` — NOT a duplicate.** PR-finding scoring, different domain entirely.
    - **`debug_scorer._extract_multiple_choice_letter` (orchestrator) — NOT a duplicate, and this
      is the dangerous one.** It sits on the authority/sealed-capture path. It accepts **A-H** vs
      canonical **A-J**, has no `\boxed{}` handling, and — the systematic difference — its
      last-resort strategy returns the **last standalone letter unconditionally**, where canonical
      accepts a bare letter only when exactly ONE candidate exists. It is therefore
      **systematically more permissive: it scores answers canonical declines to parse.** Unifying
      them is a SCORING CHANGE requiring a re-score of the affected sealed captures, not a diff.
    - **`data/vision_mmmu_cutover_20260731/harness.py:88` — NOT a duplicate.** Its
      `extract_letter(text, options)` validates against the live option set (`if c in valid`);
      canonical takes no options and cannot.
    - **Landed additively** (comments only, zero behaviour change): both extractors now carry a
      cross-reference naming the other and enumerating the four deltas, so the next reader cannot
      mistake resemblance for equivalence. Research `answer_scoring.py`, orchestrator
      `debug_scorer.py`.
  - [x] **1b.1 short-m@k multiple-choice vote extraction** ✅ 2026-07-29 (research `53eb754c`; 11 focused tests): replaced its local multiple-choice regex cascade with canonical `extract_letter_answer`; preserves final-answer precedence and adds the verbose-final-line regression.
  - [x] **1b.2 X-MAS function-axis multiple-choice scoring** ✅ 2026-07-29 (research `5ed43e1e`; targeted scorer tests): replaced its local standalone-letter regex with canonical `extract_letter_answer`; preserved the runner's bespoke substring/rubric paths. The one-cell summary fixture now explicitly requests partial-summary mode, so the full module test file validates the intended partial-run behavior.
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
- [x] **2e. Runbook: replace the P2 placeholder with the built coding ladder** ✅ 2026-07-29 —
      [`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) now distinguishes
      HumanEval validation → LCB-hard → BCB-hard → SWE-oracle → agentic, retains canonical/gold gates, and
      separates built harnesses from the still operator-gated live agentic run. It also records model-major,
      one-at-a-time GPU residency with current SMT-sibling affinity, so host placement cannot be misread as
      a model result.
      *(Declined as separate tasks: model-major driver restructure — captured in
      [[feedback_mi210_host_threads_smt_siblings]] and folds into 2e; promoting the SWE scripts from
      artifacts/ into scripts/benchmark/ — already covered by the standing runbook §10 promotion task.)*
- [ ] **2b-agentic. SWE-bench/tau-bench multi-turn harness** for true planning/tool-use. Audit Q3 unblocks a
      cheaper first rung: run a tool-use eval **through the orchestrator's live REPL loop**
      (`call_orchestrator_forced(force_role="architect_general", force_mode="repl")`) — exercises the production
      tool path with no new harness; full SWE-bench (per-instance repo envs) remains the big build.
- [x] **2b-agentic-1. Pin and verify the tool-call parser before any Jackrong-family bench.** ✅ 2026-07-29 —
      `epyc-orchestrator` commit `22c476dd` parses direct JSON inside `<tool_call>` and preserves the existing
      OpenAI-array path. Separate fixtures pin the v2 (6,994 B) and Coder (4,718 B) wire contract to executable
      `CALL()` code; `134` prompt-builder tests and ruff pass. Qwen XML remains deliberately unparsed, so a
      cross-arm parse failure cannot silently become a quality gap ([[feedback_parse_failure_rate_is_a_scoring_artifact]]).
- [x] **2b-swe-hygiene. Adopt the six-point SWE-bench disclosure standard** ✅ 2026-07-29 — harness identity + version pinned;
      the **model-harness pair** as the unit of report; denominator + split; dataset mutation disclosed;
      n/reps/seeds; contamination posture. Applied below to intake-916/917/924. No external SWE-bench figure
      gates a decision without all six.

### SWE-bench disclosure application — intake-916 / 917 / 924 (2026-07-29)

External coding numbers are observations only. `unknown` is a required disclosure result, not permission
to infer a favorable value; a row with any unresolved field cannot enter an EPYC comparison or decision gate.

| Intake / reported result | Harness identity + model-harness unit | Denominator / split | Dataset mutation | n / reps / seeds | Contamination posture / disposition |
|---|---|---|---|---|---|
| **916** — proprietary KAT-Coder-V2.5, SWE-Bench Pro `65.2` | Paper identifies Claude Code as both training and evaluation harness, but does not pin an evaluable version/config; report only as proprietary KAT-Coder-V2.5 × unspecified vendor harness. | Pro benchmark denominator/split not disclosed in the result row. | Not disclosed. | Not disclosed. | Vendor-run, no independent reproduction found; never attach this result to the downloadable Dev weights or use it for a role decision. |
| **917** — KAT-Coder-V2.5-Dev, Verified `69.40` | `KAT-Coder-V2.5-Dev × claude_code@2.1.195` (pin recorded). | Full/split detail not supplied with the card result. | Not disclosed. | Card says each model/eval set ran once: `n=1`, no repetitions/variance/seeds. | Vendor in-house result; no independent evaluation found. The reported gain is below the vendor-vs-vendor baseline gap, so it is hypothesis-grade only. |
| **924** — Qwopus Fusion, astropy `7/15`; parent claims also cite `152/202` and `335/500` | Fusion harness/version not disclosed; parent figures are distinct parent-model × undisclosed-harness results and must not be inherited by Fusion. | Fusion is an astropy-only `15`-item slice; parent rows use incompatible `202`-slice and full-`500` denominators. | Selection method for the 202 slice not disclosed. | No reproducible n/reps/seeds; the `7/15` is a single small slice. | Self-report only; the benched Q4 artifact is incomplete and non-MTP, while the usable MTP Q5 artifact is unbenched. No Fusion comparison claim is admissible. |

## Reporting
Update this handoff + progress after each phase. Per-phase commits. 1c and 2b do not start without an operator
gate (production reward path / agentic build). See [[project_architect_model_selection_bench]],
[`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) §7 (pre-verdict scoring gate),
[[feedback_parse_failure_rate_is_a_scoring_artifact]].


## 2026-07-25 — intake Stage-2a dive: ordered-subsequence verifier (BOTH metrics)

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md)._

- [x] Add an **`ordered_subsequence`** verifier to the canonical `answer_scoring` library: given an ordered concept list, lemmatize the completion and check all concepts appear as an ordered subsequence; return graded coverage in [0,1] plus a binary all-in-order flag. Must land in the canonical library — not an 11th bespoke scorer — with unit tests for lemma-boundary and repeated-concept cases. ✅ 2026-08-12 (verified by `mainB` subagent; **the work landed under its other tracking id and these rows were never ticked** — research `9cc8db2d`, filed as ID-7 in [`intake-derived-work-2026-07-25.md:86`](intake-derived-work-2026-07-25.md), which IS closed). `score_ordered_subsequence` at `scripts/benchmark/answer_scoring.py:383` in the canonical library, not a new scorer; returns `coverage`, `coverage_in_order`, `all_in_order`, `missing`, `lemmatized`. Re-derived rather than inherited: `git log -S score_ordered_subsequence` → one commit, working tree clean against it, `pytest scripts/benchmark/test_answer_scoring.py` → **12 passed**. Lemma-boundary case is `test_ordered_subsequence_multiword_contiguous` (hyphen/split forms), repeated-concept case is `test_ordered_subsequence_duplicates_need_repeats`. Empty concept list raises rather than scoring 1.0.
  - [x] **Dependency decision (2026-07-29):** the research benchmark environment has no `spacy` installation or pinned English model, while the canonical scorer intentionally has only stdlib import dependencies. Do not silently substitute stemming for the specified lemmatization. Choose either a pinned, reproducible lemmatizer dependency with model/data provenance, or explicitly amend this task to a documented dependency-free lexical verifier; then add the helper without changing the critical generic `score_response()` dispatcher (GitNexus: 60 exact upstream impacts, CRITICAL). ✅ 2026-08-12 — **resolved as the second horn, dependency-free by default.** `_lemma_tokens` tries spaCy lazily and falls back to `[a-z0-9]+` surface matching, with the choice reported per call as `lemmatized: bool` rather than hidden; the fallback direction is conservative (it can MISS an inflected variant, never false-match), so an unlemmatized environment under-scores rather than inflating. No stemming substitution. **Deviation from this row, stated rather than buried**: it did touch `score_response()` — but additively, a new `if scoring_method == "ordered_subsequence"` arm reachable only by that method, so the 60 upstream callers cannot take the new branch. Pinned by `test_ordered_subsequence_dispatch_binary_arm` and by the full file staying 12/12 green.
- [x] **Implement BOTH Ordered Rate and Coverage-with-order, not one.** An earlier note called them redundant; the dive **overturned** that — they diverge by up to **26.5 pts** on weak models (Qwen2-0.5B 30.84 vs 57.34; Phi3-mini 49.54 vs 62.04) and converge only at 405B, so both carry distinct signal exactly in the small/quantized regime we care about. ✅ 2026-08-12 — both shipped and distinguishable: `all_in_order` is the paper's Ordered Rate (binary), `coverage_in_order` is Coverage-with-order (graded, longest in-order chain by DP over all occurrence positions so an early out-of-order mention cannot shadow a later in-order one), and order-blind `coverage` is carried alongside as the third. `test_ordered_subsequence_basic_directions` pins the divergence direction: all concepts present but out of order holds `coverage` at 1.0 while the ordered metrics drop.
- [ ] Source is **ACL 2025 Main and an Outstanding Paper** (arXiv 2506.15629) — our 43-question `instruction_precision` suite has **no ordering/sequence verifier of any kind**. Known fragility: spaCy-lemmatization dependence (same class as the substring/comma brittleness). **Confound to record**: the paper's leaderboard runs 32 open models at 4-bit against full-precision API arms — do not cite that table itself as quant-quality evidence.

## 2026-08-03 — intake Stage-2b: audit our own eval paths for HARNESS-LEVEL answer leakage

_Via `/research-intake` (intake-980, plus intake-977). Filed here because the defect class is
**developer-side**: no agent-side monitor can catch it, so it is a scoring-infrastructure obligation
rather than a C6 one._

An audit of 28+ submissions across 9 agent benchmarks separates cheating into two classes, and only the
second is what our reviewer/monitor work addresses:

- **Harness-level** (developer or scaffold, invisible to any agent-side monitor): verifier injection ·
  answer-key injection · **solution injection** (e.g. an `AGENTS.md` in the working tree that contains
  the solutions).
- **Task-level** (agent-initiated, what a monitor can see): online solution retrieval · mining
  version-control history for the fix · verifier prompt injection · hardcoded test answers ·
  **simulating rather than executing**.

The audit found the **top 3 submissions on one benchmark were all cheating**, and 31 confirmed
reward-hacking cases across 6 benchmarks — roughly 3× prior audits. Separately, a widely-used benchmark
maintains its own quarantine section for submissions annotated *"Test-set feedback"*, one of which would
otherwise have ranked #1 by 7 medal outcomes.

- [x] **Audit our eval fan-out and scorer paths against the harness-level list.** Specifically: does any
  prompt-assembly path put reference answers, gold patches, or oracle metadata into a context the model
  under test can read? Does any scorer path let a candidate observe its own grade before the run ends?
  ✅ 2026-08-12 (`mainB` subagent) — **prompt assembly is CLEAN; the leak is not in the prompt, it is in
  the filesystem** (next box). Verified every `_row_to_prompt` construction site in
  `scripts/benchmark/dataset_adapter_modules/{general,coding,math_adapter,reasoning,vision_agentic}.py`
  (17 sites): `expected` / `answer` / `canonical_solution` / `test` / `scoring_config.test_code` /
  `metadata.bug_explanation` are computed alongside the prompt and never concatenated into it. The
  dispatch is the narrow surface it should be — `eval_tower.py:_generate_question` builds `call_kwargs`
  from `dispatch_prompt` plus `force_role`/`force_mode`/`image_path`/`tools`/`n_probs` only; `expected`
  is read into a local for scoring and is not among them. Two by-design inclusions, recorded so nobody
  re-reports them: MBPP puts up to 3 test cases in the prompt as hints (standard MBPP protocol; its
  `expected` is only the function name), and CRUXEval input-prediction shows the output because
  predicting the input from the output *is* the task.
  **Grade observation: none in-run.** Scoring runs in `_score_generation` after the candidate's request
  has already returned, so there is no channel back into the same generation. The rubric-judge path is
  the only one holding `expected_contains`, and it is a separate `force_mode="direct"`,
  `allow_delegation=False` call gated on `check_cross_family(generator_model, role)` — the judge sees
  the reference, the candidate never does. PromptForge trace feedback
  (`eval_tower_trace_feedback.py`) is cross-trial prompt optimisation, not an in-run channel.
  *Not audited* (named rather than implied clean): `recall()`'s episodic-memory payload, which returns
  past-task Q-values and could in principle carry a prior trial's outcome for the same question.
- [x] **Check the working tree the agent sees.** Our own repo carries `CLAUDE.md`, `AGENTS.md` and skill
  files at paths an evaluated agent would naturally read — the exact shape of the solution-injection
  case. Establish what is visible during an eval run, not what we intended to be visible
  ✅ 2026-08-12 (`mainB` subagent) — **the answer key is inside the evaluated model's allowed read root.**
  `REPLEnvironment.ALLOWED_FILE_PATHS` and the live `read_file` both resolve to
  `['/mnt/raid0/llm/', '/tmp/']`, and the question pool lives at
  `/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl` — 1.35 GB, **79,479
  rows of which 78,341 carry a non-empty `expected`**, mode `0664`, each row a single JSON object
  holding both the verbatim `prompt` and its `expected`. The REPL surface advertised to the model
  (`src/prompt_builders/constants.py`) offers `grep(pattern, file_path=...)`, `peek(n, file_path=...)`,
  `list_dir(path)` and `CALL(name, **kw)` + `list_tools()`, so one `grep` of its own prompt text against
  that path returns the row containing its own answer. **Proven functionally, not by reading**:
  `_validate_file_path(pool)` → `(True, None)`; `orchestration.tools.system.read_file(pool)` returns
  content. This is exposure, not an observed exploit — no claim is made that any run did it, and the
  tool-use suite's `get_eval_secret` sentinel counts tool calls, not pool reads.
  **Corroboration that the threat model is already ours**: `src/builtin_tools.py:_register_eval_tools`
  documents minting eval secrets to "a tmpfs path outside read_file's allowed roots, so the eval harness
  can read ground truth while the model-under-test cannot grep it from the repo" — solved for that one
  tool, unsolved for the 78,341-row pool.
  **Second, distinct defect found while proving the first**: `orchestration/tools/system.py:_is_path_allowed`
  gates on `os.path.abspath`, which does **not** resolve symlinks. Demonstrated: a symlink at
  `/mnt/raid0/llm/tmp/<probe> → /etc/passwd` passed the check and `read_file` returned `/etc/passwd`
  (probe removed). The REPL's own `_validate_file_path` uses `realpath` and correctly refused the same
  path — so the two gates that share an allow-list do not share its enforcement.
  *Reachability caveat, stated because it bounds the severity*: this needs the model to be in REPL mode
  with the tool surface attached. `build_react_prompt`'s whitelist also lists `read_file`/`list_directory`,
  but that builder has **no caller outside `src/prompt_builders/`** — dead in the serving path, so ReAct
  is not a second route today.
- [x] **Record the finding either way.** "Audited, no leakage found" is a result worth having on file;
  an unaudited harness is not evidence of a clean one ✅ 2026-08-12 (`mainB` subagent) — recorded above.
  Verdict in one line: **prompt assembly and the judge path are clean; the harness-level exposure is
  filesystem reach, and it is real and reachable.** Two remediation options, neither taken here because
  both touch a production read path and this row authorised an audit, not a fix:
  (a) move `question_pool.jsonl` (and designed-core files) outside `llm_root` — the same tmpfs pattern
  `eval_secret.py` already uses, cheapest and matches an existing precedent;
  (b) narrow `ALLOWED_FILE_PATHS` during eval runs via the existing `ORCHESTRATOR_EDIT_ROOT` task-root
  isolation, which already restricts the REPL to a scratch root when active.
  Independently of the choice, `_is_path_allowed` should use `realpath` like its REPL counterpart.

**Correction carried from the dive, so it is not restated:** the audit does **not** cover MLE-bench, and
it makes no leaderboard-status claim. An earlier framing of it as "plausibly the cause of the MLE-Bench
freeze" was speculation and is retracted — the real on-benchmark antecedents are that benchmark's own
quarantine entries and its issue #124.
