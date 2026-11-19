# frontier-lab-automation (EVL-29) closeout notes, 2026-11-07

## AFC-P5.E5: compression savings in WORDS (live tree, `wc`)

Baseline `agents/shared/ENGINEERING_STANDARDS.md`: 735 words, 103 lines.

| level | words | word delta | lines | line delta |
|---|---|---|---|---|
| mild | 674 | -8.3% | 104 | +1.0% |
| medium | 545 | -25.9% | 101 | -1.9% |
| aggressive | 421 | -42.7% | 94 | -8.7% |

A line-denominated target under-finds by 4-10x here (intake-1199#record: CLAUDE.md is 96.5th percentile by words, 85.4th by lines). The earlier 1.6/20/39% table predates the AFC-P6 restructure. Evidence grade: observation of tracked files.

## AFC-P5.E3: re-planned on the current roster

The 2026-07-30 campaign script targeted gemma4-26B, Qwen3-Next-80B and Qwen3.5-122B (three of four GGUFs are gone) and the v9 in-tree build. It is replaced by three quarter-shape rows on the v10 kernel store: Qwen3.6-35B-A3B-MTP-Q8_0, Qwen3.8-27B-Q8_0, Qwen3.8-Flash-Next-UD-IQ4_XS.
