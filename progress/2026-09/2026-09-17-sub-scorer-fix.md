# 2026-09-17 — sub-scorer-fix (PRB-T4 scorer, gold and sampler defects; zero inference)

**Worktrees.** All three are off `origin/main`:

- research `/mnt/raid0/llm/worktrees/sub-scorer-fix-research`
- orchestrator `/mnt/raid0/llm/worktrees/sub-scorer-fix-orch`
- root `/mnt/raid0/llm/worktrees/sub-scorer-fix-root`

**Inputs.**

- Evidence: research `b4d38ebc` and root `47816fe1`.
- Record: `2026-09-16-sub-gpu-runner.md` §13.

No inference was run, no process was managed, and no subagents were used.

## 1. Where each defect lives

| Defect | Location | In TALE's own scoring? |
|---|---|---|
| livecodebench scored by `substring 'def '` | **Shared pool artifact.** The live `benchmarks/prompts/question_pool.jsonl` (gitignored, built 2026-07-27) was never regenerated after the 2026-08-12 adapter rebuild (orchestrator `75b812c0`, research `cb0761b5`). It still has 2,349 livecodebench rows and 3 `real_suite_v1` rows with `substring` + `language`. The shared scorer had no guard for that shape. | No |
| mmlu_pro `ScoringUnavailableError` (gold `I`, 0 choices) | **Shared adapter + shared scorer.** The source gold is correct: `answer == LABELS[answer_index]` on 12,032/12,032 rows, and the pool matches the source exactly. `MMLUProAdapter` (research and orchestrator twins) emitted `scoring_config={}` for a 10-option A–J suite. `debug_scorer._score_multiple_choice` was hard-wired to A–H. 2,053 rows (17.1%) have gold I/J. | No |
| math sample 100% `gsm8k_*` | **The harness's own loader.** `eval_tale_budget.load_questions` took the first n rows in file order: 1,319 gsm8k rows come before 500 MATH-500 rows. `eval_trimr.py` has the identical loader. olympiadbench is skewed the same way: geometry was 15/300 trials against a 19% population share. | Yes (sampling, not scoring) |

## 2. Consumers of the broken pieces

- **Stale pool livecodebench rows / substring scoring.** Any reader of `question_pool.jsonl` that draws
  livecodebench or real_suite_v1:
  - the orchestrator `eval_tower` (T1 core pool, 5 LCB rows) and `core_v2_select`
  - `seeding_*` and `question_pool.sample_from_pool` users (`short_mk_voting`)
  - `eval_tale_budget` and `eval_trimr`
  - the offline reward-oracle pairwise builders (learned-routing A9)
  - `real_suite_v1` reconstruct/materialize
  - xmas/e5 probes that select by id
- **The A–H multiple-choice scorer with an empty config.** Every `debug_scorer` consumer that scores
  pool `mmlu_pro` rows: CT-1 `ct1_ab_runner.py`, CT-1b, and E-7 `e7_recal_runner.py`, plus any
  tower/seeding draw. The tower's T1–T3 never sampled mmlu_pro (eval-tower audit 2026-07-20).
- **Not affected.**
  - `v7_quality_gate_runner.py`, the architect bench, and the 56.7% Qwen3.8 mmlu_pro figure. These
    use the adapter directly with `answer_scoring.extract_letter_answer`, which handles A–J.
  - `mmlu_pro_hardened_control.py`, which is a v7 wrapper.
- **The first-n loader.**
  - `eval_tale_budget.py` and `eval_trimr.py`: fixed.
  - `qwable_verifier_selector_runner.py` sorts by id and slices. Its default suite is cruxeval, so it
    would draw gsm8k-first only if run with `--suite math`. It was left as-is, because the pinned
    replay order is intentional there.

## 3. Affected earlier results

| Result | Where quoted | Effect | Caveat added |
|---|---|---|---|
| PRB-T4 livecodebench 100% | per-request-reasoning-budget.md | vacuous | already flagged; superseded by the re-run note |
| PRB-T4 math cells (and the 12 ledger rows) | per-request-reasoning-budget.md, `.vidya/ledger.jsonl` | GSM8K-only, not the suite | yes, plus VB-PRB-T4-CAVEAT |
| PRB-T4 olympiadbench cells (and the 12 ledger rows) | same | subject-skewed sample | yes, plus VB-PRB-T4-CAVEAT |
| CT-1 arm0/arm1 mmlu_pro 37.5% | qwen-chat-template-evaluation.md | 10/40 I/J forced False (pre-CJ-8); re-score ≈47.5% | yes |
| CT-1b arm2 mmlu_pro 40.0% | same, wiki/chat-templates.md | ≈52.5% | yes |
| E-7 frontdoor mmlu_pro 37.5%, architect_general 27.5%; master-registry quality rows (CT-E7b) | same, wiki | ≈50.0% / ≈40.0%; the registry needs a re-stamp | yes |
| learned-routing A9 `suite:livecodebench` "repaired" stratum (2026-06-21) | learned-routing-controller.md | labels from the vacuous oracle | yes |
| Any livecodebench score from the live pool after 2026-08-12 | autopilot-continuous-optimization.md, wiki/benchmark-methodology.md | the "rebuilt" oracle never reached the pool | yes |
| TrimR 2026-04-09 "Math (GSM8K)" | reasoning-compression.md | GSM8K-only via the first-n loader; already labelled GSM8K | none needed |

The re-score estimates come from recorded `answer_tail` (last 200 chars) scored with the fixed
scorer. Artifacts: `artifacts/chat-templates/epyc-qwen3x-v1/ab-cpu-20260821/` and
`/workspace/tmp/e7-recal/`.

**Ledger** (read-only). The only affected rows are the 24 `tale_budget/v1` PRB-T4 claims. Its
mmlu/livecodebench mentions are external intake claims. The E-7 sidecars were never ingested.

## 4. Fixes

**Orchestrator** `f0015306`. It is pushed to branch `sub/scorer-fix-orch-20260917` only; landing on `main` is blocked by the held orchestrator push lock (§6).

- `debug_scorer`: `scoring_config['choice_labels']`, a contiguous `A..` range.
  - The default A–H is unchanged, and the B7 golden-corpus pin passes.
  - Gold past the configured choices raises.
  - Past H, the pronoun "I" is never a standalone-letter vote.
- `_score_substring` raises `ScoringUnavailableError` on any row that declares a code `language`.
  Exactly the 2,352 vacuous rows have that shape, so they are EXCLUDED instead of passed.
- `dataset_adapter_modules/general.py` MMLUProAdapter:
  - `gold_letter()` derives the gold from `answer_index` and cross-checks the letter.
  - Emits `choices` + `choice_labels`.
  - Reads the pinned parquet snapshot (`b189ec76`, sha256 `0e24a191…`).

**Research** `52595b9b` (pushed)

- `dataset_adapters.py`:
  - The same MMLU-Pro fix.
  - LiveCodeBench reads its pinned jsonl snapshot (`00f2d466`), so both suites are re-derived
    offline and deterministically.
- `question_pool.py`:
  - `source_stratum` and `stratified_sample`: seeded, largest-remainder proportional, independent of
    file order.
  - `refresh_suites` / `--refresh-suites`: splices only the named suites. It refuses the live pool
    without `--allow-live-overwrite`.
- `eval_tale_budget.py`:
  - Stratified `load_questions` (`--sample-seed`), with the composition recorded in meta.
  - `oracle_defect`/`preflight_oracles` exit 2 before any request.
  - Three-valued `score_question`.
  - Summary gains `n_scored`, `n_unscoreable` and `by_source`.
  - `--pool`.
- `eval_trimr.py`: uses the same sampler.

**Re-run input.** `benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl` (gitignored,
1,352,619,970 B, sha256 `3c3b498a483f4131…`).

- livecodebench is 704 rows, all `code_execution` (1,656 dropped as having no validated oracle).
- mmlu_pro is 12,032 rows with labels.
- All 704 + 12,032 + 1,819 + 674 rows pass the preflight.
- n=400 at seed 42 gives:
  - math: 290 gsm8k + 110 MATH-500 across 7 subjects.
  - olympiadbench: 157/91/77/75.

## 5. Tests (offline)

- **Orchestrator** `tests/unit/test_debug_scorer_prbt4_guards.py`:
  - every A–J gold passes, and wrong letters fail;
  - the pronoun case;
  - out-of-range gold and malformed labels refuse;
  - the adapter's right/wrong/inconsistent-gold cases;
  - the stale LCB row refuses for known-wrong code.
  - All 26 scorer/adapter/seeding/tower test files: **731 passed, 7 skipped**.
- **Research** `scripts/benchmark/tests/test_prbt4_scorer_sampler_guards.py`: 17 tests.
  - All pass against the fixed scorer, including all 12,032 MMLU-Pro rows (gold passes, wrong
    fails).
  - Refreshed-pool two-sum: known-right passes; known-wrong and stub fail.
  - First-n regression guards for both loaders.
  - Preflight exit 2 with zero requests sent.
  - 16 related research test files: **375 passed, 8 skipped**. 3 of the skips wait for the shared
    orchestrator clone to carry the scorer fix.
- Full-corpus check: under the old empty config, exactly 2,053 MMLU-Pro rows raise. Under the new
    config, 0 raise, and right/wrong are correct on 12,032/12,032.

## 6. Open items with named blockers

- **PRB-T4-RERUN** (GPU, exclusive MI210 window): filed as a box under PRB-T4. It is not for this
  agent to run.
- **Orchestrator push.**
  - The `push` lock on epyc-orchestrator has been held by `sub-train` since 2026-09-16T16:03Z. Its
    worktree has 34 unpushed commits, and there is no heartbeat.
  - Displacing another agent's lock (`--force-release sub-train`) is the caller's/operator's call.
  - Until the orchestrator commit lands, and the shared clone `/mnt/raid0/llm/epyc-orchestrator` is
    fast-forwarded, the TALE preflight refuses mmlu_pro. That is fail-closed and intended.
- **Live pool swap.**
  - `question_pool.py --refresh-suites livecodebench mmlu_pro --allow-live-overwrite` changes the
    eval tower's T1 instrument era. That decision belongs to the tower owner.
  - Meanwhile the scorer guard already stops the vacuous passes.
- **Registry re-stamp.** The frontdoor and architect_general `mmlu_pro` quality rows need a re-stamp
  on the fixed scorer, which requires inference.
