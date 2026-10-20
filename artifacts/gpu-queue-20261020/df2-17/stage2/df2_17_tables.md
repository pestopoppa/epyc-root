# DF2-17 stage2: per-prompt tables (baseline = off_A)


## dflash_n7 (kind dflash, verify width 8): PASS 13/24, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| mbpp_0391 | PASS | None |  |  |  |  | 149/149 | 168 | False |
| mbpp_0303 | FAIL | 276 | 0.03219413757324219 | True | near-tie | <0.1 | 1600/1600 | 2035 | True |
| mbpp_0508 | FAIL | 154 | 0.005100250244140625 | True | near-tie | <0.1 | 173/172 | 175 | False |
| bcb_BigCodeBench/547 | PASS | None |  |  |  |  | 302/302 | 343 | False |
| bcb_BigCodeBench/512 | PASS | None |  |  |  |  | 523/523 | 546 | False |
| debugbench_flood-fill_cpp | PASS | None |  |  |  |  | 557/557 | 511 | False |
| leetcode_the-number-of-the-smallest-unoccupied-chair | FAIL | 221 | 0.010589599609375 | True | near-tie | <0.1 | 445/432 | 518 | False |
| ma_multi_015 | PASS | None |  |  |  |  | 379/379 | 420 | False |
| gsm8k_00739 | PASS | None |  |  |  |  | 307/307 | 322 | False |
| gsm8k_00115 | PASS | None |  |  |  |  | 596/596 | 637 | False |
| gsm8k_00041 | FAIL | 51 | 0.017665743827819824 | True | near-tie | <0.1 | 593/589 | 763 | False |
| gpqa_diamond_cot_5fd3fe9084c9 | FAIL | 262 | 0.0063152313232421875 | True | near-tie | <0.1 | 1600/1600 | 2059 | True |
| gpqa_diamond_cot_8116937b0ca6 | FAIL | 46 | 0.01541900634765625 | True | near-tie | <0.1 | 1600/1435 | 1995 | True |
| phybench_electricity_25 | FAIL | 359 | 0.0066547393798828125 | True | near-tie | <0.1 | 1600/1600 | 2137 | True |
| mmlu_pro_law_01532 | PASS | None |  |  |  |  | 2/2 | 7 | False |
| mmlu_pro_health_05883 | PASS | None |  |  |  |  | 2/2 | 7 | False |
| ifeval_3456 | FAIL | 375 | 0.01500701904296875 | True | near-tie | <0.1 | 636/654 | 1176 | False |
| ifeval_322 | PASS | None |  |  |  |  | 27/27 | 42 | False |
| ifeval_1481 | FAIL | 21 | 0.031005859375 | True | near-tie | <0.1 | 373/334 | 1001 | False |
| ifeval_1129 | PASS | None |  |  |  |  | 141/141 | 224 | False |
| real_suite_v1_0003 | FAIL | 229 | 0.013347625732421875 | True | near-tie | <0.1 | 1542/1519 | 2975 | False |
| real_suite_v1_0032 | FAIL | 7 | 0.02367401123046875 | True | near-tie | <0.1 | 53/57 | 70 | False |
| simpleqa_general_01814 | PASS | None |  |  |  |  | 68/68 | 168 | False |
| hellaswag_06230 | PASS | None |  |  |  |  | 2/2 | 7 | False |

## off_B (kind none, verify width 1): PASS 24/24, drafted-all=None

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| mbpp_0391 | PASS | None |  |  |  |  | 149/149 | None | False |
| mbpp_0303 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| mbpp_0508 | PASS | None |  |  |  |  | 173/173 | None | False |
| bcb_BigCodeBench/547 | PASS | None |  |  |  |  | 302/302 | None | False |
| bcb_BigCodeBench/512 | PASS | None |  |  |  |  | 523/523 | None | False |
| debugbench_flood-fill_cpp | PASS | None |  |  |  |  | 557/557 | None | False |
| leetcode_the-number-of-the-smallest-unoccupied-chair | PASS | None |  |  |  |  | 445/445 | None | False |
| ma_multi_015 | PASS | None |  |  |  |  | 379/379 | None | False |
| gsm8k_00739 | PASS | None |  |  |  |  | 307/307 | None | False |
| gsm8k_00115 | PASS | None |  |  |  |  | 596/596 | None | False |
| gsm8k_00041 | PASS | None |  |  |  |  | 593/593 | None | False |
| gpqa_diamond_cot_5fd3fe9084c9 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| gpqa_diamond_cot_8116937b0ca6 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| phybench_electricity_25 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| mmlu_pro_law_01532 | PASS | None |  |  |  |  | 2/2 | None | False |
| mmlu_pro_health_05883 | PASS | None |  |  |  |  | 2/2 | None | False |
| ifeval_3456 | PASS | None |  |  |  |  | 636/636 | None | False |
| ifeval_322 | PASS | None |  |  |  |  | 27/27 | None | False |
| ifeval_1481 | PASS | None |  |  |  |  | 373/373 | None | False |
| ifeval_1129 | PASS | None |  |  |  |  | 141/141 | None | False |
| real_suite_v1_0003 | PASS | None |  |  |  |  | 1542/1542 | None | False |
| real_suite_v1_0032 | PASS | None |  |  |  |  | 53/53 | None | False |
| simpleqa_general_01814 | PASS | None |  |  |  |  | 68/68 | None | False |
| hellaswag_06230 | PASS | None |  |  |  |  | 2/2 | None | False |

## serial_df7 (kind dflash, verify width 8): PASS 24/24, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| mbpp_0391 | PASS | None |  |  |  |  | 149/149 | 168 | False |
| mbpp_0303 | PASS | None |  |  |  |  | 1600/1600 | 2074 | True |
| mbpp_0508 | PASS | None |  |  |  |  | 173/173 | 182 | False |
| bcb_BigCodeBench/547 | PASS | None |  |  |  |  | 302/302 | 343 | False |
| bcb_BigCodeBench/512 | PASS | None |  |  |  |  | 523/523 | 567 | False |
| debugbench_flood-fill_cpp | PASS | None |  |  |  |  | 557/557 | 518 | False |
| leetcode_the-number-of-the-smallest-unoccupied-chair | PASS | None |  |  |  |  | 445/445 | 574 | False |
| ma_multi_015 | PASS | None |  |  |  |  | 379/379 | 420 | False |
| gsm8k_00739 | PASS | None |  |  |  |  | 307/307 | 322 | False |
| gsm8k_00115 | PASS | None |  |  |  |  | 596/596 | 637 | False |
| gsm8k_00041 | PASS | None |  |  |  |  | 593/593 | 770 | False |
| gpqa_diamond_cot_5fd3fe9084c9 | PASS | None |  |  |  |  | 1600/1600 | 1925 | True |
| gpqa_diamond_cot_8116937b0ca6 | PASS | None |  |  |  |  | 1600/1600 | 2107 | True |
| phybench_electricity_25 | PASS | None |  |  |  |  | 1600/1600 | 1985 | True |
| mmlu_pro_law_01532 | PASS | None |  |  |  |  | 2/2 | 7 | False |
| mmlu_pro_health_05883 | PASS | None |  |  |  |  | 2/2 | 7 | False |
| ifeval_3456 | PASS | None |  |  |  |  | 636/636 | 1162 | False |
| ifeval_322 | PASS | None |  |  |  |  | 27/27 | 42 | False |
| ifeval_1481 | PASS | None |  |  |  |  | 373/373 | 1169 | False |
| ifeval_1129 | PASS | None |  |  |  |  | 141/141 | 224 | False |
| real_suite_v1_0003 | PASS | None |  |  |  |  | 1542/1542 | 3024 | False |
| real_suite_v1_0032 | PASS | None |  |  |  |  | 53/53 | 77 | False |
| simpleqa_general_01814 | PASS | None |  |  |  |  | 68/68 | 161 | False |
| hellaswag_06230 | PASS | None |  |  |  |  | 2/2 | 7 | False |
