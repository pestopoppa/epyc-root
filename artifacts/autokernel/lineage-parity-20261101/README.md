# AutoKernel lineage detector parity, fixture-only

The offline detector follows the default line filtering and per-program recycled
count in [EvoReplay detect_cycling.py](https://github.com/ZIB-IOL/EvoReplay/blob/1773db16c589b0ab8d3c0453b607844d133ef05e/src/evo_replay/cycling/detect_cycling.py),
commit `1773db16c589b0ab8d3c0453b607844d133ef05e`. The retrieved upstream file
SHA-256 was `81c92db5b54b0f0811e77524dd7f74feadbc8c85996601f42f4675329cc0d565`.

A synthetic three-program cross-branch fixture was run against the unmodified
upstream function and the local analyzer under the bounded CPU supervisor. Before
this change upstream reported `(added, recycled) = (4, 1)` and local reported
`(4, 2)`; afterwards both reported `(4, 1)`. The focused suite
`tests/test_autokernel_lineage_diagnostics.py` passed 8 tests, including short
lines, numeric-only content, duplicate re-additions and same-iteration exclusion.

These are engineering controls, not measurements of an AutoKernel campaign.
The prospective authoring-bound source and outcome receipts required by
`VB-AK-LINEAGE` remain necessary; historical unbound patches are not admitted.
No edit-type labels or yields were inferred from this fixture.
