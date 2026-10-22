# 2026-10-22 — VB-SPEECH-LISTEN-1 wired (coordinator 3c4ca599, no inference)

- New adapter `scripts/vidya/adapters/speech_listen_rating.py` (source `speech-listen-rating`), registered in `ingest_sources.py` and `cli.py` `_FILE_SOURCES`. Projection only; `claim_tuple.grade()` decides; empty `protocol_id` (observation); rater label and rating-docs/kit-manifest sha256 in `extra`.
- One tuple per metric: naturalness mean (higher_better), intelligibility rate (higher_better), five per-category error counts (lower_better). The WER cross-check is not projected (same clips, not independent). The record is re-derived (mean, rate, counts, n) before projection; non-re-deriving records are refused.
- Reusable: any `epyc.<item>_listen.v<N>` aggregate of the same shape projects unchanged (post-normalizer re-listen).
- Tests: `tests/vidya/test_speech_listen_rating_adapter.py` (4 passed).
- Ingested `cs8l-italian-listen-20261022.json` into the canonical ledger: 7 rows, 21 frames, all Judged.
- Ticked VB-SPEECH-LISTEN-1; README row updated.
