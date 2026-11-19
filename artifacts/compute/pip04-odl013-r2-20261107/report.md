# ODL-013 — LiteParse-local vs OpenDataLoader-local vs pdftotext

Run dir: `/mnt/raid0/llm/tmp/pip04-odl013-rerun-r2-20261107/out/run`
Date: 2026-11-07 20:59:02 UTC

## Scores (higher = better; NID/TEDS/MHS from upstream evaluator)

| engine | NID (reading order) | TEDS (tables) | MHS (headings) | overall |
|---|---|---|---|---|
| pdftotext | 0.8589 | 0.0000 | 0.0000 | 0.5705 |
| opendataloader | 0.9115 | 0.4831 | 0.7570 | 0.8419 |
| liteparse | 0.9190 | 0.7804 | 0.8012 | 0.8804 |
| legacy_router | 0.8589 | 0.0000 | 0.0000 | 0.5705 |

## Speed (per doc)

| engine | median ms | p90 ms | elapsed_per_doc (s) |
|---|---|---|---|
| pdftotext | 13.6 | 15.3 | 0.014 |
| opendataloader | 237.2 | 288.0 | 0.243 |
| liteparse | 676.9 | 1667.9 | 0.703 |
| legacy_router | 16.6 | 18.5 | 0.293 |

## JVM-free deploy footprint

- **pdftotext**: poppler binary; no JVM, no runtime deps.
- **liteparse**: self-contained manylinux wheel (PDFium+tesseract compiled in); **no JVM**.
- **opendataloader-local**: Python SDK wrapping a Java JAR; **requires Java 11+** (JVM spawn per convert()).
