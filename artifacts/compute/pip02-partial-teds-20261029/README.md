# PIP02 first retained-output table scores — 2026-10-29

The first common native scoring pass finished with435/755 ODL pages and131/243 annotated tables. Available-output table-weighted TEDS is **0.656652**, with **0.799800** structure-only TEDS (higher is better). Paddle has1/755 assembled pages and **zero scored tables**, so a paired parser comparison is undefined.

| Arm | Completed pages | Scored GT tables | Available-output TEDS | Structure-only TEDS |
|---|---:|---:|---:|---:|
| ODL2.5 + Docling2.91 raster hybrid |435/755|131/243|0.656652|0.799800|
| PaddleOCR-VL1.6 native three-stage |1/755|0/243|undefined|undefined|

These are observations from available outputs, not representative full-cohort estimates. Both arms use the canonical English image plan, identical GT and the same frozen native OmniDocBench matcher/scorer. TEDS includes content; the structure-only score omits cell content. Aggregation is table-weighted, not the official page-weighted leaderboard aggregation. Missing/unknown outputs are undefined, not zero. No full-cohort, adoption or performance gate passes: every decision cell in `row_set.json` and `existing_comparison.json` remains null.

The scorer validates native input/output completion hashes before scoring. Its existing producer-lineage adapter supports97 of the completed ODL pages, containing35 tables (TEDS0.566706; structure-only0.755193). The other completed outputs need their actual generic/parallel producer registration before they can support a decision; this is explicit per page in `coverage-and-scores.json`. Those35 tables are also a selected subset, not a substitute cohort. Separately recovered pages285/310 are outside this snapshot's default input root. No historical diagnostic result is imported.

Native output and `compare-existing` persistence are preserved unchanged beside this report; `manifest.json` binds their hashes, original source pins and scorer commit. The full755-page/243-table Phase C comparison remains open. [belief: cc]
