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

- [x] **CME-1 — Author `BEAMAdapter` (a `BaseAdapter` subclass) for the 128K/100K split** in
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
      *Evidence 2026-09-15 (research `5fb27644`, branch `sub/cme-1-beam-adapter`, NOT ticked):*
      `BEAMAdapter` authored and registered at all five points (anchors re-resolved: ADAPTER_SUITES,
      the bridge, `get_adapter`, `ROLE_SUITE_MAP` ingest + long_context); loads HF parquet or the repo
      tree, fails loudly on missing `pyarrow` / unparseable `probing_questions`; emits `llm_judge`,
      `judge_port: 8082`, and the nuggets + probing question in `scoring_config`. 41 offline tests in
      `scripts/benchmark/test_beam_adapter.py` on a synthetic fixture shaped like the HF features.
      **Remains:** (1) the served-judge consumer does NOT yet score per nugget —
      `epyc-orchestrator:scripts/benchmark/debug_scorer.py::_score_llm_judge` is a boolean
      per-answer judge that ignores `scoring_config.nuggets`; it must call the judge once per nugget
      with `beam_scoring.build_nugget_judge_prompt` and keep the 0/0.5/1 verdicts
      (`parse_nugget_verdict`) for `score_beam_run.py`; (2) a real-data smoke on the staged
      `data/100K-00000-of-00001.parquet` (5,429,768 B) under `/mnt/raid0/llm/data/eval/beam/`.
      ✅ 2026-09-16 (sub-memeval): both remains closed. (1) orchestrator `dae95a86`
      (`sub/memeval-orch-20260916`) moves the judge transport into public
      `debug_scorer.request_llm_judge_text` and makes the boolean `_score_llm_judge` REFUSE
      `per_nugget` items (`llm_judge_per_nugget_item`). Research `87991705` (`sub/memeval-20260916`)
      adds `scripts/benchmark/judge_beam_run.py`, which makes one served-judge call per nugget with
      `build_nugget_judge_prompt` and parses each reply with `parse_nugget_verdict`, writing the
      judged payload `score_beam_run.py` folds. Unavailable or unparseable questions go to
      `unjudged`, never 0.0, and the fold refuses a payload with any. Verdicts persist per
      question, so a rerun resumes. Tests: orchestrator +7 (822 passed across every
      llm_judge/debug_scorer test), research +9. (2) The data was not actually staged: fetched
      HF rev `3205395e` after re-checking the licence (CC BY-SA 4.0 / MIT). 5,429,768 B, sha256
      `c0519be2…`, provenance in `/mnt/raid0/llm/data/eval/beam/PROVENANCE.txt`. Offline smoke:
      20 conversations → 400 prompts (40 per ability), all `llm_judge`, 1–9 nuggets (median 2),
      0 dropped. **Prompt length 404k–905k chars (median 581k)**: check it against the serving
      context before M-12a. A real judged run needs the orchestrator commit merged, because the
      research shim loads the main clone's `debug_scorer.py`.
- [x] **CME-2 — Make the FOLD an explicit, tested contract** (intake-1337#record): per question, mean
      of three-valued nugget verdicts; per ability, mean over questions; headline, unweighted mean
      of the reported ability columns. Emit the rubric-item micro-average and any binarised pass
      count as clearly-labelled secondary diagnostics only. **Add a unit test that a synthetic
      all-0.5 run scores 0.500 on the headline and NOT 1.000** — the exact mutation that catches a
      `>= 0.5` binarisation regression.
      ✅ 2026-09-15 — research `5fb27644`: `scripts/benchmark/beam_scoring.py::fold_beam`
      (`FOLD_VERSION` 1, read off BEAM `report_results.py` @ `b2da22ea`; `tau_norm` for
      event_ordering when present, else the nugget mean with `event_ordering_basis` reported);
      micro-average + binarised pass count emitted under a "not the BEAM fold" label.
      `test_all_half_run_scores_0500_not_1000` pins 0.500 (and asserts the binarised rate reads 1.000
      as a labelled diagnostic); further tests cover the unweighted-column headline vs the
      question-weighted and rubric-weighted alternatives, both folds' counts, and off-scale refusal.
- [ ] **CME-3 — Carry the BEAM harness-defect note wherever a BEAM number is quoted, ours or
      anyone's** (intake-1330#record): the judge never sees the probing question (all ten
      `evaluate_*` functions accept `probing_question` and discard it, against a prompt that
      mandates a responsiveness check), and every abstention rubric is a single-nugget refusal
      template. Both are properties of the PUBLISHED artifact and apply retroactively to Table 1
      and to every third-party quote.
      *Progress 2026-09-15 (not ticked):* the note rides in every SC68 BEAM tuple
      (`beam_memory_capture.HARNESS_NOTE`) and our judge prompt passes the probing question
      (`question_in_judge_prompt` recorded); quotes outside the tuple still need it.
- [x] **CME-4 — Add a `context_mode` parameter {none, retrieved, full} to the Tulving adapter's
      `_row_to_prompt`** (verified at `tulving_episodic_adapter.py:582`, which always prepends the
      book). Route `retrieved` through the `src/trace` FTS5 + `navigation.py` surface. **The
      `"context"` key the adapter already emits at :637 is INERT** (`run_benchmark.py` never reads
      it), so each arm must be expressed in the prompt itself. (intake-408#record)
      ✅ 2026-09-16 — research `ccc41d4b` (`sub/memeval-20260916`). `context_mode` ∈ {none, retrieved,
      full}, set by constructor argument or `$TULVING_CONTEXT_MODE` (`get_adapter()` takes no
      arguments). The default is `full`, which is byte-identical to the old prompt: all 456
      stored prompts of `20260619_141212` are reproduced. Each arm has its own prompt header,
      and `none` is the bare question. `retrieved` goes through the new
      `tulving_trace_retriever.py`: one trace `Event` per chapter in a PRIVATE store built with
      the orchestrator's `ensure_schema`, queried through `navigation.search_records`, then
      bm25-ranked. **Finding:** `src/trace/query.query` says "rank by bm25" but orders by
      `ts_utc DESC`, so a limited search keeps the latest matches, not the best. The retrieved arm
      raises rather than degrade when no retriever exists. On the real 19ch book with top_k=3,
      prompts average 8.2k chars vs 50.9k for full. The scorer now reads the arm off the stored
      prompt headers (`context_mode_by_prompt`) and REFUSES a `--belief-measurements --arm` that
      disagrees. 23 new tests + 6 scorer tests; 136 passed.

## Open Questions

- Does the served-judge path at `judge_port: 8082` honour `response_format json_object` reliably?
  `judge_rubric` returns 0.0 on any JSON decode error — see CJ-10.
- ~~Is BEAM's licence compatible with staging under `/mnt/raid0/llm/data/eval/`?~~ **Resolved 2026-09-15:**
  data CC BY-SA 4.0 (HF dataset card `license: cc-by-sa-4.0`, `Mohammadta/BEAM` sha `3205395e`),
  code MIT (`github.com/mohammadtavakoli78/BEAM` LICENSE). Local staging for evaluation is
  compatible. Download size: 100K split 5,429,768 B (500K 33,956,263 B; 1M 66,156,374 B).

## Notes

Compute-gated work is filed here, never run. Adapter authoring is pure code and needs no inference.
