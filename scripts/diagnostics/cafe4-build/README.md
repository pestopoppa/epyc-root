CAFE-4 modes CPU build row
=========================

Row `df2-cafe4-modes-cpu-build-20261119` is published with four-CPU smoke PASS
on 2026-11-19 (cores 116–119, compiled-object first progress, clean STOP rc75).
Smoke receipt: `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-cpu-build-20261119/PASS.json`; SHA-256 `981e73bd926227d18dbdbe47bab5580211901c2a359ce642e5dc3daefed36f77`.
This qualifies the row for scheduling; the full executable build is pending.
No model was loaded and no rollback, GPU residency, fault-sensitivity or
performance claim follows from this smoke.

The build driver binds production v10 commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` plus diagnostic patch SHA-256
`351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd`.
Only the detached experimental tree `/mnt/raid0/llm/tmp/df2/cafe4-modes-source`
is built; production stays frozen. The patch is tracked at
`docs/reports/cafe4-rollback-preparation/geometry-frozen-build-20261104/source.patch`.

The candidate is generated with `scripts/diagnostics/cafe4_port.py`, from blob
`53035f75429327e82454f7d26f7dd67f65c80c16`; expected generated SHA-256
`71ce1fb3e92098dfb586b06000a0ed4dee1e836c7c889774cb754dcde8f1b597`.
Modes header blob `e7ffe36faf2fa8c318beb45c82b54b5d6d4db3ec`, at
`scripts/diagnostics/cafe4_modes.hpp`, has SHA-256
`3c9a64da0682769184a671212b94e434a4ef56723e139c40238f6a8259fb9538`.
The existing bridge is referenced from
`docs/reports/cafe4-rollback-preparation/draft-rewind-v4-20261104/mtp_draft_bridge.hpp`
(SHA-256 `9688a97c3ad30e5aa008650d29a7b4d463109220b7dc48a136f9324aa2cf3919`).
STOP supervision uses the existing bounded supervisor in
`/mnt/raid0/llm/tmp/df2/cafe4-mtp-rollback-rewind-v4/supervise.py`
(SHA-256 `ab378fc8bd635da299c0dbe7371cfc8d42842c864473755d905fbaa9931871c2`).
Small runtime inputs live under `/mnt/raid0/llm/tmp/df2/cafe4-modes-20261119` and are individually hash-bound
in `inputs.json`; no source tree or evidence is copied into this document.

`driver.py` compiles the candidate object during smoke and requires all MTP
load/rollback/rewind and verify-batch/fault-control strings. During the scheduled
full CPU build it also records executable/library hashes and requires every
llama/ggml library to resolve within that run's build directory. The result is
`/mnt/raid0/llm/tmp/df2/cafe4-modes-20261119/RESULT.json`. Stop on source mismatch, missing compiled markers,
build/linkage failure, deadline or STOP; stop on answer once the full build
receipt validates. The environment passed to ldd inherits FILLER_ID through
`dict(os.environ, ...)`; publish's environment-cleaning warning is a static
false positive.

Next: separately qualify a HIP-enabled modes build, then schedule CPU/GPU native
controls with the original numerical rule and exact rc1 injected-fault witness.
The parent CAFE-4 remains open; this row does not satisfy its native criteria.

Full CPU build verdict (2026-11-19)
----------------------------------

`df2-cafe4-modes-cpu-build-20261119` ended rc0 at 04:14:43Z; **PASS**
under its build-only decision rule. `driver.py check` passed input/source binding,
all recorded artifact hashes, six compiled load/rollback/rewind/mode/fault markers,
and local resolution of all five required llama/ggml libraries.
Executable SHA-256: `864bd4492e370112a5c273754b943f8f7bbe50543d76ec1bed284fdd2c600959`.
Native receipt: `/mnt/raid0/llm/tmp/df2/cafe4-modes-20261119/RESULT.json`; SHA-256 `8f6ed5697fa21c4bfafc1ff2903307455c26bfc13429299236e3340ae7d1b1bd`.
The receipt names and hashes the existing configure/build/linkage logs and libraries;
no artifacts are duplicated here. Native rollback and exact rc1 fault controls
remain unmeasured by this build, so CAFE-4 remains open.
