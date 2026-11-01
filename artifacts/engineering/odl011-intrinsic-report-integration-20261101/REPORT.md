# ODL-011 chunk-quality report integration — wrap-up draft

**Status:** Research code published; ROOT handoff/progress/report application awaits the main-lane grant.

## Published implementation

- Research `epyc-inference-research` commit `1421b578ae4d5c9afbf3b2199f89893b093a0819` (`Integrate ODL intrinsic chunk metrics in reports`), pushed to `origin/main`; serialized push verified the remote carries that commit.
- Exact six-file commit: `scripts/benchmark/odl_bench/{README.md,adapter.py,intrinsic.py,schemas.py,tests/test_intrinsic.py,tests/test_odl_bench.py}`. The unrelated AutoKernel RVP working-tree files stayed unstaged and uncommitted.
- Standard ODL row-set builders now include the existing Ekimetrics SC/BI/ICC/DCC family beside speed and (when enabled) the existing OmniDocBench structural/table/reading-order rows. No metric-family pooling, direction change, or adoption gate was added.
- Every intrinsic report row is bound to a length-framed SHA-256 of sorted prediction Markdown filenames and contents. The scorer checks that the input-set digest is unchanged before and after scoring and refuses to return rows if it changed.
- Per-page metric denominators are explicit: SC = chunks; BI = structural blocks; ICC = chunks with at least two sentences; DCC = chunk/context-window pairs. Aggregate `n` is the number of pages with a non-null metric, with detail naming the unweighted page aggregation and summed underlying units. Missing embedder means ICC/DCC `null`, `n=0`, and a reason; no default embedder provider is invoked.
- The default chunker remains a deterministic stand-in based on prediction Markdown headings/paragraphs. Its rows are diagnostic evidence about stand-in chunks and do not establish production Phase-2 chunker quality. The Phase-2 chunker, HOPE arm, common RAG correctness endpoint, and any adoption/routing decision remain open.

## NID/MHS source bridge

These are sibling `opendataloader-bench` raw scores, not aliases for the OmniDocBench edit-distance rows, and the report creates no synthetic NID/MHS values or complements:

| Raw field | Source algorithm | Direction and scope |
|---|---|---|
| NID | `src/evaluator_reading_order.py:evaluate_reading_order`: RapidFuzz ratio of whitespace-normalized reference/prediction text divided by 100 | Unitless similarity `[0,1]`, higher is better |
| NID-S | Same function, after stripping HTML table blocks from both texts | Unitless similarity `[0,1]`, higher is better; table content omitted |
| MHS | `src/evaluator_heading_level.py:evaluate_heading_level`: `1 - (APTED text-aware heading-tree edit distance / max node count)`, clamped to `[0,1]` | Unitless similarity, higher is better; includes textual content, with table blocks excluded from text similarity |
| MHS-S | Same evaluator with text ignored in node rename cost | Unitless structure-only similarity, higher is better |

When an actual sibling-scorer artifact is co-reported, preserve its field names, raw values, scorer identity and direction. It must not be converted to or substituted for OmniDocBench's lower-is-better normalized edit distances.

Source pins captured for this wrap draft:

- sibling repo `/mnt/raid0/llm/opendataloader-bench-upstream`, HEAD `7af1d8f4d0c09f51ea1a5c6ba5f66e993286d109`;
- `src/evaluator_reading_order.py` SHA-256 `9417db70bb475216d1b702e1e85f6e0af1ed113357aa8131f61fd2bcb3d21334`;
- `src/evaluator_heading_level.py` SHA-256 `839dd188a6f90eea30fd7e2f541e2431d51eb65a46500c9b1d08d619f2e1c173`.

## Existing ODL source writer/reader audit

No new Vidya source row or projection is required. ROOT `scripts/vidya/adapters/README.md` already registers `ODL-P2 Unlimited-OCR model-gated run` (current source snapshot `FETCH_HEAD` at ROOT `078d462011730f7f7658abc049a99579b247e360`, README SHA-256 `2841f915a968982fe11394309d014cac102fe1d9f0b1c5f5b9aabeb909fef078`). The existing Research writer serializes all row-set metrics into the `run_metrics` passthrough; the ROOT strict reader checks that list against the exact native `model_gated_row_set.json` metric inventory and projects only the one native Unlimited-OCR median-latency tuple. New intrinsic rows therefore remain source-bound diagnostics and do not create independent claims or a second grading ladder. Existing `SC42` / `VB-SC42-ODL-WRITER-CONFORMANCE` enrollment and task remain unchanged.

Reader source pin: ROOT `scripts/vidya/adapters/odl_model_gated.py` at the same `FETCH_HEAD`, SHA-256 `d0a835f3be572cd15f8dba6e869c1dbf13b9bccf10c544b079177e7a676b61c5`. The current parent handoff/provenance snapshot is from ROOT `FETCH_HEAD`; it was read only.

## Validation and R6 receipt

Final guarded output: **33 tests in `test_intrinsic.py` + 29 tests in `test_odl_bench.py` = 62 passed**. `TestRealPdftotextBackend` (one generated-PDF/Poppler test) was deliberately excluded to honor the no-PDF-parser-launch boundary; all other ODL tests ran, including model-gated refusal/argv guards. No model, evaluator, actual corpus benchmark, PDF corpus, or inference process ran.

- R6 receipt: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/odl-chunk-quality-r6/R6-WRAPPER-RECEIPT.json`, SHA-256 `5bc89cbf1ddc7418a90e9ffa095ad60f906847ee0a87fddae49295f53fdb83b7`.
- Captured test log: `.../publication.log`, SHA-256 `3de0a342c1610789c00897d4509792830e44004ac016f65e23ce86f031065362`.
- R6 reports return code 0, no failure, 1.347 s, sampled process-tree RSS 47,640,576 bytes, CPUs 128–129 / mutex family 32–33, drained process tree, and no native/GPU execution. The 24 declared source/input hashes match before and after.
- No 200-PDF rerun, adoption claim, routing-default change, or production/parser-quality conclusion.

## Proposed ROOT handoff box

After the ROOT lane grant, replace exactly the ODL Phase-3 integration box with:

```text
- [x] During Phase 3 benchmark integration, add intrinsic chunk-quality scores beside the committed `odl_bench` structural text edit distance, table TEDS, reading-order edit distance, and speed rows; explicitly bridge/co-report sibling NID/MHS if those names remain in the parent contract. ✅ 2026-11-01 — Research `1421b578ae4d5c9afbf3b2199f89893b093a0819`; 62 model-free tests passed under the R6 receipt above. Ekimetrics rows are informational stand-in chunk diagnostics with source-bound prediction hashes; sibling NID/MHS source fields and directions are mapped without conversion. No Phase-2 production chunker quality, HOPE endpoint, adoption or routing conclusion. [belief: cc]
```

Do not tick the sibling HOPE/common-endpoint item or any parser adoption, 200-PDF, or routing task. File the ROOT progress/log updates and durable copy of this report only after the main-lane grant.
