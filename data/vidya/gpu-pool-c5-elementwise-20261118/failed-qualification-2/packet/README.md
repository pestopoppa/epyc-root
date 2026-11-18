# C5 prospective elementwise comparison

Three native invocations select the 17 exact descriptions unsupported in the original c463 single-seed capture, seed 2026102603. C5 outcomes are not assumed: supported, unsupported, failures and missing descriptions are preserved. Any missing description is a coverage gap. Evidence is candidate-local and model-free.

The C5 executable and HIP DSO match the stated manifest hashes; the other copied DSOs are separately pinned. The source snapshot is the git object at the C5 commit, not proof of a clean build tree; build dirty state remains unknown. The separately pinned shim is the same as the earlier packet; its source provenance is explicitly limited in the capture identity. All native execution requires the rowflow GPU grant.

Each operator additionally selects one original supported control in the same process, documented in control-plan.tsv. Controls are tagged separately and must pass; they provide an opportunity for the unchanged two positive-VRAM residency witnesses. Target outcomes and control outcomes are reported separately.
