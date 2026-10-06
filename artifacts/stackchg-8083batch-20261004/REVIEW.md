# Coherence bring-up review (nodraft base vs dflash2 cand, :8083 greedy)
Overall gate: PASS (4 NEEDS_REVIEW: 4 EQUIVALENT, 0 CAND_WORSE, 0 BASE_WORSE). 20/24 byte-identical.

| item | first divergence (char) | class | reason |
|---|---|---|---|
| bcb_BigCodeBench/547 | 113 | EQUIVALENT | both valid, coherent code; base adds docstring and hashes salt+pw, cand is terse and prepends salt to the digest (arguably more correct); no degeneracy |
| ifeval_3456 | 45 | EQUIVALENT | both coherent 30+ item uppercase name lists with the *highlighted* pattern, differing names only (EMMA vs ELEANOR); neither is degenerate |
| ifeval_1481 | 114 | EQUIVALENT | both follow the SECTION 1/2 format with different jokes; same structure and substance |
| real_suite_v1_0003 | 390 | EQUIVALENT | same RAG/fine-tuning structure and content, phrase-level wording drift ("Best"/"Ideal", cost clause) |

Neither arm is truncated or looping (both finish at the same token budget or naturally; lengths 613/276, 320/317, 881/927, 989/979).
q38_t7 (20261005T121907Z): Correctness PASS, speed VALID. dflash2 35.74 tok/s vs nodraft 15.7; acceptance 0.5327; 0 drafting regressions; greedy identity 20/24 (same four items); graded answers 4/10 vs 4/10.
Decode-during-prefill (decode-during-prefill-20261005T121907Z.json): decoder1 solo 28.5 tok/s, decoder2 28.2 tok/s, both >= 20 (item 7 solo criterion MET). Verdict PASS, gap ratio vs fit 0.265, all checks true.
