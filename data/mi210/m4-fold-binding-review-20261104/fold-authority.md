# M4 fold rule — authority (INF-22, M4-FOLD-RULE)

Ratified by: the operator, 2026-11-04 (signature = the commit that adds this file under `artifacts/operator/`).

## What it decides
Whether the M4 candidate (`--prefill-order srpf`; candidate `bc441f1a2`, one commit on champion C5 `c72ec82f5`)
folds into the champion. It is applied per backend by `scripts/champion/m4/fold_gate.py` to every current role.

## Metric
Aggregate decode tok/s per cell, **higher is better**. Per role, ratio = median(candidate) / median(baseline)
over the plan's ABBA pairs (even count, alternating launch order; operator 2026-11-04, option 2).

## Thresholds
| Backend | pass_ratio | fail_ratio | Evidence |
|---|---|---|---|
| gpu | 1.000 | 0.950 | M4-GPU-AA-NOISE: n=5 same-build A/A, mean 0.968, SD 0.025; fail = 1 − 2·SD. ABBA cancels the ~3 % second-arm bias. |
| cpu | 1.000 | 0.940 | Q38 recipe r3 within-cell noise ≈ ±3 % decode; fail = 1 − 2·0.03. No dedicated CPU A/A yet. |

- ratio ≥ pass_ratio on every role of a backend: PASS.
- any role < fail_ratio: FAIL (no fold).
- otherwise: INCONCLUSIVE (no fold; more pairs may be bound).

## Quality (required, all roles)
Greedy (temperature 0, fixed seed) outputs on the sealed prompt pool must be token-identical between arms.
M4 changes only prefill scheduling, so any divergence is a defect and FAILS the fold regardless of speed.

## Scope limits
Descriptive evidence outside the sealed plan never folds. Changing any threshold needs a new signed rule.
