# P-DOCPARSE-1 (DRAFT, operator 2026-11-07 "Ratify + Re-run") — document-parser comparison protocol

Status: DRAFT annex text for MEASUREMENT.md Annex Q. The measurement trust boundary is human-amendment-only; this file is
NOT ratified by its presence here. Until the operator ratifies it, the row that uses it produces an OBSERVATION graded under
the current claim grammar, and no adoption/routing change follows from it.

- **Question**: does LiteParse-local beat OpenDataLoader-local (and the orchestrator's original pdftotext+quality-gate router)
  as the born-digital PDF fast path on structure fidelity, at no latency cost?
- **Instrument**: the 200-PDF OpenDataLoader benchmark corpus (`/mnt/raid0/llm/opendataloader-bench-upstream`, git
  7af1d8f4d0c09f51ea1a5c6ba5f66e993286d109, clean tree), ground-truth markdown, upstream evaluator (NID reading order, TEDS
  table fidelity, MHS heading fidelity; overall = mean of available components per document). All HIGHER = better.
- **Arms** (all CPU, no model inference): `pdftotext` (poppler -layout), `legacy_router` (orchestrator ORIGINAL
  `PDFRouter` fast path: pdftotext + entropy/garbage/word-length quality gate; the LightOnOCR leg is NOT exercised, flagged
  documents are scored on their pdftotext text and listed), `opendataloader` (opendataloader-pdf==2.5.0, table_method=cluster),
  `liteparse` (liteparse==2.12.0, markdown output).
- **n**: 200 documents, paired by document id. Failed or empty prediction => the run FAILS CLOSED (no partial score).
- **Primary comparison**: per-document `overall`, LiteParse minus OpenDataLoader. Paired bootstrap, 10,000 resamples of
  documents, seed 20261107, 95% percentile interval.
- **PRECOMMITTED DECISION RULE** (written before the run):
  - **ADOPT** LiteParse as the born-digital fast path iff the LOWER bound of the 95% interval of (LiteParse - ODL) overall is
    > 0 AND LiteParse median per-document latency <= ODL median latency.
  - **REJECT** LiteParse iff the UPPER bound is < 0.
  - Otherwise **NO DECISION** and the routing default stays unchanged.
  - The other pairs (LiteParse/ODL vs pdftotext, legacy_router vs each) are DESCRIPTIVE; they decide nothing.
- **Scope of any ADOPT**: born-digital documents of this corpus only. It does not authorise routing complex, dense-table or
  scanned documents to LiteParse (that stays a separate, handoff-owned policy), and it is not a promotion or deployment.
- **Claim tuple to carry**: corpus manifest sha256 (out/run/corpus.sha256 incl. evaluator sources), engine versions, orchestrator
  commit f92a89b80794d4a3d640031070c693a11c075a16, research commit b839143bb, raw per-document predictions and latencies
  (kept in the row's out/run/prediction), the interval, n, seed.
- **Latency caveat**: single-process sequential per-document wall time on one CPU quarter; JVM spawn per ODL convert() is
  included by design (it is the deployed cost). Latency is a gate only in the ADOPT clause.
