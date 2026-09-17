# 2026-09-16 — sub-runner-adapters (zero-inference porting agent)

**Branch** `sub/runner-adapters-20260916` (root worktree `/mnt/raid0/llm/worktrees/sub-runner-adapters`),
commit `2d45240f`, not pushed.

## What was done
- Ported the uncommitted GPU-runner adapters from /workspace onto origin/main:
  `tale_budget{,_capture}.py`, `review_f1{,_capture}.py`, plus their tests.
- Wired `cli.py ingest tale-budget` and `ingest review-f1` (`ingest_sources.py`), with end-to-end
  fixtures and decline/grade-down tests in `tests/vidya/test_ingest_sources.py`.
- TALE writer: added `tale_mean_latency_s_answer_only`. VB-PRB-T4 requires answer-only AND
  incl-estimator latency, and only the latter was emitted.
- Both readers project `protocol_id=""`. Before this, the writer cited its capture schema, which let
  tuples reach Witnessed/Attested without a codified protocol; the same-day OCC-1/SC85 precedent
  forbids that. Legacy rows that cite the schema stay admissible. Any other citation voids the file.
- Updated the README source rows (review-F1 row updated, TALE row added) and the VB-PRB-T4 /
  VB-REVIEW-F1 notes and status rows. The tasks stay unticked until the research drivers merge.

## Producer/adapter check
- `eval_tale_budget.py` (research main 76f5132b): same code as a454b7fd. Field names match the writer
  (`serving.*`, `budget_unit`, `temperature`, `seed`, `chat_template_kwargs`, the per-row
  `*_incl_estimator` fields). The writer recomputes values from the `.jsonl` with the same formulas as
  `summarize()`; `.summary.json` is not read or attested.
- The capture call sites live only in unmerged drivers: `prb_t4_tale_gpu.py` on
  `sub/gpu-runner-20260916` and `ev13b_run.py` on `sub/gpu-runner-ev13b-20260916@0627a5d9`. Both
  hard-code `sys.path` to `/workspace/scripts/vidya` and swallow a capture failure into their log or
  record. When /workspace syncs to main, its untracked copies will collide with the tracked files.
- `semantic_judge.py score` fields (`per_run[].f1/precision/recall/malfunction`, `spec_sha256`,
  `judge_config.*`, `golden_manifest_checksum`, `judge_swap`) match `review_f1_capture`. `reader_quant`
  comes from the reader `_summary.json`; if that file is missing, the writer refuses.
- The PRB-T4 driver analysis globs `prb_t4_gpu_*.jsonl`, which also matches its own `.beliefs.jsonl`
  sidecars. This is harmless because `load_rows` keeps only rows that have `question_id`.

## Checks
tests/vidya 1304 passed / 80 skipped; `index_state.py --check` 0 problems; cite-check clean (rc 0).
