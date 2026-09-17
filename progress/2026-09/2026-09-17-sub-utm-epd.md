# 2026-09-17 — sub-utm-epd: UTM-P1 pairing keys + EPD-3-R5/R6/R8

Zero-inference implementation. Orchestrator commits on `origin/main`: `dd24ed10`, `d3f6062c`.

## UTM-P1 — cross-harness pairing keys (unified-trace-memory-service.md)

- Event schema v2 (`src/trace/store.py`): nullable `harness`, `seed`, `turn_ordinal`, `task_key`, plus a per-row
  `schema_version`. `task_key` was added beyond the three keys the box names because "the same task" has no other
  cross-harness identity (`trial_id` is AutoPilot-only).
- Migration safety: a fresh store gets the columns from CREATE TABLE, and a v1 store gets them by idempotent
  additive ALTER with no back-fill. A NULL `schema_version` means the pairing keys were never captured.
  `upsert_events` migrates a v1 connection that skipped `ensure_schema`, and a read-only connection is tolerated.
  `query()` NULL-projects the columns on an unmigrated store and does not migrate it.
- `paired_runs(task_key, seed=...)` returns `{turn_ordinal: {harness: [events]}}`. The live-emit content key
  includes the pairing keys only when they are set, so pre-v2 keys are byte-identical and re-emits remain no-ops.
  `ReviewTracingProcessor` threads the keys from `Trace.metadata` and from span data.
- Tests: `tests/unit/test_trace_pairing_keys.py` (13), with 180 adjacent trace/ledger/review tests green.
- Follow-ups added: UTM-P1a (no live producer stamps the keys yet) and UTM-P1b (T7 must stamp `harness="hermes"`).

## EPD-3-R5/R6/R8 (learned-routing-controller.md)

- R5: annotated rather than killed, because docs and the question_pool cleanup still reference the deprecated
  file. A guard test requires the `EPD-3-R5` marker on every `objective:{` under `deprecated/`.
- R6: `seed_memory` raises `SeedLoadError` after flushing the rows that did load, and the CLI exits 1.
- R8: `memory_record.join_embedding_segments` is now the single segment assembler, and the task convention and the
  three `embedder.py` serializers all use it. The output is byte-identical to the old serializers (randomized
  differential over 3,000 cases). The only differences are texts over 2,000 chars, which are now capped, and a
  None-valued failure key, which no longer embeds `None`. No re-embed is needed, and R1 is untouched.
- Tests: `tests/unit/test_epd3_r5_r6_r8.py`, plus 258 passed / 1 skipped across 16 adjacent embedding, seed and
  retriever test files. ruff is clean.

## Notes

- `gitnexus impact` was unavailable because epyc-orchestrator is not in the gitnexus index. The blast radius was
  derived by grep. `Event`, `upsert_events` and `ensure_schema` are used widely (~130 refs), but the change is
  additive (new optional fields, and `as_row` is consumed only by `upsert_events`). The serializers have 5 call
  sites in `retriever.py`/`routing.py`, and their output is unchanged.
