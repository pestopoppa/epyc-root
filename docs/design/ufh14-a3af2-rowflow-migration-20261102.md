# UFH14-A3A-F2 rowflow migration

The prospective four-leg ABBA diagnostic and source seal are in
`/mnt/raid0/llm/tmp/codex-ni-next-gpu-backlog-prep-20261031/`, especially
`PREDECLARED.md` and `SOURCES.sha256`. The 2026-10-31 smoke timed out before
it ran; there is no F2 measurement or qualification.

The original `launch.sh` cannot be submitted unchanged: it pins
`filler_run13.sh`, whereas rowflow requires `filler_run15.sh`; it also uses
`env -i`, which drops the `FILLER_DRYRUN*` variables supplied by the keeper.
The normal F2 result is emitted only after all four legs, while qualification
requires a measured output unit before its timeout. The normal completion
check validates the four-leg result and must remain the full-run gate.

Prepare a fresh scratch packet, preserving the original packet and declaring
any changes to the seal. Port its launcher to the canonical rowflow engine,
ensure keeper-provided grant, region and dry-run settings survive the launcher,
and retain the GPU plus q3 exclusivity and CPU claims in the predeclaration.
Implement a bounded native small-model qualification path that writes an
actual measured unit to `FILLER_DRYRUN_RESULT_PATH` when that path is supplied;
keep that output separate from the full F2 result and never interpret the smoke
as F2 evidence. Ensure the stop path drains captured children. The full job must
retain the original ABBA ordering, quiet-sampling criteria, full-result
completion checks and fresh-attempt isolation. Validate source seal, shell
syntax and offline controls before publishing a spec with
`dryrun_native_result: true`; the keeper alone qualifies and runs it. Declare
the full result path and descriptive decision rule in the spec.

The original resource declaration is `mi210_0,184-191`, an additional q3
claim on CPUs 72–95 with GPU quiet exclusive, 64 GiB and a 6000 s minimum
window. Confirm that the current keeper and engine can reserve all those
resources together before publication; do not silently weaken quiet sampling.
