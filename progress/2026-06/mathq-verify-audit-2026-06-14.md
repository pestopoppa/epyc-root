# MathQ-Verify Audit Report

**Date**: 2026-06-14
**Script**: `scripts/benchmark/dataset_audit/mathq_verify_audit.py` (NIB2-03)
**Source**: intake-379 MathQ-Verify (arxiv:2505.13903), stages 1-3 only
**Total scanned**: 1819
**Total flagged**: 357 (19.63%)

## Per-suite flag rate

| Suite | Total | Flagged | Rate |
|-------|-------|---------|------|
| math | 1819 | 357 | 19.63% |

## Stage 1 (InstValid) reason-code distribution

- `S1_unbalanced_dollar`: 232
- `S1_unbalanced_braces`: 2
- `S1_unbalanced_left_right`: 1

## Stage 2 (Clean) applied transformations

- `S2_collapse_whitespace`: 460
- `S2_normalize_quotes`: 53
- `S2_display_math_present`: 18
- `S2_collapse_newlines`: 1

## Stage 3 (Parse) reason-code distribution

Toolchain: `sympy_parse_available`

- `S3_latex_parse_error`: 121
- `S3_malformed_frac`: 7
- `S3_malformed_sqrt`: 2

## Out of scope

- **Stage 4 (Consistent)** — requires LLM-based atomic decomposition (inference-gated); deferred to a follow-up work item.
- **Stage 5 (Complete)** — skipped per paper ablation insight (hurts F1 by +0.57pp, introduces false positives).

