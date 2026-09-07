# Conversational / Episodic Memory Eval Instruments — BEAM + Tulving adapters

**Status**: stub
**Created**: 2026-09-07 (via research intake, operator-approved plan 2026-09-07)
**Categories**: benchmark_methodology, memory_augmented, context_management
**Related**: [episodic-memory-integrity.md](episodic-memory-integrity.md) (M-12 consumes these),
[unified-trace-memory-service.md](unified-trace-memory-service.md) (the retrieval backend),
[canonical-judge-suite-revamp.md](canonical-judge-suite-revamp.md) (the judge),
[../completed/long-context-eval-datasets.md](../completed/long-context-eval-datasets.md) (roster gap)

## Objective

Build the two adapters M-12 needs and that our five-suite long-context roster lacks: a BEAM
128K/100K adapter, and a `context_mode` axis on the existing `tulving_episodic` adapter.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1330 | BEAM | instrument for M-12 | adopt-as-instrument | dive-verified |
| intake-1337 | MemPalace issue #125 | fold + judge-prompt evidence | adopt-with-caution | dive-verified |
| intake-408 | Tulving Episodic Memory Benchmark | primary M-12 instrument | adopt-as-instrument | dive-verified |
| intake-1342 | LOCA-bench | surveyed candidate | declined | dive-verified |

## Tasks

- [ ] **CME-1 — Author `BEAMAdapter` (a `BaseAdapter` subclass) for the 128K/100K split** in
      `epyc-inference-research/scripts/benchmark/long_context_adapters.py`, registered at the five
      points the intake-1330 dive enumerated: the lazy-import bridge `_get_long_context_adapter`
      (`dataset_adapters.py`, verified in-tree at :89–96), the `ADAPTER_SUITES` set (:50), the
      `get_adapter` dispatch (:182 region), and `ROLE_SUITE_MAP` in `suites.py`. Load from HF
      parquet (`Mohammadta/BEAM`, split `100K`, 20 rows; `probing_questions` is a STRING needing
      `ast.literal_eval` per the dataset card) or from the repo tree. Emit
      `scoring_method: "llm_judge"` with `scoring_config {"judge_port": 8082}` and carry the nugget
      list in `scoring_config` so the existing served-judge path scores per-nugget, not per-answer.
      **Re-resolve the four line anchors before editing** — they were verified 2026-09-07 and the
      registration *structure*, not the numbers, is what is load-bearing. (intake-1330#record)
- [ ] **CME-2 — Make the FOLD an explicit, tested contract** (intake-1337#record): per question, mean
      of three-valued nugget verdicts; per ability, mean over questions; headline, unweighted mean
      of the reported ability columns. Emit the rubric-item micro-average and any binarised pass
      count as clearly-labelled secondary diagnostics only. **Add a unit test that a synthetic
      all-0.5 run scores 0.500 on the headline and NOT 1.000** — the exact mutation that catches a
      `>= 0.5` binarisation regression.
- [ ] **CME-3 — Carry the BEAM harness-defect note wherever a BEAM number is quoted, ours or
      anyone's** (intake-1330#record): the judge never sees the probing question (all ten
      `evaluate_*` functions accept `probing_question` and discard it, against a prompt that
      mandates a responsiveness check), and every abstention rubric is a single-nugget refusal
      template. Both are properties of the PUBLISHED artifact and apply retroactively to Table 1
      and to every third-party quote.
- [ ] **CME-4 — Add a `context_mode` parameter {none, retrieved, full} to the Tulving adapter's
      `_row_to_prompt`** (verified at `tulving_episodic_adapter.py:582`, which always prepends the
      book). Route `retrieved` through the `src/trace` FTS5 + `navigation.py` surface. **The
      `"context"` key the adapter already emits at :637 is INERT** (`run_benchmark.py` never reads
      it), so each arm must be expressed in the prompt itself. (intake-408#record)

## Open Questions

- Does the served-judge path at `judge_port: 8082` honour `response_format json_object` reliably?
  `judge_rubric` returns 0.0 on any JSON decode error — see CJ-10.
- Is BEAM's licence compatible with staging under `/mnt/raid0/llm/data/eval/`? Resolve before download.

## Notes

Compute-gated work is filed here, never run. Adapter authoring is pure code and needs no inference.
