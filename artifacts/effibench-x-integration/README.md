# EffiBench-X acceptance-gated preparation

This reproducible integration pins upstream `EffiBench/EffiBench-X` at
`21b6668a49a342c843e679cc5ed16081064a5768` (Apache-2.0) and carries the four
patches and DATED cohort from the canonical-solutions acceptance gate in
`epyc-inference-research/artifacts/effibench-x-acceptance-gate-20260812/`.
It does not run inference or establish model scores.

1. Check out that upstream commit in a **separate clean checkout** and run
   `./artifacts/effibench-x-integration/apply-patches.sh CHECKOUT` from the root.
2. Export the `test` split of `EffiBench/effibench-x` as a JSON array, preserving
   all fields. Run `python3 artifacts/effibench-x-integration/prepare.py EXPORT.json NEW_DATASET_DIR`.
   It fails closed unless the non-null `release_timestamp` records match the
   exact 308 acceptance-gate problem identifiers, then emits 306 individual
   JSON files, excluding `leetcode_3264` and `leetcode_3451`. Set the upstream
   harness dataset path to that directory and run **Python only**.

The identifier check fixes the cohort, but does not authenticate dataset row
contents: record the dataset revision and content digest for every model run and
verify them against the intended source before measuring. The acceptance gate
used single-execution timing, which is not ladder-grade. The working scoring
convention and its unratified status are in the handoff; the upstream acceptance
report describes the two exclusions and four patches. A model-arm protocol,
content pin, and decision-grade timing remain necessary before a ranking run.
