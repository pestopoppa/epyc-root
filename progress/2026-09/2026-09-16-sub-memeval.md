# 2026-09-16 — sub-memeval: memory-eval instruments + belief-kernel wiring (zero inference)

Lane: M-12e, SC67, SC75, and CME-1/2/4 + SC68. All work was offline: no model was served, no process
was started or stopped, and the only network use was fetching the BEAM 100K split after its licence
was re-checked.

**Baseline finding.** The shared `/workspace` checkout is **377 commits behind `origin/main`**, and
local research `main` was 312 behind origin. On origin, M-12e (research `dcb769c1`), SC67 (root
`baaa6741`), CME-1 authoring and CME-2 (research `5fb27644`) and SC68 (root `a48a2425`) had already
landed and been ticked, 2026-09-14/15. All worktrees were therefore based on `origin/main`, and the
handoff edits were committed on the lane branch rather than applied in place to the stale checkout.

## Branches / commits (none merged or pushed)
- root `sub/memeval-root-20260916`: `e54c86cf`, `685a72bc`, `1e9b822d`, `e4bc7d71`
- research `sub/memeval-20260916`: `ccc41d4b`, `87991705`
- orchestrator `sub/memeval-orch-20260916`: `dae95a86`

## M-12e — verified, one gap closed
- 108/108 tests pass. Independent offline re-score of the only stored Tulving run (`20260619_141212`):
  - pre-fix scorer (`dcb769c1^`): **SRS 0.5530, CAS 0.1593**
  - v2: **SRS 0.5684** over 366 `get=="all"` questions, **CAS 0.1593**, with 37 of 45 partial
  - the fresh v2 summary is identical to the committed rescore.
- The wiki had already been corrected. Three unannotated `0.5530` quotes remained in
  `bulk-inference-campaign.md` (:5, :83, :584); they now carry the corrected figure (root `e54c86cf`).

## SC67 — already landed
- Tests: 52 passed, 1 skipped.
- The re-score emits **zero belief rows** by SC67 doctrine: the run predates the hook, so no sidecar was
  written at score time.
- Finding for the owner: the stored result file records every prompt, and all 456 carry the
  `Book narrative:` header. The arm (`full`) is therefore recoverable from producer-authored data. The
  doctrine's claim that the arm was never recorded is weaker than stated.

## SC75 / VB-INF70-ARMS — done (root `685a72bc`)
- New write-side and reader modules: `inf70_serving_arm_capture.py` + `inf70_serving_arm.py`, with 36 tests.
- The capture refuses to write a row when any of these hold:
  - the contention verdict is missing or unknown;
  - the sampler used the legacy vocabulary;
  - the arm started before 2026-09-07;
  - it runs more than 1 h after the arm's rows were written.
- The reader voids a forged pre-fix row.
- Real HARNESS-1 arms have no sidecar and project zero rows.
- The harness scripts live only in scratch, so the producer hook line is recorded in the SC75 evidence.

## CME-4 + M-12e-a (research `ccc41d4b`)
- CME-4:
  - `context_mode` now selects none / retrieved / full; `full` reproduces all 456 stored prompts exactly.
  - `retrieved` goes through the orchestrator trace FTS5 surface, using a private store.
  - Finding: `src/trace/query.query` orders by `ts_desc` despite its "bm25" docstring.
  - The scorer now refuses an `--arm` that contradicts the stored prompt headers.
- M-12e-a: only the raise half is done, so the box stays unticked. pyarrow was not installed into the
  research `.venv`, which would need network.

## CME-1 — closed (orchestrator `dae95a86`, research `87991705`)
- Orchestrator: new `request_llm_judge_text` transport, and the boolean judge now refuses `per_nugget`
  items. Blast radius MEDIUM, derived structurally because the orchestrator has no GitNexus index;
  822 judge/scorer tests pass.
- New `judge_beam_run.py`: calls the judge once per nugget; unjudged questions are listed, never scored
  0.0, and the fold refuses to run while any remain.
- BEAM 100K data staged: HF rev `3205395e`, sha256 `c0519be2…`.
- Offline smoke: 400 prompts, with prompts of **404k–905k chars**. Check that against the serving
  context before M-12a.

## For the owning session
- Merge the three lane branches. The orchestrator commit must land in the main clone before a real
  judged BEAM run.
- Then run `python3 scripts/handoffs/index_state.py`. The only failure after the ticks is FRESHNESS,
  and regenerating rewrites `master-handoff-index.md`, which this lane may not do.
- Pre-existing, unrelated: `tests/vidya/test_autokernel_serving_feedback.py` needs `EPYC_RESEARCH_ROOT`
  set (1 failure + 12 errors), and cite-check flags an overturned `intake-883` citation in
  `agent-collab-rnd-harness.md`.

## Review follow-up
- Research `194a83a9` (`sub/memeval-20260916`) fixes a `judge_beam_run.py` resume bug. A rerun used to carry
  forward unjudged rows, so it exited 3 forever even after the judge recovered. Now only judged rows carry
  forward and the rest are retried. A regression test fails on `87991705` and passes now; 50 passed, 1 skipped.
- Root `6c1484a9` (new branch `sub/memeval-root-fix-20260916`, off origin/main `c57b0b6c`, because `e4bc7d71`
  was already merged): the SC75 README rows now say the producer hook call is PENDING and point to the SC75
  evidence for the one-line call.
