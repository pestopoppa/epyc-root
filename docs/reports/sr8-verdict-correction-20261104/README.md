# SR-8 verdict classification correction

`sr8-bep-lookup-gpu-sealed-20261104` ended rc1; native RESULT is UNKNOWN with one completed arm and missing or ambiguous per-request speculation statistics. The predeclared rule maps incomplete or failed evidence to UNKNOWN. The original filing used `fail` and produced `SCIENCE-VERDICT`, although its rationale explicitly said UNKNOWN. That classification is corrected to inconclusive / partial verdict; both the original verdict and original FILED text are retained here. There is no paired speed ratio, keep/decline or routing conclusion.

The current SR-8 stop-on-futility rule forbids extending the original packet after invalid or incomplete capture. Any future test requires a separately frozen protocol and appropriate fresh inputs; the old evidence is not relabeled.
