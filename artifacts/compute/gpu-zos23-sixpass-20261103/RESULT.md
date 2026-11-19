# GPU-ZOS-2.3 six-pass §9.4 recompute (analysis only, 2026-11-03)

Inputs: `artifacts/compute/ni-gpu-zos23-r6-20261031/RESPONSE-PROJECTIONS.json` (A1,B1,A2,B2,A3,B3 x 24 prompts, `timings.predicted_per_second`, token identity via `token_sha256`). Rule: design `docs/design/gpu-zos-2-one-step-lag-design-20261024.md` §9.4. Script: `sixpass.py`; full numbers: `out.json`. No threshold was changed (E_min 1.0%, NF ceiling 1.85%, U = 3.71% + 2NF, SHIP needs S >= max(E_min, 2NF)).

Token identity: all 24 prompts token-identical across all six passes (0 excluded), so the 25% exclusion rule never bites.

Arm geomean tok/s: A1 21.497, A2 21.466, A3 21.298, B1 21.921, B2 21.357, B3 21.703.

## Generalisation
Two-pass equations: S = g(sqrt(B1B2)/sqrt(A1A2)) - 1; NF = max(|g(A2/A1)-1|, |g(B2/B1)-1|); alternation B1/A1, B1/A2, B2/A2.
Unambiguous part: S uses the per-prompt geometric mean over the 3 passes of each arm (sqrt -> cube root). Alternation extends along the run order A1 B1 A2 B2 A3 B3: B1/A1, B1/A2, B2/A2, B2/A3, B3/A3.
S (six-pass) = **+1.116%** (two-pass S was +0.725%).
Alternation: +1.973%, +2.122%, **-0.508%**, +0.277%, +1.903% -> NOT all the same sign as S (B2/A2 is negative), under every reading.

Ambiguous part: NF, since a within-arm noise floor with 3 repeats has no single two-pass form.
| Reading | NF terms | NF | Threshold max(1%,2NF) | Verdict |
|---|---|---|---|---|
| R1 consecutive-pass drift (A2/A1, A3/A2, B2/B1, B3/B2) | -0.146, -0.783, **-2.575**, +1.622 % | 2.575% | 5.15% | **INCONCLUSIVE** (NF > 1.85%, still underpowered after the one extension) |
| R2 max over all within-arm pass pairs (adds A3/A1 -0.927, B3/B1 -0.996) | same max | 2.575% | 5.15% | **INCONCLUSIVE** |
| R3 max |pass vs arm 3-pass mean| (weaker generalisation: deviation from a mean that contains the pass shrinks the estimate by ~2/3) | max 1.396% (B2) | 1.396% | 2.79% | **NULL** (|S| 1.116% < 2.79%, NF <= 1.85%) |

Under no reading is the verdict SHIP, SUSPECT or REGRESS: alternation fails, S < 2NF always, S > -2NF always.

## Verdict
Primary (R1/R2, which keep §9.4's own form "max of the within-arm repeat drift"): **INCONCLUSIVE**, exactly the clause "if it is still underpowered, the result is INCONCLUSIVE". The NF is set by B2/B1 = -2.575%, a pass pair that was already in the two-pass NF; adding passes cannot lower a max-over-pairs. B2 is the outlier pass (B2 arm geomean 21.357 vs B1 21.921, B3 21.703).
Alternate (R3): NULL. R3 is not a faithful extension of "|g(A2/A1)-1|" (it is a deviation-from-mean statistic), so it is reported but not adopted. Either way no ship and no speed claim: S = +1.12% is inside noise.
Not adopting a reading post hoc to flip the verdict is the point: the R1/R2 INCONCLUSIVE should stand unless the operator explicitly ratifies an R3-style NF.
