# C5-7 Counter-Gated Acceptance Source Seam

2026-10-31 — Added an opt-in counter acceptance seam at the terminal rankability
decision in `scripts/kernel_rnd/autokernel/controller/hip_decision_grade.py`.
An explicit pre-run expectation is written before measured GPU windows. When
declared, missing, malformed, mismatched, or wrong-direction counter evidence
blocks the speedup belief/decision; stable zero counter values remain valid,
and legacy runs without a declaration keep their existing behavior.

The seam hashes and parses the same bounded raw CSV snapshot, binds exact
counter/kernel/dispatch rows to candidate and anchor identities, workload,
campaign, unit, and normalization, and refuses ambiguous headers and unstable
files. Focused tests passed 19/19 under the model-free pair 34-35 lock with
OMP=1 and the 8 GiB/900 s guard; Python compilation and `git diff --check`
passed. Source commit: `39b63b061`.

This is a conditional source seam only. Its counter receipt and raw CSV are
caller-supplied; the runner does not capture or attest profiler output. No
native GPU capture, live activation, kernel deployment, or ClaimTuple grading
change occurred. C5-7 remains open for a broader native caller and an
end-to-end capture path.
