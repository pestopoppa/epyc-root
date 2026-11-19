# PF1 EXP04 r6 bounded screen filing

This is the later r6 screen recorded by the main session on 2026-11-03 at 22:00Z, not a result of r3/r4/r5 grants. Those earlier attempts were separately filed inconclusive. The full raw 24-unit result, summary, completion report and 12 per-launch identity/placement proofs are retained here.

The existing operator amendment of 2026-11-03, recorded in mi210-serving-program.md PF1-EXP04-PLACEMENT, keeps CPU A0 strict at 40% maximum node share and records GPU skew as a covariate while requiring valid in-window capture and >= 90% RSS coverage. It explicitly repoints the diagnostic to C6 candidate 729599d69, build 10500. This is not a new amendment and C6 is not called production or a qualified champion.

The bounded pilot completed 24/24 valid units with complete capture and no run, residency or placement-proof failures. The disabled-control/A0 launch-paired median ratios are 0.9657 at 2048 and 1.0041 at 8192, within the predeclared ±10% screen. All arm/length samples, per-arm variance, per-cell durations and consumer coverage are in summary.json. Owner disposition: EXPAND the matrix. GPU samples have 99% RSS coverage; their skew is recorded, not claimed <=40%. CPU placement is 25% per node.

Limitations: CPU and GPU arms were collected in separate windows rather than interleaved per block. Treat these as indicative pilot observations and an operational expansion decision. They establish neither a final crossover threshold nor a best-recipe, current-serving, quality, or promotion verdict. The full matrix, confidence intervals and a later reversed-order holdout remain required. The older claim that the crossover is established below 2048 is not adopted here.
