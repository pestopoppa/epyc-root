# MI210 row verdicts — 2026-11-04

The row owner filed all 14 pending terminal events using file_result.py. Each row directory preserves its original manifest, end marker, available result, explicit interpretation and filed verdict. Historical shared result paths were overwritten; snapshots named native-result.json for the PF1 and memory-replay lineages are later shared output, **not attributable to those attempts**. Their verdicts use the matching archived attempt summary or original failure evidence. See each verdict-input.json for precise scope and evidence hashes.

| Scope | Filed result | Interpretation |
|---|---|---|
| PF1 EXP04 r3/r4/r5 | inconclusive | REVISE the harness: 4/8, 2/8 and 1/2 valid units respectively. Neither expansion nor PF1 rejection follows. |
| M4 A/A np4 r8 | pass for capture completion | A1 136.7283, A2 131.2162 tok/s; ratio 0.959686. Eight 256-token successes and overlapping own-PID residency per arm. No acceptance threshold or fold decision. |
| E1 A0 low 2026-11-02 | pass for historical capture | Smoke and 128k/240k phases complete. Peak 37.132 GiB. A0 capture alone does not close A1 memory attribution. |
| E1 memory r2/r3/r4/r5 | inconclusive | r2 missing input, r3 wrong-image preflight, r4/r5 stopped. Later shared COMPLETE is not a result of these grant intervals; split groups do not cover a continuous A1 chain. |
| Q38 recipe r1/r2/r3 | inconclusive | Refusal, signal, and stop-before-start respectively; declared native results absent. A separate bare run does not satisfy the sealed comparison. |
| Q38 custody r1 | inconclusive | Signalled; no custody result. |
| Q38 custody r2 | pass for custody only | Four receipt hashes and a sealed-plan hash. measurement=false, shared host, no timing or best-recipe conclusion. |

Higher decode throughput is better; higher VRAM is worse. No new inference, production change, quality conclusion, or promotion is represented by these filings. Scientific parent boxes remain open wherever their completion criteria were not met. The independently completed M4 descriptive A/A box can close.
