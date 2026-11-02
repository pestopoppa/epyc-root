# EffiBench-X pinned patch bundle

This bundle preserves the four patches from the canonical-solutions acceptance gate in
`epyc-inference-research` commit `0cf315c3`, artifact
`artifacts/effibench-x-acceptance-gate-20260812/`. The upstream source is
[EffiBench/EffiBench-X](https://github.com/EffiBench/EffiBench-X), Apache-2.0, at commit
`21b6668a49a342c843e679cc5ed16081064a5768`.

From the root of a clean checkout at that commit, verify and apply the patches in order,
substituting the absolute path to this directory for `BUNDLE`:

```bash
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
git apply --check "$BUNDLE"/patches/01-deprecated-openjdk-image.patch \
  "$BUNDLE"/patches/02-time-sleep-attributeerror.patch \
  "$BUNDLE"/patches/03-fail-open-to-zero-metric.patch \
  "$BUNDLE"/patches/04-is-passed-empty-output-fail-open.patch
git apply "$BUNDLE"/patches/01-deprecated-openjdk-image.patch \
  "$BUNDLE"/patches/02-time-sleep-attributeerror.patch \
  "$BUNDLE"/patches/03-fail-open-to-zero-metric.patch \
  "$BUNDLE"/patches/04-is-passed-empty-output-fail-open.patch
git diff --check
```

The four patches repair the Java image, the shadowed `time` module, failure-to-zero
measurement handling, and an empty-output correctness false pass. On 2026-11-02 they
applied cleanly to the pinned source; the combined diff SHA-256 was
`b87733644b59545737a3a50ce0a5350265a0b80680fd21cb8a09ee6fce6c6534`.

Use Python only, select the 308 problems with non-null release timestamps, and exclude
`leetcode_3264` and `leetcode_3451` from every model arm. The existing acceptance gate
found at least one passing canonical arm for 306 of 308; its timing was single-execution
and is not ladder-grade. The bundle is a reproducible source input: it does not implement
the dataset selection, run an evaluation, or establish a model score. The research gate
report contains the full method, mutation tests and limitations.

On 2026-11-02, the eight existing acceptance regression tests were rerun against the
reconstructed checkout in a disposable Python environment: **8 passed in 6.16 seconds**.
The test copy only changed the historical checkout path. This verifies those regression
cases; it does not rerun the canonical-solutions gate or replace a model-arm evaluation.
