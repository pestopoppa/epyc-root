# STT5 baseline validation: offline scoring verdict

**INCONCLUSIVE**, selection only. Row `stt5-baseline-offline-score-r1-20261119` ended rc=0, reason=complete at 2026-11-19T13:43:51Z. All 32 declared cells were produced. This records a committed conclusion, not a retroactive measurement warrant.

Question: what does the plan-pinned scorer report for the retained frozen whisper large-v3-turbo / large-v3 forced/auto validation ledger, preserving unknowns? Lower WER is better. Scoring stopped after the declared cells; no inference was run or redrawn.

The figures below are **full-utterance deletion sensitivity**, including the references of exposed units with no result. Those units remain unknown, not observed decode errors. Intervals are the scorer’s 95% utterance-bootstrap intervals (4,000 resamples, seed 146064415); they do not resolve missing outcomes or qualify a correctness claim. Every cell has repetition_check=COULD_NOT_CHECK. All v1 normalizer contracts PASS; all v2 candidate contracts FAIL; normalizer properties PASS for both. Do not rank across normalizers, use v2 as a qualified score, or infer acceptance, test performance, advancement or promotion.

| Model | Mode | Norm | Lang | n | Reference tokens | Errors (sensitivity) | WER % (95% CI) | Unknown utterances / tokens |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| large | auto | stt_norm/v1 | de | 363 | 7410 | 355 | 4.791 (4.098–5.526) | 0 / 0 |
| large | auto | stt_norm/v1 | en | 394 | 8244 | 483 | 5.859 (4.966–6.760) | 0 / 0 |
| large | auto | stt_norm/v1 | fr | 289 | 6759 | 545 | 8.063 (6.809–9.391) | 0 / 0 |
| large | auto | stt_norm/v1 | it | 391 | 8771 | 257 | 2.930 (2.452–3.433) | 0 / 0 |
| large | auto | stt_norm/v2 | de | 363 | 7410 | 375 | 5.061 (4.335–5.829) | 0 / 0 |
| large | auto | stt_norm/v2 | en | 394 | 8241 | 477 | 5.788 (4.896–6.683) | 0 / 0 |
| large | auto | stt_norm/v2 | fr | 289 | 6644 | 359 | 5.403 (4.514–6.339) | 0 / 0 |
| large | auto | stt_norm/v2 | it | 391 | 8752 | 256 | 2.925 (2.445–3.434) | 0 / 0 |
| large | forced | stt_norm/v1 | de | 363 | 7410 | 349 | 4.710 (4.047–5.403) | 0 / 0 |
| large | forced | stt_norm/v1 | en | 394 | 8244 | 482 | 5.847 (4.950–6.753) | 0 / 0 |
| large | forced | stt_norm/v1 | fr | 289 | 6759 | 545 | 8.063 (6.809–9.391) | 0 / 0 |
| large | forced | stt_norm/v1 | it | 391 | 8771 | 255 | 2.907 (2.430–3.411) | 0 / 0 |
| large | forced | stt_norm/v2 | de | 363 | 7410 | 369 | 4.980 (4.282–5.703) | 0 / 0 |
| large | forced | stt_norm/v2 | en | 394 | 8241 | 476 | 5.776 (4.883–6.676) | 0 / 0 |
| large | forced | stt_norm/v2 | fr | 289 | 6644 | 359 | 5.403 (4.514–6.339) | 0 / 0 |
| large | forced | stt_norm/v2 | it | 391 | 8752 | 254 | 2.902 (2.424–3.404) | 0 / 0 |
| turbo | auto | stt_norm/v1 | de | 363 | 7410 | 389 | 5.250 (4.511–6.098) | 1 / 16 |
| turbo | auto | stt_norm/v1 | en | 394 | 8244 | 523 | 6.344 (5.398–7.330) | 0 / 0 |
| turbo | auto | stt_norm/v1 | fr | 289 | 6759 | 648 | 9.587 (8.090–11.116) | 2 / 42 |
| turbo | auto | stt_norm/v1 | it | 391 | 8771 | 257 | 2.930 (2.453–3.430) | 0 / 0 |
| turbo | auto | stt_norm/v2 | de | 363 | 7410 | 408 | 5.506 (4.718–6.363) | 1 / 16 |
| turbo | auto | stt_norm/v2 | en | 394 | 8241 | 517 | 6.274 (5.335–7.269) | 0 / 0 |
| turbo | auto | stt_norm/v2 | fr | 289 | 6644 | 468 | 7.044 (5.886–8.352) | 2 / 42 |
| turbo | auto | stt_norm/v2 | it | 391 | 8752 | 260 | 2.971 (2.488–3.477) | 0 / 0 |
| turbo | forced | stt_norm/v1 | de | 363 | 7410 | 373 | 5.034 (4.387–5.725) | 0 / 0 |
| turbo | forced | stt_norm/v1 | en | 394 | 8244 | 523 | 6.344 (5.398–7.330) | 0 / 0 |
| turbo | forced | stt_norm/v1 | fr | 289 | 6759 | 613 | 9.069 (7.812–10.384) | 0 / 0 |
| turbo | forced | stt_norm/v1 | it | 391 | 8771 | 255 | 2.907 (2.436–3.405) | 0 / 0 |
| turbo | forced | stt_norm/v2 | de | 363 | 7410 | 392 | 5.290 (4.598–5.999) | 0 / 0 |
| turbo | forced | stt_norm/v2 | en | 394 | 8241 | 517 | 6.274 (5.335–7.269) | 0 / 0 |
| turbo | forced | stt_norm/v2 | fr | 289 | 6644 | 433 | 6.517 (5.595–7.486) | 0 / 0 |
| turbo | forced | stt_norm/v2 | it | 391 | 8752 | 258 | 2.948 (2.467–3.456) | 0 / 0 |

Each setting retains 1,437 utterances (en 394, it 391, de 363, fr 289). The three distinct unknowns affect turbo auto only: de one utterance / 16 reference tokens; fr two / 42. Counts repeat across normalizer columns; they are not six distinct missing outcomes.

- turbo auto de_de: `88d4febaf9ef68196bcec3e6522a2a67c193d4cbd21a9b0a8479e2899192fd3e`.
- turbo auto fr_fr: `e47c18fbd6c33d7da58a3b2f751050472e4b6d3a5ac5b9350841a9cb57a2ca4d`.
- turbo auto fr_fr: `8c49fa215b0d11678e3f644bf312a17b1e2585dd7bfb72f527c22c2c27fef83f`.

Exposure widths remain mixed: 24 threads = 2,613, 32 = 3,140, 8 = 39. These are cumulative chunk exposures; neither a uniform-width experiment nor timing comparability is established. Prior CPU-configured, unfenced windows retain their original device limitations.

## Evidence identities

- Native result: `/mnt/raid0/llm/tmp/stt5/baseline-score-20261119/score-output/validation-score.json`, SHA-256 `97157ba351b44087fb63082cc63c04e07386cb0382586283f9b0ff85d9503442`.
- Research source git `99301fa149af86a6f9743d2b0405c9234ba39586`, `scripts/speech/stt_bakeoff/scorer.py` SHA-256 `83f9cbba8485ca34d70801af54d77e077a6adb7a967601dd9405720d7be39bc7`.
- Root scoring wrapper: `scripts/speech/stt5_score_baseline.py` at git `f78fae2c96fca5127b8e23da4dc8b0a349163c4f`.
- Config SHA-256 `698162543a60c2a042fd0c20e48a6e40bc266bec36432d55c81c93cd61f7666a`; prepared native ledger digest `cac12c83cbc707a4e556b59e2e2a393471caa4803219db86c213ae018f76c55d` over 30,393 files.
- Collection provenance and original runner/plan/input identities: [r6 collection report](stt5-baseline-r6-validation-20261119.md).

No source, log or binary was copied into this report. Existing VB-SPEECH-STT5-RAW and canonical STT scorer registrations cover the source; no new grading ladder. The parent CS-8.STT5 remains open for remaining arms and the test screen. Filing does not tick that parent. Preserve the external native ledger; reclamation belongs to the keeper.

Next: review the held Crisp matched-weight runtime packet and restore/rebind its missing runtime inputs before publishing a fresh STT5 validation successor; preserve prior exposure custody and use the publisher smoke.
