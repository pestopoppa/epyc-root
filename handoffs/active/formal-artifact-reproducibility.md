# Formal Artifact Reproducibility

**Status**: stub
**Created**: 2026-09-25 (via research intake, operator-approved Stage 3 plan)
**Categories**: formal_verification, benchmark_methodology, reproducibility
**Tracked in**: `research-evaluation-index.md` EVL-51

## Objective

Independently rebuild externally published formal proof artifacts and preserve enough source, toolchain, dependency, transcript, axiom, and trust-boundary evidence to distinguish a successful build from the mathematical scope of the checked theorem.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|---|---|---|---|---|
| intake-1667#record | Settling the Optimal Exponent Relating Sumsets and Difference Sets | high | adopt_patterns | dive-verified |
| intake-1690#record | Lean formalization of the optimal sum/difference exponent | high | adopt_component | dive-verified |

## Open Tasks

- [ ] **FAR-1 — Independently rebuild the pinned Lean artifact in an isolated allowed workspace.** Pin repository commit, `lean-toolchain`, mathlib revision, dependency lock, runner identity, and commands; archive source/output hashes and complete `lake build` plus `CheckAxioms` or equivalent output. Record all `native_decide` uses and keep build success separate from theorem generalization or benchmark performance. Source: intake-1690#record.
- [ ] **FAR-2 — Emit the VB-FORMAL-1 producer receipt during FAR-1.** A clean reader must reproduce source identity, build result, axiom footprint, and trust-boundary classification from retained artifacts without reconstructing missing provenance.

## Open Questions

- Does the pinned repository build from its declared lock and toolchain without an author cache?
- Which theorem statements depend on `native_decide`, and which axioms appear in the final checked declarations?
- Does the repository certify only `sum_difference_C`, or any additional metric family?

## Notes

The completed `lean-proving-pipeline.md` is historical and cannot own new work. This stub verifies a published artifact; it does not reopen model-serving or Goedel-Prover deployment work.
