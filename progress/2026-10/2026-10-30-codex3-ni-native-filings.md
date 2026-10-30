# 2026-10-30 — NI native diagnostic filings

## LFMI native worker_general suite-origin diagnostic

`codex-ni-wg-lfmi-quality-native-r1-20261030` ended rc0 with 211 distinct cases × two canonical LFM2.5-1.2B quants, 512 token cap. Q4_K_M: **55 correct, 77 incorrect, 79 unknown**; Q8_0: **50 correct, 80 incorrect, 81 unknown**. Existing pinned official scorer (SHA256 `3209635449516793fdf7e4904fcbe389bbf92b971ed415b9ba4c47c9af8ad94e`, app `4cd6622f37079f44477ed3f138cc99639ef71685`) is source-identical. Unknown precedence is absent-context 7, unsupported scorer 36, cap 36/38; no transport or cutoff unknowns, 0 unattempted of 422. Unsupported/absent context can overlap the cap in the raw responses. Arithmetic is separate: Q4 4/1/28, Q8 2/1/30, each out of 33. Suite labels overlap, so suite denominators must not be summed. Higher correct count is better within supported suites; no quality threshold was declared. Captured prompt arguments do not reconstruct original server-side wire/system context and are not a representative organic-traffic sample. No timing, promotion, parent quality or WG-LFMI-3 claim. All 422 request and response files were verified present; source manifest hashes pass. [belief: cc]

| Suite | Q4 correct / incorrect / unknown | Q8 correct / incorrect / unknown |
|---|---:|---:|
| agentic | 6/2/0 | 6/2/0 |
| aime | 0/0/3 | 0/0/3 |
| aime25 | 0/0/3 | 0/0/3 |
| bigcodebench | 0/0/4 | 0/0/4 |
| coder | 5/1/0 | 5/0/1 |
| cruxeval | 0/5/1 | 0/5/1 |
| debugbench | 1/4/3 | 1/5/2 |
| general | 8/8/0 | 8/8/0 |
| gpqa | 5/12/0 | 5/12/0 |
| gpqa_diamond | 3/9/0 | 3/9/0 |
| gpqa_diamond_cot | 1/0/8 | 1/1/7 |
| hotpotqa | 0/0/7 | 0/0/7 |
| instruction_precision | 0/0/6 | 0/0/6 |
| long_context | 8/2/0 | 8/2/0 |
| longcot_mini | 0/0/3 | 0/0/3 |
| math | 4/1/4 | 2/1/6 |
| mmlu_pro | 4/10/0 | 5/9/0 |
| mode_advantage | 2/3/6 | 1/3/7 |
| mode_advantage_hard | 0/0/6 | 0/0/6 |
| olympiadbench | 0/0/5 | 0/0/5 |
| omniscience | 0/9/0 | 0/9/0 |
| physics | 0/0/9 | 0/0/9 |
| physreason | 0/0/1 | 0/0/1 |
| real_suite_v1 | 2/2/5 | 2/2/5 |
| ruler | 0/3/0 | 0/3/0 |
| scoring_verifiers | 4/7/0 | 3/8/0 |
| simpleqa | 0/2/0 | 0/2/0 |
| skill_transfer | 1/2/0 | 1/2/0 |
| thinking | 4/4/0 | 4/4/0 |
| usaco | 0/0/9 | 0/0/9 |
| web_research | 2/1/0 | 0/3/0 |
| zeroscrolls | 0/1/0 | 0/1/0 |

## G11 graph fidelity diagnostic

`codex-ni-kbrag-g11-parity-r2-20261030` completed all 200 frozen real KB chunks in query and document roles across four pinned graphs. Existing 70 K7 certification queries vs 200 docs are the primary ranking set. Exact top-1 FP32–INT8: mirror **59/70**, upstream **59/70**; same-precision mirror vs upstream: **70/70** FP32, **70/70** INT8. Both quantization pairs fail the declared 100% agreement. Separate self-containing 200-chunk rankings: **200/200** for each of all four pairs. Each of 12 role/pair groups has its full 200/200 or 70/70 items; 1,880 pair records, no missing, shape or transport failures. No retrieval-quality or B6 swap claim follows.

For each FP32–INT8 pair, per-token cosine min/p01/p50/p99/max and max absolute delta (higher cosine, lower maxabs = closer):

| Role (items; tokens) | Cosine min / p01 / p50 / p99 / max | Maxabs | Ratio / delta vs 0.00660 |
|---|---|---:|---:|
| Query (200; 6,108) | .933490 / .964149 / .989331 / .999736 / .999819 | .141253 | 21.402 / +.134653 |
| Document (200; 41,323) | .871885 / .964658 / .990526 / .998323 / .999838 | .184379 | 27.936 / +.177779 |
| K7 query (70; 1,649) | .950022 / .969922 / .990376 / .999754 / .999809 | .091622 | 13.882 / +.085022 |

Same-precision mirror–upstream FP32 and INT8 each have maxabs 0 (ratio 0, delta −.00660); query cosine min/p01/p50/p99/max .999999821/.999999881/1/1.000000238/1.000000238, document .999999762/.999999881/1/1.000000238/1.000000238, K7 matches query. Values above 1 are floating-point rounding. The accepted 0.00660 is a reference, not an invented numeric same-order tolerance. Mirror and upstream have identical initializer payload multisets, not graph byte identity. Original upstream literal-prefix tokenizer IDs differ from declared role IDs and the serving guard remains a separate blocker. Input/output identities, full distributions, rankings, source/model pins and native files are retained at `/mnt/raid0/llm/tmp/codex-ni-kbrag-g11-parity-r2-20261030/`; source manifest hashes, per-item denominators, finite values and per-query top1 counts independently checked. [belief: cc]

Belief projection and planning-context canary remain open under existing source families; these are committed conclusions, not invented historical measurement warrants. Wiki candidates: worker model selection and KB-RAG fidelity, at the next requested compilation sweep.
