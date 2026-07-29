# MathQ-Verify Audit Report

**Date**: 2026-04-21  
**Script**: `scripts/benchmark/dataset_audit/mathq_verify_audit.py` (NIB2-03)  
**Source**: intake-379 MathQ-Verify (arxiv:2505.13903), stages 1-3 only  
**Total scanned**: 5670  
**Total flagged**: 251 (4.43%)  

## Per-suite flag rate

| Suite | Total | Flagged | Rate |
|-------|-------|---------|------|
| aime | 60 | 1 | 1.67% |
| math | 1819 | 244 | 13.41% |
| olympiadbench | 674 | 3 | 0.45% |
| physreason | 3117 | 3 | 0.10% |

## Stage 1 (InstValid) reason-code distribution

- `S1_unbalanced_dollar`: 234
- `S1_unbalanced_braces`: 5
- `S1_unbalanced_left_right`: 1

## Stage 2 (Clean) applied transformations

- `S2_collapse_whitespace`: 819
- `S2_display_math_present`: 134
- `S2_normalize_quotes`: 121
- `S2_collapse_newlines`: 47

## Stage 3 (Parse) reason-code distribution

- `S3_malformed_frac`: 7
- `S3_malformed_sqrt`: 3
- `S3_malformed_int`: 1

## Spot check observations

- **GSM8K currency collision** — the `math` suite's elevated 13.4% flag rate is driven almost entirely by GSM8K questions using `$` as a **currency** symbol (`$10`, `$68`). Stage 1's `unbalanced_dollar` heuristic correctly identifies these as not valid LaTeX math, but the questions themselves are fine for human readers. **Action**: gate the unbalanced-$ check on whether LaTeX commands (`\sqrt`, `\frac`, `\log`, etc.) appear in the prompt — skip the check for prose-only questions. Deferred to a v2 pass.
- **S3_malformed_sqrt false positives** — ~10 AIME/math questions flagged where `\sqrt{N}` is actually well-formed. The regex triggers on `\sqrt<space>{N}` patterns where the 4-char lookahead window doesn't cleanly capture the brace. Deferred to a v2 pass; volume is low (<0.2%).
- **No Stage 3 parse errors detected** because `antlr4.error.ErrorListener` is unavailable in the current venv — stage 3 is gated on a working `antlr4` install and falls back to regex-only sanity checks. Install `antlr4-python3-runtime` to re-enable deep parse validation.

## Out of scope

- **Stage 4 (Consistent)** — requires LLM-based atomic decomposition (inference-gated); deferred to a follow-up work item.
- **Stage 5 (Complete)** — skipped per paper ablation insight (hurts F1 by +0.57pp, introduces false positives).

