# AutoKernel hardening — 2026-09-15

## Integrity, abstention and dispatch checkpoint

Reviewed the AutoKernel hardening series through research `bada71c2` against the exact acceptance text
in the active handoffs. A zero-compute targeted run passed 171 tests with the repository root and
`scripts/kernel_rnd` on `PYTHONPATH` and `TMPDIR` on `/mnt/raid0`.

- Closed S3-AKU-15 and its mirrored AKX-P2-PRE: full dirty-set validation, protected oracle/bench paths,
  typed pre-build refusal, and measured-tree/kept-commit identity are wired and tested.
- Closed S3-AKU-16: literal tensor-shape/type/op predicates and mutable hot-path state are screened;
  suspicious keeps require an unseen confirmation and retain the public-to-held-out speedup gap.
- Closed S3-AKU-18: proposal/author abstention is a science outcome, feeds future context, does not count
  as a transient, and contributes to the published per-run abstain rate.
- Closed R23-69 after adding canonical regime matching, changed-diff/new-epoch reopening and a
  content-addressed operator-unblock path, with ambiguous or corrupt state refusing closed.
- Closed S3-AKU-03 with a declared 3.0% MDE and 14 independent launches per arm (28 total), plus a
  session-unit bootstrap CI and a hard under-N refusal.
- Closed S3-AKU-10 with streaming retrospective metrics over four genuine stores and an explicit finding
  that historical rows cannot support the requested critic-cohort comparison because they lack pass-1 lineage.
- Closed AKX-P0a and AKX-P1a's zero-compute portions: per-workload census production and the static
  diff/compile-closure footprint producer now have their historical acceptance fixtures.
- Closed S3-AKU-08 as a design task. Its controls bind when the still-open U3-SEED knob-box proposer is
  implemented; the current deterministic one-factor enumerator contains no sampler or LLM override path.
- Closed AKX-P2a/P2b's zero-compute refusal logic: non-author workload regressions now use the interim
  unit-matched k_delta=1 floor (or a witnessed T0/T1 INERT row), and a failed aggregate now changes
  controller state and synchronously refuses instead of merely withholding LOO.
- Closed S3-AKU-12/S3-AKU-14 with observe-only stagnation and rejection-round telemetry; neither changes
  selection policy.
- Closed S3-AKU-02 as a documented decline: a compile-time “official” stamp is forgeable or forces a
  post-measurement rebuild, while the existing source/recipe/build/object/binary provenance chain preserves
  measured-artifact identity without conflating compilation with operator ratification.
- Added the AKX-P0c CPU/HIP coverage recipe variants without touching base recipe identities. Hardware
  build and W1/W4 executed-line acceptance remain open and are not represented as complete.
- Closed AKX-P2c with live serial ordering and early-refusal wiring. Review removed an accidental default
  receipt dependency: priority evidence is strict when explicitly enrolled, while existing scheduled
  campaigns retain their established order and still stop unconditionally after the first failed aggregate.
- Audited AKX-P3a/P3b and stopped a dead-code/high-impact edit: the live serial loop bypasses the offline
  ValidationConsumer, and the 18-call-site promotion manifest cannot yet bind composed census/footprint
  evidence or per-keep TOUCHED subsets. The prerequisite is a live durable freeze boundary, followed by a
  reviewed manifest schema migration; no disconnected gate was landed.
- Corrected the D3 capability statement: build flags are representable but both builds share sealed defines,
  so planner-selectable per-arm BUILD_RECIPE A/B is still missing. Added S3-AKU-19 for that implementation;
  source pragmas already use the SOURCE arm. AK-QL-8 remains a completed decision/specification row.

No index row, benchmark, production tree, or measurement authority was changed. The GLM loop was stopped
cleanly at a completed batch boundary before this hardening wave; its valid store and continuation remain intact.
