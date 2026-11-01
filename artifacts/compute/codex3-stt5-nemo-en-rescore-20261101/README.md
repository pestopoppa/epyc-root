# CS-8.STT5 Nemotron English validation offline rescore

The original validation receipt and PARTIAL filing (`8157690fd`) remain unchanged. The original scorer caller incorrectly treated the generic taxonomy check's categorical FAIL as invalid taxonomy. The repaired caller checks completeness and counts independently, retains the check's outcome and reasons, and computes the STT5 campaign's predeclared deletion-inclusive validation WER using the pinned scorer normalization. Generic taxonomy/checker behavior is unchanged. This is selection-only; no P-STT-1 qualification, test verdict, or advancement is asserted. No original measurement warrant is inferred; the filed finding is a committed conclusion.

The plan (`research d1c7a8ffb`, SHA-256 `61722f4fa38bd4e50c1fc33a94e82f1ed3af414cbaaa1feb27dc12ababc71533`) specifies all cases, with a known failed utterance counted as full deletions. The generic checker reason says failures are not WER contributions in its generic aggregation; the separately labelled campaign metric follows the explicit STT5 plan while preserving categorical FAIL. WER is lower-better. The declared test comparison baseline is production whisper.cpp large-v3-turbo f16 in matching language mode; no paired baseline result is included here, so no comparison is claimed.

The re-run verified all 1,580 original chunk exposures/results and bindings across 394 utterances per setting. All 1,580 process return codes were 0; one R6 chunk had an empty emitted hypothesis, classified as a decode error, and its utterance is scored as full deletions. The receipt index hashes each original exposure and result; the input reader also verifies source, manifest, chunk, stdout/stderr/text bindings. Original native files remain in the run's scratch root. Only derived scores, hashes and source are filed here, not raw transcripts.

| Right context | v1 WER % | 95% bootstrap interval % | correctness |
| --- | ---: | ---: | --- |
| R0 | 9.886 | 8.616–11.174 | PASS |
| R1 | 9.243 | 8.080–10.458 | PASS |
| R6 | 8.819 | 7.735–9.940 | FAIL: one decode error |
| R13 | 8.358 | 7.306–9.447 | PASS |

Each cell includes 394 utterances. v2-candidate is separately reported in `validation-score.json`; it is not pooled or differenced with v1. Every setting's normalizer route is COULD_NOT_CHECK (43–44 numeral_uncovered and 26 unknown_marker utterances), and repetition checking is COULD_NOT_CHECK because no validation-derived envelope was supplied. Bootstrap uses 4,000 resamples, seed 146064415. No model was loaded or inference run.

`score_validation.patch` applies to the original caller (SHA-256 `f1de4b8b797ca5ef1d7d4db7c16739f02942ae428233a365b3192095e9c87e69`); `score_validation_rescore.py` is the exact executed version, differing in input/output paths to preserve original files. `test_rescore.py` exercises a real decode-error row, its full deletion and categorical failure, a passing case, and malformed taxonomy counts. `run-summary.log` records the successful bounded regression and rescore (R6 fallback 122–123, 5.501 s, sampled peak 52,744,192 B, rc0, drained). Earlier fixture and receipt-count assertion refusals are retained in their logs and did not alter the original run. `native-receipt-index.json` contains 1,580 input receipt hashes and hashed clip locators, and `SHA256SUMS` binds the published files. Per-utterance derived outputs and raw text remain in private scratch, not this publication.
