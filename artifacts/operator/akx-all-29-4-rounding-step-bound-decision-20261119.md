# AKX-ALL-29.4 decision package: type-relative rounding-step bound for fp16/bf16 outputs

Prepared 2026-11-19 by the AutoKernel session. PREPARE ONLY: the correctness gate is a MEASUREMENT
trust-boundary item (human-amendment-only); nothing here changes a gate, a tolerance or a mode.

## Context

The GPU/CPU op correctness gate projects every `test-backend-ops` case into
`ReferenceComparison(mode="metric_bounded", metric_id=test_backend_ops_error/v1)` and fails a case when
`max_error_observed > tolerance_error` (provider `execution/t0_provider.py`, evaluator
`evaluator/correctness.py` `check_exact_reference_comparison`). The default tolerance is NMSE 1e-7
(`test_case::max_nmse_err`). There is no per-output-dtype branch.

AKX-ALL-29.4 asks whether a type-relative bound, `sqrt(error_power / step_power) <= alpha`, where
`step` is the rounding step of the output dtype at the output RMS, should be ADDED next to NMSE.
Falsifier: the bound gives the same verdict as the current gate on every recorded candidate.

Evidence (receipt-based, offline, `ak2904_rounding_step_compare.txt` beside
`/mnt/raid0/llm/tmp/gpu-staged-20261020/runs/akx2905-20261020T234212Z/`; 6003 receipts, 325 fp16/bf16):

- NMSE 1e-7 already demands sub-step agreement: `alpha_equiv` = 0.36-0.63 steps (f16), 0.042-0.057 steps
  (bf16). f32 outputs are 2.6e3-5.3e3 steps, so a step bound is irrelevant there.
- All 5771 supported cases passed NMSE. Pass-to-pass on the 325 fp16/bf16 receipts is identical for any
  alpha >= 0.64.
- NOT decidable from recorded data: fail-to-pass and alpha < 0.64, because the receipts carry output RMS
  but no observed error (the run used no `--autokernel-properties`, so no `AK_REF_V1`).
- Composition matters. An ADDITIONAL check ANDed with NMSE can only tighten (never admits anything NMSE
  rejects), so at alpha >= 0.64 it is vacuous on every recorded case. Only an OR/relaxation (a step bound
  that REPLACES NMSE for f16/bf16) can change a verdict toward pass.

## Question for the operator

Should the gate gain a step-relative check for fp16/bf16 outputs, and in which composition?

## Options

1. Close as "no change": NMSE already demands sub-step agreement for fp16/bf16. Zero risk, zero work.
   Cost: if a legitimate fp16/bf16 reformulation (reduction reorder) differs by one rounding step it is
   refused with no way to tell a one-step rounding difference from a real defect.
2. Adopt the step bound as an AND check (alpha 1.0). Cost: adds a code path and a ratification for a
   check proven vacuous on all 325 recorded fp16/bf16 receipts. No benefit demonstrated.
3. Adopt the step bound as a RELAXATION for fp16/bf16 outputs only (alpha 1.0, replaces NMSE there).
   Benefit: stops false refusals on one-step rounding differences. Cost: loosens a correctness gate by up
   to ~1.6x (f16) and ~17x (bf16) in error amplitude; admits one-step differences NMSE rejects; no
   observed-error data exists to show what it would newly admit.

## Recommendation

Option 1 now, plus a zero-risk record-keeping step that makes the question decidable: re-run the
fp16/bf16 guard-band case set once WITH `--autokernel-properties` so `AK_REF_V1` observed/tolerance sit
beside the already-recorded `output_dtype`/`output_rms`; then decide Option 3 only if a real candidate was
refused by NMSE at <= 1 step. The write side (`loop/gates.py` `case_records`, research `ed059b186`) already
persists observed/tolerance for every future gated case, so new candidates accumulate the data without any
change. No ratify script is needed for Options 1 or the record step; Option 3 would need the usual
MEASUREMENT amendment script.
