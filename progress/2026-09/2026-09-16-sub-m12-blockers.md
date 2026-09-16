# 2026-09-16 — sub-m12-blockers: M-12 zero-compute blockers B1, B2, B3, B5 (+B4 recorded, B7 checked)

**M-12 GPU window deferred by operator 2026-09-16; smoke_prefix_reuse.sh ready (a6491b9e) for when it resumes.**

This lane did no inference and no process management. The work used offline tests only; the one real-data
step read the book and parquet files to build prompts. Branches are unmerged and unpushed:
- research `sub/m12-blockers-20260916`, worktree `/mnt/raid0/llm/worktrees/sub-m12-blockers`, based on
  origin/main `6459a86e`;
- root `sub/m12-blockers-root-20260916`, worktree `/mnt/raid0/llm/worktrees/sub-m12-blockers-root`, based on
  origin/main `f339916f`.

## Commits
| Repo | Commit | Content |
|---|---|---|
| research | `b69be5b2` | B1 chapter-set gold binding, plus the B3 plumbing (recorded `provenance`/`inference`/`finish_reason`) |
| research | `a6491b9e` | B5/B4: eval recipes (35B np4 and 27B np1 at 196608/slot; gemma judge), `m12_launch_argv.py`, `smoke_prefix_reuse.{sh,py}`, `docs/m12-long-context-gpu-recipe.md` |
| research | `3f16537d` | B2: BEAM `rag` (pair_chunk × BM25) and `trace` (pair_chunk via trace store, `order="relevance"`) arms; judge/scorer arm gate |
| research | `ec7fb4ab` | Belief rows only for rows bound by their own record (the pre-hook zero-rows rule, now mechanical) |
| root | `126d1b9a` | SC67 requires `gold_binding`, the nominal `chapters`, `book_chapters` and `row_binding=recorded`. SC68 ARMS = full/rag/trace, gated on `context_mode_by_row`. README rows updated. |

## B1 verification (stored run 20260619_141212)
- `--chapters 20`:
  - SRS 0.5684169470017096, CAS 0.1593154658715299.
  - The summary and all 456 per-question rows are identical to the origin/main scorer.
  - `row_binding = {legacy_prompt_verified: 456}`, because all 456 stored prompts are byte-identical to the 20ch full-arm gold.
- `--chapters 200`: all 456 rows refused.
- No `--chapters`: refused.
- `--belief-measurements --arm full`: refused, since this is a pre-hook run.

## Tests
- Research: 125 passed and 0 skipped, run against the root branch via `EPYC_ROOT`. This covers the new
  `test_tulving_chapter_set_binding` (26), `test_beam_memory_arms` (21), `test_smoke_prefix_reuse` (7) and
  `test_m12_eval_recipes` (7).
- Research `scripts/benchmark` + `scripts/lib`: the failure set is unchanged (the same 43 environment-dependent
  failures as origin/main).
- Root: `tests/vidya` 1235 passed / 80 skipped (was 1220).

## Decisions and findings
- **B3 defaults**, each recorded per row:
  - Tulving: max_tokens 1024. The longest gold answer is 17 items, 317 chars.
  - BEAM: max_tokens 2048. The longest reference is 1,584 chars.
  - Both suites: temperature 0, enable_thinking false (which forces the chat path), cache_prompt true, timeout 1800.
- **Latent prefix-reuse defect, now fixed.** `lib/executor.py` `/completion` hard-coded `cache_prompt:false`,
  which would have defeated reuse. A pinned suite now takes the chat path with `cache_prompt: true`.
- **Checkpoint mechanics** (champion `server-context.cpp:3640-3700`). M-12 prompts are a single user message,
  so the `end-(4+ubatch)` checkpoint carries reuse. The smoke test verifies this through
  `timings.cache_n`/`prompt_n`.
- **Why the recipes live in `artifacts/serving-recipes/eval/`.** The autokernel resolver rejects `extra_flags`
  (`extra_flags_unsupported`), so these are not autokernel-measurable recipes.
- **B4 judge.** gemma-4-26B-A4B-it-ORIG-Q8_0 (25.0 GiB; it fits alone). The ORIG Q4_K_M is also on disk.
  It runs as a separate, sequential launch with `--reasoning off` and no spec-decode.
- **B7.** pyarrow and pandas were already declared (`benchmark` extra) and locked (pyarrow 24.0.0,
  pandas 3.0.3), so pyproject and uv.lock are unchanged.
  - The research `.venv` has pyarrow 25.0.1 (off-lock) and **no pandas**. The M-12a Tulving adapter still needs
    pandas there: `uv sync --extra benchmark`, which would also realign pyarrow to 24.0.0.
  - The BEAM and smoke tests pass using the venv's own pyarrow.
- **At check time the MI210 (card2) had 40.6 GiB in use**, so no long-context reader fits until that load is gone.

## Intended handoff edits (not applied; episodic-memory-integrity.md is being ported by the wrap-up agent)
- M-12 section, after B-list:
  - "B1, B2, B3 closed on research sub/m12-blockers-20260916 (b69be5b2, 3f16537d, ec7fb4ab)."
  - "B4: judge = gemma-4-26B-A4B-it-ORIG-Q8_0 (operator 2026-09-16), recipe eval/gemma-4-26b-a4b-orig-q8-gpu-judge-np4."
  - "B5: recipe + smoke a6491b9e, docs/m12-long-context-gpu-recipe.md; M-12 GPU window deferred by operator 2026-09-16; smoke_prefix_reuse.sh ready (a6491b9e) for when it resumes."
  - "B6 now also includes these two branches."
  - "B7: add pandas to research .venv (uv sync --extra benchmark)."
- M-12a command: add `TULVING_CHAPTERS=200`. `score_tulving_run --chapters` is now optional and must agree with the rows.
- M-12b arms: `BEAM_CONTEXT_MODE=full|rag|trace`; `score_beam_run --arm full|rag|trace`.
- `conversational-memory-eval-instrument.md` (CME): note the B2 arm names and the `context_mode_by_row` gate.

## Belief kernel
B1 changed what SC67 reads (the chapter-set identity), so SC67 was updated on the root branch. B2 changed the
SC68 arm vocabulary, so SC68 was updated too. No new unwired measurement sources: the smoke test writes a
receipt only, and it is a gate, not a claim.

## Review fixes (Fable: research MERGE-AFTER-FIX, root MERGE) — research `06ae638d`
1. `finish_reason=length` is now surfaced.
   - Both scorers' summaries carry `finish_reason_by_row` and `truncated_rows`. `truncated_rows` is None when no row recorded a reason.
   - The judged BEAM payload carries the same fields, next to `context_mode_by_row`.
2. The streaming `/completion` path in the executor maps `stop_type` to `finish_reason`: `limit` becomes `length`; `eos` and `word` become `stop`.
3. `run_benchmark` ignores registry temperature, max_tokens multiplier and thinking-trick overrides for the tulving and beam suites. Each ignored override is logged and recorded.
4. `smoke_prefix_reuse` refuses any port declared in the launch manifest or in either registry (36 ports today). It fails closed if those files cannot be read.

Tests:
- New `test_m12_review_fixes.py`: 17 tests.
- M-12 test set: 152 passed, 0 skipped.
- Wider suite: the same 43 environment failures as origin/main.
- The June run re-scores identically.
