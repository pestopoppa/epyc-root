CAFE-4 pre-intervention provenance HIP build (R8)
===============================================

Row `df2-cafe4-modes-hip-build-r8-20261120` binds the generated candidate
SHA-256 `ef0c9a46421ad2c6414eab8dab316985b80b065315875ef9d118c7a4daf72260`
and header `0cbd694c9bf74495d1c76a700b5a43a4f1c0a5583a492eaa9740e030498540b2`
from root commit `02e42be05b32e6ebae4a01e69cd69232fe0267cf`.
Source diagnostics retain target hidden/logit and draft-logit fingerprints
before verification without changing token selection. R7 native UNKNOWN and
fixed native error tolerance **0.743863867** remain unchanged.

Scratch root: `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r8-20261120`.
The row reuses the existing detached v10 diagnostic tree without modifying it.
`inputs.json` binds all small build inputs by SHA-256. Smoke object and full
executable require `CAFE4_FLOAT_WITNESS` plus all R7 markers. Full qualification
retains exact defined IQK/HIP exports, six local libraries, HIP/gfx90a content,
Clang IQK compatibility and artifact/input/source bindings.

Validation: **17/17 model-free ELF-fixture tests PASS**, including rejection of
each witness marker in smoke and full-build modes. Shell syntax and pinned
input checks PASS. GitNexus status/impact unavailable in this unindexed lane;
direct inspection confines changes to the new runner and marker gate.

Stop on validated full receipt; futility on source mismatch, build/linkage
failure, STOP or deadline. This build-only row cannot establish native model
execution, rollback, fault sensitivity, GPU residency or performance.
File the full build receipt before publishing the hash-bound native diagnostic;
retain widths 2/3 normal rc0 and fault rc1, matched independent-trial controls,
live residency evidence and the fixed tolerance. Existing CAFE-4 source
registration and VB-SERVING-DF2 wiring task apply. Parent CAFE-4 stays open.

[no-belief: build qualification only; native cause unproven]

Publication smoke (2026-11-20)
------------------------------

Four-CPU smoke **PASS** on 116–119 at 11:40:07Z; clean STOP rc75.
Publisher validated the compiled object including `CAFE4_FLOAT_WITNESS`.
Original receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-hip-build-r8-20261120/PASS.json` has SHA-256 `fa5c2ae63243519d0f496f5d2677e038bad30c2f3666ebc0f17661257cd07893`.
Full HIP build and native controls remain pending.
