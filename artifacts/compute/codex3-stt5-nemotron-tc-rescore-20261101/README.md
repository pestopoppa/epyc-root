# CS-8.STT5 Nemotron multilingual validation offline rescore

Selection-only results from the original 2026-11-01 FLEURS validation collection. This is not a test-set, baseline comparison, P-STT-1 qualification, advancement, or promotion result. Eight settings (R0/R3/R6/R13, each auto/forced) contain 1,437 utterances apiece: en 394, it 391, de 363, fr 289. Each setting has 1,448 native chunks. The native worker records identify 40 failed utterances across settings; known empty decoded outcomes count as full utterance deletions under the frozen plan and remain categorical correctness failures. In the audited first cell, those empty outcomes occurred with process rc=0; do not equate decode failure with process failure. No model inference was run.

The repaired caller matches the reviewed English rescore's taxonomy-repair AST: malformed counts still refuse; categorical FAIL remains explicit while the separately labelled campaign metric follows the predeclared deletion-inclusive rule. Original caller SHA-256 `b9f6beacc7efcf5273e4f77fff63b7d97ae33db5dbec19b721bc515ed30a467e`; repaired caller SHA-256 `f5c00f64988e52e8687148f09f545b09385a0a4c3e2eec3308ebd2c6de7b5f24`; source catalog SHA-256 `38ff90db7666e67d09a7192cd16c13941ddad2373f98f755be95bf42ff2f429c`; plan SHA-256 `61722f4fa38bd4e50c1fc33a94e82f1ed3af414cbaaa1feb27dc12ababc71533`, research commit `d1c7a8ffb`. Relevant pinned source and helpers matched their catalog after execution; the scorer checked its pinned scorer catalog and each native binding, output hash, chunk and input manifest during execution. The eight receipt indices bind 11,584 exposure/result pairs without including transcripts.

This table reports v1 campaign deletion-inclusive WER and percentile bootstrap CI (4,000 utterance resamples, seed 146064415); lower is better. Every v1 normalizer route is `COULD_NOT_CHECK` because of unknown markers and/or numeral-uncovered cases, and repetition checking is `COULD_NOT_CHECK` (no validation-derived envelope). These labels qualify all numbers below. `validation-score.json` also contains v2 candidate sensitivity values separately; never pool the normalizers.

| Context | Language mode | Language | n | WER % | 95% CI % | Categorical correctness |
| --- | --- | --- | ---: | ---: | --- | --- |
| R0 | auto | en | 394 | 14.410 | 12.779–16.097 | FAIL |
| R0 | auto | it | 391 | 8.323 | 6.976–9.829 | FAIL |
| R0 | auto | de | 363 | 12.578 | 10.950–14.376 | FAIL |
| R0 | auto | fr | 289 | 14.336 | 12.779–15.936 | PASS |
| R0 | forced | en | 394 | 13.234 | 11.740–14.792 | PASS |
| R0 | forced | it | 391 | 8.163 | 6.814–9.665 | FAIL |
| R0 | forced | de | 363 | 11.781 | 10.233–13.538 | FAIL |
| R0 | forced | fr | 289 | 14.366 | 12.803–15.940 | PASS |
| R3 | auto | en | 394 | 12.749 | 11.176–14.378 | FAIL |
| R3 | auto | it | 391 | 7.399 | 6.090–8.878 | FAIL |
| R3 | auto | de | 363 | 11.673 | 10.136–13.462 | FAIL |
| R3 | auto | fr | 289 | 13.404 | 11.859–14.996 | PASS |
| R3 | forced | en | 394 | 12.276 | 10.827–13.853 | PASS |
| R3 | forced | it | 391 | 7.342 | 6.042–8.843 | FAIL |
| R3 | forced | de | 363 | 10.972 | 9.467–12.699 | FAIL |
| R3 | forced | fr | 289 | 13.493 | 11.933–15.076 | PASS |
| R6 | auto | en | 394 | 12.033 | 10.565–13.592 | FAIL |
| R6 | auto | it | 391 | 7.000 | 5.748–8.462 | FAIL |
| R6 | auto | de | 363 | 11.080 | 9.543–12.860 | FAIL |
| R6 | auto | fr | 289 | 13.256 | 11.742–14.799 | PASS |
| R6 | forced | en | 394 | 11.875 | 10.466–13.420 | FAIL |
| R6 | forced | it | 391 | 7.069 | 5.804–8.527 | FAIL |
| R6 | forced | de | 363 | 10.945 | 9.371–12.728 | FAIL |
| R6 | forced | fr | 289 | 13.197 | 11.679–14.783 | PASS |
| R13 | auto | en | 394 | 12.482 | 10.861–14.234 | FAIL |
| R13 | auto | it | 391 | 6.898 | 5.648–8.335 | FAIL |
| R13 | auto | de | 363 | 10.364 | 8.874–12.079 | FAIL |
| R13 | auto | fr | 289 | 12.709 | 11.167–14.256 | PASS |
| R13 | forced | en | 394 | 11.451 | 10.068–12.963 | FAIL |
| R13 | forced | it | 391 | 6.818 | 5.575–8.276 | FAIL |
| R13 | forced | de | 363 | 10.256 | 8.738–12.021 | FAIL |
| R13 | forced | fr | 289 | 12.872 | 11.324–14.450 | PASS |

The score ran under the R4 supervisor on physical CPUs 30–31, OMP/BLAS threads 1, 54.80 s, sampled peak tree RSS 88,256,512 B, rc 0, children drained. The unchanged taxonomy regression passed under the same guard. An earlier invocation of the original script with `--help` (it has no help parser) ran outside this supervisor, created first-cell private derived outputs and stopped at the categorical failure check; those outputs are not the published scores. The repaired run wrote a separate output epoch; native input receipts were not altered.
