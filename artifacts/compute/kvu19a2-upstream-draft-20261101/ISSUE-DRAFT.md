# Draft: possible gfx90a flash-attention tile output instability for D=512/576

**Status: NOT READY TO FILE.** This is an issue draft, not a reproduced upstream defect. Do not send externally until the source-bound repeated-input experiment below has completed and its actual evidence is filled in. A candidate-only failure does not establish that the unmodified upstream kernel is nondeterministic.

## Observed historical report

A 2026-10-03 local fold record reports that placing a branch in the KV loop of a D=512/576 GQA tile kernel changed gfx90a outputs between runs (roughly 1e-4 NMSE), including with mask skipping disabled. The retained evidence does not bind that historical observation to a particular binary, input or environment; these statements are the original author's report, not a confirmed independent reproduction. The existing upstream masked-skip issue #28495 is not established as this separate issue.

## Candidate cases and source

The retained harness identifies three candidate cases, each f16 with 8192 KV cells and four sequences: case 78 has 576/512 head dimensions, one KV head, 16 query heads and 4 rows; case 79 has the same dimensions and heads with 256 rows; case 80 has 512/512, one KV head, eight query heads and four rows. Confirm the exact case definitions and runtime dispatch before presenting any as a reproducer.

A prospective candidate can be reconstructed on commit `a0d0ae238e714aaab04e973ef4b5a4b7c9917744` using the preserved companion patch; neither its build compatibility nor its identity with the historical binary is established. The baseline, patch and relevant files are preserved in `../kvu19a2-companion-20261101/` and `../kvu19a2-candidate-20261101/`. Do not alter the frozen production tree.

## Evidence required before filing

1. Source-bound isolated baseline and candidate builds, with full commits/patches, toolchain and configure commands, binary and dynamically loaded library digests, and live gfx90a residency evidence.
2. The same captured Q/K/V/mask tensor bytes in every run, and complete captured output bytes. Execute five independently launched repetitions per case and binary in ABBAABBAAB order with skip disabled; preserve per-run status and cleanup evidence. Treat any missing identity, input, residency or output as incomplete.
3. Report within-binary comparisons per case and actual NMSE/nonfinite values. A differing pair under identical verified conditions establishes observed output nondeterminism only for that binary/case; five matches mean no difference observed at n=5. Cross-binary difference alone is not nondeterminism.
4. Provide exact standalone reproduction commands, expected versus observed output, compiler and ROCm versions, device, source revisions, minimized source patch and attached native results. State explicitly whether the baseline or only the modified candidate exhibits a difference; do not assert root cause without evidence.

Detailed protocol and qualification requirements: `../kvu19a2-repro-plan-20261101/README.md`. Historical evidence and its limitations: `../kvu19a2-evidence-20261101/README.md`. No compute, GPU measurement or external message was performed to create this draft.
