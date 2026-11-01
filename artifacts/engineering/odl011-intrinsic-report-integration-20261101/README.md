# ODL-011 intrinsic report integration — 2026-11-01

Research commit `1421b578ae4d5c9afbf3b2199f89893b093a0819` is published on `origin/main`. The exact six-file change adds the existing Ekimetrics SC/BI/ICC/DCC family to standard `odl_bench` row sets alongside structural, table, reading-order, and speed rows. Prediction-set hashes bind each intrinsic report; the report preserves explicit denominators and missing-embedder reasons. Existing sibling NID/MHS source fields and directions are mapped in `REPORT.md` without conversion or aliases.

## Verification and limits

- 62 model-free tests passed: 33 intrinsic + 29 ODL tests. The generated-PDF Poppler test was intentionally excluded. No PDF corpus, model, evaluator, or benchmark ran.
- R6 receipt: `receipts/R6-WRAPPER-RECEIPT.json`; captured output: `logs/publication.log`.
- Receipt SHA-256: `5bc89cbf1ddc7418a90e9ffa095ad60f906847ee0a87fddae49295f53fdb83b7`.
- Log SHA-256: `3de0a342c1610789c00897d4509792830e44004ac016f65e23ce86f031065362`.
- Source pins, adapter/writer audit, metric directions and denominators, and the precise limits are in `REPORT.md`. Existing strict Vidya run-metrics passthrough remains the sole carrier; no new adapter or grading ladder was added.
- The deterministic stand-in chunker reports diagnostic stand-in chunks. Phase-2 chunker quality, HOPE/common endpoint, adoption, routing defaults, and native work remain open.

[belief: cc]
