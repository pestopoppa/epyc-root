# Pseudonymization note (2026-11-09)

This directory is a copy of the PIP-04 ODL-013 r2 evidence (run 2026-11-07, raw dir
`/mnt/raid0/llm/tmp/pip04-odl013-rerun-r2-20261107/out`) in which the **200 benchmark document IDs**
(14-digit strings of the form `0103...`, the file stems of the corpus PDFs) were replaced so that the
PII hook's 12-19-digit rule does not fire on them and the IDs are not committed.

- Replacement: each ID `X` became `doc-` + the first 16 hex characters of `SHA-256(X)` (UTF-8, no salt).
  The replacement is applied consistently across every file and every occurrence, including the paths in
  `corpus.sha256`, so rows still join across files and arms. 200 IDs, 4,711 substitutions, 0 originals left.
- The id mapping is NOT in git. It is kept at `/mnt/raid0/llm/tmp/pip04-odl013-idmap-20261109/idmap.json`
  (mode 0600). Because the scheme is unsalted, anyone who already holds the original ID list can recompute
  the mapping; the scheme hides nothing from them and is a hygiene measure, not a secrecy guarantee.
- Hashes: the sha256 values in `corpus.sha256` (source PDFs and ground-truth files) are unchanged and refer to
  those source files. The per-file digests in `SHA256.json` bind the **original** (pre-pseudonymization)
  copies and the files under `raw_dir`; they do NOT match the bytes committed here. Verify against the
  originals in `raw_dir`, or re-derive the committed bytes by applying the mapping above to the originals.
- Everything else (scores, CIs, verdict `NO_DECISION_DEFAULT_UNCHANGED`, arm summaries) is byte-for-byte
  the original apart from the ID substitution.
