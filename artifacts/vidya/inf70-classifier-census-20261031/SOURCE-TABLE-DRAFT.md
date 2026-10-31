# Draft amendment for MAIN — existing INF-70 source row only

Target the existing `INF-70 serving-harness arm records` row in `scripts/vidya/adapters/README.md`; do not add a source family or ladder. Add a short write-side clarification to the existing row:

> The maintained client declares classifier identity `inf70-classify.v1` and writes `token_source="synthetic-ids(uniq/top/run vacuous)"` for the synthetic `list(range(npred))` input used by the classifier; the existing SC75 producer census preserves both exact values. Missing/malformed fields stay `UNREPORTED`. This is provenance only: verdict rules, shared `ClaimTuple.grade()`, and the existing one-ladder-per-source-class contract are unchanged. No historical records are reconstructed. The code is at root `fc5688b802491af08243f57d2812937bcc3efa56`; original acceptance still needs a future genuine producer sidecar and `inf70-arms` ingest.

This is a prepared text fragment only. MAIN owns source-table and handoff edits.
